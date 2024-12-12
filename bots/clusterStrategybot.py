import random
from math import sqrt
from dnd_auction_game import AuctionGameClient

class ClusterBot:
    def __init__(self, k=2):
        self.k = k  # Number of clusters
        self.centroids = []

    def calculate_distance(self, point1, point2):
        return sqrt(sum((p1 - p2) ** 2 for p1, p2 in zip(point1, point2)))

    def k_means(self, points):
        # Initialize centroids randomly
        self.centroids = random.sample(points, self.k)
        clusters = [[] for _ in range(self.k)]

        for _ in range(10):  # Iterations
            clusters = [[] for _ in range(self.k)]
            for point in points:
                distances = [self.calculate_distance(point, centroid) for centroid in self.centroids]
                cluster_idx = distances.index(min(distances))
                clusters[cluster_idx].append(point)

            for i, cluster in enumerate(clusters):
                if cluster:
                    self.centroids[i] = [
                        sum(d) / len(cluster) for d in zip(*cluster)
                    ]

        return clusters

    def bid(self, agent_id, current_round, states, auctions, prev_auctions, reminder_info):
        agent_state = states[agent_id]
        current_gold = agent_state["gold"]

        # Extract features from auctions
        auction_features = [
            (info["num"], info["die"], info["bonus"]) for info in auctions.values()
        ]
        clusters = self.k_means(auction_features)

        # Prioritize high-value clusters
        high_value_cluster = max(clusters, key=lambda c: sum(f[0] * (f[1] + 1) / 2 + f[2] for f in c))
        bids = {}
        for auction_id, auction in auctions.items():
            if (auction["num"], auction["die"], auction["bonus"]) in high_value_cluster:
                bids[auction_id] = current_gold // len(high_value_cluster)

        return bids

if __name__ == "__main__":
    bot = ClusterBot(k=2)
    game = AuctionGameClient(
        host="localhost", agent_name="ClusterBot", player_id="ClusterPlayer", port=8000
    )
    game.run(bot.bid)

