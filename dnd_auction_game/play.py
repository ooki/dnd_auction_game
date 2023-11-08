import sys
import random
import asyncio
import json
import websockets


class AuctionGameRunner:
    def __init__(self, host:str, n_rounds=5, time_per_round:float=1.0, token:str="play123", port:int=8000):
        self.host = host
        self.port = port
        self.n_rounds = n_rounds
        self.token = token
        
        self.time_per_round = time_per_round
        
    def run(self):
        asyncio.run(self._internal_run())
        
        
    async def _internal_run(self):
        connection_str = "ws://{}:{}/ws_run/{}".format(self.host, self.port, self.token)
        print("connecting to: {}".format(connection_str))
        
        async with websockets.connect(connection_str) as sock:
            print("<connected - starting game>")
            
            for i in range(self.n_rounds):
                print("start round:", i)
                d = {"start_round": i}
                await sock.send(json.dumps(d))            
                await asyncio.sleep(self.time_per_round)
            
        print("<done>")
            
        
        

if __name__ == "__main__":    
    host = "localhost"
    
    n_rounds = 12
    if len(sys.argv) == 2:
        n_rounds = int(sys.argv[1])
        
    runner = AuctionGameRunner(host, n_rounds=n_rounds)
    print("Running the game for: {} rounds.".format(n_rounds))
    print("Ctrl+C to stop cleanly")
    
    try:
        runner.run()
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")





