import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

from dnd_auction_game.auction_house import AuctionHouse, parse_int


class ParseIntTests(unittest.TestCase):
    def test_accepts_int_integral_float_and_short_numeric_string(self):
        self.assertEqual(parse_int(5, 0, 10), 5)
        self.assertEqual(parse_int(5.0, 0, 10), 5)
        self.assertEqual(parse_int(" 7 ", 0, 10), 7)
        self.assertEqual(parse_int(0, 0, 10), 0)
        self.assertEqual(parse_int(10, 0, 10), 10)

    def test_rejects_bool_nan_fraction_garbage_and_huge_strings(self):
        for bad in (True, False, None, 2.5, float("nan"), float("inf"),
                    "abc", "1e9", [], {}, "9" * 13, -1, 11):
            self.assertIsNone(parse_int(bad, 0, 10), repr(bad))


class PointPurchaseTests(unittest.TestCase):
    def make_house(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        with patch("dnd_auction_game.auction_house.os.path.isfile", return_value=False):
            house = AuctionHouse("game", "play", save_logs=False)
        house.log_file = str(Path(temp_dir.name) / "auction.jsonl")
        return house

    @staticmethod
    def add_agent(house, agent_id, gold=0, points=0):
        house.agents[agent_id] = {"gold": gold, "points": points}
        house.names[agent_id] = agent_id
        house.priority[agent_id] = 1

    def test_initial_rate_is_zero_and_purchase_can_reach_point_floor(self):
        house = self.make_house()
        self.add_agent(house, "agent", points=200)

        self.assertEqual(house.gold_per_point, 0.0)
        house.register_point_purchase("agent", 500)
        house.process_point_purchases()

        self.assertEqual(house.agents["agent"]["points"], -100)
        self.assertEqual(house.agents["agent"]["gold"], 0)

    def test_purchase_uses_published_rate_and_rounds_gold_down(self):
        house = self.make_house()
        self.add_agent(house, "agent", points=10)
        house.gold_per_point = 2.75

        house.register_point_purchase("agent", 3)
        house.process_point_purchases()

        self.assertEqual(house.agents["agent"]["points"], 7)
        self.assertEqual(house.agents["agent"]["gold"], 8)

    def test_rate_uses_winning_gold_and_aggregate_actual_rewards(self):
        house = self.make_house()
        self.add_agent(house, "winner_one", gold=100)
        self.add_agent(house, "winner_two", gold=50)
        self.add_agent(house, "loser", gold=40)
        house.current_auctions = {"a1": {}, "a2": {}}
        house.current_rolls = {"a1": 10, "a2": -20}

        house.register_bid("winner_one", "a1", 100)
        house.register_bid("loser", "a1", 40)
        house.register_bid("winner_two", "a2", 50)
        house.process_all_bids()

        # 150 winning gold / max(1, 10 + -20) points.
        self.assertEqual(house.gold_per_point, 150.0)
        self.assertEqual(house.agents["winner_one"]["points"], 10)
        self.assertEqual(house.agents["winner_two"]["points"], -20)
        self.assertEqual(house.agents["loser"]["gold"], 20)

    def test_first_round_payload_exposes_only_public_team_names(self):
        house = self.make_house()
        house.add_agent("The Dragons", "agent1", "private-player-id", "s3cret-value")

        state = house.prepare_auctions()

        self.assertEqual(state["round"], 0)
        self.assertEqual(state["team_names"], {"agent1": "The Dragons"})
        self.assertNotIn("player_id", state)
        self.assertNotIn("private-player-id", str(state))
        self.assertNotIn("s3cret-value", str(state))

    def test_reconnect_requires_matching_secret(self):
        house = self.make_house()
        self.assertTrue(house.add_agent("A", "agent1", "pid", "correct-secret"))
        house.agents["agent1"]["gold"] = 500

        self.assertFalse(house.add_agent("Impostor", "agent1", "pid2", "wrong-secret"))
        self.assertTrue(house.add_agent("A", "agent1", "pid", "correct-secret"))

        # state untouched and secret only stored hashed
        self.assertEqual(house.agents["agent1"]["gold"], 500)
        self.assertEqual(house.names["agent1"], "A")
        self.assertNotEqual(house.secrets["agent1"], "correct-secret")
        self.assertFalse(house.verify_secret("unknown", "correct-secret"))

    def test_malformed_bids_and_purchases_are_ignored(self):
        house = self.make_house()
        self.add_agent(house, "agent", gold=100, points=10)
        house.current_auctions = {"a1": {}}

        for bad in (True, "9" * 13, 2.5, None, "abc", 0, -5, 101, [50]):
            house.register_bid("agent", "a1", bad)
        self.assertEqual(house.current_bids, {})
        self.assertEqual(house.agents["agent"]["gold"], 100)

        for bad in (True, "9" * 13, 2.5, None, "abc", -5):
            house.register_point_purchase("agent", bad)
        self.assertEqual(house.current_point_purchases, {})

        house.register_bid("agent", "a1", "100")
        self.assertEqual(house.current_bids["a1"], [("agent", 100)])
        self.assertEqual(house.agents["agent"]["gold"], 0)

    def test_no_winners_sets_rate_to_zero(self):
        house = self.make_house()
        self.add_agent(house, "agent")
        house.current_auctions = {"a1": {}}
        house.current_rolls = {"a1": 15}

        house.process_all_bids()

        self.assertEqual(house.gold_per_point, 0.0)


if __name__ == "__main__":
    unittest.main()
