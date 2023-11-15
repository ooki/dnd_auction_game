import sys
import random
import asyncio
import json
import websockets


class AuctionGameRunner:
    def __init__(self, host:str, play_token:str, n_rounds=5, time_per_round:float=1.0, port:int=8000):
        self.host = host
        self.port = port
        self.n_rounds = n_rounds
        self.token = play_token
        
        self.time_per_round = time_per_round
        
    def run(self):
        asyncio.run(self._internal_run())
        
        
    async def _internal_run(self):
        connection_str = "ws://{}:{}/ws_run/{}".format(self.host, self.port, self.token)
        print("connecting to: {}".format(connection_str))
        
        round_k = 0

        while True:
            try:
                async with websockets.connect(connection_str) as sock:
                    print("<connected - starting game>")
                    
                    for i in range(round_k, self.n_rounds):
                        print("start round:", i)
                        d = {"start_round": i, "done": 0}
                        await sock.send(json.dumps(d))            
                        await asyncio.sleep(self.time_per_round)

                        round_k = i
                    
                    d = {"start_round": i, "done": 1}
                    await sock.send(json.dumps(d))
                    break
            except:
                continue

        print("<done>")
            
        
        

if __name__ == "__main__":    
    host = "localhost"
    
    n_rounds = 12
    if len(sys.argv) >= 2:
        n_rounds = int(sys.argv[1])

    if len(sys.argv) >= 3:
        play_token = sys.argv[2]
    else:
        play_token = "play123"
        
    runner = AuctionGameRunner(host, n_rounds=n_rounds, play_token=play_token)
    print("Running the game for: {} rounds.".format(n_rounds))
    print("Ctrl+C to stop cleanly")
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")





