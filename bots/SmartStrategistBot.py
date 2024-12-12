from dnd_auction_game import AuctionGameClient
from math import exp

def sigmoid(x):
    return 1 / (1 + exp(-x))

def interest_rate(g):
    return 1 + sigmoid(4 - g / 1000)

def auction_value_estimate(auction_info):
    die = auction_info.get("die", 6)
    num = auction_info.get("num", 1)
    bonus = auction_info.get("bonus", 0)
    return (1 + die) / 2 * num + bonus

def smart_strategist_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = bank_state.get("total_rounds", 10)
    desired_capital = max(2000, current_gold // 2) if total_rounds - current_round < 5 else 4000
    gold_to_spend = max(0, current_gold - desired_capital)

    bids = {}
    auction_estimates = {auction_id: auction_value_estimate(info) for auction_id, info in auctions.items()}

    for auction_id, value in sorted(auction_estimates.items(), key=lambda x: x[1], reverse=True):
        if gold_to_spend <= 0:
            break
        bid = min(gold_to_spend, max(1, int(value / sum(auction_estimates.values()) * gold_to_spend)))
        bids[auction_id] = bid
        gold_to_spend -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="SmartStrategist", player_id="SmartStrategist", port=8000)
    try:
        game.run(smart_strategist_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
