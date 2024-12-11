
from typing import List, Dict, Union
import random
from collections import defaultdict
import json
import math
import os



def generate_gold_random_walk(n_steps:int) -> List[float]:

    gold_per_round = 1000
    step_size = 100
    max_gold_per_round = 10000

    gold = [gold_per_round]
    for _ in range(n_steps-1):
        next_gold = gold[-1] + random.randint(-step_size, step_size)

        if next_gold < 0:
            next_gold = 0
        
        if next_gold > max_gold_per_round:
            next_gold = max_gold_per_round

        gold.append(next_gold)

    return gold

def braavos_bank_limit_random_walk(n_steps:int) -> List[int]:

    upper_limit_start = 2000
    upper_limit_end = 10000
    step_size = 100

    upper_limits = [upper_limit_start]
    for _ in range(n_steps-1):
        next_limit = upper_limits[-1] + random.randint(-step_size, step_size)

        if next_limit < 0:
            next_limit = 0
        
        if next_limit > upper_limit_end:
            next_limit = upper_limit_end

        upper_limits.append(next_limit)

    return upper_limits

def braavos_bank_interest_rate_random_walk(n_steps:int) -> List[float]:

    start_rate = 1.05
    min_rate = 0.9
    max_rate = 1.15
    step_size = 0.01

    rates = [start_rate]
    for _ in range(n_steps-1):
        next_rate = rates[-1] + random.uniform(-step_size, step_size)

        if next_rate < min_rate:
            next_rate = min_rate
        
        if next_rate > max_rate:
            next_rate = max_rate

        rates.append(next_rate)

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
        
        self.agents = {}
        self.names = {}
        
        self.auctions_per_agent = 1.5
        self.gold_back_fraction = 0.6
        
        self.die_sizes = [2,   3,  4,  6,   8, 10,  12,   20,  20]
        self.die_prob =  [8,   8,  9,  8,   6,  6,   5,    2,   1]
        self.max_n_die = [5,   7, 10,  2,   3,  3,   6,    2,   4]
        self.max_bonus = [10,  2, 16,  8,  21,  2,   5,    7,   3] 
        self.min_bonus = [-2, -8, -5, -5, -10, -4,  -5,  -4,  -4]

        self.round_counter = 0
        self.auction_counter = 1
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        
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

    def reset(self):
        self.is_done = False
        self.agents = {}
        self.names = {}
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.round_counter = 0
        self.auction_counter = 1
        self.set_num_rounds(10)

    def set_num_rounds(self, num_rounds:int):
        self.num_rounds_in_game = num_rounds
        
        self.gold_income_per_round = generate_gold_random_walk(num_rounds)
        self.bank_limit_per_round = braavos_bank_limit_random_walk(num_rounds)
        self.bank_interest_per_round = braavos_bank_interest_rate_random_walk(num_rounds)
        
    
    def add_agent(self, name:str, a_id:str, player_id:str):
        if a_id in self.agents:
            print("Agent {}  id:{} reconnected".format(name, a_id))
            return

        with open(self.log_player_id_file, 'a') as fp:
            pid = {"player_id": player_id, "agent_id": a_id, "name": name}
            fp.write("{}\n".format(json.dumps(pid)))
                    
        self.agents[a_id] = {"gold": 0, "points": 0}
        self.names[a_id] = name
    
    
    def prepare_auction(self):        
        prev_auctions = self.current_auctions
        prev_bids = self.current_bids
        prev_rolls = self.current_rolls
        
        self.current_bids = defaultdict(list)
        self.current_auctions, self.current_rolls = self._generate_auctions()        


        
        # update gold for agents
        upper_rate = self.bank_limit_per_round[self.round_counter]
        interest_rate = self.bank_interest_per_round[self.round_counter]
        gold_income = self.gold_income_per_round[self.round_counter]

        for agent in self.agents.values():
            # bank of Braavos gives interest on stored gold
            
            interest_available_gold = 0
            if agent["gold"] >= upper_rate:
                interest_available_gold = upper_rate
            else:
                interest_available_gold = agent["gold"]
            
            agent["gold"] = int(interest_available_gold * interest_rate)            
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
            "reminder_gold_income": self.gold_income_per_round[self.round_counter+1:], # +1 as we want to report on the next state - not the current state
            "reminder_bank_limit": self.bank_limit_per_round[self.round_counter+1:],
            "reminder_bank_interest": self.bank_interest_per_round[self.round_counter+1:],
        }

        if self.save_logs and self.log_file is not None:
            with open(self.log_file, "a") as fp:
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
            return
                
        self.current_bids[auction_id].append( (a_id, gold) )
        self.agents[a_id]["gold"] -= gold
    
    def process_all_bids(self):        
        
        for auction_id, bids in self.current_bids.items():

            if not bids or len(bids) == 0:
                continue

            win_amount = max(bids, key=lambda x:x[1])[1]
            for a_id, bid in bids:
                if bid == win_amount:
                    self.agents[a_id]["points"] += self.current_rolls[auction_id]
                
                else:
                    # cashback
                    back_value = int(math.floor(bid * self.gold_back_fraction))
                    self.agents[a_id]["gold"] += back_value
            


    
        