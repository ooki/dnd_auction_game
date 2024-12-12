from dnd_auction_game import AuctionGameClient

def aggressive_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    max_gold_fraction = 0.50  # Spend 50% of gold each round

    bids = {}
    for auction_id, auction_info in auctions.items():
        die = auction_info.get("die", 6)
        num = auction_info.get("num", 1)
        bonus = auction_info.get("bonus", 0)
        expected_value = num * (1 + die) / 2 + bonus

        bid = int(expected_value / 20 * current_gold * max_gold_fraction)  # Scale based on the largest die size
        bid = min(max(1, bid), current_gold)

        if bid > 0:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="Aggressive", player_id="Aggressive", port=8000)
    try:
        game.run(aggressive_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
