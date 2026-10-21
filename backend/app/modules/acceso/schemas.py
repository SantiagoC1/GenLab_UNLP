from pydantic import BaseModel


class RegisterData(BaseModel):
    role: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    password: str | None = None
    license_number: str | None = None
    specialties: list[int] | None = None
    province: str | None = None


class CreateUserData(BaseModel):
    role: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    license_number: str | None = None
    specialties: list[int] | None = None
    province: str | None = None


class LoginData(BaseModel):
    email: str | None = None
    password: str | None = None


class VerifyCodeData(BaseModel):
    email: str | None = None
    code: str | None = None


class ChangePasswordData(BaseModel):
    current_password: str | None = None
    new_password: str | None = None
    confirmation: str | None = None