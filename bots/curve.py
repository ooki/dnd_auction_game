from math import exp, log10
from dnd_auction_game import AuctionGameClient

def sigmoid(x):
    return 1 / (1 + exp(-x))

def interest_rate(g):
    return 1 + sigmoid(4 - g / 1000)

def curve_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = bank_state.get("total_rounds", 10)

    def get_spend_percentage(gold):
        if gold > 0:
            num_digits = int(log10(gold)) + 1
        else:
            num_digits = 1
        return min(0.01 + 0.01 * (num_digits - 3), 1.0)

    if current_round <= total_rounds // 2:
        spend_percentage = get_spend_percentage(current_gold)
        total_gold_to_spend = current_gold * spend_percentage * interest_rate(current_gold)
    else:
        total_gold_to_spend = current_gold

    bids = {}
    gold_per_auction = total_gold_to_spend / max(1, len(auctions))

    for auction_id in auctions:
        bid = max(1, int(gold_per_auction))
        if bid <= current_gold:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="Curve", player_id="Curve", port=8000)
    try:
        game.run(curve_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
