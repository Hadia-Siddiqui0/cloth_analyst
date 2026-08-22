import uuid
from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: str
    company_id: uuid.UUID

    class Config:
        from_attributes = True
