from pydantic import BaseModel

from app.common.exception.error_code import ErrorCode
from app.common.exception.success_code import SuccessCode


class ErrorMeta(BaseModel):
    path: str
    timestamp: int


class ApiResponse[T, M](BaseModel):
    success: bool
    status: int
    message: str
    data: T | None = None
    code: str | None = None
    meta: M | None = None

    @classmethod
    def ok(
        cls, success_code: SuccessCode, data: T | None = None
    ) -> "ApiResponse[T, None]":
        return cls(
            success=True,
            status=success_code.status,
            message=success_code.message,
            data=data,
        )

    @classmethod
    def created(cls, success_code: SuccessCode, data: T) -> "ApiResponse[T, None]":
        return cls(
            success=True,
            status=success_code.status,
            message=success_code.message,
            data=data,
        )

    @classmethod
    def on_failure(
        cls,
        error_code: ErrorCode,
        meta: ErrorMeta | None = None,
        message: str | None = None,
    ) -> "ApiResponse[None, ErrorMeta]":
        return cls(
            success=False,
            status=error_code.status,
            message=message or error_code.message,
            code=error_code.code,
            meta=meta,
        )
