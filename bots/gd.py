from dnd_auction_game import AuctionGameClient
import random


class GradientDescentModel:
    def __init__(self, learning_rate=0.01):
        # Initialize weights randomly for num_rolls, die_size, and bonus
        self.weights = [random.uniform(0, 1) for _ in range(3)]
        self.learning_rate = learning_rate

    def predict(self, features):
        """
        Predict the bid value using a weighted sum of features.
        """
        return sum(w * f for w, f in zip(self.weights, features))

    def train(self, X, y):
        """
        Train the model using gradient descent to minimize MSE.
        """
        n = len(X)
        gradients = [0] * len(self.weights)

        # Compute gradients
        for i in range(n):
            prediction = self.predict(X[i])
            error = prediction - y[i]
            for j in range(len(self.weights)):
                gradients[j] += (2 / n) * error * X[i][j]

        # Update weights
        for j in range(len(self.weights)):
            self.weights[j] -= self.learning_rate * gradients[j]


class GradientDescentBot:
    def __init__(self, learning_rate=0.01):
        self.model = GradientDescentModel(learning_rate)
        self.auction_history = []

    def collect_data(self, prev_auctions):
        """
        Collect data for training the model.
        """
        for auction_id, auction in prev_auctions.items():
            for bid in auction["bids"]:
                features = [
                    auction["num"],  # num_rolls
                    auction["die"],  # die_size
                    auction["bonus"],  # bonus
                ]
                self.auction_history.append((features, bid["gold"]))

    def train_model(self):
        """
        Train the model using collected auction data.
        """
        if len(self.auction_history) < 2:
            return  # Not enough data to train
        X = [data[0] for data in self.auction_history]
        y = [data[1] for data in self.auction_history]
        self.model.train(X, y)

    def bid(self, agent_id, current_round, states, auctions, prev_auctions, reminder_info):
        """
        Predict and place bids based on auction features and model predictions.
        """
        # Collect and train the model using historical data
        self.collect_data(prev_auctions)
        self.train_model()

        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        bids = {}
        for auction_id, auction in auctions.items():
            features = [auction["num"], auction["die"], auction["bonus"]]
            predicted_bid = max(1, int(self.model.predict(features)))
            bid_amount = min(current_gold, predicted_bid)
            bids[auction_id] = bid_amount
            current_gold -= bid_amount

        return bids


if __name__ == "__main__":
    bot = GradientDescentBot(learning_rate=0.01)
    game = AuctionGameClient(
        host="localhost", agent_name="GradientDescentBot", player_id="GradientDescentPlayer", port=8000
    )
    game.run(bot.bid)
