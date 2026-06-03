from typing import Any

from app.common.exception.error_code import ErrorCode
from app.common.response import ApiResponse, ErrorMeta

_META_EXAMPLE = ErrorMeta(path="/api/example", timestamp=1733000000000)


def success_response(
    status_code: int, example: dict[str, Any]
) -> dict[int | str, dict[str, Any]]:
    return {status_code: {"content": {"application/json": {"example": example}}}}


def error_responses(*error_codes: ErrorCode) -> dict[int | str, dict[str, Any]]:
    grouped: dict[int, list[ErrorCode]] = {}
    for error_code in error_codes:
        grouped.setdefault(error_code.status, []).append(error_code)

    responses: dict[int | str, dict[str, Any]] = {}
    for status, codes in grouped.items():
        examples = {
            code.code: {
                "summary": f"{code.code} · {code.message}",
                "value": ApiResponse.on_failure(code, _META_EXAMPLE).model_dump(
                    exclude_none=True
                ),
            }
            for code in codes
        }
        responses[status] = {
            "model": ApiResponse[None, ErrorMeta],
            "description": " / ".join(code.message for code in codes),
            "content": {"application/json": {"examples": examples}},
        }
    return responses
