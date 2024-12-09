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
        self.min_bid = 3        
        self.current_bid = random.randint(1, 100)


        self.last_bid_auction_id = None

    def random_walk(self, agent_id:str, current_round:int, states:dict, auctions:dict, prev_auctions:dict, bank_state:dict):
        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        if current_gold < self.current_bid:
            self.current_bid -= random.randint(1, self.max_move_up_or_down)        

        # how much gold we get next round
        next_round_gold_income = 0
        if len(bank_state["gold_income_per_round"]) > 0:
            next_round_gold_income = bank_state["gold_income_per_round"][0]

        # always bid at least 50% off what we get next round
        if self.current_bid < next_round_gold_income*0.5:
            self.current_bid = int(next_round_gold_income*0.5)

        # move up or down based on if we won the auction or not
        if self.last_bid_auction_id is not None and len(prev_auctions) > 0:
            for auction_id, auction in prev_auctions.items():
                if auction_id == self.last_bid_auction_id:
                    bids_for_this_auction = auction["bids"]
                    
                    if len(bids_for_this_auction) > 0:
                        winning_bid = bids_for_this_auction[0]
                        
                        if winning_bid["a_id"] == agent_id: # we won
                            self.current_bid -= random.randint(1, self.max_move_up_or_down)

                        else: # we lost
                            self.current_bid += random.randint(1, self.max_move_up_or_down)

        self.current_bid = max(self.current_bid, self.min_bid)                    
    
        # bid for next auction
        bids = {}
        if agent_state["gold"] > 0:           
            # pick a random auction
            actions = list(auctions.keys())     
            target_auction_id = random.sample(actions, k=1)[0] # sample returns a list

            bids[target_auction_id] = self.current_bid
            self.last_bid_auction_id = target_auction_id
                
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
    
    agent = RandomWalkAgent(max_move_up_or_down=10)

    try:
        game.run(agent.random_walk)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")
