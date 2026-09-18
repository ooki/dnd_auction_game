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
from dnd_auction_game.auction_house import AuctionHouse, parse_int
from dnd_auction_game.leadboard import generate_leadboard   


game_token = os.environ.get("AH_GAME_TOKEN", "play123")
play_token = os.environ.get("AH_PLAY_TOKEN", "play123")
MAX_ROUNDS = int(os.environ.get("AH_MAX_ROUNDS", "10000"))
MAX_AGENTS = int(os.environ.get("AH_MAX_AGENTS", "200"))
auction_house = AuctionHouse(game_token=game_token, play_token=play_token, save_logs=True)
connection_manager = ConnectionManager()

_previous_ranks: Dict[str, int] = {}
_rank_signals: Dict[str, Dict[str, int]] = {}
_last_rank_round: int = -1
# Serialises game-state transitions (tick, reset, start) so a reset can never
# interleave with a round being processed.
_state_lock = asyncio.Lock()


def _reset_game_state():
    """Reset auction house and clear leaderboard rank tracking state."""
    global _previous_ranks, _rank_signals, _last_rank_round
    auction_house.reset()
    _previous_ranks = {}
    _rank_signals = {}
    _last_rank_round = -1


async def _reset_if_done():
    """Start a fresh game if the previous one has finished."""
    if not auction_house.is_done:
        return
    async with _state_lock:
        if auction_house.is_done:
            _reset_game_state()


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
    gold_per_point = auction_house.gold_per_point

    # 20-round change calculations
    gold_income_change = 0.0
    interest_rate_change = 0.0
    gold_limit_change = 0.0

    try:
        rc = auction_house.round_counter
        max_idx = len(auction_house.gold_income_per_round) - 1
        rc_clamped = min(rc, max_idx) if max_idx >= 0 else 0
        gold_income = auction_house.gold_income_per_round[rc_clamped]
        interest_rate = auction_house.bank_interest_per_round[rc_clamped]
        gold_limit = auction_house.bank_limit_per_round[rc_clamped]
        
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
        "gold_per_point": gold_per_point,
        "gold_income_change": round(gold_income_change, 1),
        "interest_rate_change": round(interest_rate_change, 1),
        "gold_limit_change": round(gold_limit_change, 1),
        "max_gold": max_gold,
        "min_gold": min_gold,
    }

async def _process_round():
    # Rate the agents saw when they submitted this round's requests.
    published_rate = auction_house.gold_per_point

    # Resolve auctions first, then settle point sales: gold from a sale can
    # never fund bids in the same round, but points won this round can be sold.
    try:
        auction_house.process_all_bids()
    except Exception as e:
        print("error in process_all_bids:", e)

    try:
        auction_house.process_point_purchases(published_rate)
    except Exception as e:
        print("error in process_point_purchases:", e)

    round_data = None
    try:
        round_data = auction_house.prepare_auctions()
    except Exception as e:
        print("error in prepare_auctions:", e)

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


async def server_tick():
    while True:
        async with _state_lock:
            if auction_house.is_active:
                await _process_round()

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
        await websocket.close(code=1008)  # policy violation -> HTTP 403 before accept
        return

    await _reset_if_done()

    try:
        await websocket.accept()
        agent_info = await websocket.receive_json()
        
        a_id = agent_info.get("a_id", "")
        name = agent_info.get("name", "")
        player_id = agent_info.get("player_id", "")
        secret = agent_info.get("secret", "")
        
        if not all(isinstance(v, str) for v in (a_id, name, player_id, secret)):
            await websocket.close()
            return

        if len(a_id) < 5 or len(name) < 1 or len(name) > 64:
            await websocket.close()
            return
        
        if len(player_id) < 1 or len(player_id) > 128:
            await websocket.close()
            return

        if len(secret) < 8 or len(secret) > 256:
            await websocket.close()
            return
        
        agent_info["a_id"] = a_id
        agent_info["name"] = name
        agent_info["player_id"] = player_id
        agent_info["secret"] = secret
        
    except WebSocketDisconnect:
        return
    
    except Exception:
        return
        
    
    # Block new players after the game has started; allow reconnections only
    if auction_house.is_active and agent_info["a_id"] not in auction_house.agents:
        try:
            await websocket.close()
        except Exception:
            pass
        return
    
    a_id = agent_info["a_id"]
    if a_id not in auction_house.agents and len(auction_house.agents) >= MAX_AGENTS:
        print("agent: {} rejected: server full ({} agents)".format(a_id, MAX_AGENTS))
        try:
            await websocket.close()
        except Exception:
            pass
        return

    accepted = auction_house.add_agent(
        agent_info["name"], a_id, agent_info["player_id"], agent_info["secret"]
    )
    if not accepted:
        try:
            await websocket.close()
        except Exception:
            pass
        return

    try:        
        await connection_manager.add_connection(websocket, a_id=a_id)
        
        while auction_house.is_done is False:
            bids_and_purchase = await websocket.receive_json()
            if not isinstance(bids_and_purchase, dict) or not bids_and_purchase:
                continue

            bids = bids_and_purchase.get("bids", {})
            points_to_spend = bids_and_purchase.get("points_to_spend", 0)

            try:
                auction_house.register_point_purchase(a_id, points_to_spend)

                if isinstance(bids, dict):
                    # An agent can hold at most one bid per open auction; anything
                    # beyond that is noise and is not worth iterating.
                    max_bids = len(auction_house.current_auctions)
                    for auction_id, gold in list(bids.items())[:max_bids]:
                        if isinstance(auction_id, str):
                            auction_house.register_bid(a_id, auction_id, gold)

            except Exception as e:
                print("error processing bids:", e)
                continue

        await websocket.close()
            
    except WebSocketDisconnect:        
        print("agent: {} disconnected.".format(agent_info["a_id"]))
        connection_manager.disconnect(websocket)
        return
    
    except Exception as e:
        print("agent: {} was disconnected due to error: {!r}".format(agent_info["a_id"], e))
        connection_manager.disconnect(websocket)
        return
    

@app.websocket("/ws_run/{play_token}")
async def websocket_endpoint_runner(websocket: WebSocket, play_token: str):
    
    if play_token != auction_house.play_token:
        print("ws_run: rejected request with wrong play token")
        await websocket.close(code=1008)
        return
    
    await _reset_if_done()

    try:
        await websocket.accept()

        game_info = await websocket.receive_json()
        requested = game_info.get("num_rounds", 10) if isinstance(game_info, dict) else None
        num_rounds = parse_int(requested, 1, MAX_ROUNDS)
        if num_rounds is None:
            print("invalid num_rounds: {!r} (must be 1..{})".format(requested, MAX_ROUNDS))
            await websocket.send_json({"error": "num_rounds must be an int in 1..{}".format(MAX_ROUNDS)})
            await websocket.close()
            return

        async with _state_lock:
            if auction_house.is_active:
                print("game already running; ignoring start request")
                await websocket.send_json({"error": "a game is already running; reset the server first"})
                await websocket.close()
                return

            auction_house.num_rounds_in_game = num_rounds
            auction_house.set_num_rounds(auction_house.num_rounds_in_game)
            auction_house.assign_priorities()
            auction_house.is_active = True

        print("<started game with {} rounds>".format(num_rounds))

        await websocket.send_json({
            "game_token": auction_house.game_token,
            "num_players": len(auction_house.agents),
        })
        await websocket.close()

    except WebSocketDisconnect:
        print("runner disconnected.")
    except Exception as e:
        print("error in runner endpoint:", repr(e))


@app.post("/reset/{play_token}")
async def reset_server(play_token: str):
    if play_token != auction_house.play_token:
        print("reset: rejected request with wrong play token")
        return {"ok": False, "error": "wrong play token"}

    async with _state_lock:
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
            gold_per_point=state["gold_per_point"],
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
        "gold_per_point": state["gold_per_point"],
        # a_id is the reconnect identity; never expose it on the public API.
        "players": [{k: v for k, v in p.items() if k != "id"} for p in state["players"]],
        "max_gold": state["max_gold"],
        "min_gold": state["min_gold"],
        "gold_income_change": state["gold_income_change"],
        "gold_limit_change": state["gold_limit_change"],
        "interest_rate_change": state["interest_rate_change"],
    }


