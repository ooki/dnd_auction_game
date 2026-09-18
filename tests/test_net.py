import unittest
from unittest.mock import patch

from dnd_auction_game.net import resolve_ssl, ws_scheme, http_scheme, is_local_host


class ResolveSslTests(unittest.TestCase):
    def test_auto_is_plain_for_local_hosts_only(self):
        for host in ("localhost", "LOCALHOST", "127.0.0.1", "::1", " localhost "):
            self.assertTrue(is_local_host(host))
            self.assertFalse(resolve_ssl(host, None), host)
        for host in ("auction.example.org", "10.0.0.5", "myserver"):
            self.assertFalse(is_local_host(host))
            self.assertTrue(resolve_ssl(host, None), host)

    def test_explicit_override_wins(self):
        self.assertTrue(resolve_ssl("localhost", True))
        self.assertFalse(resolve_ssl("auction.example.org", False))

    def test_schemes(self):
        self.assertEqual(ws_scheme(True), "wss")
        self.assertEqual(ws_scheme(False), "ws")
        self.assertEqual(http_scheme(True), "https")
        self.assertEqual(http_scheme(False), "http")


class ClientSchemeTests(unittest.TestCase):
    def make_client(self, host, **kw):
        from dnd_auction_game.client import AuctionGameClient
        with patch("dnd_auction_game.client.os.path.isdir", return_value=True), \
             patch("dnd_auction_game.client.os.listdir", return_value=[]), \
             patch("dnd_auction_game.client.machineid.hashed_id", side_effect=lambda s: "h-" + s):
            return AuctionGameClient(host, "tester", port=1234, **kw)

    def test_client_defaults_to_wss_for_remote_and_ws_for_local(self):
        self.assertFalse(self.make_client("localhost").use_ssl)
        self.assertTrue(self.make_client("auction.example.org").use_ssl)
        self.assertFalse(self.make_client("auction.example.org", use_ssl=False).use_ssl)

    def test_runner_defaults(self):
        from dnd_auction_game.play import AuctionGameRunner
        self.assertFalse(AuctionGameRunner("localhost", "tok").use_ssl)
        self.assertTrue(AuctionGameRunner("auction.example.org", "tok").use_ssl)
        self.assertTrue(AuctionGameRunner("localhost", "tok", use_ssl=True).use_ssl)


if __name__ == "__main__":
    unittest.main()
