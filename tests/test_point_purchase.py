import json
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
        return AuctionHouse("game", "play", save_logs=False)

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
        house.process_point_purchases(house.gold_per_point)

        self.assertEqual(house.agents["agent"]["points"], -100)
        self.assertEqual(house.agents["agent"]["gold"], 0)

    def test_purchase_uses_published_rate_and_rounds_gold_down(self):
        house = self.make_house()
        self.add_agent(house, "agent", points=10)

        house.register_point_purchase("agent", 3)
        house.process_point_purchases(2.75)

        self.assertEqual(house.agents["agent"]["points"], 7)
        self.assertEqual(house.agents["agent"]["gold"], 8)

    def test_points_won_this_round_can_be_sold_but_gold_cannot_fund_same_round_bids(self):
        house = self.make_house()
        self.add_agent(house, "agent", gold=100, points=0)
        house.current_auctions = {"a1": {}}
        house.current_rolls = {"a1": 30}
        published_rate = 5.0

        # Agent bids everything and asks to sell 25 points it does not yet have.
        house.register_bid("agent", "a1", 100)
        house.register_point_purchase("agent", 25)
        self.assertEqual(house.agents["agent"]["gold"], 0)

        # A bid placed after the request cannot use the not-yet-settled gold.
        house.register_bid("agent", "a1", 1)
        self.assertEqual(len(house.current_bids["a1"]), 1)

        # Server order: bids first, then purchases at the published rate.
        house.process_all_bids()
        house.process_point_purchases(published_rate)

        self.assertEqual(house.agents["agent"]["points"], 5)      # 30 won - 25 sold
        self.assertEqual(house.agents["agent"]["gold"], 125)      # 25 * 5.0
        self.assertNotEqual(house.gold_per_point, published_rate)  # next round's rate differs

    def test_sale_is_clamped_to_floor_after_auction_results(self):
        house = self.make_house()
        self.add_agent(house, "agent", gold=10, points=-100)
        house.current_auctions = {"a1": {}}
        house.current_rolls = {"a1": 4}

        house.register_bid("agent", "a1", 10)
        house.register_point_purchase("agent", 1000)
        house.process_all_bids()
        house.process_point_purchases(2.0)

        self.assertEqual(house.agents["agent"]["points"], -100)  # -96 -> sells 4
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


class LogFileTests(unittest.TestCase):
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.log_dir = Path(temp_dir.name) / "nested" / "logs"

    def test_no_files_written_when_logging_disabled(self):
        house = AuctionHouse("game", "play", save_logs=False, log_dir=str(self.log_dir))
        house.add_agent("A", "agent1", "pid", "secret-1")
        house.prepare_auctions()

        self.assertIsNone(house.log_file)
        self.assertIsNone(house.log_player_id_file)
        self.assertFalse(self.log_dir.exists())

    def test_logs_written_to_log_dir_and_new_pair_per_game(self):
        house = AuctionHouse("game", "play", save_logs=True, log_dir=str(self.log_dir))
        house.add_agent("A", "agent1", "human-42", "secret-1")
        house.prepare_auctions()

        self.assertEqual(sorted(p.name for p in self.log_dir.iterdir()),
                         ["auction_house_log_1.jsonln", "auction_house_log_player_id_1.jsonln"])
        pid_row = json.loads((self.log_dir / "auction_house_log_player_id_1.jsonln").read_text())
        self.assertEqual(pid_row, {"player_id": "human-42", "agent_id": "agent1", "name": "A"})
        self.assertNotIn("human-42", (self.log_dir / "auction_house_log_1.jsonln").read_text())

        house.reset()
        house.add_agent("B", "agent2", "human-43", "secret-2")
        house.prepare_auctions()
        self.assertTrue((self.log_dir / "auction_house_log_2.jsonln").is_file())
        self.assertTrue((self.log_dir / "auction_house_log_player_id_2.jsonln").is_file())
        self.assertNotIn("human-43", (self.log_dir / "auction_house_log_player_id_1.jsonln").read_text())

    def test_log_dir_from_environment(self):
        with patch.dict("os.environ", {"AH_LOG_DIR": str(self.log_dir)}):
            house = AuctionHouse("game", "play", save_logs=True)
        self.assertEqual(Path(house.log_file).parent, self.log_dir)
        self.assertTrue(self.log_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
