import random
import os
import json

import numpy as np
from sklearn.linear_model import LinearRegression


from dnd_auction_game import AuctionGameClient
############################################################################################
#
#
# Linear Prediction
#   Loops through all the logs in @target_log_dir and tries to estimate how much each auction is worth.
#   The model takes two inputs:  mean-value of the throw, and the minimum value of the throw
#       And predicts the winning bid
#
############################################################################################
    

class AuctionPredictionModel:
    
    def __init__(self):
        self.average_roll_for_die = {  # there is a more math'y way to do this. Left as an exerecise for the reader :)
            2: 1.5,
            3: 2.0,
            4: 2.5,
            6: 3.5,
            8: 4.5,
            10: 5.5,
            12: 6.5,
            20: 10.5
        }
        
        self.x = []
        self.y = []
        self.model : LinearRegression = None
    
    def load(self, target_log_directory):
        
        for f in os.listdir(target_log_directory):                        
            path = os.path.join(target_log_directory, f)
            with open(path, "r") as fp:
                for line in fp:
                    round = json.loads(line)
                    
                    for auction in round["prev_auctions"].values():
                        # example: {"die": 6, "num": 3, "bonus": 7, "reward": 14, "bids": [{"a_id": "local_rand_id_377500", "gold": 741}
                        
                        bids = auction["bids"]
                        if len(bids) > 0:                                                
                            mean_value = (self.average_roll_for_die[auction["die"]] * auction["num"]) + auction["bonus"]
                            min_value =  auction["num"] + auction["bonus"]
                            
                            winning_bid = bids[0]
                            winning_amount = winning_bid["gold"]
                            
                            self.x.append([mean_value, min_value])
                            self.y.append(winning_amount + 1)  # we want to bid 1 more than the winner
        
        
                    
    def train(self):
        if len(self.x) < 1:
            raise ValueError("Cannot train a model without ANY data. Please get some logs I can train on.")                  
        
        self.model = LinearRegression()
        train_x = np.array(self.x)
        train_y = np.array(self.y)
        
        self.model.fit(train_x, train_y)
        
        
    def make_bids(self, agent_id:str, states:dict, auctions:dict, prev_auctions:dict):        
        agent_state = states[agent_id]        
        current_gold = agent_state["gold"]
        
        # potentially we could retrain/update the model here
        # update self.x, self.y using prev_auctions
        # call train()
        
    
        bids = {}        
        for auction_id, auction in auctions.items():
            mean_value = (self.average_roll_for_die[auction["die"]] * auction["num"]) + auction["bonus"]
            min_value =  auction["num"] + auction["bonus"]
            
            x = np.array([mean_value, min_value]).reshape(1, -1) 
            est_cost = int(self.model.predict(x))
            
            if est_cost < current_gold:
                bids[auction_id] = est_cost
                current_gold -= est_cost
                
        return bids
                
            


if __name__ == "__main__":    
    agent_name = __file__[:-3] # get rid of .py (or write a awesome name here! )
    if agent_name.startswith("./"):
        agent_name = agent_name[2:]
    agent_name = "{}_{}".format(agent_name, random.randint(1, 1000))
    
    
    predict_model = AuctionPredictionModel()
    predict_model.load("./logs")
    predict_model.train()
    
    
    host = "localhost"
    game = AuctionGameClient(host, agent_name)    
    try:
        game.run(predict_model.make_bids)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
