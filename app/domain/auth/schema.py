from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"name": "신진수", "password": "capstone"}}
    )

    name: str
    password: str


class UserSummary(BaseModel):
    id: int
    name: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiI...",
                "token_type": "bearer",
                "user": {"id": 1, "name": "신진수"},
            }
        }
    )

    access_token: str
    token_type: str = "bearer"
    user: UserSummary
