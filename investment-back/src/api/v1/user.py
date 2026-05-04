from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT
from src.db.session import get_db
from src.models.judgment_history import JudgmentHistory
from src.models.user import User
from src.schemas.common import ErrorDetail, ErrorResponse
from src.schemas.user import (
    UserProfile,
    UserProfileUpdate,
    UserWithProfile,
    LoginRequest,
    LoginResponse
)
from src.schemas.learning_feedback import (
    LearningFeedbackRequest,
    LearningFeedbackResponse,
    LearningHistoryResponse,
)
from src.api.deps import get_current_user
from src.core.config import get_settings
from src.services.user_service import UserService
from src.services.profile_service import ProfileService
from jose import jwt
from datetime import datetime, timedelta
import structlog

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


def api_error(
    status_code: int,
    code: str,
    message: str,
    request: Request = None,
    retryable: bool = False,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") if request else None
    body = ErrorResponse(error=ErrorDetail(
        code=code,
        message=message,
        request_id=request_id,
        retryable=retryable,
    ))
    return JSONResponse(status_code=status_code, content=body.model_dump())

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


def get_profile_service(db: Session = Depends(get_db)):
    return ProfileService(db)


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """用户注册（创建账号并返回 JWT token）

    测试身份能力通过此显式接口提供，不再依赖启动时隐式注入。
    """
    existing = db.query(User).filter(User.username == login_data.username).first()
    if existing:
        return api_error(
            HTTP_409_CONFLICT,
            "USERNAME_EXISTS",
            "用户名已存在",
            request,
        )

    new_user = User(username=login_data.username)
    new_user.set_password(login_data.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    from src.models.user import UserProfile, ExperienceLevel, HoldingHorizon, RiskTolerance

    new_profile = UserProfile(
        user_id=new_user.id,
        experience_level=ExperienceLevel.NOVICE,
        holding_horizon=HoldingHorizon.MEDIUM,
        risk_tolerance=RiskTolerance.MEDIUM,
        behavior_tags=[],
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=access_token_expires,
    )

    service = get_user_service(db)
    user_with_profile = service.get_user_with_profile(new_user.id)

    logger.info("register_success", user_id=new_user.id)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_with_profile,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """用户登录（获取 JWT token）"""
    logger.info("login_attempt", username=login_data.username)

    # 查找用户
    user = db.query(User).filter(
        User.username == login_data.username
    ).first()

    if not user or not user.verify_password(login_data.password):
        return api_error(
            HTTP_401_UNAUTHORIZED,
            "INVALID_CREDENTIALS",
            "用户名或密码错误",
            request,
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
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新用户画像"""
    logger.info("update_user_profile", user_id=current_user.id)

    service = get_user_service(db)

    try:
        profile = service.update_profile(current_user.id, profile_data)
    except Exception as e:
        return api_error(HTTP_404_NOT_FOUND, "PROFILE_NOT_FOUND", "用户画像未找到", request)

    return profile

@router.get("", response_model=UserWithProfile)
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取当前用户信息（含用户画像）"""
    logger.info("get_current_user_info", user_id=current_user.id)

    service = get_user_service(db)
    user_with_profile = service.get_user_with_profile(current_user.id)

    if not user_with_profile:
        return api_error(HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "用户未找到", request)

    return user_with_profile


@router.get("/profile/learning-history", response_model=LearningHistoryResponse)
async def get_learning_history(
    request: Request,
    days: int = Query(default=30, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """获取画像学习历史：情绪历史 + 判断质量历史

    用于前端情绪 sparkline 和判断质量趋势图。
    """
    logger.info("get_learning_history", user_id=current_user.id, days=days)

    service = get_profile_service(db)
    return service.get_learning_history(current_user.id, days)


@router.post("/profile/learning-history/debug-seed")
async def debug_seed_learning_history(
    data: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Seed learning history for E2E tests. Available only when DEBUG=true."""
    if not settings.DEBUG:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Not found")

    days = int(data.get("days", 30))
    judgment_scores = data.get("judgment_scores", [])
    if not isinstance(judgment_scores, list) or not judgment_scores:
        raise HTTPException(status_code=400, detail="judgment_scores is required")

    today = datetime.utcnow().date()
    cutoff = today - timedelta(days=days)
    db.query(JudgmentHistory).filter(
        JudgmentHistory.user_id == current_user.id,
        JudgmentHistory.judgment_date >= cutoff,
    ).delete(synchronize_session=False)
    db.commit()

    label_by_score = {
        100: "主要来自判断",
        50: "部分判断 + 部分运气",
        0: "主要来自运气",
    }
    service = get_profile_service(db)
    for index, raw_score in enumerate(judgment_scores):
        score = int(raw_score)
        label = label_by_score.get(score)
        if label is None:
            raise HTTPException(status_code=400, detail=f"unsupported judgment score: {score}")
        service.upsert_judgment_history(
            user_id=current_user.id,
            judgment_date=today - timedelta(days=index),
            judgment_label=label,
            is_hard_to_tell=False,
        )

    return {"success": True, "seeded": len(judgment_scores)}


@router.post("/profile/learning-feedback", response_model=LearningFeedbackResponse)
async def record_learning_feedback(
    data: LearningFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """写入学习反馈：行为标签更新 + 判断质量历史 + 情绪历史

    由前端 LearningFeedbackCard 用户点击"确认"后调用。
    每天同一用户调用多次时，后续调用会覆盖当日记录（upsert）。
    """
    logger.info(
        "record_learning_feedback",
        user_id=current_user.id,
        judgment_quality=data.judgment_quality,
        emotion_level=data.emotion_level,
        tag_count=len(data.tag_updates),
    )

    service = get_profile_service(db)
    result = service.record_learning_feedback(current_user.id, data)

    return result
