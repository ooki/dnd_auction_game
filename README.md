# dnd-auction-game


In this game, your goal is to score as many points as possible by participating in auctions. 

Every round, each player gets 1000 gold to use in these auctions. At the beginning of each round, you'll see a set number of auctions, and you need to submit your bids in the form of a dictionary (you can choose not to bid as well).  

The server will reward the auctions to the highest bidders (there can be multiple winners if there's a tie), and the winning player will earn points based on a random dice roll.  

If you don't win an auction, you'll get back 60% of the gold you bid. The exact number of points you receive from an auction is determined by rolling dice, so it's a bit unpredictable.  

In addition, the gold you have after bidding is increased with a 10% interest rate*, thanks to the Iron Bank of Braavos.

To pass, according to Gandalf, you must obtain at least 10 points. 

*Turns out: Reading the fine print, tells us that the interest rate starts at 10% (= 1.1) and follows the function:  $1 + \sigma(4 - \frac{g}{1000} )$. Where $\sigma(\cdot)$ is the sigmoid function and $g$ is the amount of gold you have.

_Auctions_  
The auctions are presented in D&D form, for example: 3d6+5 means throw a 6 sided die 3 times and add 5, add it all up
and thats the number of points given by the auction. In other words the exact amount of points given for an auction is
stochastic. 



# Installation
To install, run:  
pip install dnd_auction_game



# Flow
A game is done in the following order:
1. start the server
2. start&connect all agents 
3. run the game runner
4. Observe the leadboard at '/' on the server (http://localhost:8000 if running default & local)
5. The logs of all the games is stored in /logs - Use these to train & improve your agent.


# Server 
To run the server, use: 'uvicorn dnd_auction_game.server:app' in the directory root directory.  
Ctrl+C to stop it cleanly.

# Agents (players)
See the folder example_agents (on github) for examples on how to create a agent.
    agent_print_info.py
    agent_tiny_bid.py
    agent_random_walk.py
    agent_random_single.py



NOTE: If playing on a non-local server the agent must set the host&port in the file.

In general you must implement a make_bid() function that takes the following parameters (see agent_print_info.py for how to parse this info):

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
Run 'python -m dnd_auction_game.play' 
This will run the game for 12 rounds.

Use python 'python -m dnd_auction_game.play XX'
to play for XX rounds. Example: 'python -m dnd_auction_game.play 42' will play the game for 42 rounds.

Remember: connect all agents BEFORE running play_game.py, the server does not need to be restarted.

# The logs (complete history)
The logs (complete history) will be stored in ./logs use it to  create clever agents.









