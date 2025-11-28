from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from database import Base, engine
from api.v1.auth import router as auth_router
from api.v1.users import router as users_router
from api.v1.drawings import router as drawings_router
from api.v1.analytics import router as analytics_router
from api.v1.home import router as home_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(drawings_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")