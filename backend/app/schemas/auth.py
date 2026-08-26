import re
import uuid
from pydantic import BaseModel, EmailStr, field_validator


# Common passwords that should be rejected
COMMON_PASSWORDS = {
    "password", "password123", "123456", "12345678", "qwerty", "abc123",
    "monkey", "master", "dragon", "letmein", "login", "admin", "welcome",
    "password1", "123456789", "password!", "passw0rd", "iloveyou",
}


class SignupRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce strong passwords to prevent brute-force attacks."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters long")

        # Check for common weak passwords
        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("This password is too common. Please choose a stronger password.")

        # Check for at least one uppercase, one lowercase, one digit
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one number"
            )

        # Check for common character patterns
        if re.search(r"(.)\1{2,}", v):  # Three or more repeated characters
            raise ValueError("Password contains repeated characters. Please choose a stronger password.")

        # Check for sequential characters
        for i in range(len(v) - 2):
            if ord(v[i+1]) == ord(v[i]) + 1 and ord(v[i+2]) == ord(v[i+1]) + 1:
                raise ValueError("Password contains sequential characters. Please choose a stronger password.")

        return v


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
