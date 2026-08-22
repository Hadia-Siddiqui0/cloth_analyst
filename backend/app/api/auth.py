from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Note: login below takes JSON (email/password), which is what the React
# frontend will call. The OAuth2PasswordBearer in core/deps.py only
# points at this URL for Swagger's "Authorize" button, which expects
# form-encoded data -- so testing login via the /docs UI directly won't
# work as-is. Fine for now; revisit if that friction matters later.


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # MVP: signup creates a brand-new company. Later (multi-user companies)
    # this needs an "invite" flow instead of always creating a new tenant.
    company = Company(name=payload.company_name)
    db.add(company)
    db.flush()  # get company.id without committing yet

    user = User(
        company_id=company.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="ceo",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(company.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.company_id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
