# auction-game

To install, run:  
pip install -r requirements.txt

# Flow
A game is done in the following order:
1. start the server
2. start&connect all agents 
3. run the game runner
4. Observe the leadboard at '/' on the server (http://localhost:8000 if running default & local)
5. The logs of all the games is stored in /logs - Use these to train & improve your agent.


# Server 
To run the server, use: 'uvicorn ag_server:app' in the directory root directory.  
Ctrl+C to stop it cleanly.

# Agents (players)
See:
    agent_linear_prediction.py
    agent_linear_prediction.py
    agent_tiny_bid.py

For examples on how to create a agent.
NOTE: If playing on a non-local server the agent must set the host in the file.

In general you must implement a make_bid() function that takes the following parameters:

* @agent_id:str - a string that is the agent id of the current agent.

* @states:dict - a dict of all agents, key: agent_id, value is a dict:  
              {"gold": agents_gold, "points": agents points}

* @auctions:dict - a dict of the auctions in the current round, key: auction_id, value is a dict:  
  {"die": size of the die: 2,3,4,6,8,10,12 or 20,  
   "num": the number of dices to be thrown, 
   "bonus": a flat sum to be added.}  
   This can be read as D&D style throw, example: 3d6+7  
   would be: {"die": 6, "num": 3, "bonus": 7}.

* @prev_auctions:dict - a dict of the previous round. similar to
@auctions, but also contains the "reward" field that tells how many 
the winner of the auction gained. In addition it contain a "bids" key
that gives a list of the bids for this particular auction, sorted so that the winning bid is always the first in the list.


# Play the Game
Run python ./play_game.py  
This will run the game for 12 rounds.

Use python ./play_game.py  XX  
to play for XX rounds.

Remember: connect all agents BEFORE running play_game.py, the server does not need to be restarted.

# The logs (complete history)
The logs (complate history) will be stored in ./logs use it to 
create clever agents.









