from enum import Enum


class ErrorCode(Enum):

    # ===== COMMON =====
    INVALID_MAPPING_PARAMETER = (400, "COM_400_001", "매핑할 수 없는 값입니다.")
    UNAUTHORIZED = (401, "COM_401_001", "인증이 필요합니다.")
    RESOURCE_NOT_FOUND = (404, "COM_404_001", "존재하지 않는 리소스입니다.")
    INTERNAL_SERVER_ERROR = (500, "COM_500_001", "서버 내부 오류가 발생했습니다.")

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
