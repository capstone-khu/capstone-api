from pydantic import BaseModel


class LoginRequest(BaseModel):
    name: str
    password: str


class UserSummary(BaseModel):
    id: int
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary
