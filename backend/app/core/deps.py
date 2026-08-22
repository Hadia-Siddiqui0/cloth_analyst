"""
Every protected endpoint depends on `get_current_user`, and every query
inside a service should be filtered by the `company_id` this returns --
never trust a company_id passed in the request body/query params, always
take it from the verified JWT. This is the single choke point that
prevents Company A from ever seeing Company B's data.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_error
    return user


def get_current_company_id(current_user: User = Depends(get_current_user)) -> uuid.UUID:
    """The one line every service call should use to scope its query."""
    return current_user.company_id


def require_role(*allowed_roles: str):
    """Usage: Depends(require_role('ceo', 'finance_manager'))"""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform this action",
            )
        return current_user
    return checker
