from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.auth import decode_token
from app.core.ws import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    user_id = payload.sub
    await manager.connect(websocket, user_id)
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_json({"echo": message})
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
