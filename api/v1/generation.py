from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from services.ai import get_ai_generator
from api.v1.users import get_current_user
from database import get_db
from models.user import User
from models.drawing import Drawing
from api.v1.credits import deduct_credits, add_credits

router = APIRouter(prefix="/generation")

class GenerateRequest(BaseModel):
    """图像生成请求模型

    Requirements: 4.2 - 生成任务包含所有必要参数
    """
    prompt: str = Field(..., description="正面提示词")
    negative_prompt: Optional[str] = Field("", description="负面提示词")
    backend: str = Field("comfyui", description="后端类型: 'comfyui' 或 'external'")
    width: Optional[int] = Field(512, ge=64, le=2048, description="图像宽度")
    height: Optional[int] = Field(512, ge=64, le=2048, description="图像高度")
    seed: Optional[int] = Field(-1, description="随机种子，-1 表示随机")
    model_name: Optional[str] = Field(None, description="模型名称")
    cfg: Optional[float] = Field(7.0, ge=1.0, le=30.0, description="CFG Scale")
    steps: Optional[int] = Field(20, ge=1, le=150, description="采样步数")
    sampler: Optional[str] = Field("euler", description="采样器名称")
    scheduler: Optional[str] = Field("normal", description="调度器名称")
    # 自定义配置参数
    comfyui_host: Optional[str] = Field(None, description="用户自定义的 ComfyUI 地址")
    api_key: Optional[str] = Field(None, description="用户自定义的 External API Key")
    api_url: Optional[str] = Field(None, description="用户自定义的 External API URL")

@router.post("/draw")
async def generate_image(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """触发 AI 绘图任务。需消耗积分。

    Requirements: 4.1, 4.2 - 创建并发送包含所有参数的生成任务
    """
    try:
        # 扣除积分 logic
        # 如果用户使用了自定义的 ComfyUI 地址或 API Key，也许可以不扣分？
        # 暂时策略：统一扣除 2 积分
        cost = 2

        # 特殊情况：如果用户完全使用自定义后端资源（如本地ComfyUI），可以免费
        # if req.comfyui_host or (req.backend == 'external' and req.api_key):
        #     cost = 0

        if cost > 0:
            try:
                deduct_credits(current_user.id, cost, "generation_cost", "AI 绘图消耗", db)
            except ValueError as e:
                raise HTTPException(status_code=402, detail=str(e)) # 402 Payment Required

        generator = get_ai_generator(req.backend)

        # 构建生成参数
        params = {
            "width": req.width,
            "height": req.height,
            "seed": req.seed if req.seed is not None else -1,
            "model_name": req.model_name,
            "cfg": req.cfg,
            "steps": req.steps,
            "sampler": req.sampler,
            "scheduler": req.scheduler,
        }

        # 注入自定义配置
        if req.comfyui_host:
            params['server_address'] = req.comfyui_host
        if req.api_key:
            params['api_key'] = req.api_key
        if req.api_url:
            params['api_url'] = req.api_url

        try:
            result = await generator.generate_image(req.prompt, req.negative_prompt, params)

            # 如果是异步任务（queued），保存初始记录到数据库
            if result.get("status") == "queued":
                prompt_id = result.get("prompt_id")
                if prompt_id:
                    new_drawing = Drawing(
                        user_id=current_user.id,
                        prompt=req.prompt,
                        negative_prompt=req.negative_prompt,
                        model_name=req.model_name or "default",
                        width=req.width,
                        height=req.height,
                        seed=str(result.get("seed")),
                        status="queued",
                        prompt_id=prompt_id,
                        is_public=False
                    )
                    db.add(new_drawing)
                    db.commit()

            return {"code": 200, "msg": "OK", "data": result}
        except Exception as gen_err:
            # 生成失败，退还积分
            if cost > 0:
                add_credits(current_user.id, cost, "refund", "生成失败退款", db)
            raise gen_err

    except ValueError as e:
        raise HTTPException(status_code=400, detail={"message": str(e), "error_code": "VALIDATION_ERROR"})
    except Exception as e:
        # 提供更详细的错误信息
        error_msg = str(e)
        error_detail = {
            "message": error_msg,
            "error_code": "INTERNAL_ERROR"
        }

        # 检测特定错误类型
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            error_detail["error_code"] = "CONNECTION_ERROR"
        elif "timeout" in error_msg.lower():
            error_detail["error_code"] = "TIMEOUT_ERROR"
        elif "memory" in error_msg.lower() or "cuda" in error_msg.lower():
            error_detail["error_code"] = "OUT_OF_MEMORY"

        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/status/{backend}/{task_id}")
async def check_generation_status(
    backend: str,
    task_id: str,
    comfyui_host: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """检查绘图任务状态（针对异步后端如 ComfyUI）。

    Args:
        backend: 后端类型 (comfyui/external)
        task_id: 任务 ID (prompt_id)
        comfyui_host: 可选，用户自定义的 ComfyUI 地址
    """
    try:
        generator = get_ai_generator(backend)
        params = {}
        if comfyui_host:
            params['server_address'] = comfyui_host

        result = await generator.check_status(task_id, params=params)

        # 如果任务完成，更新数据库状态
        if result.get("status") == "completed":
            drawing = db.query(Drawing).filter(Drawing.prompt_id == task_id).first()
            if drawing:
                # 只有当状态不是 finish 时才更新，避免重复写入
                if drawing.status != "finish":
                    drawing.status = "finish"
                    images = result.get("images", [])
                    if images:
                        # 暂时只取第一张
                        drawing.image_url = images[0]
                    db.commit()

        return {"code": 200, "msg": "OK", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{backend}/{task_id}")
async def cancel_generation(
    backend: str,
    task_id: str,
    comfyui_host: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消正在进行的生成任务。

    Args:
        backend: 后端类型 (comfyui/external)
        task_id: 任务 ID (prompt_id)
        comfyui_host: 可选，用户自定义的 ComfyUI 地址

    Requirements: 4.6 - 支持取消正在进行的生成任务
    """
    try:
        generator = get_ai_generator(backend)

        # 检查任务是否属于当前用户
        drawing = db.query(Drawing).filter(
            Drawing.prompt_id == task_id,
            Drawing.user_id == current_user.id
        ).first()

        if not drawing:
            raise HTTPException(status_code=404, detail="任务不存在或无权限取消")

        # 只有在队列中或正在生成的任务才能取消
        if drawing.status not in ["queued", "generating", "processing"]:
            raise HTTPException(status_code=400, detail="任务已完成或已取消，无法再次取消")

        # 调用取消方法
        if hasattr(generator, 'cancel_task'):
            params = {}
            if comfyui_host:
                params['server_address'] = comfyui_host
            result = await generator.cancel_task(task_id, server_address=comfyui_host)
        else:
            result = {"status": "cancelled", "message": "Task marked as cancelled"}

        # 更新数据库状态
        drawing.status = "cancelled"
        db.commit()

        # 退还积分
        add_credits(current_user.id, 2, "refund", "取消生成退款", db)

        return {"code": 200, "msg": "OK", "data": result}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/{backend}")
async def get_queue_status(
    backend: str,
    comfyui_host: Optional[str] = None
):
    """获取生成队列状态。

    Args:
        backend: 后端类型 (comfyui/external)
        comfyui_host: 可选，用户自定义的 ComfyUI 地址

    Requirements: 4.4 - 显示生成进度和状态更新
    """
    try:
        generator = get_ai_generator(backend)

        if hasattr(generator, 'get_queue'):
            result = await generator.get_queue(server_address=comfyui_host)
            return {"code": 200, "msg": "OK", "data": result}
        else:
            return {"code": 200, "msg": "OK", "data": {"queue_running": [], "queue_pending": []}}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{backend}")
async def get_available_models(
    backend: str,
    comfyui_host: Optional[str] = None
):
    """获取可用的模型列表。

    Args:
        backend: 后端类型 (comfyui/external)
        comfyui_host: 可选，用户自定义的 ComfyUI 地址

    Returns:
        可用模型列表，包括 checkpoints、VAE、samplers 等
    """
    try:
        if backend != "comfyui":
            return {"code": 200, "msg": "OK", "data": {"checkpoints": []}}

        # 使用 ComfyUI 客户端获取模型信息
        from services.comfyui.client import ComfyUIClient
        from core.comfyui_config import get_comfyui_settings
        import httpx

        settings = get_comfyui_settings()

        # 确定使用的地址
        if comfyui_host:
            # 用户自定义地址，直接使用
            target_url = f"http://{comfyui_host}"
        else:
            # 使用配置的地址
            target_url = settings.base_url

        # 获取模型信息
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{target_url}/object_info")
            resp.raise_for_status()
            object_info = resp.json()

        # 解析模型信息
        models = {}

        # Checkpoints
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                ckpt_name = checkpoint_info["input"]["required"].get("ckpt_name")
                if ckpt_name and isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                    models["checkpoints"] = ckpt_name[0] if isinstance(ckpt_name[0], list) else []

        return {"code": 200, "msg": "OK", "data": models}

    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"无法连接到 ComfyUI 服务 ({target_url if 'target_url' in locals() else 'unknown'})。请检查 ComfyUI 是否正在运行。",
                "error_code": "CONNECTION_ERROR"
            }
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail={
                "message": f"ComfyUI 返回错误: {e.response.status_code}",
                "error_code": "HTTP_ERROR"
            }
        )
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"获取模型列表失败: {error_msg}",
                "error_code": "INTERNAL_ERROR"
            }
        )


@router.get("/comfyui/info")
async def get_comfyui_info(
    comfyui_host: Optional[str] = None
):
    """获取 ComfyUI 服务器信息和配置。

    Args:
        comfyui_host: 可选，用户自定义的 ComfyUI 地址

    Returns:
        ComfyUI 服务器信息，包括系统状态、模型路径等
    """
    try:
        from core.comfyui_config import get_comfyui_settings
        import httpx

        settings = get_comfyui_settings()

        # 确定使用的地址
        if comfyui_host:
            # 用户自定义地址，直接使用
            target_url = f"http://{comfyui_host}"
        else:
            # 使用配置的地址
            target_url = settings.base_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 获取系统状态
            system_resp = await client.get(f"{target_url}/system_stats")
            system_resp.raise_for_status()
            system_stats = system_resp.json()

            # 获取对象信息（包含模型路径信息）
            object_resp = await client.get(f"{target_url}/object_info")
            object_resp.raise_for_status()
            object_info = object_resp.json()

            # 提取模型数量
            model_counts = {}
            if "CheckpointLoaderSimple" in object_info:
                checkpoint_info = object_info["CheckpointLoaderSimple"]
                if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                    ckpt_name = checkpoint_info["input"]["required"].get("ckpt_name")
                    if ckpt_name and isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                        checkpoints = ckpt_name[0] if isinstance(ckpt_name[0], list) else []
                        model_counts["checkpoints"] = len(checkpoints)

            return {
                "code": 200,
                "msg": "OK",
                "data": {
                    "host": target_url,
                    "system_stats": system_stats,
                    "model_counts": model_counts,
                    "status": "connected"
                }
            }

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail={
                "message": f"无法连接到 ComfyUI 服务 ({target_url if 'target_url' in locals() else 'unknown'})。请检查 ComfyUI 是否正在运行。",
                "error_code": "CONNECTION_ERROR"
            }
        )
    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"获取 ComfyUI 信息失败: {error_msg}",
                "error_code": "INTERNAL_ERROR"
            }
        )
