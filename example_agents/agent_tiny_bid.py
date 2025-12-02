import random
import os
from typing import List
from dnd_auction_game import AuctionGameClient


############################################################################################
#
# tiny_value
#   Bids a tiny amount on every auction
#
############################################################################################




def tiny_bid(agent_id: str,
             round: int,
             states: dict,
             auctions: dict,
             prev_auctions: dict,
             pool: int,
             prev_pool_buys: dict,
             bank_state: dict):

    agent_state = states[agent_id]
    current_gold = agent_state["gold"]

    print("Current pool size: {}".format(pool))
    
    bids = {}       


    for auction_id in auctions.keys():
        bid = random.randint(1, 200)
        if bid < current_gold:
            bids[auction_id] = bid 
            current_gold -= bid


    # 
    points_for_pool = 0
    return {"bids": bids, "pool": points_for_pool}



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
        game.run(tiny_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
