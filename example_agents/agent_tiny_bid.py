import random

from dnd_auction_game import AuctionGameClient


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
    agent_name = __file__[:-3] # get rid of .py (or write a awesome name here! )
    if agent_name.startswith("./"):
        agent_name = agent_name[2:]
    agent_name = "{}_{}".format(agent_name, random.randint(1, 1000))
    
    
    host = "localhost"
    game = AuctionGameClient(host, agent_name)    
    try:
        game.run(tiny_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
