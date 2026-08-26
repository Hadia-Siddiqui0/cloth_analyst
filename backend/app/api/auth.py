import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiting store (for MVP - will use Redis in production)
# Tracks failed attempts by IP address
_failed_attempts: dict[str, list[float]] = {}
RATE_LIMIT_WINDOW = 900  # 15 minutes
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes


def _is_rate_limited(ip: str) -> bool:
    """Check if IP is rate limited due to too many failed attempts."""
    now = time.time()
    attempts = _failed_attempts.get(ip, [])

    # Clean old attempts outside the window
    recent_attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW]
    _failed_attempts[ip] = recent_attempts

    if len(recent_attempts) >= MAX_FAILED_ATTEMPTS:
        # Check if lockout period has passed
        oldest_attempt = min(recent_attempts)
        if now - oldest_attempt < LOCKOUT_DURATION:
            return True
        else:
            # Lockout expired, clear attempts
            _failed_attempts[ip] = []
            return False

    return False


def _record_failed_attempt(ip: str):
    """Record a failed authentication attempt."""
    now = time.time()
    if ip not in _failed_attempts:
        _failed_attempts[ip] = []
    _failed_attempts[ip].append(now)


def _clear_failed_attempts(ip: str):
    """Clear failed attempts after successful authentication."""
    _failed_attempts.pop(ip, None)


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# Note: login below takes JSON (email/password), which is what the React
# frontend will call. The OAuth2PasswordBearer in core/deps.py only
# points at this URL for Swagger's "Authorize" button, which expects
# form-encoded data -- so testing login via the /docs UI directly won't
# work as-is. Fine for now; revisit if that friction matters later.


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _get_client_ip(request)

    # Check rate limiting
    if _is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again in 15 minutes."
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        # Record failed attempt for rate limiting
        _record_failed_attempt(client_ip)
        # Use same error message to prevent account enumeration
        # but with a subtle hint that's not obvious to attackers
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to create account. Please try with different details."
        )

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

    # Clear any failed attempts on success
    _clear_failed_attempts(client_ip)

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(company.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = _get_client_ip(request)

    # Check rate limiting
    if _is_rate_limited(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please try again in 15 minutes."
        )

    user = db.query(User).filter(User.email == payload.email).first()

    # Use constant-time comparison to prevent timing attacks
    # Always perform password verification even if user doesn't exist
    if user:
        password_valid = verify_password(payload.password, user.hashed_password)
    else:
        # Hash a dummy password to maintain consistent timing
        hash_password("dummy_password_for_timing")
        password_valid = False

    if not user or not password_valid:
        # Record failed attempt
        _record_failed_attempt(client_ip)
        # Generic error message to prevent account enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        # Don't reveal that account exists but is disabled
        # Use same message as incorrect credentials
        _record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Clear any failed attempts on success
    _clear_failed_attempts(client_ip)

    return TokenResponse(
        access_token=create_access_token(str(user.id), str(user.company_id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
