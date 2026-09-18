import random
import os
from typing import List
from dnd_auction_game import AuctionGameClient


############################################################################################
#
# tiny_value
#   Bids a tiny amount on every auction.
#   If it has more than 20 points, it occasionally (p=0.1) sells 10 points for gold.
#
############################################################################################




def tiny_bid(agent_id: str,
             round: int,
             states: dict,
             auctions: dict,
             prev_auctions: dict,
             gold_per_point: float,
             bank_state: dict):

    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    current_points = agent_state["points"]

    print("Current gold per point: {:.2f}".format(gold_per_point))

    # Sell points for gold: if we have more than 20 points, sell 10 with probability 0.1.
    # The gold arrives at the next tick (at the gold_per_point rate shown above).
    points_to_spend = 0
    if current_points > 20 and random.random() < 0.1:
        points_to_spend = 10
        print("Selling {} points for ~{:.0f} gold".format(points_to_spend, points_to_spend * gold_per_point))
    
    bids = {}       


    for auction_id in auctions.keys():
        bid = random.randint(1, 200)
        if bid < current_gold:
            bids[auction_id] = bid 
            current_gold -= bid


    return {"bids": bids, "points_to_spend": points_to_spend}



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
