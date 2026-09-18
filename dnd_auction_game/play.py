import sys
import os
import random
import asyncio
import json
from typing import Optional
from websockets.asyncio.client import connect

from dnd_auction_game.net import resolve_ssl, ws_scheme


class AuctionGameRunner:
    def __init__(self, host:str, play_token:str, n_rounds=5, time_per_round:float=1.0, port:int=8000,
                 use_ssl:Optional[bool]=None):
        """use_ssl: None = auto (ws:// for localhost, wss:// otherwise); True/False to force."""
        self.host = host
        self.port = port
        self.use_ssl = resolve_ssl(host, use_ssl)
        self.n_rounds = n_rounds
        self.play_token = play_token
        
        self.time_per_round = time_per_round
        
    def run(self):
        asyncio.run(self._internal_run())
        
        
    async def _internal_run(self):
        scheme = ws_scheme(self.use_ssl)
        connection_str = "{}://{}:{}/ws_run/{}".format(scheme, self.host, self.port, self.play_token)
        print("connecting to: {}://{}:{}/ws_run/<play_token>".format(scheme, self.host, self.port))
        

        async with connect(connection_str) as sock:
            print("<connected - starting game>")

            game_info = {"num_rounds": self.n_rounds}
            await sock.send(json.dumps(game_info))

            server_info_raw = await sock.recv()
            server_info = json.loads(server_info_raw)
            if "error" in server_info:
                print("<ERROR: server refused to start game: {}>".format(server_info["error"]))
                return
            print("<server info: {}>".format(server_info))
            print("<game started>")

    
        print("<done>")
            
        
def main():
    # usage: python -m dnd_auction_game.play [N_ROUNDS] [PLAY_TOKEN] [HOST] [PORT] [--ssl|--no-ssl]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    use_ssl = True if "--ssl" in flags else False if "--no-ssl" in flags else None

    n_rounds = int(args[0]) if len(args) >= 1 else 12
    play_token = args[1] if len(args) >= 2 else os.environ.get("AH_PLAY_TOKEN", "play123")
    host = args[2] if len(args) >= 3 else "localhost"
    port = int(args[3]) if len(args) >= 4 else 8000

    runner = AuctionGameRunner(host, n_rounds=n_rounds, play_token=play_token, port=port, use_ssl=use_ssl)
    print("Running the game for: {} rounds.".format(n_rounds))
    runner.run()


if __name__ == "__main__":
    main()
    
    print("<game is done>")





