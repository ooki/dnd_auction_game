import html
import random
import math
import asyncio
from typing import List, Dict, Union
from collections import defaultdict
import json
from contextlib import asynccontextmanager


import os
import websockets
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse



@asynccontextmanager
async def start_server_loop(app: FastAPI):

    asyncio.create_task(update_games_task())    
    yield


app = FastAPI(lifespan=start_server_loop)




def generate_leadboard(leadboard, round, is_done):

    do_refresh = """<meta http-equiv="refresh" content="1">"""
    if is_done:
        do_refresh = ""
    html_head = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leadboard - Auction Game</title>
        {}
    </head>
    """.format(do_refresh)

    h = ""
    if is_done:
        h = " - FINISHED GAME"
    else:
        h = "Round: {}".format(round)
        
    html_body_top = """
    <body>
        <h2>Leadboard {}</h2>        
    """.format(h)
    
    html_body_bottom = """                
    </body>    
    </html>
    """
    board = []
    for rank, (a_name, points, gold) in enumerate(leadboard):
        safe_name = html.escape(a_name)
        if rank == 0:
            board.append("<p><b>#{} - {} : gold {} : points {}</b></p>".format(rank+1, safe_name, gold, points))
        else:
            board.append("<p>#{} - {} : gold {} : <b>points {}</b></p>".format(rank+1, safe_name, gold, points))
        
    return html_head + html_body_top + "\n".join(board) + html_body_bottom





class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def add_connection(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def disconnect_all(self):
        for ws in self.active_connections:
            await ws.close()            

    async def send_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)



class AuctionHouse:
    def __init__(self, game_token:str, play_token:str, save_logs=False):
        self.is_done = False
        
        self.game_token = game_token
        self.play_token = play_token
        self.save_logs = save_logs
        self.gold_income = 1000
        
        self.agents = {}
        self.names = {}
        
        self.give_out_gold_rounds = 1       
        self.auctions_per_agent = 1.5
        self.gold_back_fraction = 0.6
        
        self.die_sizes = [2,   3,  4,  6,   8, 10,  12,   20,  20]
        self.die_prob =  [8,   8,  9,  8,   6,  6,   5,    2,   1]
        self.max_n_die = [5,   4, 10,  2,   3,  3,   6,    2,   4]
        self.max_bonus = [10,  2, 16,  8,  21,  2,   5,    7,   3] 
        self.min_bonus = [-2, -5, -5, -5, -10, -4,  -5,  -2,  -1]

        self.round_counter = 0
        self.auction_counter = 1
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)

    
    def reset(self):
        self.is_done = False
        self.agents = {}
        self.names = {}
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.round_counter = 0
        self.auction_counter = 1
        
    
    def add_agent(self, name:str, a_id:str):
        if a_id in self.agents:
            print("Agent {}  id:{} reconnected".format(name, a_id))
            return
        
        self.agents[a_id] = {"gold": 0, "points": 0}
        self.names[a_id] = name
    
    
    def prepare_auction(self):        
        prev_auctions = self.current_auctions
        prev_bids = self.current_bids
        prev_rolls = self.current_rolls
        
        self.current_bids = defaultdict(list)
        self.current_auctions, self.current_rolls = self._generate_auctions()        
        
        # update gold for agents
        if (self.round_counter % self.give_out_gold_rounds) == 0:
            for agent in self.agents.values():
                agent["gold"] += self.gold_income
                
                
        out_prev_state = {}
        for auction_id, info in prev_auctions.items():
            out_prev_state[auction_id] = {}
            out_prev_state[auction_id].update(info)            
            out_prev_state[auction_id]["reward"] = prev_rolls[auction_id]
            
            prev_bids[auction_id].sort(key=lambda x:x[1], reverse=True)            
            out_prev_state[auction_id]["bids"] = [{"a_id": a_id, "gold": g} for a_id, g in prev_bids[auction_id]]

        state = {
            "round": self.round_counter,
            "states": self.agents,
            "auctions": self.current_auctions,
            "prev_auctions": out_prev_state
        }

        if self.save_logs:
            with open("./auction_house_log.jsonln", "a") as fp:
                fp.write("{}\n".format(json.dumps(state)))
        
        self.round_counter += 1
        return state
        
  
    def _generate_auctions(self) -> Dict[str, dict]:
        auctions = {}
        rolls = {} # the amount rolled - hidden for agents
        
        indices = list(range(len(self.die_sizes)))
                
        n_auctions = int(math.ceil(self.auctions_per_agent*len(self.agents)))
                
        for _ in range(n_auctions):
            i = random.choices(indices, weights=self.die_prob, k=1)[0]            
            die = self.die_sizes[i]
            n_dices = random.randint(1, self.max_n_die[i])
            bonus = random.randint(self.min_bonus[i], self.max_bonus[i])
                                    
            auction_id = "a{}".format(self.auction_counter)
            a = {"die": die, "num": n_dices, "bonus": bonus}
            auctions[auction_id] = a
            self.auction_counter += 1
            
            points = sum( (random.randint(1, a["die"]) for _ in range(a["num"])) )
            points += a["bonus"]
            rolls[auction_id] = points
                    
        return auctions, rolls
    
    def register_bid(self, a_id:str, auction_id:str, gold:int):        
        if auction_id not in self.current_auctions:
            return
        
        gold = int(gold)
        if gold < 1:
            return
                
        if self.agents[a_id]["gold"] < gold:
            gold = self.agents[a_id]["gold"]

        self.current_bids[auction_id].append( (a_id, gold) )
        self.agents[a_id]["gold"] -= gold
    
    def process_all_bids(self):        
        
        for auction_id, bids in self.current_bids.items():
            win_amount = max(bids, key=lambda x:x[1])[1]
            for a_id, bid in bids:
                if bid == win_amount:
                    self.agents[a_id]["points"] += self.current_rolls[auction_id]
                
                else:
                    # cashback
                    back_value = int(bid * self.gold_back_fraction)
                    self.agents[a_id]["gold"] += back_value
            
        
        
game_token = os.environ.get("AH_GAME_TOKEN", "play123")
play_token = os.environ.get("AH_PLAY_TOKEN", "play123")

game_manager = AuctionHouse(game_token=game_token, play_token=play_token, save_logs=True)
connection_manager = ConnectionManager()

@app.websocket("/ws/{token}")
async def websocket_endpoint_client(websocket: WebSocket, token: str):
    
    if token != game_manager.game_token:
        return

    if game_manager.is_done:
        game_manager.reset()

    try:
        await websocket.accept()        
        agent_info = await websocket.receive_json()
        
        if len(agent_info["a_id"]) < 5 or len(agent_info["name"]) < 1 or len(agent_info["name"]) > 64:            
            await websocket.close()
            return
        
    except WebSocketDisconnect:        
        return
    
    except:
        return
        
    
    try:        
        await connection_manager.add_connection(websocket)
        game_manager.add_agent(agent_info["name"], agent_info["a_id"])
        a_id = agent_info["a_id"]
        
        while True:
            bids = await websocket.receive_json()
                        
            for auction_id, gold in bids.items():
                game_manager.register_bid(a_id, auction_id, gold)                
            
    except WebSocketDisconnect:        
        print("agent: {} disconnected.".format(agent_info["a_id"]))
        connection_manager.disconnect(websocket)
        return
    
    except:
        print("agent: {} was disconnected due to error.".format(agent_info["a_id"]))
        connection_manager.disconnect(websocket)
        return
    

    

@app.websocket("/ws_run/{token}")
async def websocket_endpoint_runner(websocket: WebSocket, token: str):
    
    if token != game_manager.play_token:
        return
    
    if game_manager.is_done:
        print("starting new game")
        game_manager.reset()
        
    
    try:
        await websocket.accept()
        await asyncio.sleep(0.01)        
        
        while True:
            round_info = await websocket.receive_json()
            game_manager.process_all_bids()
                                            
            round_data = game_manager.prepare_auction()            
            await connection_manager.broadcast(round_data)

            if round_info["done"] == 1:
                print("play is done.")
                game_manager.is_active = False
                game_manager.is_done = True
                break

            
    except WebSocketDisconnect:
        game_manager.is_active = True
        print("<game done after {} rounds>".format(game_manager.round_counter))
    
    finally:     
        if game_manager.is_done == True:
            await connection_manager.disconnect_all()
            game_manager.is_done = True


@app.get("/")
async def get():    
    leadboard = []
    for a_id, info in game_manager.agents.items():
        name = game_manager.names[a_id]        
        leadboard.append((name, info["points"], info["gold"]))
        
    leadboard.sort(key=lambda x:x[1], reverse=True)    
    return HTMLResponse(generate_leadboard(leadboard, game_manager.round_counter ,game_manager.is_done))



async def update_games_task():
    while True:        
        await game_manager.update()        
        await asyncio.sleep(0.1)