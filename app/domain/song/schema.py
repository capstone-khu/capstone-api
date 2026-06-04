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


class Note(BaseModel):
    pitch: str
    duration: str
    position: int
    lyric: str | None = None


class ScoreMeasure(BaseModel):
    measure_index: int
    notes: list[Note]


class SongDetail(BaseModel):
    id: int
    number: int
    title: str
    bpm: int
    time_signature: str
    total_measures: int


class ScoreResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "song": {
                    "id": 1,
                    "number": 1,
                    "title": "반짝 반짝 작은별",
                    "bpm": 96,
                    "time_signature": "4/4",
                    "total_measures": 12,
                },
                "measures": [
                    {
                        "measure_index": 1,
                        "notes": [
                            {
                                "pitch": "D4",
                                "duration": "quarter",
                                "position": 0,
                                "lyric": "반",
                            },
                            {
                                "pitch": "D4",
                                "duration": "quarter",
                                "position": 1,
                                "lyric": "짝",
                            },
                        ],
                    }
                ],
            }
        }
    )

    song: SongDetail
    measures: list[ScoreMeasure]
