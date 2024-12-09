import random
import os 

from dnd_auction_game import AuctionGameClient


############################################################################################
#
# random_all_in
#   Picks a single auction and bid a random fraction of the agents gold.
#   Also make sure we never bid more than the max of all the other agents.
#
############################################################################################
    

def random_single_bid(agent_id:str, current_round:int, states:dict, auctions:dict, prev_auctions:dict, bank_state:dict):
    agent_state = states[agent_id]
    
    # get the gold amount of the wealthiest agent (that is not ourself)
    max_gold = 1
    for a_id, other_agent in states.items():
        if a_id != agent_id:
            if other_agent["gold"] > max_gold:
                max_gold = other_agent["gold"]
                    
        
    bids = {}
    if agent_state["gold"] > 0:           
        # pick a random auction
        actions = list(auctions.keys())     
        target_auction_id = random.sample(actions, k=1)[0] # sample returns a list
        
        bid_amount = int(agent_state["gold"] * random.uniform(0.5, 0.9))        
        bid_amount = min(bid_amount, max_gold)  # never more than the other agents have
        
        bids[target_auction_id] = bid_amount

    return bids



if __name__ == "__main__":    

    host = "localhost"
    agent_name = "{}_{}".format(os.path.basename(__file__), random.randint(1, 1000))
    player_id = "id_of_human_player"
    port = 8000

    game = AuctionGameClient(host=host,
                             agent_name=agent_name,
                             player_id=player_id,
                             port=port)
    try:
        game.run(random_single_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
