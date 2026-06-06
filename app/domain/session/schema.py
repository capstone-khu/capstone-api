from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.common.types import KSTDateTime


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"song_id": 1, "mode": "duet", "partner_recording_id": 1}
        }
    )

    song_id: int
    mode: Literal["solo", "duet"]
    partner_recording_id: int | None = None

    @model_validator(mode="after")
    def _require_partner_for_duet(self) -> "SessionCreateRequest":
        if self.mode == "duet" and self.partner_recording_id is None:
            raise ValueError("partner_recording_id is required for duet mode")
        return self


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 12,
                "status": "created",
                "song_title": "반짝 반짝 작은별",
                "partner_name": "손수민",
                "audio_url": "/media/recordings/1.mp4",
            }
        }
    )

    session_id: int
    status: str
    song_title: str
    partner_name: str | None = None
    audio_url: str | None = None


class SessionCompleteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 12,
                "recording_id": 21,
                "duet_composite_id": 5,
            }
        }
    )

    session_id: int
    recording_id: int
    duet_composite_id: int | None = None


class Marking(BaseModel):
    domain: str
    action_id: str
    feedback: str


class MeasureMarkings(BaseModel):
    measure_index: int
    markings: list[Marking]


class PreviousMarkingsResponse(BaseModel):
    previous_session_id: int | None = None
    measures: list[MeasureMarkings]


class NoteItem(BaseModel):
    pitch: str
    duration: str
    position: int
    lyric: str | None = None


class MeasureDetailResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "measure_index": 1,
                "notes": [
                    {"pitch": "D4", "duration": "quarter", "position": 0, "lyric": "반"}
                ],
                "current_markings": [
                    {
                        "domain": "pitch",
                        "action_id": "PT-03",
                        "feedback": "음정을 내리세요",
                    }
                ],
                "previous_markings": [],
            }
        }
    )

    measure_index: int
    notes: list[NoteItem]
    current_markings: list[Marking]
    previous_markings: list[Marking]


class MeasureResult(BaseModel):
    measure_index: int
    current: list[Marking]
    previous: list[Marking]


class SessionResultResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": 12,
                "song_id": 1,
                "song_title": "반짝 반짝 작은별",
                "played_at": "2026-06-02T09:30:00+09:00",
                "mode": "duet",
                "partner_name": "손수민",
                "measures": [
                    {
                        "measure_index": 1,
                        "current": [
                            {
                                "domain": "pitch",
                                "action_id": "PT-03",
                                "feedback": "음정을 내리세요",
                            }
                        ],
                        "previous": [
                            {
                                "domain": "rhythm",
                                "action_id": "RH-03",
                                "feedback": "박자보다 늦게 연주하고 있습니다",
                            }
                        ],
                    }
                ],
            }
        }
    )

    session_id: int
    song_id: int
    song_title: str
    played_at: KSTDateTime
    mode: str
    partner_name: str | None = None
    measures: list[MeasureResult]


class DuetVideoResponse(BaseModel):
    duet_composite_id: int
    song_title: str
    partner_name: str
    status: str
    composite_video_url: str | None = None
    created_at: datetime
