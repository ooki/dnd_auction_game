from typing import List, Dict, Optional
import asyncio
from fastapi import (
    WebSocket,
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.agent_connections: Dict[str, WebSocket] = {}

    async def add_connection(self, websocket: WebSocket, a_id: Optional[str] = None):
        if a_id is not None:
            old = self.agent_connections.get(a_id)
            if old is not None and old is not websocket:
                self.disconnect(old)
                try:
                    await old.close()
                except Exception:
                    pass
            self.agent_connections[a_id] = websocket
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError: #already removed from list
            pass
        for a_id, ws in list(self.agent_connections.items()):
            if ws is websocket:
                del self.agent_connections[a_id]
        
    async def disconnect_all(self):
        print("disconnect all")
        for ws in self.active_connections:
            try:
                await ws.close()            
            except Exception:
                print("error closing connection")

        self.active_connections = []
        self.agent_connections = {}

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, timeout: float = 1.0):
        stale = []
        for connection in list(self.active_connections):
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=timeout)
            except Exception:
                stale.append(connection)
        for ws in stale:
            try:
                await ws.close()
            except Exception:
                pass
            try:
                self.active_connections.remove(ws)
            except ValueError:
                pass
