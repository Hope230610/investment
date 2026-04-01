from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.user import User
from src.schemas.user import (
    UserProfile,
    UserProfileUpdate,
    UserWithProfile,
    LoginRequest,
    LoginResponse
)
from src.api.deps import get_current_user
from src.core.config import get_settings
from src.services.user_service import UserService
from jose import jwt
from datetime import datetime, timedelta
import structlog

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """创建访问 token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# 初始化服务
def get_user_service(db: Session = Depends(get_db)):
    return UserService(db)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录（获取 JWT token）"""
    logger.info("login_attempt", username=login_data.username)

    # 查找用户
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()

    if not user or not user.verify_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建 token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # 获取用户信息（含用户画像）
    service = get_user_service(db)
    user_with_profile = service.get_user_with_profile(user.id)

    logger.info("login_success", user_id=user.id)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_with_profile
    )

@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取用户画像"""
    logger.info("get_user_profile", user_id=current_user.id)

    service = get_user_service(db)
    profile = service.get_or_create_profile(current_user.id)

    return profile

@router.put("/profile", response_model=UserProfile)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新用户画像"""
    logger.info("update_user_profile", user_id=current_user.id)

    service = get_user_service(db)

    try:
        profile = service.update_profile(current_user.id, profile_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户画像未找到"
        )

    return profile

@router.get("", response_model=UserWithProfile)
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取当前用户信息（含用户画像）"""
    logger.info("get_current_user_info", user_id=current_user.id)

    service = get_user_service(db)
    user_with_profile = service.get_user_with_profile(current_user.id)

    if not user_with_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户未找到"
        )

    return user_with_profile
