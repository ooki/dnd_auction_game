from dnd_auction_game import AuctionGameClient
from math import log10

def invincible_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = bank_state.get("total_rounds", 100)

    def get_spend_percentage(gold):
        num_digits = int(log10(max(gold, 1))) + 1  # Avoid log10(0)
        return min(0.02 + 0.02 * (num_digits - 3), 0.5)  # 2% base, scaling up to 50%

    if current_round <= total_rounds // 2:
        spend_percentage = get_spend_percentage(current_gold)
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
    game = AuctionGameClient(host="localhost", agent_name="Invincible", player_id="Invincible", port=8000)
    try:
        game.run(invincible_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
