from fastapi import APIRouter, Header

router = APIRouter(prefix="/headers", tags=["Headers"])


@router.get("/", summary="Echo common request headers")
async def get_request_headers(
    user_agent: str | None = Header(None),
    accept_encoding: str | None = Header(None),
    referer: str | None = Header(None),
    connection: str | None = Header(None),
    accept_language: str | None = Header(None),
    host: str | None = Header(None),
) -> dict[str, str | None]:
    return {
        "User-Agent": user_agent,
        "Accept-Encoding": accept_encoding,
        "Referer": referer,
        "Accept-Language": accept_language,
        "Connection": connection,
        "Host": host,
    }
