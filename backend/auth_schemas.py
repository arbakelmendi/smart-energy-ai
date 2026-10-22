"""Explicit authentication contracts; passwords are redacted in representations."""
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from email_validator import validate_email, EmailNotValidError
from typing import Literal


def normalize_email(value: str) -> str:
    try:
        result = validate_email(value.strip(), check_deliverability=False, allow_smtputf8=False)
    except EmailNotValidError:
        raise ValueError("Enter a valid email address") from None
    return result.ascii_email.lower()


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=320)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value):
        return normalize_email(value)


class SignupRequest(AuthRequest):
    password: SecretStr = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)

    @field_validator("full_name")
    @classmethod
    def nonblank_name(cls, value):
        if not value.strip():
            raise ValueError("Full name must not be blank")
        return value  # Do not silently normalize unrelated profile fields.


class LoginRequest(AuthRequest):
    password: SecretStr = Field(min_length=1, max_length=128)


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: Literal["USER", "ADMIN"]
    is_active: bool
