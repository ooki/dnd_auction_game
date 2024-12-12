from dnd_auction_game import AuctionGameClient
from math import exp, log10

def sigmoid(x):
    return 1 / (1 + exp(-x))

def interest_rate(g):
    return 1 + sigmoid(4 - g / 1000)

def sigmoid_max_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = bank_state.get("total_rounds", 100)

    def get_spend_percentage(gold):
        num_digits = int(log10(max(1, gold))) + 1
        return min(0.01 + 0.01 * (num_digits - 2), 1.0)

    spend_percentage = get_spend_percentage(current_gold) * interest_rate(current_gold)

    if current_round <= total_rounds // 2:
        total_gold_to_spend = current_gold * spend_percentage
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
    game = AuctionGameClient(host="localhost", agent_name="SigmoidMax", player_id="SigmoidMax", port=8000)
    try:
        game.run(sigmoid_max_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
