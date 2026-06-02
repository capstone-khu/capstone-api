from app.common.exception.error_code import ErrorCode


class BusinessException(Exception):

    def __init__(self, error_code: ErrorCode, detail: str | None = None) -> None:
        self.error_code = error_code
        message = (
            error_code.message
            if detail is None
            else f"{error_code.message} - {detail}"
        )
        super().__init__(message)
