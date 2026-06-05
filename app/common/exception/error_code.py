from enum import Enum


class ErrorCode(Enum):

    # ===== COMMON =====
    INVALID_MAPPING_PARAMETER = (400, "COM_400_001", "매핑할 수 없는 값입니다.")
    UNAUTHORIZED = (401, "COM_401_001", "인증이 필요합니다.")
    RESOURCE_NOT_FOUND = (404, "COM_404_001", "존재하지 않는 리소스입니다.")
    INTERNAL_SERVER_ERROR = (500, "COM_500_001", "서버 내부 오류가 발생했습니다.")

    # ===== AUTH =====
    LOGIN_FAILED = (401, "AUT_401_001", "이름 또는 비밀번호가 올바르지 않습니다.")

    # ===== SONG =====
    SONG_NOT_FOUND = (404, "SON_404_001", "존재하지 않는 곡입니다.")

    # ===== SESSION =====
    INVALID_DUET_PARTNER = (400, "SES_400_001", "협주 상대 녹음이 올바르지 않습니다.")
    FORBIDDEN_SESSION = (403, "SES_403_001", "본인의 세션이 아닙니다.")
    SESSION_NOT_FOUND = (404, "SES_404_001", "존재하지 않는 세션입니다.")
    SESSION_ALREADY_ENDED = (409, "SES_409_001", "이미 종료된 세션입니다.")

    # ===== RECORDING =====
    RECORDING_NOT_FOUND = (404, "REC_404_001", "존재하지 않는 녹음입니다.")

    # ===== DUET =====
    FORBIDDEN_DUET = (403, "DUE_403_001", "본인의 협주 영상이 아닙니다.")
    DUET_NOT_FOUND = (404, "DUE_404_001", "존재하지 않는 협주 영상입니다.")

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
