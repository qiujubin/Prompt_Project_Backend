from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.ai import get_ai_generator

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
async def generate_image(req: GenerateRequest):
    """触发 AI 绘图任务。"""
    try:
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
        
        result = await generator.generate_image(req.prompt, req.negative_prompt, params)
        return {"code": 200, "msg": "OK", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{backend}/{task_id}")
async def check_generation_status(backend: str, task_id: str, comfyui_host: Optional[str] = None):
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
        return {"code": 200, "msg": "OK", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
