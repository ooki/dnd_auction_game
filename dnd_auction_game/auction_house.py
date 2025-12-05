
from typing import List, Dict, Union
import random
from collections import defaultdict
import json
import math
import os


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
    def __init__(self, game_token:str, play_token:str, save_logs=False):
        self.is_done = False
        self.is_active = False
        
        self.log_player_id_file = None
        self.log_file = None
        self.game_token = game_token
        self.play_token = play_token
        self.save_logs = save_logs
        self.gold_income = 1000

        self.gold_in_pool = 0 # the gold that was removed during the cashback
        self.convert_to_pool_fraction = 0.9 # the fraction of gold that is returned to the hoard
        
        self.agents = {}
        self.names = {}
        self.points_gain_history = {}
        self._prev_points = {}
        
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
        self.current_pool_buys = {}

        self.num_rounds_in_game : int = None
        self.gold_income_per_round : List[int] = None
        self.bank_limit_per_round : List[int] = None
        self.bank_interest_per_round : List[float] = None
        self.set_num_rounds(10)
        
        # set the logfile
        self._find_log_file()

        print("logging to: '{}'".format(self.log_file))

    
    def _find_log_file(self):
        if self.log_file is None:            
            i = 1

            f = "./auction_house_log_{}.jsonln".format(i)         
            f_player_id = "./auction_house_log_player_id_{}.jsonln".format(i)   
            while os.path.isfile(f):
                f = "./auction_house_log_{}.jsonln".format(i)
                f_player_id = "./auction_house_log_player_id_{}.jsonln".format(i)   
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
        self.points_gain_history = {}
        self._prev_points = {}
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.round_counter = 0
        self.auction_counter = 1
        self.num_rounds_in_game = 10
        self.priority = {}
        self.gold_in_pool = 0
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
        
    def add_agent(self, name:str, a_id:str, player_id:str):
        if a_id in self.agents:
            print("Agent {}  id:{} reconnected".format(name, a_id))
            return

        try:
            with open(self.log_player_id_file, 'a') as fp:
                pid = {"player_id": player_id, "agent_id": a_id, "name": name}
                fp.write("{}\n".format(json.dumps(pid)))
        except Exception as e:
            print("error writing player id log:", e)
            self.save_logs = False
                    
        self.agents[a_id] = {"gold": 0, "points": 0}
        self.names[a_id] = name
        self.points_gain_history.setdefault(a_id, [])
        self._prev_points.setdefault(a_id, 0)
    
    
    def prepare_auctions_and_pool(self):        
        prev_auctions = self.current_auctions
        prev_bids = self.current_bids
        prev_rolls = self.current_rolls
        
        self.current_bids = defaultdict(list)
        self.current_auctions, self.current_rolls = self._generate_auctions()

        # copy the pool buys to broodcast, reset the pool buys
        buy_pool_copy = self.current_pool_buys.copy()
        self.current_pool_buys = {} 


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
            "states": self.agents,
            "auctions": self.current_auctions,
            "prev_auctions": out_prev_state,
            "prev_pool_buys": buy_pool_copy,
            "pool": self.gold_in_pool,
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

    def register_pool_buy(self, a_id:str, points:int):
        if a_id not in self.agents:
            return
        
        try:
            points = int(points)
        except (TypeError, ValueError):
            return
        
        points = max(points, 0)

        self.current_pool_buys[a_id] = points
            
        # register the negative amount of points (if any)
        self.agents[a_id]["points"] -= points

    
    def process_pool_buys(self):

        total_amount = max(1, sum(self.current_pool_buys.values()))

        # now divide the pool by the fraction each player has bought
        for a_id, points in self.current_pool_buys.items():

            fraction = points / total_amount
            gold_return = int(self.gold_in_pool * fraction)
            if points > 0:
                gold_return = max(1, gold_return)

            self.agents[a_id]["gold"] += gold_return



    def register_bid(self, a_id:str, auction_id:str, gold:int):       
        if auction_id not in self.current_auctions:
            return
        
        if a_id not in self.agents:
            return

        try:
            gold = int(gold)
        except (TypeError, ValueError):
            return
        
        if gold < 1:
            return

                
        if self.agents[a_id]["gold"] < gold:
            return

        self.current_bids[auction_id].append( (a_id, gold) )
        self.agents[a_id]["gold"] -= gold

    
    def process_all_bids(self):        

        gold_from_non_winning_bids = 0
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

            # update now that we know the winners
            for a_id, bid in bids:
                if a_id == winner and bid == win_amount:
                    self.agents[a_id]["points"] += points
                else:
                    back_value = int(bid * self.gold_back_fraction)
                    removed_value = max(0, bid - back_value)
                    gold_from_non_winning_bids += removed_value
                    self.agents[a_id]["gold"] += back_value

        self.gold_in_pool = max(len(self.agents), int(gold_from_non_winning_bids * self.convert_to_pool_fraction))
        