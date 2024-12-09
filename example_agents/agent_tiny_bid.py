import random
import os

from dnd_auction_game import AuctionGameClient


############################################################################################
#
# tiny_value
#   Bids a tiny amount on every auction
#
############################################################################################
    

def tiny_bid(agent_id:str, current_round:int, states:dict, auctions:dict, prev_auctions:dict, bank_state:dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]

    next_round_gold_income = 0
    if len(bank_state["gold_income_per_round"]) > 0:
        next_round_gold_income = bank_state["gold_income_per_round"][0]


    # if we are getting a lot of money next round, increase how much we can bid to 100.
    max_bid = 20
    if next_round_gold_income > 1050:
        max_bid = 100        
    
    bids = {}        
    for auction_id in auctions.keys():        
        bid = random.randint(1, max_bid)
        if bid < current_gold:
            bids[auction_id] = bid
            current_gold -= bid
            
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
        game.run(tiny_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
