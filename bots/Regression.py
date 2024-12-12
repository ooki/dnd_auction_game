
from dnd_auction_game import AuctionGameClient

class RegressionModel:
    def __init__(self):
        # Weights for linear regression (initialized randomly)
        self.weights = None

    def train(self, X, y):
        """
        Train the model using normal equation: (X^T * X)^-1 * X^T * y
        """
        X_transpose = self.transpose(X)
        XTX = self.multiply(X_transpose, X)
        XTX_inv = self.invert(XTX)
        XTy = self.multiply(X_transpose, y)
        self.weights = self.multiply(XTX_inv, XTy)

    def predict(self, X):
        """
        Predict bid values for given features.
        """
        return self.multiply(X, self.weights)

    @staticmethod
    def transpose(matrix):
        return [[matrix[j][i] for j in range(len(matrix))] for i in range(len(matrix[0]))]

    @staticmethod
    def multiply(A, B):
        if isinstance(B[0], list):  # Matrix multiplication
            return [[sum(a * b for a, b in zip(A_row, B_col)) for B_col in zip(*B)] for A_row in A]
        else:  # Vector multiplication
            return [sum(a * b for a, b in zip(A_row, B)) for A_row in A]

    @staticmethod
    def invert(matrix):
        """
        Invert a 2x2 matrix for simplicity (expandable for higher dimensions).
        """
        det = matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        return [
            [matrix[1][1] / det, -matrix[0][1] / det],
            [-matrix[1][0] / det, matrix[0][0] / det]
        ]


class PredictionBot:
    def __init__(self):
        self.model = RegressionModel()
        self.auction_history = []

    def collect_data(self, prev_auctions):
        """
        Collect data for training the regression model.
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
        Train the regression model on collected auction data.
        """
        if len(self.auction_history) < 2:
            return  # Not enough data to train
        X = [data[0] for data in self.auction_history]
        y = [[data[1]] for data in self.auction_history]  # Reshape for matrix operations
        self.model.train(X, y)

    def bid(self, agent_id, current_round, states, auctions, prev_auctions, reminder_info):
        """
        Predict and place bids based on auction features and model predictions.
        """
        # Determine total and remaining rounds
        total_rounds = len(reminder_info["gold_income_per_round"])
        remaining_rounds = total_rounds - current_round
        is_final_rounds = remaining_rounds <= 3

        # Collect and train the model using historical data
        self.collect_data(prev_auctions)
        self.train_model()

        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        # Adjust spending strategy based on game phase
        if is_final_rounds:
            spend_ratio = 1.0  # Spend all remaining gold
        else:
            spend_ratio = 0.5  # Save some gold in earlier rounds

        gold_to_spend = int(current_gold * spend_ratio)

        bids = {}
        for auction_id, auction in auctions.items():
            features = [auction["num"], auction["die"], auction["bonus"]]
            predicted_bid = self.model.predict([features])[0][0] if self.model.weights else 100
            bid_amount = min(gold_to_spend, max(1, int(predicted_bid)))
            bids[auction_id] = bid_amount
            gold_to_spend -= bid_amount

        return bids



if __name__ == "__main__":
    bot = PredictionBot()
    game = AuctionGameClient(
        host="localhost", agent_name="PredictionBot", player_id="PredictionPlayer", port=8000
    )
    game.run(bot.bid)
