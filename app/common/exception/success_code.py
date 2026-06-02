from enum import Enum


class SuccessCode(Enum):

    OK = (200, "요청에 성공했습니다.")
    CREATED = (201, "리소스가 생성되었습니다.")

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
