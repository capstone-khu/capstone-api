from pydantic import BaseModel, ConfigDict


class SongSummary(BaseModel):
    id: int
    number: int
    title: str


class SongListResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 1,
                "songs": [{"id": 1, "number": 1, "title": "반짝 반짝 작은별"}],
            }
        }
    )

    total: int
    songs: list[SongSummary]
