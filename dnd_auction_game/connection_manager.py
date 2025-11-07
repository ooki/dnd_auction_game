from typing import List
import asyncio
from fastapi import (
    WebSocket,
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def add_connection(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError: #already removed from list
            pass
        
    async def disconnect_all(self):
        print("disconnect all")
        for ws in self.active_connections:
            try:
                await ws.close()            
            except:
                print("error closing connection")
                pass

        self.active_connections = []

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
            except:
                pass
            try:
                self.active_connections.remove(ws)
            except ValueError:
                pass
