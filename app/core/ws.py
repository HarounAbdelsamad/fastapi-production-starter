from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        for websocket in self.active_connections.get(user_id, []):
            await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for sockets in self.active_connections.values():
            for websocket in sockets:
                await websocket.send_json(message)


manager = ConnectionManager()
