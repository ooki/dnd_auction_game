
from typing import List, Dict, Union
import random
from collections import defaultdict
import json
import math
import os

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

        self.gold_in_pool = 0 # the gold that was removed during the cashbacki
        self.convert_to_pool_fraction = 0.7 # the fraction of gold that is returned to the hoard
        
        self.agents = {}
        self.names = {}
        
        self.bank_interest_rate = 1.10
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
        self.num_rounds_in_game = 10
        self.priority = {}
        self.current_pool_buys = {}
        
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
        self.is_active = False
        self.agents = {}
        self.names = {}
        self.current_auctions = {}
        self.current_rolls = {} 
        self.current_bids = defaultdict(list)
        self.round_counter = 0
        self.auction_counter = 1
        self.num_rounds_in_game = 10
        self.priority = {}
        self.gold_in_pool = 0
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
    
    
    def prepare_auctions_and_pool(self):        
        prev_auctions = self.current_auctions
        prev_bids = self.current_bids
        prev_rolls = self.current_rolls
        
        self.current_bids = defaultdict(list)
        self.current_auctions, self.current_rolls = self._generate_auctions()

        # copy the pool buys to broodcast, reset the pool buys
        buy_pool_copy = self.current_pool_buys.copy()
        self.current_pool_buys = {} 

        
        # update gold for agents
        for agent in self.agents.values():

            # bank of Braavos gives interest on stored gold
            agent["gold"] = int(agent["gold"] * self.bank_interest_rate)
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
            "prev_auctions": out_prev_state,
            "prev_pool_buys": buy_pool_copy,
            "pool": self.gold_in_pool,
        }

        if self.save_logs and self.log_file is not None:
            try:
                with open(self.log_file, "a") as fp:
                    fp.write("{}\n".format(json.dumps(state)))
            except Exception as e:
                print("error writing auction log:", e)
                self.save_logs = False
        
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
        points = int(max(points, 0))

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
                gold_return = min(1, gold_return)

            self.agents[a_id]["gold"] += gold_return



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
            for a_id, bid in bids:
                if a_id == winner and bid == win_amount:
                    self.agents[a_id]["points"] += points
                else:
                    back_value = int(bid * self.gold_back_fraction)
                    removed_value = max(0, bid - back_value)
                    gold_from_non_winning_bids += removed_value
                    self.agents[a_id]["gold"] += back_value

        self.gold_in_pool = max(len(self.agents), int(gold_from_non_winning_bids * self.convert_to_pool_fraction))
        