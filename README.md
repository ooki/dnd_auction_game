# dnd-auction-game

# In this game, your goal is to score as many points as possible by participating in auctions.

Every round, each player receives gold income (starts at ~1000, varies each round via random walk). At the beginning of each round, you'll see a set of auctions, and you submit your bids as a dictionary (you can choose not to bid).

The server awards each auction to the highest bidder. In case of a tie, priority determines the winner (priority swaps after ties to keep things fair). The winning player earns points based on a random dice roll.

If you don't win an auction, you get back 50% of the gold you bid. The remaining 50% goes into a shared gold pool that players can claim by spending points.

In addition, the Iron Bank of Braavos pays interest on your gold holdings (up to a limit). The interest rate, bank limit, and gold income all vary each round via random walks—use `bank_state` to see future values and plan ahead.

To pass, according to Gandalf, you must obtain at least 10 points.

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
6. (Reset the server if you want to play again : you can also just turn it on and off)

# Server

To run the server, use: 'uvicorn dnd_auction_game.server:app' in the directory root directory.
Ctrl+C to stop it cleanly.

# Agents (players)

See the folder example_agents (on github) for examples on how to create a agent.
    agent_print_info.py
    agent_tiny_bid.py
    agent_random_walk.py
    agent_random_single.py

## Running multiple example agents

To quickly spin up several example agents in parallel, use the helper script in `example_agents`:

- `example_agents/run_multi_agents.py`

This script:

- Discovers all `agent_*.py` files in `example_agents`.
- Randomly picks N of them (with replacement if N is larger than the number of files).
- Starts each chosen agent as its own OS process from a single controller process.

Example usage from the project root:

```bash
python example_agents/run_multi_agents.py --num 6
```

Short form:

```bash
python example_agents/run_multi_agents.py -n 6
```

You can also pass extra arguments to all agents by putting them after `--`:

```bash
python example_agents/run_multi_agents.py -n 6 -- --some-arg value
```

NOTE: If playing on a non-local server the agent must set the host&port in the file.

## Implementing Your Agent

You must implement a `make_bid()` function that takes the following parameters (see `agent_print_info.py` for a complete example):

```python
def make_bid(agent_id: str,
             round: int,
             states: dict,
             auctions: dict,
             prev_auctions: dict,
             pool: int,
             prev_pool_buys: dict,
             bank_state: dict) -> dict:
```

### Parameters

- **`agent_id`** (`str`): Your agent's unique identifier.

- **`round`** (`int`): The current round number.

- **`states`** (`dict`): All agents' current state. Key: `agent_id`, Value: `{"gold": int, "points": int}`.
  - Access your own state: `states[agent_id]`
  - Iterate over opponents by skipping your own `agent_id`.

- **`auctions`** (`dict`): Auctions available this round. Key: `auction_id`, Value: `{"die": int, "num": int, "bonus": int}`.
  - `die`: Size of the die (2, 3, 4, 6, 8, 10, 12, or 20).
  - `num`: Number of dice to roll.
  - `bonus`: Flat value added to the roll.
  - Example: `{"die": 6, "num": 3, "bonus": 7}` represents `3d6+7` (roll 3 six-sided dice and add 7).
  - Expected value: `(die + 1) / 2 * num + bonus`.

- **`prev_auctions`** (`dict`): Results from the previous round. Key: `auction_id`, Value includes:
  - `die`, `num`, `bonus`: Same as `auctions`.
  - `reward`: The actual points the winner received (dice roll result).
  - `bids`: List of bids sorted by amount (highest first). Each bid: `{"a_id": str, "gold": int}`.
  - The first entry in `bids` is always the winning bid.

- **`pool`** (`int`): Current gold in the pool. Players can spend points to claim a share of this gold.

- **`prev_pool_buys`** (`dict`): Pool purchases from the previous round. Key: `agent_id`, Value: points spent.

- **`bank_state`** (`dict`): Bank parameters from current round to end of game:
  - `gold_income_per_round`: List of gold income values. Index 0 is the current round.
  - `bank_interest_per_round`: List of interest rates. Index 0 is the current round.
  - `bank_limit_per_round`: List of bank limits (max gold that earns interest). Index 0 is the current round.
  - Example: On round 5 of a 10-round game, each list has 5 elements (rounds 5–9).

### Return Value

Return a dictionary with your bids and optional pool purchase:

```python
{
    "bids": {
        "auction_id_1": gold_amount,
        "auction_id_2": gold_amount,
        # ... bid on as many auctions as you want
    },
    "pool": points_to_spend  # optional, spend points to claim pool gold
}
```

Return an empty dict `{}` to skip bidding for the round.

# Play the Game

Run 'python -m dnd_auction_game.play'
This will run the game for 12 rounds.

Use python 'python -m dnd_auction_game.play XX'
to play for XX rounds. Example: 'python -m dnd_auction_game.play 42' will play the game for 42 rounds.

Remember: connect all agents BEFORE running play_game.py, the server does not need to be restarted.

# The logs (complete history)

The logs (complete history) will be stored in ./logs use it to  create clever agents.

# Resetting the Server Between Games

If you want to start a fresh game without restarting uvicorn, you can reset the server:

- Run: `python -m dnd_auction_game.reset [PLAY_TOKEN] [HOST] [PORT]`
- Examples:
  - `python -m dnd_auction_game.reset`  (uses `AH_PLAY_TOKEN` env var or 'play123', host=localhost, port=8000)
  - `python -m dnd_auction_game.reset mytoken`  (host=localhost, port=8000)
  - `python -m dnd_auction_game.reset mytoken 10.0.0.5 9000`

Environment variable:

- `AH_PLAY_TOKEN` — server-side env var defining the play token; the CLI will also use this as default if no token is provided.

What reset does:

- Disconnects all connected clients.
- Clears all game state (players, rounds, auctions, pool).
- Makes the server ready to accept new players and start a new game.
