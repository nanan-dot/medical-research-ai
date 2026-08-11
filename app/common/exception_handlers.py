"""Map domain errors to stable, non-sensitive HTTP responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.common.exceptions import AppError


async def app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    # 运行时只注册给 AppError；参数放宽为 Exception 以匹配 Starlette handler 签名契约。
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
