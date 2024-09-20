


from typing import List
from fastapi import (
    WebSocket,
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def add_connection(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
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

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


