import random

from dnd_auction_game import AuctionGameClient


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
        target_auction_id = random.sample(auctions.keys(), k=1)[0] # sample returns a list
        
        bid_amount = int(agent_state["gold"] * random.uniform(0.5, 0.9))        
        bid_amount = min(bid_amount, max_gold)  # never more than the other agents have
        
        bids[target_auction_id] = bid_amount

    return bids



if __name__ == "__main__":    
    agent_name = __file__[:-3] # get rid of .py (or write a awesome name here! )
    if agent_name.startswith("./"):
        agent_name = agent_name[2:]
    agent_name = "{}_{}".format(agent_name, random.randint(1, 1000))
    
    
    host = "localhost"
    game = AuctionGameClient(host, agent_name)    
    try:
        game.run(random_single_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
