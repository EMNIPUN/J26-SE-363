"""API errors with a stable machine-readable code.

The body is `{"detail": "<message>", "code": "<code>"}`. The frontend branches on `code` and
shows `detail`; see frontend/src/shared/api/apiError.js.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


def bad_request(code: str, message: str) -> ApiError:
    return ApiError(status.HTTP_400_BAD_REQUEST, code, message)


def forbidden(code: str, message: str) -> ApiError:
    return ApiError(status.HTTP_403_FORBIDDEN, code, message)


def not_found(message: str = "Not found") -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "not_found", message)


def conflict(code: str, message: str) -> ApiError:
    return ApiError(status.HTTP_409_CONFLICT, code, message)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )
