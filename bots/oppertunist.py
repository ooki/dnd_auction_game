from dnd_auction_game import AuctionGameClient

def opportunist_bid(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    max_gold_fraction = 0.20

    if prev_auctions:
        for auction in prev_auctions.values():
            for bid in auction["bids"]:
                if bid["a_id"] == agent_id:
                    max_gold_fraction = 0.40  # Increase spending if we won last round

    bids = {}
    for auction_id, auction_info in auctions.items():
        die = auction_info.get("die", 6)
        num = auction_info.get("num", 1)
        bonus = auction_info.get("bonus", 0)
        auction_value = (1 + die) / 2 * num + bonus

        bid = min(current_gold, int(auction_value / 20 * current_gold * max_gold_fraction))
        bid = max(1, bid)

        if bid <= current_gold:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="Opportunist", player_id="Opportunist", port=8000)
    try:
        game.run(opportunist_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
