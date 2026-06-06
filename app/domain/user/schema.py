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


class HistoryStats(BaseModel):
    pitch: int
    rhythm: int
    posture: int


class HistoryItem(BaseModel):
    session_id: int
    song_title: str
    played_at: KSTDateTime
    mode: str
    stats: HistoryStats
    focus_measures: list[int]
    duet_composite_id: int | None = None
    partner_name: str | None = None


class HistoryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "size": 3,
                "total": 7,
                "items": [
                    {
                        "session_id": 12,
                        "song_title": "반짝 반짝 작은별",
                        "played_at": "2026-06-02T09:30:00+09:00",
                        "mode": "duet",
                        "stats": {"pitch": 3, "rhythm": 1, "posture": 2},
                        "focus_measures": [5, 7],
                        "duet_composite_id": 5,
                        "partner_name": "이준호",
                    },
                    {
                        "session_id": 10,
                        "song_title": "반짝 반짝 작은별",
                        "played_at": "2026-06-01T18:10:00+09:00",
                        "mode": "solo",
                        "stats": {"pitch": 0, "rhythm": 2, "posture": 1},
                        "focus_measures": [],
                    },
                ],
            }
        }
    )

    page: int
    size: int
    total: int
    items: list[HistoryItem]
