import random
import math
import os
import asyncio
from typing import List, Dict, Union
from collections import defaultdict
import json
from contextlib import asynccontextmanager
import threading


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

_previous_ranks: Dict[str, int] = {}
_rank_signals: Dict[str, Dict[str, int]] = {}
_last_rank_round: int = -1
_reset_lock = threading.Lock()


def _reset_game_state():
    """Reset auction house and clear leaderboard rank tracking state."""
    global _previous_ranks, _rank_signals, _last_rank_round
    auction_house.reset()
    _previous_ranks = {}
    _rank_signals = {}
    _last_rank_round = -1


def _compute_leadboard_state():
    global _previous_ranks, _rank_signals, _last_rank_round

    leadboard = []
    for a_id, info in auction_house.agents.items():
        name = auction_house.names[a_id]
        leadboard.append(
            {
                "id": a_id,
                "name": name,
                "points": info["points"],
                "gold": info["gold"],
            }
        )

    gold_income = 1000
    interest_rate = 1.0
    gold_limit = 2000
    gold_in_pool = max(auction_house.gold_in_pool, 0)

    # 20-round change calculations
    gold_income_change = 0.0
    interest_rate_change = 0.0
    gold_limit_change = 0.0

    try:
        rc = auction_house.round_counter
        gold_income = auction_house.gold_income_per_round[rc]
        interest_rate = auction_house.bank_interest_per_round[rc]
        gold_limit = auction_house.bank_limit_per_round[rc]
        
        # Calculate 20-round change (compare current to 20 rounds ago)
        if rc >= 20:
            old_income = auction_house.gold_income_per_round[rc - 20]
            old_interest = auction_house.bank_interest_per_round[rc - 20]
            old_limit = auction_house.bank_limit_per_round[rc - 20]
            if old_income > 0:
                gold_income_change = ((gold_income - old_income) / old_income) * 100
            if old_interest > 0:
                interest_rate_change = ((interest_rate - old_interest) / old_interest) * 100
            if old_limit > 0:
                gold_limit_change = ((gold_limit - old_limit) / old_limit) * 100
    except IndexError:
        pass

    leadboard.sort(key=lambda x: x["points"], reverse=True)
    n_players = max(len(leadboard), 1)

    current_round = auction_house.round_counter

    if current_round != _last_rank_round:
        updated_signals: Dict[str, Dict[str, int]] = {}
        for a_id, sig in _rank_signals.items():
            remaining = sig.get("remaining", 0)
            move = sig.get("move", 0)
            if remaining > 1 and move:
                updated_signals[a_id] = {"move": move, "remaining": remaining - 1}

        _rank_signals = updated_signals

        current_ranks: Dict[str, int] = {}
        for idx, entry in enumerate(leadboard):
            a_id = entry["id"]
            rank_index = idx + 1
            current_ranks[a_id] = rank_index
            prev_rank = _previous_ranks.get(a_id)
            if prev_rank is not None:
                if rank_index < prev_rank:
                    _rank_signals[a_id] = {"move": 1, "remaining": 5}
                elif rank_index > prev_rank:
                    _rank_signals[a_id] = {"move": -1, "remaining": 10}

        _previous_ranks = current_ranks
        _last_rank_round = current_round

    all_players = []
    for idx, entry in enumerate(leadboard):
        a_id = entry["id"]
        name = entry["name"]
        points = entry["points"]
        gold = entry["gold"]

        rank_fraction = (n_players - idx) / n_players

        grade = "F"
        if points > 10:

            if rank_fraction > 0.89:
                grade = "A"
            elif rank_fraction > 0.75:
                grade = "B"
            elif rank_fraction > 0.60:
                grade = "C"
            elif rank_fraction > 0.40:
                grade = "D"
            else:
                grade = "E"

        history = auction_house.points_gain_history.get(a_id, [])
        last_window = history[-10:]
        avg_gain_10 = float(sum(last_window)) / len(last_window) if last_window else 0.0

        sig = _rank_signals.get(a_id, {})
        move_val = sig.get("move", 0) if sig.get("remaining", 0) > 0 else 0
        if move_val > 0:
            rank_move = "up"
        elif move_val < 0:
            rank_move = "down"
        else:
            rank_move = "none"

        # Build sparkline data from cumulative points history
        sparkline = []
        cumulative = 0
        for gain in history[-20:]:
            cumulative += gain
            sparkline.append(cumulative)
        # Normalize sparkline relative to first value so it shows trend
        if sparkline:
            base = sparkline[0] if sparkline[0] != 0 else 1
            # Keep raw values for sparkline, JS will normalize
        
        all_players.append(
            {
                "id": a_id,
                "grade": grade,
                "name": name,
                "gold": gold,
                "points": points,
                "avg_gain_10": avg_gain_10,
                "rank_move": rank_move,
                "sparkline": sparkline,
            }
        )

    # Calculate min/max gold for volume bar normalization (relative scaling)
    gold_values = [p["gold"] for p in all_players] if all_players else [0]
    max_gold = max(gold_values) if gold_values else 1
    min_gold = min(gold_values) if gold_values else 0

    return {
        "players": all_players,
        "gold_income": gold_income,
        "interest_rate": interest_rate,
        "gold_limit": gold_limit,
        "gold_in_pool": gold_in_pool,
        "gold_income_change": round(gold_income_change, 1),
        "interest_rate_change": round(interest_rate_change, 1),
        "gold_limit_change": round(gold_limit_change, 1),
        "max_gold": max_gold,
        "min_gold": min_gold,
    }

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
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=start_app_background_tasks)


@app.websocket("/ws/{token}")
async def websocket_endpoint_client(websocket: WebSocket, token: str):
    

    if token != auction_house.game_token:
        return

    if auction_house.is_done:
        with _reset_lock:
            if auction_house.is_done:
                _reset_game_state()

    try:
        await websocket.accept()
        agent_info = await websocket.receive_json()
        
        a_id = agent_info.get("a_id", "")
        name = agent_info.get("name", "")
        player_id = agent_info.get("player_id", "")
        
        if len(a_id) < 5 or len(name) < 1 or len(name) > 64:
            await websocket.close()
            return
        
        if len(player_id) < 1:
            await websocket.close()
            return
        
        agent_info["a_id"] = a_id
        agent_info["name"] = name
        agent_info["player_id"] = player_id
        
    except WebSocketDisconnect:
        return
    
    except Exception:
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
        with _reset_lock:
            if auction_house.is_done:
                _reset_game_state()

    try:
        await websocket.accept()

        game_info = await websocket.receive_json()
        num_rounds = max(1, int(game_info.get("num_rounds", 10)))
        auction_house.num_rounds_in_game = num_rounds
        auction_house.set_num_rounds(auction_house.num_rounds_in_game)

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

    _reset_game_state()
    print("<server reset>")
    return {"ok": True}

@app.get("/")
async def get():    
    state = _compute_leadboard_state()

    return HTMLResponse(
        generate_leadboard(
            state["players"],
            auction_house.round_counter,
            auction_house.is_done,
            bank_state={
                "gold_income_per_round": state["gold_income"],
                "bank_interest_per_round": state["interest_rate"],
                "bank_limit_per_round": state["gold_limit"],
            },
            gold_in_pool=state["gold_in_pool"],
        )
    )


@app.get("/api/leadboard")
async def get_leadboard_data():
    state = _compute_leadboard_state()

    return {
        "round": auction_house.round_counter,
        "is_done": auction_house.is_done,
        "bank_state": {
            "gold_income_per_round": state["gold_income"],
            "bank_interest_per_round": state["interest_rate"],
            "bank_limit_per_round": state["gold_limit"],
        },
        "gold_in_pool": state["gold_in_pool"],
        "players": state["players"],
        "max_gold": state["max_gold"],
        "min_gold": state["min_gold"],
        "gold_income_change": state["gold_income_change"],
        "gold_limit_change": state["gold_limit_change"],
        "interest_rate_change": state["interest_rate_change"],
    }


