from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from src.models.user import ExperienceLevel, HoldingHorizon, RiskTolerance, BehaviorTag
from src.schemas.common import TimestampMixin


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., max_length=50)
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: "UserWithProfile"

class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr = Field(..., max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class User(UserBase, TimestampMixin):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class UserProfileBase(BaseModel):
    experience_level: ExperienceLevel = ExperienceLevel.NOVICE
    holding_horizon: HoldingHorizon = HoldingHorizon.MEDIUM
    risk_tolerance: RiskTolerance = RiskTolerance.MEDIUM
    behavior_tags: List[BehaviorTag] = Field(default_factory=list)

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(BaseModel):
    experience_level: Optional[ExperienceLevel] = None
    holding_horizon: Optional[HoldingHorizon] = None
    risk_tolerance: Optional[RiskTolerance] = None
    behavior_tags: Optional[List[BehaviorTag]] = None

class UserProfile(UserProfileBase, TimestampMixin):
    id: int
    user_id: int
    investment_goals: Optional[str] = None
    portfolio_size: Optional[str] = None
    preferred_sectors: Optional[List[str]] = None

    class Config:
        from_attributes = True

class UserWithProfile(User):
    profile: Optional[UserProfile] = None

    class Config:
        from_attributes = True
