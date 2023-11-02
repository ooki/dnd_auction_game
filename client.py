
import random
import asyncio

import machineid
import websockets



class AuctionGameClient:
    def __init__(self, host:str, token:str, agent_name:str, port:int=8001):
        self.host = host
        self.port = port

        self.token = token
        self.agent_name = agent_name
        self.secret = machineid.hashed_id('auction-game')


    def run(self, bid_callback):
        asyncio.run(self._internal_run(bid_callback))
        print("<run done>")

    async def _internal_run(self, bid_callback):
        agent_info = {}
        agent_info["name"] = self.agent_name
        agent_info["secret"] = self.secret

        connection_str = "ws://{}:{}/{}".format(self.host, self.port, self.token)
        print("connection to: {}".format(connection_str))

        async with websockets.connect(connection_str) as websocket:
            print("<connected>")

        print("<internal done>")



    


def random_all_in(state: dict, all_states:list, auctions:dict):
    bids = {}
    if state["gold"] > 0:
        target_auction_id = random.sample(auctions.keys(), k=1)[0] # sample returns a list
        bids[target_auction_id] = state["gold"]

    return bids

      


if __name__ == "__main__":
    game = AuctionGameClient("localhost" token="123", agent_name="random_all_in_v1")
    try:
        game.run(random_all_in)
    except KeyboardInterrupt:
        print("<interrupt - shutting down>")

    print("<game is done>")









