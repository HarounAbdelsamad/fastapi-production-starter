from fastapi import Request
from fastapi.responses import JSONResponse


def api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str | None]] | None = None,
    request: Request | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) if request else None
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or [],
            }
        },
    )
