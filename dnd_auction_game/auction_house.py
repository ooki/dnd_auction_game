
from typing import List, Dict, Union
import random
from collections import defaultdict
import json
import math
import os
import hmac
import hashlib


MAX_INT_STR_LEN = 12
MAX_POINTS_REQUEST = 10**9


def parse_int(value, lo:int, hi:int):
    """Strictly parse an untrusted value into an int within [lo, hi].

    Accepts int (not bool), integral float, or a short numeric string.
    Returns None if the value is malformed or out of range.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        value = int(value)
    elif isinstance(value, str):
        value = value.strip()
        if len(value) > MAX_INT_STR_LEN:
            return None
        try:
            value = int(value)
        except ValueError:
            return None
    elif not isinstance(value, int):
        return None

    if value < lo or value > hi:
        return None
    return value


def generate_gold_random_walk(n_steps:int) -> List[float]:

    gold_per_round = 1000
    step_size = 150
    max_gold_per_round = 3000

    gold = [gold_per_round]
    for i in range(n_steps-1):
        next_gold = gold[-1] + random.randint(-step_size, step_size) - 1

        if next_gold < 10:
            next_gold = 10

        if next_gold > max_gold_per_round:
            next_gold = max_gold_per_round

        gold.append(next_gold)

        if i % 500 == 0:
            gold[-1] = gold_per_round + random.randint(-step_size // 2, step_size)

    return gold

def braavos_bank_limit_random_walk(n_steps:int) -> List[int]:

    upper_limit_start = 5000
    upper_limit_end = 20000
    step_size = 150

    upper_limits = [upper_limit_start]
    for i in range(n_steps-1):
        next_limit = upper_limits[-1] + random.randint(-step_size, step_size)

        if next_limit < 50:
            next_limit = 50

        if next_limit > upper_limit_end:
            next_limit = upper_limit_end

        upper_limits.append(next_limit)

        if i % 300 == 0:
            upper_limits[-1] = upper_limit_start

    return upper_limits

def braavos_bank_interest_rate_random_walk(n_steps:int) -> List[float]:

    start_rate = 1.00
    min_rate = 1.0
    max_rate = 1.1
    step_size = 0.02

    rates = [start_rate]
    for i in range(n_steps-1):
        next_rate = rates[-1] + random.uniform(-step_size, step_size)

        if next_rate < min_rate:
            next_rate = min_rate

        if next_rate > max_rate:
            next_rate = max_rate

        rates.append(next_rate)

        if i % 250 == 0:
            rates[-1] = start_rate + random.uniform(-step_size, step_size)


    return rates




class AuctionHouse:
    def __init__(self, game_token:str, play_token:str, save_logs=False, log_dir:str=None):
        self.is_done = False
        self.is_active = False
        
        self.log_dir = log_dir if log_dir is not None else os.environ.get("AH_LOG_DIR", ".")
        self.log_player_id_file = None
        self.log_file = None
        self.game_token = game_token
        self.play_token = play_token
        self.save_logs = save_logs
        self.gold_income = 1000

        # Gold received for one point spent. The initial round has no prior auctions.
        self.gold_per_point = 0.0
        self.current_point_purchases = {}

        self.agents = {}
        self.names = {}
        self.secrets = {}
        self.points_gain_history = {}
        self._prev_points = {}
        # Kept outside the public agent state: it is for leaderboard reporting
        # only and must never be included in websocket round payloads.
        self.points_sold_total = {}
        
        self.bank_interest_rate = 1.1
        self.auctions_per_agent = 1.5
        self.gold_back_fraction = 0.5
        
        self.die_sizes = [2,   3,  4,  6,   8, 10,  12,   20,  20]
        self.die_prob =  [7,   8,  9,  8,   6,  6,   5,    2,   1]
        self.max_n_die = [6,   7, 10,  2,   3,  3,   6,    2,   4]
        self.max_bonus = [11,  2, 16,  8,  21,  2,   5,    7,   3] 
        self.min_bonus = [-2, -8, -5, -5, -10, -4,  -5,  -4,  -4]

        self.round_counter = 0
        self.auction_counter = 1
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.num_rounds_in_game = 10
        self.priority = {}

        self.num_rounds_in_game : int = None
        self.gold_income_per_round : List[int] = None
        self.bank_limit_per_round : List[int] = None
        self.bank_interest_per_round : List[float] = None
        self.set_num_rounds(10)
        
        # set the logfile
        self._find_log_file()

        if self.save_logs:
            print("logging to: '{}'".format(self.log_file))

    
    def _find_log_file(self):
        """Pick the next unused log file pair in log_dir (one pair per game)."""
        if not self.save_logs:
            self.log_file = None
            self.log_player_id_file = None
            return

        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except OSError as e:
            print("error creating log dir '{}': {} - logging disabled".format(self.log_dir, e))
            self.save_logs = False
            self.log_file = None
            self.log_player_id_file = None
            return

        i = 1
        while True:
            f = os.path.join(self.log_dir, "auction_house_log_{}.jsonln".format(i))
            f_player_id = os.path.join(self.log_dir, "auction_house_log_player_id_{}.jsonln".format(i))
            if not os.path.isfile(f) and not os.path.isfile(f_player_id):
                break
            i += 1

        self.log_file = f
        self.log_player_id_file = f_player_id



    def set_num_rounds(self, num_rounds:int):
        self.num_rounds_in_game = num_rounds

        self.gold_income_per_round = generate_gold_random_walk(num_rounds)
        self.bank_limit_per_round = braavos_bank_limit_random_walk(num_rounds)
        self.bank_interest_per_round = braavos_bank_interest_rate_random_walk(num_rounds)


    def reset(self):
        self.is_done = False
        self.is_active = False
        self.agents = {}
        self.names = {}
        self.secrets = {}
        self.points_gain_history = {}
        self._prev_points = {}
        self.points_sold_total = {}
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.round_counter = 0
        self.auction_counter = 1
        self.num_rounds_in_game = 10
        self.priority = {}
        self.gold_per_point = 0.0
        self.current_point_purchases = {}
        self.set_num_rounds(10)
        self._find_log_file()
        
    
    def assign_priorities(self):
        self.priority = {}
        used = set()
        for a_id in self.agents.keys():
            while True:
                p = random.randint(1, 10**9)
                if p not in used:
                    used.add(p)
                    self.priority[a_id] = p
                    break
        
    @staticmethod
    def _hash_secret(secret:str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def verify_secret(self, a_id:str, secret:str) -> bool:
        """True if a_id is known and secret matches the one given at first connect."""
        stored = self.secrets.get(a_id)
        if stored is None:
            return False
        return hmac.compare_digest(stored, self._hash_secret(secret))

    def add_agent(self, name:str, a_id:str, player_id:str, secret:str) -> bool:
        """Register a new agent, or accept a reconnect if the secret matches.

        Returns False if a_id is already taken and the secret does not match.
        """
        if a_id in self.agents:
            if not self.verify_secret(a_id, secret):
                print("Agent id:{} rejected: wrong secret".format(a_id))
                return False
            print("Agent {}  id:{} reconnected".format(name, a_id))
            return True

        if self.save_logs and self.log_player_id_file is not None:
            try:
                with open(self.log_player_id_file, 'a') as fp:
                    pid = {"player_id": player_id, "agent_id": a_id, "name": name}
                    fp.write("{}\n".format(json.dumps(pid)))
            except Exception as e:
                print("error writing player id log:", e)
                self.save_logs = False
                    
        self.agents[a_id] = {"gold": 0, "points": 0}
        self.names[a_id] = name
        self.secrets[a_id] = self._hash_secret(secret)
        self.points_gain_history.setdefault(a_id, [])
        self._prev_points.setdefault(a_id, 0)
        self.points_sold_total.setdefault(a_id, 0)
        return True
    
    
    def prepare_auctions(self):
        prev_auctions = self.current_auctions
        prev_bids = self.current_bids
        prev_rolls = self.current_rolls
        
        self.current_bids = defaultdict(list)
        self.current_auctions, self.current_rolls = self._generate_auctions()


        # update gold for agents - clamp round_counter to valid index
        rc = min(self.round_counter, len(self.bank_limit_per_round) - 1)
        upper_rate = self.bank_limit_per_round[rc]
        interest_rate = self.bank_interest_per_round[rc]
        gold_income = self.gold_income_per_round[rc]
        
        # update gold for agents
        for agent in self.agents.values():

            # bank of Braavos gives interest on stored gold
            interest_available_gold = 0
            if agent["gold"] >= upper_rate:
                interest_available_gold = upper_rate
            else:
                interest_available_gold = agent["gold"]

            agent["gold"] += int(interest_available_gold * (interest_rate - 1))
            agent["gold"] += gold_income
                
                
        out_prev_state = {}
        for auction_id, info in prev_auctions.items():
            out_prev_state[auction_id] = {}
            out_prev_state[auction_id].update(info)            
            out_prev_state[auction_id]["reward"] = prev_rolls[auction_id]
            
            prev_bids[auction_id].sort(key=lambda x:x[1], reverse=True)            
            out_prev_state[auction_id]["bids"] = [{"a_id": a_id, "gold": g} for a_id, g in prev_bids[auction_id]]

        state = {
            "round": self.round_counter,
            # Public team labels shown on the leaderboard. Player IDs are never broadcast.
            "team_names": self.names.copy(),
            "states": self.agents,
            "auctions": self.current_auctions,
            "prev_auctions": out_prev_state,
            "gold_per_point": self.gold_per_point,
            "remainder_gold_income": self.gold_income_per_round[self.round_counter:],
            "remainder_bank_limit": self.bank_limit_per_round[self.round_counter:],
            "remainder_bank_interest": self.bank_interest_per_round[self.round_counter:],
        }

        if self.save_logs and self.log_file is not None:
            try:
                with open(self.log_file, "a") as fp:
                    fp.write("{}\n".format(json.dumps(state)))
            except Exception as e:
                print("error writing auction log:", e)
                self.save_logs = False
        
        for a_id, info in self.agents.items():
            current_points = info.get("points", 0)
            prev_points = self._prev_points.get(a_id, 0)
            gain = current_points - prev_points
            history = self.points_gain_history.get(a_id)
            if history is None:
                history = []
            history.append(gain)
            if len(history) > 100:
                history = history[-100:]
            self.points_gain_history[a_id] = history
            self._prev_points[a_id] = current_points

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

    def register_point_purchase(self, a_id: str, points: int):
        """Register this round's point-to-gold purchase request.

        A request replaces any earlier request from the same agent in this round.
        Settlement occurs at the next tick, *after* this round's auctions are
        resolved, using the rate that was visible to the agent. The request is
        clamped to the -100 floor at settlement time, so points won in this
        round's auctions can be sold in the same request.
        """
        if a_id not in self.agents:
            return

        points = parse_int(points, 0, MAX_POINTS_REQUEST)
        if points is None:
            return

        self.current_point_purchases[a_id] = points

    def process_point_purchases(self, gold_per_point: float):
        """Settle requested purchases at `gold_per_point` while enforcing the -100 point floor.

        Must run after process_all_bids() so the gold cannot be used for bids in
        the round it was earned, and so freshly won points are sellable.
        """
        for a_id, requested_points in self.current_point_purchases.items():
            agent = self.agents.get(a_id)
            if agent is None:
                continue

            points = min(requested_points, max(0, agent["points"] + 100))
            agent["points"] -= points
            self.points_sold_total[a_id] = self.points_sold_total.get(a_id, 0) + points
            # Gold balances and bids are integers, so fractional gold is rounded down.
            agent["gold"] += int(points * gold_per_point)

        self.current_point_purchases = {}



    def register_bid(self, a_id:str, auction_id:str, gold:int):       
        if auction_id not in self.current_auctions:
            return
        
        if a_id not in self.agents:
            return

        gold = parse_int(gold, 1, self.agents[a_id]["gold"])
        if gold is None:
            return

        self.current_bids[auction_id].append( (a_id, gold) )
        self.agents[a_id]["gold"] -= gold

    
    def process_all_bids(self):
        winning_gold_total = 0
        winning_points_total = 0
        for auction_id, bids in self.current_bids.items():
            if not bids:
                continue
            points = self.current_rolls.get(auction_id)
            if points is None:
                continue
            win_amount = max(bids, key=lambda x:x[1])[1]
            tied = [a_id for a_id, bid in bids if bid == win_amount]
            if len(tied) == 1:
                winner = tied[0]
            else:
                winner = max(tied, key=lambda a: self.priority.get(a, 0))
                losers_tied = [a for a in tied if a != winner]
                if losers_tied:
                    weights = [1.0 / max(self.priority.get(a, 1), 1) for a in losers_tied]
                    swap_with = random.choices(losers_tied, weights=weights, k=1)[0]
                    pw = self.priority.get(winner, 0)
                    pl = self.priority.get(swap_with, 0)
                    self.priority[winner] = pl
                    self.priority[swap_with] = pw

            # The next round's exchange rate uses one selected winning bid per auction.
            winning_gold_total += win_amount
            winning_points_total += points

            # update now that we know the winners
            for a_id, bid in bids:
                if a_id == winner and bid == win_amount:
                    self.agents[a_id]["points"] += points
                else:
                    back_value = int(bid * self.gold_back_fraction)
                    self.agents[a_id]["gold"] += back_value

        self.gold_per_point = winning_gold_total / max(1, winning_points_total)
