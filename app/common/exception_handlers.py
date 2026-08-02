"""Map domain errors to stable, non-sensitive HTTP responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.common.exceptions import AppError


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
