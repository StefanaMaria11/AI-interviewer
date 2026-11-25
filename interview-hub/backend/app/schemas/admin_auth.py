from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)
    totp_code: str = Field(pattern=r"^[0-9]{6}$")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()