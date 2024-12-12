from dnd_auction_game import AuctionGameClient

def auction_value_estimate(die, num_rolls, bonus=0):
    return (1 + die) / 2 * num_rolls + bonus

def conservative_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    max_gold_fraction = 0.25  # Conservative bot spends 25% of its gold each round

    bids = {}
    for auction_id, auction_info in auctions.items():
        die = auction_info.get("die", 6)
        num = auction_info.get("num", 1)
        bonus = auction_info.get("bonus", 0)
        estimated_value = auction_value_estimate(die, num, bonus)

        bid = int(estimated_value / 20 * current_gold * max_gold_fraction)
        bid = min(max(1, bid), current_gold)

        if bid > 0:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="Conservative", player_id="Conservative", port=8000)
    try:
        game.run(conservative_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
