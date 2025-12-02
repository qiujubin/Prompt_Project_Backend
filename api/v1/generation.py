from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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
    prompt: str
    negative_prompt: Optional[str] = ""
    backend: str = "comfyui"  # 'comfyui' or 'external'
    width: Optional[int] = 512
    height: Optional[int] = 512
    seed: Optional[int] = None
    model_name: Optional[str] = None
    # 新增：自定义配置参数
    comfyui_host: Optional[str] = None  # 用户自定义的 ComfyUI 地址
    api_key: Optional[str] = None       # 用户自定义的 External API Key
    api_url: Optional[str] = None       # 用户自定义的 External API URL

@router.post("/draw")
async def generate_image(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """触发 AI 绘图任务。需消耗积分。"""
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
        
        # 注入自定义配置
        config_overrides = {}
        if req.comfyui_host:
            config_overrides['server_address'] = req.comfyui_host
        if req.api_key:
            config_overrides['api_key'] = req.api_key
        if req.api_url:
            config_overrides['api_url'] = req.api_url
            
        params = {
            "width": req.width,
            "height": req.height,
            "seed": req.seed,
            "model_name": req.model_name,
            **config_overrides  # 将配置也传入 params，或者修改 generator 接口
        }
        
        # 注意：为了支持 config_overrides，我们需要修改 generator 的 generate_image 接口或者在调用前 configure
        # 这里我们选择将配置放入 params 中，并在 generator 内部处理
        
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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
