from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", summary="Admin dashboard placeholder")
async def get_admin_dashboard() -> dict[str, str]:
    return {"message": "Admin Dashboard"}
