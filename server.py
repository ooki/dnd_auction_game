

from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


app = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def add_client(self, websocket: WebSocket):        
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()



@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    
    try:
        await websocket.accept()
        agent_info = await websocket.receive_json()


    except WebSocketDisconnect:


    

    # try:
    #     while True:
    #         data = await websocket.receive_text()
    #         await manager.send_personal_message(f"You wrote: {data}", websocket)
    #         await manager.broadcast(f"Client #{client_id} says: {data}")
    # except WebSocketDisconnect:
    #     manager.disconnect(websocket)
    #     await manager.broadcast(f"Client #{client_id} left the chat")






