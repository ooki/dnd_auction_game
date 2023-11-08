import random
<<<<<<< HEAD:example_agents/agent_random_single.py

from dnd_auction_game import AuctionGameClient
=======
import os 
from ag_client import AuctionGameClient
>>>>>>> 4ccc04224a7800ee74a3b9d16d4db1c77e18b1d9:agent_random_single.py


############################################################################################
#
# random_all_in
#   Picks a single auction and bid a random fraction of the agents gold.
#   Also make sure we never bid more than the max of all the other agents.
#
############################################################################################
    

def random_single_bid(agent_id:str, states:dict, auctions:dict, prev_auctions:dict):
    agent_state = states[agent_id]
    
    # get the gold amount of the wealthiest agent (that is not ourself)
    max_gold = 1
    for a_id, other_agent in states.items():
        if a_id != agent_id:
            if other_agent["gold"] > max_gold:
                max_gold = other_agent["gold"]
                    
        
    bids = {}
    if agent_state["gold"] > 0:                
        target_auction_id = random.sample((auctions.keys()), k=1)[0] # sample returns a list
        
        bid_amount = int(agent_state["gold"] * random.uniform(0.5, 0.9))        
        bid_amount = min(bid_amount, max_gold)  # never more than the other agents have
        
        bids[target_auction_id] = bid_amount

    return bids



if __name__ == "__main__":    

    host = "localhost"
    agent_name = "{}_{}".format(os.path.basename(__file__), random.randint(1, 1000))
    
    game = AuctionGameClient(host, agent_name) 
    try:
        game.run(random_single_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
