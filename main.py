"""项目后端应用入口。

负责创建 FastAPI 应用、配置 CORS 中间件、挂载路由与性能监控中间件。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from database import Base, engine
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.drawings import router as drawings_router
from api.v1.analytics import router as analytics_router
from api.v1.home import router as home_router
from api.v1.prompts import router as prompts_router
from middleware import MetricsMiddleware
from api.v1.crud import router as admin_crud_router
from api.v1.favorites import fav_router, upk_router
from api.v1.generation import router as generation_router
from api.v1.community import router as community_router
from api.v1.admin_community import router as admin_community_router
from api.v1.user_collections import router as user_collections_router
from api.v1.credits import router as credits_router
from api.v1.content_discovery import router as content_discovery_router
from fastapi.staticfiles import StaticFiles
import os

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(drawings_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(admin_crud_router, prefix="/api")
app.include_router(admin_community_router, prefix="/api")
app.include_router(user_collections_router, prefix="/api")
app.include_router(credits_router, prefix="/api")
app.include_router(fav_router, prefix="/api")
app.include_router(upk_router, prefix="/api")
app.include_router(generation_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(content_discovery_router, prefix="/api/v1/content-discovery")

app.add_middleware(MetricsMiddleware)
