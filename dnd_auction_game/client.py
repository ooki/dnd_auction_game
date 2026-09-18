
import random
import asyncio
import json
import os
import ssl

from typing import Optional

import machineid
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, InvalidHandshake

from dnd_auction_game.net import resolve_ssl, ws_scheme, is_local_host


class AuctionGameClient:
    def __init__(self, host:str, agent_name:str, token:str="play123", player_id:str="<identifier>",
                 port:int=8000, use_ssl:Optional[bool]=None):
        """
        use_ssl: None (default) picks automatically - plain ws:// for localhost/127.0.0.1,
                 encrypted wss:// for any other host. Pass True/False to force it.
        """
        self.host = host
        self.port = port
        self.use_ssl = resolve_ssl(host, use_ssl)
        self.player_id = player_id

        self.token = token
        self.agent_name = agent_name        
        self.log_file = None
        
        if len(self.agent_name) < 2:
            raise ValueError("Agent name is too short: '{}'".format(self.agent_name))
        
        if len(self.agent_name) > 64:
            raise ValueError("Agent name is too long: '{}'".format(self.agent_name))
        
        if is_local_host(self.host):
            self.agent_id = "local_rand_id_{}".format(random.randint(100, 1000000))
            self.agent_secret = machineid.hashed_id('auction-game-secret-{}'.format(self.agent_id))
        else:
            self.agent_id = machineid.hashed_id('auction-game')
            self.agent_secret = machineid.hashed_id('auction-game-secret')
        
        if not os.path.isdir("logs"):            
            print("unable to find ./logs => creating dir.")
            os.makedirs("logs")
        
        n_id = len(os.listdir("logs"))
        self.log_file = os.path.join("logs", "agent_{}_n{}.jsonl".format(self.agent_id, n_id))
        
        print("logging to file: '{}'".format(self.log_file))


    def run(self, bid_callback):
        asyncio.run(self._internal_run(bid_callback))
        print("<run done>")

    async def _internal_run(self, bid_callback):
        agent_info = {}
        agent_info["name"] = self.agent_name
        agent_info["a_id"] = self.agent_id
        agent_info["player_id"] = self.player_id[0:128]
        agent_info["secret"] = self.agent_secret

        scheme = ws_scheme(self.use_ssl)
        connection_str = "{}://{}:{}/ws/{}".format(scheme, self.host, self.port, self.token)
        print("connecting to: {}://{}:{}/ws/<token>".format(scheme, self.host, self.port))

        rounds_received = 0
        try:
            async with connect(connection_str) as sock:
                print("<connected to game server>")
                print(json.dumps({k: v for k, v in agent_info.items() if k != "secret"}))
                await sock.send(json.dumps(agent_info))
                                
                while True:
                    round_data_raw = await sock.recv()
                    round_data = json.loads(round_data_raw)
                    rounds_received += 1
                    
                    round_data["current_agent"] = self.agent_id
                    with open(self.log_file, "a") as fp:
                        fp.write("{}\n".format(json.dumps(round_data)))
                        

                    bank_state = {}
                    bank_state["gold_income_per_round"] = round_data["remainder_gold_income"]
                    bank_state["bank_interest_per_round"] = round_data["remainder_bank_interest"]
                    bank_state["bank_limit_per_round"] = round_data["remainder_bank_limit"]
                    
                    new_bids = bid_callback(self.agent_id, 
                                            round_data["round"],
                                            round_data["states"],
                                            round_data["auctions"],
                                            round_data["prev_auctions"],
                                            round_data["gold_per_point"],
                                            bank_state)

                    await sock.send(json.dumps(new_bids))
        
        except InvalidHandshake as e:
            if "403" in str(e):
                print("<ERROR: server refused the connection ({}). Wrong game token?>".format(e))
            elif not self.use_ssl:
                print("<ERROR: no valid response from server ({}). If this is the real game server it "
                      "requires TLS: use its DNS name as host, or pass use_ssl=True.>".format(e))
            else:
                print("<ERROR: websocket handshake failed ({})>".format(e))

        except ssl.SSLError as e:
            print("<ERROR: TLS handshake failed ({}). Is the server running with SSL? "
                  "For a plain local server pass use_ssl=False.>".format(e))

        except OSError as e:
            hint = ""
            if self.use_ssl:
                hint = " (connecting with wss://; if the server has no certificate, pass use_ssl=False)"
            print("<ERROR: could not reach server at {}:{} ({}){}>".format(self.host, self.port, e, hint))

        except ConnectionClosedError:
            print("<ERROR: Connection to server closed unexpectedly>")
        
        except ConnectionClosedOK:
            if rounds_received == 0:
                print("<ERROR: server rejected this agent before the game started. "
                      "Possible causes: the game is already running, the server is full, "
                      "or another agent already uses this agent id with a different secret.>")



      











