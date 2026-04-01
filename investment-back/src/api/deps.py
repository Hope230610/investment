from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.db.session import get_db
from src.models.user import User, UserProfile
from src.services.market_data_service import MarketDataService


security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    user_id: Optional[int] = None


def _get_or_create_debug_user(db: Session) -> User:
    """Return the seeded debug user, creating it when needed."""
    test_user = db.query(User).filter(User.username == "testuser").first()
    if test_user:
        return test_user

    from src.models.user import ExperienceLevel, HoldingHorizon, RiskTolerance

    test_user = User(username="testuser", email="test@example.com")
    test_user.set_password("testpassword123")
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    test_profile = UserProfile(
        user_id=test_user.id,
        experience_level=ExperienceLevel.NOVICE,
        holding_horizon=HoldingHorizon.MEDIUM,
        risk_tolerance=RiskTolerance.MEDIUM,
        behavior_tags=[],
    )
    db.add(test_profile)
    db.commit()
    return test_user


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Return the authenticated user, or the seeded dev user in debug mode."""
    settings = get_settings()
    if settings.DEBUG and (not credentials or not credentials.credentials):
        return _get_or_create_debug_user(db)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        if not credentials:
            raise credentials_exception

        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=int(user_id))
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Return the current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )
    return profile


def get_market_data_service() -> Generator[MarketDataService, None, None]:
    """Provide a request-scoped market data client."""
    service = MarketDataService()
    try:
        yield service
    finally:
        service.close()
