from dnd_auction_game import AuctionGameClient
from math import exp

def sigmoid(x):
    return 1 / (1 + exp(-x))

def interest_rate(g):
    return 1 + sigmoid(4 - g / 1000)

def save_max_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    target_interest_rate = 1.15  # Aim for 15% interest rate

    current_interest_rate = interest_rate(current_gold)
    max_gold_fraction = 0.02 if current_interest_rate < target_interest_rate else 0.25

    bids = {}
    for auction_id, auction_info in auctions.items():
        die = auction_info.get("die", 6)
        num = auction_info.get("num", 1)
        bonus = auction_info.get("bonus", 0)
        estimated_value = (1 + die) / 2 * num + bonus

        bid = min(current_gold, int(estimated_value / 20 * current_gold * max_gold_fraction))
        bid = max(1, min(bid, current_gold))

        if bid <= current_gold:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="SaveMax", player_id="SaveMax", port=8000)
    try:
        game.run(save_max_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
