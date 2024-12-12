import os
import random
from dnd_auction_game import AuctionGameClient

class RandomWalkAgent:
    def __init__(self, max_move: int = 10):
        self.max_move = max_move
        self.min_bid = 3
        self.current_bid = random.randint(1, 100)
        self.last_bid_auction_id = None

    def random_walk(self, agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        # Adjust bid amount based on previous results
        if self.last_bid_auction_id and self.last_bid_auction_id in prev_auctions:
            winning_bid = prev_auctions[self.last_bid_auction_id]["bids"][0]
            if winning_bid["a_id"] == agent_id:
                self.current_bid = max(self.current_bid - random.randint(1, self.max_move), self.min_bid)
            else:
                self.current_bid = min(self.current_bid + random.randint(1, self.max_move), current_gold)

        bids = {}
        if current_gold >= self.current_bid:
            auction_id = random.choice(list(auctions.keys()))
            bids[auction_id] = self.current_bid
            self.last_bid_auction_id = auction_id

        return bids

if __name__ == "__main__":
    host = "localhost"
    agent_name = "{}_{}".format(os.path.basename(__file__), random.randint(1, 1000))
    player_id = "id_of_human_player"
    port = 8000

    game = AuctionGameClient(host=host, agent_name=agent_name, player_id=player_id, port=port)
    agent = RandomWalkAgent(max_move=10)
    try:
        game.run(agent.random_walk)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
