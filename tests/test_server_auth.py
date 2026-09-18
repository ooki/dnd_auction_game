import asyncio
import json
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import uvicorn
import websockets
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

_LOG_DIR = tempfile.TemporaryDirectory()
with patch.dict("os.environ", {"AH_LOG_DIR": _LOG_DIR.name}):
    from dnd_auction_game import server


def hello(a_id="agent_one", name="Agent One", secret="secret-agent-one", player_id="pid"):
    return {"a_id": a_id, "name": name, "player_id": player_id, "secret": secret}


def wait_for(cond, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.01)
    return cond()


async def async_wait_for(cond, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        await asyncio.sleep(0.01)
    return cond()


def n_active():
    return len(server.connection_manager.active_connections)


def reset_server_state():
    server.auction_house.save_logs = False
    server._reset_game_state()
    server.connection_manager.active_connections = []
    server.connection_manager.agent_connections = {}


class ServerAuthTests(unittest.TestCase):
    def setUp(self):
        reset_server_state()
        self.client = TestClient(server.app)
        self.url = "/ws/{}".format(server.auction_house.game_token)

    def test_impostor_with_wrong_secret_is_rejected(self):
        with self.client.websocket_connect(self.url) as ws:
            ws.send_json(hello())
            self.assertTrue(wait_for(lambda: n_active() == 1))
            self.assertIn("agent_one", server.auction_house.agents)

            with self.client.websocket_connect(self.url) as impostor:
                impostor.send_json(hello(name="Impostor", secret="guess"))
                with self.assertRaises(WebSocketDisconnect):
                    impostor.receive_json()

            self.assertEqual(server.auction_house.names["agent_one"], "Agent One")
            self.assertEqual(n_active(), 1)
            self.assertIn("agent_one", server.connection_manager.agent_connections)

    def test_missing_secret_is_rejected(self):
        with self.client.websocket_connect(self.url) as ws:
            info = hello()
            del info["secret"]
            ws.send_json(info)
            with self.assertRaises(WebSocketDisconnect):
                ws.receive_json()
        self.assertNotIn("agent_one", server.auction_house.agents)

    def test_runner_rejects_out_of_range_or_malformed_num_rounds(self):
        run_url = "/ws_run/{}".format(server.auction_house.play_token)
        for bad in ({"num_rounds": server.MAX_ROUNDS + 1}, {"num_rounds": "abc"},
                    {"num_rounds": True}, {"num_rounds": 0}, ["not", "a", "dict"]):
            with self.client.websocket_connect(run_url) as ws:
                ws.send_json(bad)
                self.assertIn("error", ws.receive_json())
                with self.assertRaises(WebSocketDisconnect):
                    ws.receive_json()
            self.assertFalse(server.auction_house.is_active)

    def test_runner_accepts_valid_num_rounds(self):
        run_url = "/ws_run/{}".format(server.auction_house.play_token)
        with self.client.websocket_connect(run_url) as ws:
            ws.send_json({"num_rounds": 7})
            self.assertEqual(ws.receive_json()["num_players"], 0)
        self.assertTrue(wait_for(lambda: server.auction_house.is_active))
        self.assertEqual(server.auction_house.num_rounds_in_game, 7)
        self.assertEqual(len(server.auction_house.gold_income_per_round), 7)

    def test_server_rejects_new_agents_when_full(self):
        with patch.object(server, "MAX_AGENTS", 1):
            with self.client.websocket_connect(self.url) as first:
                first.send_json(hello())
                self.assertTrue(wait_for(lambda: n_active() == 1))

                with self.client.websocket_connect(self.url) as second:
                    second.send_json(hello(a_id="agent_two", secret="secret-agent-two"))
                    with self.assertRaises(WebSocketDisconnect):
                        second.receive_json()
                self.assertNotIn("agent_two", server.auction_house.agents)

    def test_oversized_and_malformed_bid_messages_are_ignored(self):
        with self.client.websocket_connect(self.url) as ws:
            ws.send_json(hello())
            self.assertTrue(wait_for(lambda: n_active() == 1))
            server.auction_house.agents["agent_one"]["gold"] = 1000
            server.auction_house.current_auctions = {"a1": {}, "a2": {}}

            ws.send_json(["not", "a", "dict"])
            ws.send_json({"bids": "not-a-dict", "points_to_spend": "abc"})
            ws.send_json({"bids": {1: 10, "a1": True, "a2": "9" * 13}})
            # 500 keys, only the first len(current_auctions) are examined
            many = {"junk{}".format(i): 1 for i in range(500)}
            many["a1"] = 10
            ws.send_json({"bids": many})
            ws.send_json({"bids": {"a2": 20}})
            self.assertTrue(wait_for(lambda: "a2" in server.auction_house.current_bids))

        self.assertEqual(server.auction_house.current_bids["a2"], [("agent_one", 20)])
        self.assertNotIn("a1", server.auction_house.current_bids)
        self.assertEqual(server.auction_house.agents["agent_one"]["gold"], 980)

    def test_runner_refuses_to_start_while_game_running(self):
        run_url = "/ws_run/{}".format(server.auction_house.play_token)
        with self.client.websocket_connect(run_url) as ws:
            ws.send_json({"num_rounds": 5})
            ws.receive_json()
        self.assertTrue(wait_for(lambda: server.auction_house.is_active))

        with self.client.websocket_connect(run_url) as ws:
            ws.send_json({"num_rounds": 99})
            self.assertIn("error", ws.receive_json())
        self.assertEqual(server.auction_house.num_rounds_in_game, 5)
        self.assertTrue(server.auction_house.is_active)

    def test_wrong_tokens_are_rejected_at_handshake(self):
        for url in ("/ws/wrong-token", "/ws_run/wrong-token"):
            with self.assertRaises(WebSocketDisconnect) as cm:
                with self.client.websocket_connect(url):
                    pass
            self.assertEqual(cm.exception.code, 1008)

    def test_reset_requires_post_and_correct_token(self):
        token = server.auction_house.play_token
        self.assertEqual(self.client.get("/reset/{}".format(token)).status_code, 405)

        resp = self.client.post("/reset/not-the-token")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["ok"])

    def test_reset_clears_state_and_disconnects_clients(self):
        with self.client.websocket_connect(self.url) as ws:
            ws.send_json(hello())
            self.assertTrue(wait_for(lambda: n_active() == 1))
            server.auction_house.is_active = True

            resp = self.client.post("/reset/{}".format(server.auction_house.play_token))
            self.assertTrue(resp.json()["ok"])
            with self.assertRaises(WebSocketDisconnect):
                ws.receive_json()

        self.assertEqual(server.auction_house.agents, {})
        self.assertFalse(server.auction_house.is_active)
        self.assertEqual(n_active(), 0)

    def test_public_api_does_not_expose_agent_id(self):
        with self.client.websocket_connect(self.url) as ws:
            ws.send_json(hello())
            self.assertTrue(wait_for(lambda: n_active() == 1))
            data = self.client.get("/api/leadboard").json()
        self.assertEqual(len(data["players"]), 1)
        self.assertNotIn("id", data["players"][0])
        self.assertNotIn("agent_one", str(data))
        self.assertEqual(data["players"][0]["name"], "Agent One")


class LiveServerReconnectTests(unittest.TestCase):
    """Cross-socket behaviour (handler B closing socket A) needs a single event
    loop, which Starlette's TestClient does not provide, so run real uvicorn."""

    @classmethod
    def setUpClass(cls):
        reset_server_state()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        config = uvicorn.Config(server.app, host="127.0.0.1", port=cls.port, log_level="warning")
        cls.uvicorn = uvicorn.Server(config)
        cls.thread = threading.Thread(target=cls.uvicorn.run, daemon=True)
        cls.thread.start()
        assert wait_for(lambda: cls.uvicorn.started, timeout=5.0)
        cls.url = "ws://127.0.0.1:{}/ws/{}".format(cls.port, server.auction_house.game_token)

    @classmethod
    def tearDownClass(cls):
        cls.uvicorn.should_exit = True
        cls.thread.join(timeout=5.0)

    def setUp(self):
        reset_server_state()

    @staticmethod
    async def closed(ws, timeout=2.0):
        try:
            await asyncio.wait_for(ws.recv(), timeout)
            return False
        except websockets.ConnectionClosed:
            return True
        except asyncio.TimeoutError:
            return False

    def test_reconnect_with_correct_secret_replaces_old_socket(self):
        async def scenario():
            old = await websockets.connect(self.url)
            await old.send(json.dumps(hello()))
            self.assertTrue(await async_wait_for(lambda: n_active() == 1))
            first = server.connection_manager.agent_connections["agent_one"]

            new = await websockets.connect(self.url)
            await new.send(json.dumps(hello()))
            self.assertTrue(await self.closed(old))
            self.assertTrue(await async_wait_for(lambda: n_active() == 1))
            self.assertIsNot(server.connection_manager.agent_connections["agent_one"], first)

            self.assertFalse(await self.closed(new, timeout=0.3))
            await new.close()

        asyncio.run(scenario())

    def test_reconnect_allowed_when_server_full(self):
        async def scenario():
            with patch.object(server, "MAX_AGENTS", 1):
                first = await websockets.connect(self.url)
                await first.send(json.dumps(hello()))
                self.assertTrue(await async_wait_for(lambda: n_active() == 1))

                again = await websockets.connect(self.url)
                await again.send(json.dumps(hello()))
                self.assertTrue(await self.closed(first))
                self.assertFalse(await self.closed(again, timeout=0.3))
                self.assertEqual(n_active(), 1)
                await again.close()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
