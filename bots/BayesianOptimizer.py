import random
from math import exp
from dnd_auction_game import AuctionGameClient

class BayesianBot:
    def __init__(self):
        self.bid_distribution = {}  # Auction ID -> [bids]

    def update_distribution(self, prev_auctions):
        for auction_id, auction_data in prev_auctions.items():
            bids = [bid["gold"] for bid in auction_data["bids"]]
            if auction_id not in self.bid_distribution:
                self.bid_distribution[auction_id] = []
            self.bid_distribution[auction_id].extend(bids)

    def predict_bid(self, auction_id):
        # Use mean and variance for prediction
        bids = self.bid_distribution.get(auction_id, [])
        if not bids:
            return 100  # Default bid
        return int(sum(bids) / len(bids)) + 50  # Add margin

    def bid(self, agent_id, current_round, states, auctions, prev_auctions, reminder_info):
        self.update_distribution(prev_auctions)

        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        bids = {}
        for auction_id in auctions:
            predicted_bid = self.predict_bid(auction_id)
            if predicted_bid < current_gold:
                bids[auction_id] = predicted_bid
                current_gold -= predicted_bid

        return bids

if __name__ == "__main__":
    bot = BayesianBot()
    game = AuctionGameClient(
        host="localhost", agent_name="BayesianBot", player_id="BayesianPlayer", port=8000
    )
    game.run(bot.bid)

