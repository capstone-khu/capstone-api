from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


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
    model_config = ConfigDict(json_schema_extra={"example": {"session_id": 12}})

    session_id: int
