import os
import random

from dnd_auction_game.client import AuctionGameClient  # Current AuctionGameClient import path

def save_and_spend_later_bid(agent_id: str, states: dict, auctions: dict, prev_auctions: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]
    total_rounds = 10  # Default total rounds (adjust if game setup changes)
    current_round = states.get("round", 1)  # Extract current round
    num_auctions = len(auctions)

    # Early phase: Spend only 1% of current gold on each auction
    if current_round <= total_rounds // 2:
        spend_percentage = 0.01  # Spend 1% of gold
        total_gold_to_spend = current_gold * spend_percentage
    else:
        # Later phase: Spend all remaining gold evenly across auctions
        total_gold_to_spend = current_gold

    gold_per_auction = total_gold_to_spend / num_auctions

    bids = {}
    for auction_id in auctions.keys():
        bid = max(1, int(gold_per_auction))
        if bid <= current_gold:
            bids[auction_id] = bid
            current_gold -= bid

    # Final round: Spend all remaining gold
    if current_round == total_rounds and current_gold > 0:
        remaining_gold_per_auction = current_gold // num_auctions
        for auction_id in auctions.keys():
            bids[auction_id] += remaining_gold_per_auction
            current_gold -= remaining_gold_per_auction
        if current_gold > 0:
            last_auction = list(auctions.keys())[-1]
            bids[last_auction] += current_gold

    return bids

if __name__ == "__main__":
    host = "localhost"
    agent_name = "{}_{}".format(os.path.basename(__file__), random.randint(1, 1000))
    player_id = "id_of_human_player"
    port = 8001

    game = AuctionGameClient(host=host,
                             agent_name=agent_name,
                             player_id=player_id,
                             port=port)
    try:
        game.run(save_and_spend_later_bid)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
