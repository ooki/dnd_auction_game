import random
<<<<<<< HEAD:example_agents/agent_tiny_bid.py

from dnd_auction_game import AuctionGameClient
=======
import os
from ag_client import AuctionGameClient
>>>>>>> 4ccc04224a7800ee74a3b9d16d4db1c77e18b1d9:agent_tiny_bid.py


############################################################################################
#
# tiny_value
#   Bids a tiny amount on every auction
#
############################################################################################
    

def tiny_bid(agent_id:str, states:dict, auctions:dict, prev_auctions:dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    
    bids = {}        
    for auction_id in auctions.keys():
        
        bid = random.randint(1, 20)
        if bid < current_gold:
            bids[auction_id] = bid
            current_gold -= bid
            
    return bids



if __name__ == "__main__":
    
    host = "localhost"
    agent_name = "{}_{}".format(os.path.basename(__file__), random.randint(1, 1000))
    game = AuctionGameClient(host, agent_name) 
    try:
        game.run(tiny_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
