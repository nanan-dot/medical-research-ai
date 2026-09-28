"""Map domain errors to stable, non-sensitive HTTP responses."""

from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from app.common.exceptions import AppError


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # 运行时只注册给 AppError；参数放宽为 Exception 以匹配 Starlette handler 签名契约。
    assert isinstance(exc, AppError)
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    error = {"code": exc.code, "message": exc.message, "request_id": request_id}
    if isinstance(exc.detail, dict) and "fields" in exc.detail:
        error["fields"] = exc.detail["fields"]
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error},
        headers={"X-Request-ID": request_id},
    )
