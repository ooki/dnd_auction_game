
from dnd_auction_game import AuctionGameClient
from math import exp, log

def sigmoid(x, k=1, x0=0):
    """Smooth spending curve."""
    return 1 / (1 + exp(-k * (x - x0)))

def auction_value(auction_info):
    """Calculate expected value of an auction."""
    die = auction_info.get("die", 6)
    num = auction_info.get("num", 1)
    bonus = auction_info.get("bonus", 0)
    return num * (die + 1) / 2 + bonus

def optimal_bid(agent_id, current_round, states, auctions, prev_auctions, reminder_info):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    rounds_left = len(reminder_info["gold_income_per_round"])
    bank_limit = reminder_info["bank_limit_per_round"][0]
    interest_rate = reminder_info["bank_interest_per_round"][0]

    # Spend ratio based on sigmoid function
    spend_ratio = sigmoid(current_round, k=0.5, x0=rounds_left / 2)
    gold_to_spend = int(current_gold * spend_ratio)

    # Prioritize auctions by value
    auction_values = {
        auction_id: auction_value(info)
        for auction_id, info in auctions.items()
    }
    sorted_auctions = sorted(auction_values.items(), key=lambda x: x[1], reverse=True)

    # Allocate gold to maximize value
    bids = {}
    total_value = sum(auction_values.values()) or 1  # Avoid division by zero
    for auction_id, value in sorted_auctions:
        if gold_to_spend <= 0:
            break
        bid_amount = max(1, int(gold_to_spend * (value / total_value)))
        bid_amount = min(bid_amount, current_gold)  # Don't overspend
        bids[auction_id] = bid_amount
        current_gold -= bid_amount
        gold_to_spend -= bid_amount

    return bids

if __name__ == "__main__":
    host = "localhost"
    agent_name = "OptimalBot"
    player_id = "OptimalPlayer"
    port = 8000

    game = AuctionGameClient(host=host, agent_name=agent_name, player_id=player_id, port=port)
    game.run(optimal_bid)
