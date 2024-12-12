from dnd_auction_game import AuctionGameClient

def auction_value_estimate(die, num_rolls, bonus=0):
    return (1 + die) / 2 * num_rolls + bonus

def balance_max(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = bank_state.get("total_rounds", 10)
    max_gold_fraction = 0.20 if current_round <= total_rounds // 2 else 0.40

    bids = {}
    for auction_id, auction_info in auctions.items():
        die = auction_info.get("die", 6)
        num = auction_info.get("num", 1)
        bonus = auction_info.get("bonus", 0)
        expected_value = auction_value_estimate(die, num, bonus)

        bid = int(expected_value / 20 * current_gold * max_gold_fraction)
        bid = min(max(1, bid), current_gold)

        if bid > 0:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="BalanceMax", player_id="BalanceMax", port=8000)
    try:
        game.run(balance_max)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
