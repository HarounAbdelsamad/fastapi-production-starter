"""Outgoing webhook service.

Dispatch flow
-------------
1. ``dispatch_event(db, event, payload)`` finds all active endpoints subscribed
   to the event.
2. For each match it POSTs the JSON payload with an HMAC-SHA256 signature in
   the ``X-Webhook-Signature`` header (``sha256=<hex>``).
3. On non-2xx or network error: schedule exponential-backoff retry (max 5
   attempts: 30 s → 2 m → 8 m → 32 m → done/failed).
4. ``replay_delivery(db, delivery_id)`` re-sends the original payload and
   resets the attempt counter.

Consumers verify the signature with::

    import hashlib, hmac
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, request.headers["X-Webhook-Signature"])
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.webhook import WebhookDelivery, WebhookEndpoint

_MAX_ATTEMPTS = 5
_TIMEOUT = 10.0


def _sign(payload: str, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _matches(endpoint_events: str, event: str) -> bool:
    if endpoint_events.strip() == "*":
        return True
    return event in {e.strip() for e in endpoint_events.split(",")}


async def register_endpoint(
    db: AsyncSession,
    *,
    url: str,
    secret: str,
    events: str = "*",
) -> WebhookEndpoint:
    ep = WebhookEndpoint(url=url, secret=secret, events=events)
    db.add(ep)
    await db.commit()
    await db.refresh(ep)
    return ep


async def list_endpoints(db: AsyncSession) -> list[WebhookEndpoint]:
    result = await db.execute(
        select(WebhookEndpoint).order_by(WebhookEndpoint.created_at)
    )
    return list(result.scalars().all())


async def delete_endpoint(db: AsyncSession, endpoint_id: str) -> bool:
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id)
    )
    ep = result.scalars().first()
    if ep is None:
        return False
    await db.delete(ep)
    await db.commit()
    return True


async def dispatch_event(
    db: AsyncSession, event: str, payload: dict
) -> list[WebhookDelivery]:
    """Send *event* to all active subscribed endpoints.

    Returns the delivery records (one per endpoint).  Does *not* raise on
    delivery failure — failures are recorded in the delivery log.
    """
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.active.is_(True))
    )
    endpoints = result.scalars().all()

    deliveries: list[WebhookDelivery] = []
    payload_json = json.dumps(payload)

    for ep in endpoints:
        if not _matches(ep.events, event):
            continue
        delivery = WebhookDelivery(
            endpoint_id=ep.id,
            event=event,
            payload=payload_json,
            status="pending",
        )
        db.add(delivery)
        await db.flush()
        await _deliver(db, delivery, ep)
        deliveries.append(delivery)

    await db.commit()
    return deliveries


async def _deliver(
    db: AsyncSession, delivery: WebhookDelivery, endpoint: WebhookEndpoint
) -> None:
    delivery.attempts += 1
    signature = _sign(delivery.payload, endpoint.secret)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": delivery.event,
        "X-Webhook-Delivery": delivery.id,
        "X-Webhook-Signature": signature,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                endpoint.url, content=delivery.payload, headers=headers
            )
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:2000]
        if resp.is_success:
            delivery.status = "success"
            delivery.next_retry_at = None
        else:
            _schedule_retry(delivery)
    except Exception as exc:
        delivery.response_body = str(exc)[:2000]
        _schedule_retry(delivery)


def _schedule_retry(delivery: WebhookDelivery) -> None:
    """Set next_retry_at using exponential backoff; mark failed after max attempts."""
    if delivery.attempts >= _MAX_ATTEMPTS:
        delivery.status = "failed"
        delivery.next_retry_at = None
    else:
        # 30 s, 120 s, 480 s, 1920 s (≈ 32 min)
        delay = int(30 * math.pow(4, delivery.attempts - 1))
        delivery.next_retry_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            seconds=delay
        )
        delivery.status = "pending"


async def list_deliveries(
    db: AsyncSession,
    *,
    endpoint_id: str | None = None,
    limit: int = 50,
) -> list[WebhookDelivery]:
    q = select(WebhookDelivery).order_by(WebhookDelivery.created_at.desc()).limit(limit)
    if endpoint_id:
        q = q.where(WebhookDelivery.endpoint_id == endpoint_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def replay_delivery(db: AsyncSession, delivery_id: str) -> WebhookDelivery | None:
    """Re-send the original payload for *delivery_id* and reset retry state."""
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.id == delivery_id)
        .options(selectinload(WebhookDelivery.endpoint))
    )
    delivery = result.scalars().first()
    if delivery is None:
        return None
    delivery.status = "pending"
    delivery.next_retry_at = None
    await _deliver(db, delivery, delivery.endpoint)
    await db.commit()
    return delivery
