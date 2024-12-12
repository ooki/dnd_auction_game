from dnd_auction_game import AuctionGameClient
import random

def random_max(agent_id: str, current_round: int, states: dict, auctions: dict, prev_auctions: dict, bank_state: dict):
    agent_state = states[agent_id]
    current_gold = agent_state["gold"]

    bids = {}
    for auction_id in auctions:
        bid = random.randint(1, max(1, current_gold // 2))
        if bid <= current_gold:
            bids[auction_id] = bid
            current_gold -= bid

    return bids

if __name__ == "__main__":
    game = AuctionGameClient(host="localhost", agent_name="RandomMax", player_id="RandomMax", port=8000)
    try:
        game.run(random_max)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")
