import random
import numpy as np
from dnd_auction_game import AuctionGameClient

class QLearningBot:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.q_table = {}  # {(state, action): value}
        self.alpha = alpha  # Learning rate
        self.gamma = gamma  # Discount factor
        self.epsilon = epsilon  # Exploration probability

    def get_state(self, auctions, gold):
        return (tuple(sorted(auctions.keys())), gold)

    def choose_action(self, state, actions):
        if random.random() < self.epsilon:  # Explore
            return random.choice(actions)
        # Exploit
        q_values = [self.q_table.get((state, action), 0) for action in actions]
        return actions[np.argmax(q_values)]

    def update_q_value(self, state, action, reward, next_state):
        old_value = self.q_table.get((state, action), 0)
        next_max = max([self.q_table.get((next_state, a), 0) for a in actions], default=0)
        self.q_table[(state, action)] = old_value + self.alpha * (reward + self.gamma * next_max - old_value)

    def bid(self, agent_id, current_round, states, auctions, prev_auctions, reminder_info):
        agent_state = states[agent_id]
        gold = agent_state["gold"]
        state = self.get_state(auctions, gold)

        # Possible actions: Bid on any auction
        actions = list(auctions.keys())

        # Choose action
        action = self.choose_action(state, actions)

        # Allocate maximum bid for the chosen action
        bids = {auction: 0 for auction in auctions}
        if action:
            bids[action] = gold // 2  # Bid half of available gold
        return bids

if __name__ == "__main__":
    bot = QLearningBot()
    game = AuctionGameClient(
        host="localhost", agent_name="QLearningBot", player_id="QLearningPlayer", port=8000
    )
    game.run(bot.bid)

