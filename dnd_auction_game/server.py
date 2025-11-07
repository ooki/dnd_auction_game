import random
import math
import os
import asyncio
from typing import List, Dict, Union
from collections import defaultdict
import json
from contextlib import asynccontextmanager


from fastapi.responses import HTMLResponse
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

from dnd_auction_game.connection_manager import ConnectionManager
from dnd_auction_game.auction_house import AuctionHouse
from dnd_auction_game.leadboard import generate_leadboard   


game_token = os.environ.get("AH_GAME_TOKEN", "play123")
play_token = os.environ.get("AH_PLAY_TOKEN", "play123")
auction_house = AuctionHouse(game_token=game_token, play_token=play_token, save_logs=True)
connection_manager = ConnectionManager()

async def server_tick():
  while True:
        
    if auction_house.is_active:

            try:
                auction_house.process_pool_buys()
            except Exception as e:
                print("error in process_pool_buys:", e)

            try:
                auction_house.process_all_bids()
            except Exception as e:
                print("error in process_all_bids:", e)

            round_data = None
            try:
                round_data = auction_house.prepare_auctions_and_pool()
            except Exception as e:
                print("error in prepare_auctions_and_pool:", e)

            if round_data is not None:
                try:
                    await connection_manager.broadcast(round_data, timeout=0.5)
                except Exception as e:
                    print("error in broadcast:", e)

            if auction_house.round_counter >= auction_house.num_rounds_in_game:
                auction_house.is_active = False
                auction_house.is_done = True

                try:
                    await connection_manager.disconnect_all()
                except Exception as e:
                    print("error in disconnect_all:", e)
                

    await asyncio.sleep(1.0)



@asynccontextmanager
async def start_app_background_tasks(app: FastAPI):
    task = asyncio.create_task(server_tick())
    yield


app = FastAPI(lifespan=start_app_background_tasks)


@app.websocket("/ws/{token}")
async def websocket_endpoint_client(websocket: WebSocket, token: str):
    

    if token != auction_house.game_token:
        return

    if auction_house.is_done:
        auction_house.reset()

    try:
        await websocket.accept()
        agent_info = await websocket.receive_json()
        
        if len(agent_info["a_id"]) < 5 or len(agent_info["name"]) < 1 or len(agent_info["name"]) > 64:         
            await websocket.close()
            return
        
        if len(agent_info["player_id"]) < 1:
            await websocket.close()
            return
        
    except WebSocketDisconnect:
        return
    
    except:
        return
        
    
    # Block new players after the game has started; allow reconnections only
    if auction_house.is_active and agent_info["a_id"] not in auction_house.agents:
        try:
            await websocket.close()
        except:
            pass
        return
    
    try:        
        await connection_manager.add_connection(websocket)
        auction_house.add_agent(agent_info["name"], agent_info["a_id"], agent_info["player_id"])
        a_id = agent_info["a_id"]
        
        while auction_house.is_done is False:
            binds = {}
            pool = 0

            bids_and_pool = await websocket.receive_json()
            try:
                if bids_and_pool is None or bids_and_pool == {}:
                    continue
                
                bids = bids_and_pool.get("bids", {})
                pool = bids_and_pool.get("pool", 0)

            except Exception as e:
                print("error in receive_json:", e)
                continue
                        
            try:
                if pool > 0:
                    auction_house.register_pool_buy(a_id, pool)

                for auction_id, gold in bids.items():
                    auction_house.register_bid(a_id, auction_id, gold)

            except Exception as e:
                print("error in receive_json:", e)
                continue

        await websocket.close()
            
    except WebSocketDisconnect:        
        print("agent: {} disconnected.".format(agent_info["a_id"]))
        connection_manager.disconnect(websocket)
        return
    
    except:
        print("agent: {} was disconnected due to error.".format(agent_info["a_id"]))
        connection_manager.disconnect(websocket)
        return
    

@app.websocket("/ws_run/{play_token}")
async def websocket_endpoint_runner(websocket: WebSocket, play_token: str):
    
    print("websocket_endpoint_runner - PLAY TOKEN:", play_token)

    if play_token != auction_house.play_token:
        print("wrong play token")
        return
    
    if auction_house.is_done:
        print("starting new game")
        auction_house.reset()

    try:
        await websocket.accept()

        game_info = await websocket.receive_json()
        auction_house.num_rounds_in_game = int(game_info["num_rounds"])
        print("starting game with {} rounds".format(auction_house.num_rounds_in_game))

        game_info = {
            "game_token": auction_house.game_token,
            "num_players": len(auction_house.agents),
        }

        await websocket.send_json(game_info)        
        
    except WebSocketDisconnect:
        print("game not started due to disconnect.")
        return

    
    auction_house.assign_priorities()
    auction_house.is_active = True
    print("<started game>")

    try:
        await websocket.close()
    except:
        print("game not started due to error.")
        

@app.get("/reset/{play_token}")
async def reset_server(play_token: str):
    print("reset_server - PLAY TOKEN:", play_token)
    if play_token != auction_house.play_token:
        return {"ok": False, "error": "wrong play token"}

    # Disconnect any existing clients and reset state
    try:
        await connection_manager.disconnect_all()
    except Exception as e:
        print("error in disconnect_all during reset:", e)

    auction_house.reset()
    print("<server reset>")
    return {"ok": True}

@app.get("/")
async def get():    
    leadboard = []
    for a_id, info in auction_house.agents.items():
        name = auction_house.names[a_id]        
        leadboard.append([name, info["points"], info["gold"]])

    all_players = []
    leadboard.sort(key=lambda x:x[1], reverse=True)
    n_players = max(len(leadboard), 1)
    for k, (name, points, gold) in enumerate(leadboard):
        rank = (n_players - k) / n_players

        grade = "F"

        if points > 10:

            if rank > 0.89:
                grade = "A"
            elif rank > 0.75:
                grade = "B"
            elif rank > 0.60:
                grade = "C"
            elif rank > 0.40:
                grade = "D"
            else:
                grade = "E"

        all_players.append({'grade': grade, 'name': name, 'gold': gold, 'points': points})


    return HTMLResponse(generate_leadboard(all_players,
                                           auction_house.round_counter,
                                           auction_house.is_done))


