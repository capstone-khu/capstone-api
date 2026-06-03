from pydantic import BaseModel

from app.common.types import KSTDateTime


class ProfileResponse(BaseModel):
    id: int
    name: str
    created_at: KSTDateTime
