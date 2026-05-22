from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from services.ai import get_ai_generator
from api.v1.users import get_current_user
from database import get_db
from models.user import User
from models.drawing import Drawing
from models.prompt_log import PromptLog
from models.prompt_keyword import PromptKeyword
from models.user_prompt_keyword import UserPromptKeyword
from api.v1.credits import deduct_credits, add_credits
from services.cos import COSStorageService, ImageProcessor, StorageManager
from core.logger import get_logger
from utils.http_client import SafeHTTPClient, ConnectionError, TimeoutError, HTTPError
import os
import tempfile
import base64
from datetime import datetime

logger = get_logger(__name__)
router = APIRouter(prefix="/generation")

class TestConnectionRequest(BaseModel):
    """测试连接请求模型"""
    provider: str = Field(..., description="API 提供商 ID")
    api_key: Optional[str] = Field(None, description="API Key (自定义提供商必需)")
    api_url: Optional[str] = Field(None, description="可选，自定义 API URL")
    secret_key: Optional[str] = Field(None, description="可选，Secret Key (百度等需要)")

class PromptKeywordUsage(BaseModel):
    """提示词使用记录"""
    keyword_id: int = Field(..., description="关键词ID")
    weight: float = Field(1.0, description="权重")
    is_negative: bool = Field(False, description="是否负面提示词")
    category_id: int = Field(..., description="小分类ID")

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
    # 外部 API 专用参数
    provider: Optional[str] = Field("openai", description="外部 API 提供商: openai, tongyi, baidu, deepseek, custom")
    secret_key: Optional[str] = Field(None, description="API Secret Key (百度等需要)")
    # 提示词关键词ID列表（用于统计）
    positive_keywords: Optional[List[PromptKeywordUsage]] = Field(default=[], description="正面提示词关键词列表")
    negative_keywords: Optional[List[PromptKeywordUsage]] = Field(default=[], description="负面提示词关键词列表")

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

        # 外部 API 专用参数
        if req.backend == "external":
            from services.ai.providers_config import get_provider_config

            provider = req.provider or "openai"
            params['provider'] = provider

            # 如果是自定义提供商，使用用户提供的配置
            if provider == "custom":
                if req.api_key:
                    params['api_key'] = req.api_key
                if req.api_url:
                    params['api_url'] = req.api_url
                if req.secret_key:
                    params['secret_key'] = req.secret_key
            else:
                # 预设提供商，从环境变量读取配置
                config = get_provider_config(provider)
                if config and config.is_configured:
                    params['api_key'] = config.api_key
                    if config.api_url:
                        params['api_url'] = config.api_url
                    if config.secret_key:
                        params['secret_key'] = config.secret_key

        try:
            logger.info(f"Starting generation with backend: {req.backend}")
            logger.info(f"Generation params: {params}")
            result = await generator.generate_image(req.prompt, req.negative_prompt, params)
            logger.info(f"Generation result: {result}")

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
                    # 记录提示词使用日志
                    log_prompt_usage(new_drawing.id, req.positive_keywords, req.negative_keywords, current_user.id, db)

            # 如果是同步完成的任务（completed），立即保存到数据库并上传到 COS
            elif result.get("status") == "completed":
                images = result.get("images", [])
                if images:
                    image_url = images[0]

                    # 创建 Drawing 记录
                    new_drawing = Drawing(
                        user_id=current_user.id,
                        prompt=req.prompt,
                        negative_prompt=req.negative_prompt,
                        model_name=req.model_name or "default",
                        width=req.width,
                        height=req.height,
                        seed=str(result.get("seed", -1)),
                        status="finish",
                        image_url=image_url,
                        is_public=False
                    )
                    db.add(new_drawing)
                    db.commit()
                    db.refresh(new_drawing)

                    # 记录提示词使用日志
                    log_prompt_usage(new_drawing.id, req.positive_keywords, req.negative_keywords, current_user.id, db)

                    # 尝试上传到 COS
                    try:
                        await upload_image_to_cos(new_drawing, image_url, db)
                        logger.info(f"Successfully uploaded drawing {new_drawing.id} to COS")

                        # 更新返回结果，使用 COS URL
                        result["images"] = [new_drawing.image_url]
                        result["thumbnail_url"] = new_drawing.thumbnail_url
                        result["drawing_id"] = new_drawing.id
                    except Exception as e:
                        logger.error(f"Failed to upload to COS, but generation succeeded: {e}")
                        # COS 上传失败不影响生成结果，但记录原始 URL
                        result["drawing_id"] = new_drawing.id

            return {"code": 200, "msg": "OK", "data": result}
        except Exception as gen_err:
            # 生成失败，退还积分
            logger.error(f"Generation failed with error: {gen_err}")
            logger.error(f"Error type: {type(gen_err)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """检查绘图任务状态（针对异步后端如 ComfyUI 和部分外部 API）。

    Args:
        backend: 后端类型 (comfyui/external)
        task_id: 任务 ID (prompt_id)
        comfyui_host: 可选，用户自定义的 ComfyUI 地址
        provider: 可选，外部 API 提供商
        api_key: 可选，用户自定义的 API Key
        api_url: 可选，用户自定义的 API URL
    """
    try:
        # 首先检查数据库中的任务状态
        drawing = db.query(Drawing).filter(Drawing.prompt_id == task_id).first()

        # 如果数据库中已经标记为完成，直接返回数据库结果，避免重复查询
        if drawing and drawing.status == "finish":
            logger.debug(f"Drawing {drawing.id} already finished, returning from database cache")
            return {
                "code": 200,
                "msg": "OK",
                "data": {
                    "status": "completed",
                    "images": [drawing.image_url] if drawing.image_url else [],
                    "thumbnail_url": drawing.thumbnail_url,
                    "drawing_id": drawing.id,
                    "prompt_id": task_id
                }
            }

        # 否则，查询对应的后端获取最新状态
        generator = get_ai_generator(backend)
        params = {}
        if comfyui_host:
            params['server_address'] = comfyui_host
        if provider:
            params['provider'] = provider
        if api_key:
            params['api_key'] = api_key
        if api_url:
            params['api_url'] = api_url

        result = await generator.check_status(task_id, params=params)

        # 如果任务完成，更新数据库状态并上传到 COS
        if result.get("status") == "completed":
            if drawing and drawing.status != "finish":
                images = result.get("images", [])
                if images:
                    # 获取第一张图片 URL
                    image_url = images[0]
                    drawing.image_url = image_url

                    # 尝试上传到 COS
                    try:
                        await upload_image_to_cos(drawing, image_url, db)
                        logger.info(f"Successfully uploaded drawing {drawing.id} to COS")
                    except Exception as e:
                        logger.error(f"Failed to upload to COS, but generation succeeded: {e}")
                        # COS 上传失败不影响生成结果

                    drawing.status = "finish"
                    db.commit()
                    db.refresh(drawing)

                    # 更新返回结果，使用 COS URL 而不是原始 URL
                    result["images"] = [drawing.image_url]
                    result["thumbnail_url"] = drawing.thumbnail_url
                    result["drawing_id"] = drawing.id
                    logger.info(f"Drawing {drawing.id} status updated to finish, returning COS URLs")

        return {"code": 200, "msg": "OK", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def log_prompt_usage(drawing_id: int, positive_keywords: List[PromptKeywordUsage], negative_keywords: List[PromptKeywordUsage], user_id: int, db: Session):
    """记录提示词使用日志并更新用户统计

    Args:
        drawing_id: Drawing记录ID
        positive_keywords: 正面提示词列表
        negative_keywords: 负面提示词列表
        user_id: 用户ID
        db: 数据库会话
    """
    # 合并正负面提示词
    all_keywords = []
    if positive_keywords:
        for kw in positive_keywords:
            all_keywords.append({
                "keyword_id": kw.keyword_id,
                "weight": kw.weight,
                "is_negative": False,
                "category_id": kw.category_id
            })
    if negative_keywords:
        for kw in negative_keywords:
            all_keywords.append({
                "keyword_id": kw.keyword_id,
                "weight": kw.weight,
                "is_negative": True,
                "category_id": kw.category_id
            })

    if not all_keywords:
        logger.debug(f"No keywords to log for drawing {drawing_id}")
        return

    for kw_data in all_keywords:
        keyword_id = kw_data["keyword_id"]
        weight = kw_data["weight"]
        is_negative = kw_data["is_negative"]
        category_id = kw_data["category_id"]

        # 1. 创建 PromptLog 记录
        prompt_log = PromptLog(
            user_id=user_id,
            prompt_id=keyword_id,
            drawing_id=drawing_id,
            small_category_id=category_id,
            weight=weight,
            is_negative=is_negative
        )
        db.add(prompt_log)

        # 2. 更新 UserPromptKeyword 的 generated_count
        user_keyword = db.query(UserPromptKeyword).filter(
            UserPromptKeyword.user_id == user_id,
            UserPromptKeyword.keyword_id == keyword_id
        ).first()

        if user_keyword:
            user_keyword.generated_count = (user_keyword.generated_count or 0) + 1
            user_keyword.last_generated_at = datetime.now()
        else:
            # 如果不存在记录，创建新记录
            new_user_keyword = UserPromptKeyword(
                user_id=user_id,
                keyword_id=keyword_id,
                used_count=0,
                generated_count=1,
                last_used_at=datetime.now(),
                first_used_at=datetime.now(),
                last_generated_at=datetime.now(),
                first_generated_at=datetime.now()
            )
            db.add(new_user_keyword)

    db.commit()
    logger.info(f"Logged {len(all_keywords)} keyword usage for drawing {drawing_id}")


async def upload_image_to_cos(drawing: Drawing, image_url: str, db: Session):
    """上传图片到 COS

    Args:
        drawing: Drawing 模型实例
        image_url: 图片 URL 或 Base64 编码的图片
        db: 数据库会话
    """
    cos_service = COSStorageService()
    image_processor = ImageProcessor()

    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    local_path = None
    thumbnail_path = None

    try:
        # 1. 下载图片到本地临时文件
        local_path = os.path.join(temp_dir, f"drawing_{drawing.id}_{timestamp}.png")

        # 处理不同类型的图片源
        if image_url.startswith("data:image"):
            # Base64 编码的图片
            logger.info(f"Processing Base64 image for drawing {drawing.id}")
            try:
                # 提取 Base64 数据
                base64_data = image_url.split(",")[1] if "," in image_url else image_url
                image_data = base64.b64decode(base64_data)

                # 保存到临时文件
                with open(local_path, 'wb') as f:
                    f.write(image_data)
                logger.info(f"Base64 image decoded and saved to {local_path}")
            except Exception as e:
                logger.error(f"Failed to decode Base64 image: {e}")
                raise ValueError(f"Base64 图片解码失败: {e}")

        elif image_url.startswith("http://") or image_url.startswith("https://"):
            # HTTP URL，下载图片
            logger.info(f"Downloading image from URL for drawing {drawing.id}: {image_url}")
            await image_processor.download_image(image_url, local_path)

        else:
            # 本地文件路径，直接复制
            logger.info(f"Copying local file for drawing {drawing.id}: {image_url}")
            import shutil
            if os.path.exists(image_url):
                shutil.copy(image_url, local_path)
            else:
                raise FileNotFoundError(f"本地文件不存在: {image_url}")

        # 2. 生成缩略图
        logger.info(f"Generating thumbnail for drawing {drawing.id}")
        thumbnail_data = image_processor.generate_thumbnail(local_path)
        thumbnail_path = os.path.join(temp_dir, f"drawing_{drawing.id}_{timestamp}_thumb.png")
        with open(thumbnail_path, 'wb') as f:
            f.write(thumbnail_data)

        # 3. 上传原图到 COS
        logger.info(f"Uploading original image to COS for drawing {drawing.id}")
        original_result = await cos_service.upload_image(
            local_path,
            drawing.user_id,
            drawing.id,
            is_thumbnail=False
        )

        # 4. 上传缩略图到 COS
        logger.info(f"Uploading thumbnail to COS for drawing {drawing.id}")
        thumbnail_result = await cos_service.upload_image(
            thumbnail_path,
            drawing.user_id,
            drawing.id,
            is_thumbnail=True
        )

        # 5. 更新数据库记录
        drawing.image_url = original_result["cos_url"]
        drawing.cos_key = original_result["cos_key"]
        drawing.thumbnail_url = thumbnail_result["cos_url"]
        drawing.thumbnail_key = thumbnail_result["cos_key"]
        drawing.file_size = original_result["file_size"]

        # 6. 更新用户存储统计
        StorageManager.update_user_storage(
            drawing.user_id,
            original_result["file_size"],
            db
        )

        logger.info(f"Successfully uploaded drawing {drawing.id} to COS")

    except Exception as e:
        logger.error(f"Failed to upload drawing {drawing.id} to COS: {e}")
        raise

    finally:
        # 7. 清理本地临时文件
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.debug(f"Removed temp file: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {local_path}: {e}")

        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
                logger.debug(f"Removed temp file: {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temp file {thumbnail_path}: {e}")



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
        logger.info(f"Getting models for backend: {backend}, custom host: {comfyui_host}")

        if backend != "comfyui":
            return {"code": 200, "msg": "OK", "data": {"checkpoints": []}}

        # 使用 ComfyUI 客户端获取模型信息
        from services.comfyui.client import ComfyUIClient
        from core.comfyui_config import get_comfyui_settings

        settings = get_comfyui_settings()
        logger.info(f"ComfyUI settings loaded: {settings.base_url}")

        # 确定使用的地址
        if comfyui_host:
            # 用户自定义地址，直接使用
            target_url = f"http://{comfyui_host}"
            logger.info(f"Using custom ComfyUI host: {target_url}")
        else:
            # 使用配置的地址
            target_url = settings.base_url
            logger.info(f"Using configured ComfyUI host: {target_url}")

        # 获取模型信息
        logger.info(f"Fetching models from: {target_url}/object_info")

        try:
            http_client = SafeHTTPClient(timeout=30.0)
            resp = await http_client.get(f"{target_url}/object_info")
            object_info = resp.json()
        except ConnectionError as e:
            error_code = "CONNECTION_ERROR"
            error_msg = f"无法连接到 ComfyUI 服务 ({target_url})。请检查 ComfyUI 是否正在运行。"
            raise HTTPException(
                status_code=503,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )
        except TimeoutError as e:
            error_code = "TIMEOUT_ERROR"
            error_msg = f"连接 ComfyUI 超时。请检查服务器状态。"
            raise HTTPException(
                status_code=504,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )
        except HTTPError as e:
            if e.status_code in [502, 503]:
                error_code = "SERVICE_UNAVAILABLE"
                error_msg = f"ComfyUI 服务不可用。请检查 ComfyUI 是否正在运行。"
            else:
                error_code = "HTTP_ERROR"
                error_msg = f"HTTP {e.status_code} 错误"
            raise HTTPException(
                status_code=e.status_code or 500,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )

        logger.info(f"Successfully fetched object_info, parsing models...")

        # 解析模型信息
        models = {}

        # Checkpoints
        if "CheckpointLoaderSimple" in object_info:
            checkpoint_info = object_info["CheckpointLoaderSimple"]
            if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                ckpt_name = checkpoint_info["input"]["required"].get("ckpt_name")
                if ckpt_name and isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                    models["checkpoints"] = ckpt_name[0] if isinstance(ckpt_name[0], list) else []

        logger.info(f"Successfully parsed {len(models.get('checkpoints', []))} checkpoints")
        return {"code": 200, "msg": "OK", "data": models}

    except (ConnectionError, TimeoutError, HTTPError):
        # 这些异常已经在上面处理过了，直接重新抛出
        raise
    except Exception as e:
        error_msg = str(e)
        error_code = "INTERNAL_ERROR"

        logger.error(f"Unexpected error in get_available_models: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"获取模型列表失败: {error_msg}",
                "error_code": error_code
            }
        )


@router.get("/providers")
async def get_external_providers():
    """获取支持的外部 API 提供商列表。

    Returns:
        支持的外部 AI 服务提供商信息
    """
    from services.ai.providers_config import load_provider_configs

    configs = load_provider_configs()

    providers = []
    for provider_id, config in configs.items():
        providers.append({
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "is_configured": config.is_configured,
            "requires_secret_key": config.requires_secret_key,
            "supported_models": config.supported_models
        })

    return {"code": 200, "msg": "OK", "data": providers}


@router.get("/provider-models/{provider}")
async def get_provider_models(provider: str):
    """获取指定提供商支持的模型列表。

    Args:
        provider: 提供商 ID

    Returns:
        模型列表
    """
    from services.ai.providers_config import get_provider_config

    config = get_provider_config(provider)
    if not config:
        raise HTTPException(status_code=404, detail="提供商不存在")

    return {
        "code": 200,
        "msg": "OK",
        "data": {
            "provider": provider,
            "models": config.supported_models
        }
    }


@router.post("/test-api-connection")
async def test_external_api_connection_v2(request_body: TestConnectionRequest):
    """测试外部 API 连接 (v2)。

    Args:
        request_body: 测试连接请求参数

    Returns:
        连接测试结果
    """
    try:
        from services.ai.providers_config import get_provider_config

        # 构建测试参数
        params = {"provider": request_body.provider}

        # 如果是自定义提供商，使用用户提供的配置
        if request_body.provider == "custom":
            if not request_body.api_key:
                return {"code": 400, "msg": "自定义提供商需要提供 API Key", "data": {"status": "failed"}}
            params["api_key"] = request_body.api_key
            if request_body.api_url:
                params["api_url"] = request_body.api_url
            if request_body.secret_key:
                params["secret_key"] = request_body.secret_key
        else:
            # 预设提供商，从环境变量读取配置
            config = get_provider_config(request_body.provider)
            if not config or not config.is_configured:
                return {"code": 400, "msg": f"提供商 {request_body.provider} 未配置", "data": {"status": "failed"}}

            params["api_key"] = config.api_key
            if config.api_url:
                params["api_url"] = config.api_url
            if config.secret_key:
                params["secret_key"] = config.secret_key

        generator = get_ai_generator("external")

        # 使用简单的测试提示词
        test_prompt = "a simple test image"

        # 对于支持异步的 API，我们只测试连接，不实际生成
        if request_body.provider.lower() in ["tongyi", "qwen", "aliyun"]:
            # 通义千问：尝试获取模型列表或发送测试请求
            result = await generator.generate_image(test_prompt, "", params)
            if result.get("status") in ["queued", "completed"]:
                return {"code": 200, "msg": "连接成功", "data": {"status": "connected"}}
            else:
                return {"code": 400, "msg": f"连接失败: {result.get('msg', '未知错误')}", "data": {"status": "failed"}}
        else:
            # 其他 API：发送测试请求
            result = await generator.generate_image(test_prompt, "", params)
            if result.get("status") == "completed":
                return {"code": 200, "msg": "连接成功", "data": {"status": "connected"}}
            else:
                return {"code": 400, "msg": f"连接失败: {result.get('msg', '未知错误')}", "data": {"status": "failed"}}

    except Exception as e:
        return {"code": 500, "msg": f"连接测试失败: {str(e)}", "data": {"status": "error"}}


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

        settings = get_comfyui_settings()

        # 确定使用的地址
        if comfyui_host:
            # 用户自定义地址，直接使用
            target_url = f"http://{comfyui_host}"
        else:
            # 使用配置的地址
            target_url = settings.base_url

        try:
            http_client = SafeHTTPClient(timeout=30.0)

            # 获取系统状态
            system_resp = await http_client.get(f"{target_url}/system_stats")
            system_stats = system_resp.json()

            # 获取对象信息（包含模型路径信息）
            object_resp = await http_client.get(f"{target_url}/object_info")
            object_info = object_resp.json()
        except ConnectionError as e:
            error_code = "CONNECTION_ERROR"
            error_msg = f"无法连接到 ComfyUI 服务 ({target_url})。请检查 ComfyUI 是否正在运行。"
            raise HTTPException(
                status_code=503,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )
        except TimeoutError as e:
            error_code = "TIMEOUT_ERROR"
            error_msg = f"连接 ComfyUI 超时。请检查服务器状态。"
            raise HTTPException(
                status_code=504,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )
        except HTTPError as e:
            if e.status_code in [502, 503]:
                error_code = "SERVICE_UNAVAILABLE"
                error_msg = f"ComfyUI 服务不可用。请检查 ComfyUI 是否正在运行。"
            else:
                error_code = "HTTP_ERROR"
                error_msg = f"HTTP {e.status_code} 错误"
            raise HTTPException(
                status_code=e.status_code or 500,
                detail={
                    "message": error_msg,
                    "error_code": error_code
                }
            )

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

    except (ConnectionError, TimeoutError, HTTPError):
        # 这些异常已经在上面处理过了，直接重新抛出
        raise
    except Exception as e:
        error_msg = str(e)
        error_code = "INTERNAL_ERROR"

        raise HTTPException(
            status_code=500,
            detail={
                "message": f"获取 ComfyUI 信息失败: {error_msg}",
                "error_code": error_code
            }
        )
