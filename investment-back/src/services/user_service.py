from typing import Optional
from sqlalchemy.orm import Session
from src.models.user import User, UserProfile
from src.schemas.user import UserProfileCreate, UserProfileUpdate
import structlog

logger = structlog.get_logger()

class UserService:
    """用户服务"""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logger.bind(service="user")

    def get_or_create_profile(
        self, user_id: int
    ) -> UserProfile:
        """获取或创建用户画像"""
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        if not profile:
            self.logger.info("creating_profile", user_id=user_id)
            profile_data = UserProfileCreate()
            profile = UserProfile(
                user_id=user_id,
                **profile_data.dict()
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        return profile

    def update_profile(
        self, user_id: int, profile_update: UserProfileUpdate
    ) -> UserProfile:
        """更新用户画像"""
        profile = self.get_or_create_profile(user_id)

        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(profile)
        self.logger.info("profile_updated", user_id=user_id)

        return profile

    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_with_profile(self, user_id: int) -> Optional[User]:
        """获取用户（包含画像）"""
        user = self.get_user(user_id)
        if user:
            # 加载profile
            user.profile = self.get_or_create_profile(user_id)
        return user
