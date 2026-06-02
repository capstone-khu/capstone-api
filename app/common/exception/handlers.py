import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.exception.business import BusinessException
from app.common.exception.error_code import ErrorCode
from app.common.response import ApiResponse, ErrorMeta


def add_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(BusinessException)
    async def handle_business(request: Request, exc: BusinessException) -> JSONResponse:
        error_code = exc.error_code
        body = ApiResponse.on_failure(error_code, _meta(request))
        return JSONResponse(
            status_code=error_code.status,
            content=body.model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        error_code = ErrorCode.INVALID_MAPPING_PARAMETER
        body = ApiResponse.on_failure(error_code, _meta(request))
        return JSONResponse(
            status_code=error_code.status,
            content=body.model_dump(exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        error_code = ErrorCode.INTERNAL_SERVER_ERROR
        body = ApiResponse.on_failure(error_code, _meta(request), message=str(exc))
        return JSONResponse(
            status_code=error_code.status,
            content=body.model_dump(exclude_none=True),
        )


def _meta(request: Request) -> ErrorMeta:
    return ErrorMeta(path=request.url.path, timestamp=int(time.time() * 1000))
