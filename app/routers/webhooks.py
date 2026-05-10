"""Outgoing webhook management endpoints (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AnyHttpUrl, BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "service-account"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RegisterEndpointRequest(BaseModel):
    url: AnyHttpUrl
    secret: str
    events: str = "*"  # "*" for all, or comma-separated event names


class EndpointResponse(BaseModel):
    id: str
    url: str
    events: str
    active: bool
    created_at: str


class DeliveryResponse(BaseModel):
    id: str
    endpoint_id: str
    event: str
    status: str
    attempts: int
    response_status: int | None
    next_retry_at: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=EndpointResponse)
async def register_endpoint(
    body: RegisterEndpointRequest,
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
) -> EndpointResponse:
    ep = await webhook_service.register_endpoint(
        db, url=str(body.url), secret=body.secret, events=body.events
    )
    return EndpointResponse(
        id=ep.id,
        url=ep.url,
        events=ep.events,
        active=ep.active,
        created_at=ep.created_at.isoformat(),
    )


@router.get("/", response_model=list[EndpointResponse])
async def list_endpoints(
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
) -> list[EndpointResponse]:
    endpoints = await webhook_service.list_endpoints(db)
    return [
        EndpointResponse(
            id=ep.id,
            url=ep.url,
            events=ep.events,
            active=ep.active,
            created_at=ep.created_at.isoformat(),
        )
        for ep in endpoints
    ]


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
) -> None:
    deleted = await webhook_service.delete_endpoint(db, endpoint_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Endpoint not found")


@router.get("/deliveries/", response_model=list[DeliveryResponse])
async def list_deliveries(
    endpoint_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
) -> list[DeliveryResponse]:
    deliveries = await webhook_service.list_deliveries(
        db, endpoint_id=endpoint_id, limit=limit
    )
    return [
        DeliveryResponse(
            id=d.id,
            endpoint_id=d.endpoint_id,
            event=d.event,
            status=d.status,
            attempts=d.attempts,
            response_status=d.response_status,
            next_retry_at=d.next_retry_at.isoformat() if d.next_retry_at else None,
            created_at=d.created_at.isoformat(),
        )
        for d in deliveries
    ]


@router.post("/deliveries/{delivery_id}/replay", response_model=DeliveryResponse)
async def replay_delivery(
    delivery_id: str,
    db: AsyncSession = Depends(get_session),
    _admin: User = Depends(_require_admin),
) -> DeliveryResponse:
    delivery = await webhook_service.replay_delivery(db, delivery_id)
    if delivery is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return DeliveryResponse(
        id=delivery.id,
        endpoint_id=delivery.endpoint_id,
        event=delivery.event,
        status=delivery.status,
        attempts=delivery.attempts,
        response_status=delivery.response_status,
        next_retry_at=delivery.next_retry_at.isoformat() if delivery.next_retry_at else None,
        created_at=delivery.created_at.isoformat(),
    )
