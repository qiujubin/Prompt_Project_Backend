from fastapi import APIRouter
from utils.crud import create_crud_router
from models.user import User, SocialAccount
from models.drawing import Drawing
from models.prompt_log import PromptLog
from models.prompt_category import PromptCategory
from models.prompt_subcategory import PromptSubcategory
from models.prompt_keyword import PromptKeyword
from schemas.user import UserRead, UserCreate, UserUpdate
from schemas.social_account import SocialAccountRead, SocialAccountCreate, SocialAccountUpdate
from schemas.drawing import DrawingRead, DrawingCreate, DrawingUpdate
from schemas.prompt_log import PromptLogRead, PromptLogCreate, PromptLogUpdate
from schemas.prompt import (
    PromptCategoryRead, PromptCategoryCreate, PromptCategoryUpdate,
    PromptSubcategoryRead, PromptSubcategoryCreate, PromptSubcategoryUpdate,
    PromptKeywordRead, PromptKeywordCreate, PromptKeywordUpdate,
)

router = APIRouter()

# Admin CRUD routers (single-key tables)
router.include_router(create_crud_router(User, UserRead, UserCreate, UserUpdate, prefix="/admin/users"))
router.include_router(create_crud_router(SocialAccount, SocialAccountRead, SocialAccountCreate, SocialAccountUpdate, prefix="/admin/social_accounts"))
router.include_router(create_crud_router(Drawing, DrawingRead, DrawingCreate, DrawingUpdate, prefix="/admin/drawings"))
router.include_router(create_crud_router(PromptLog, PromptLogRead, PromptLogCreate, PromptLogUpdate, prefix="/admin/prompt_logs"))
router.include_router(create_crud_router(PromptCategory, PromptCategoryRead, PromptCategoryCreate, PromptCategoryUpdate, prefix="/admin/prompt_categories"))
router.include_router(create_crud_router(PromptSubcategory, PromptSubcategoryRead, PromptSubcategoryCreate, PromptSubcategoryUpdate, prefix="/admin/prompt_subcategories"))
router.include_router(create_crud_router(PromptKeyword, PromptKeywordRead, PromptKeywordCreate, PromptKeywordUpdate, prefix="/admin/prompt_keywords"))

