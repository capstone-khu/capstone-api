from pydantic import BaseModel, ConfigDict

from app.common.types import KSTDateTime


class ProfileResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "신진수",
                "created_at": "2026-06-01T10:00:00+09:00",
            }
        }
    )

    id: int
    name: str
    created_at: KSTDateTime
