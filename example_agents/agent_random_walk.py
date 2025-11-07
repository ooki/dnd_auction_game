import random
import os

from dnd_auction_game import AuctionGameClient


############################################################################################
#
# random_walk 
#   Walks up if we won the auction, otherwise walk down
#
############################################################################################
    

class RandomWalkAgent:
    def __init__(self, max_move_up_or_down:int=10):
        self.max_move_up_or_down = max_move_up_or_down
        self.current_bid = random.randint(1, 100)

        self.last_bid_auction_id = None

    def random_walk(self, agent_id:str, states:dict, auctions:dict, prev_auctions:dict, pool_gold:int, prev_pool_buys:dict):
        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        if current_gold < self.current_bid:
            self.current_bid -= random.randint(1, self.max_move_up_or_down)
        

        # move up or down based on if we won the auction or not
        if self.last_bid_auction_id is not None and len(prev_auctions) > 0:
            for auction_id, auction in prev_auctions.items():
                if auction_id == self.last_bid_auction_id:
                    bids_for_this_auction = auction["bids"]
                    
                    if len(bids_for_this_auction) > 0:
                        winning_bid = bids_for_this_auction[0]
                        
                        if winning_bid["a_id"] == agent_id: # we won
                            self.current_bid += random.randint(1, self.max_move_up_or_down)
                        else: # we lost
                            self.current_bid -= random.randint(1, self.max_move_up_or_down)
        
        self.current_bid = max(1, self.current_bid)                    
        
        print("Current bid: {}".format(self.current_bid))
    
        # bid for next auction
        bids = {}
        if agent_state["gold"] > 0:           
            # pick a random auction
            actions = list(auctions.keys())     
            target_auction_id = random.sample(actions, k=1)[0] # sample returns a list

            bids[target_auction_id] = self.current_bid
            self.last_bid_auction_id = target_auction_id

        points_for_pool = 1 
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
    
    agent = RandomWalkAgent(max_move_up_or_down=10)

    try:
        game.run(agent.random_walk)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
