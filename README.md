# dnd-auction-game

# In this game, your goal is to score as many points as possible by participating in auctions.

Every round, each player receives gold income (starts at ~1000, varies each round via random walk). At the beginning of each round, you'll see a set of auctions, and you submit your bids as a dictionary (you can choose not to bid).

The server awards each auction to the highest bidder. In case of a tie, priority determines the winner (priority swaps after ties to keep things fair). The winning player earns points based on a random dice roll.

If you don't win an auction, you get back 50% of the gold you bid; the other 50% is removed from the game. Players may also spend points to buy gold at the current gold-per-point rate. This rate is calculated from the previous round as total winning-bid gold divided by `max(1, total actual points awarded to winners)`. The first round's rate is 0 gold per point. A player may spend points down to, but never below, -100 points.

Order of settlement each round: the auctions are resolved first, then point sales are settled at the rate that was shown to you. This means the gold you get from selling points is only available for bidding from the *next* round, but points you win in this round's auctions can already be sold in the same request (the -100 floor is applied after the auction results).

In addition, the Iron Bank of Braavos pays interest on your gold holdings (up to a limit). The interest rate, bank limit, and gold income all vary each round via random walks—use `bank_state` to see future values and plan ahead.

To pass, according to Gandalf, you must obtain at least 10 points.

_Auctions_
The auctions are presented in D&D form, for example: 3d6+5 means throw a 6 sided die 3 times and add 5, add it all up
and thats the number of points given by the auction. In other words the exact amount of points given for an auction is
stochastic.

# Installation

To install, run:
pip install dnd_auction_game

**Upgrading to 0.5.0 (breaking):** agents built on `dnd_auction_game < 0.5.0` can no longer connect.
Agents now send a per-agent `secret` (derived from the machine id) alongside their `a_id`, and the
server uses it to verify reconnects so nobody can bid as someone else. Just `pip install -U dnd_auction_game`
on every machine running an agent - no code changes are needed in your agent.

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

The server is configured with environment variables:

| Variable         | Default   | Meaning |
|------------------|-----------|---------|
| `AH_GAME_TOKEN`  | `play123` | Token agents use to connect (`/ws/{token}`). |
| `AH_PLAY_TOKEN`  | `play123` | Admin token for starting (`/ws_run/{token}`) and resetting (`POST /reset/{token}`) a game. |
| `AH_MAX_AGENTS`  | `200`     | Maximum number of distinct agents in one game. Reconnects of existing agents are always allowed. |
| `AH_MAX_ROUNDS`  | `10000`   | Upper bound for `num_rounds` requested by the game runner. |
| `AH_LOG_DIR`     | `.`       | Directory for the server-side game logs (created if missing). |

Notes:

- The runner refuses to start a game while one is already running; reset the server first.
- New agents cannot join after the game has started; existing agents may reconnect at any time.
- If an agent reconnects while its previous connection is still open, the old connection is closed.

## Server logs

Each game writes two files to `AH_LOG_DIR`, numbered so nothing is overwritten:

- `auction_house_log_N.jsonln` - one JSON line per round with the full public state (the same data agents receive).
- `auction_house_log_player_id_N.jsonln` - one JSON line per agent mapping `player_id` -> `agent_id` / `name`.
  `player_id` is stored in plaintext and is never sent to other agents; treat this file as private.

## Running the server for others (not on localhost)

The defaults are meant for local play. If agents connect over a network:

- Set `AH_GAME_TOKEN` and `AH_PLAY_TOKEN` to two different, unguessable values. Anyone with the play token can start
  and reset games; anyone with the game token can join.
- Tokens travel in the URL path, so put the server behind TLS (a reverse proxy such as nginx or Caddy terminating
  `https://`/`wss://`), and point agents at `wss://`.
- Limit the size of incoming websocket messages, e.g. `uvicorn dnd_auction_game.server:app --ws-max-size 65536`
  (the default is 16 MiB). A bid message is a few hundred bytes.
- Lower `AH_MAX_AGENTS` to the number of players you expect.
- Set `AH_LOG_DIR` to a directory that is not world-readable, since the player-id log is written there.

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
             gold_per_point: float,
             bank_state: dict) -> dict:
```

### Parameters

- **`agent_id`** (`str`): Your agent's unique identifier.

- **`round`** (`int`): The current round number.

- **`states`** (`dict`): All agents' current state. Key: `agent_id`, Value: `{"gold": int, "points": int}`.
  - Access your own state: `states[agent_id]`
  - Iterate over opponents by skipping your own `agent_id`.
  - The raw round payload also includes `team_names`, a mapping from `agent_id` to the public team name shown on the leaderboard. Player IDs are never sent to clients.

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

- **`gold_per_point`** (`float`): Gold received for each point spent this round. It is based on the completed previous round's winning bids and rewards; it is `0` in the first round and after a round with no winning bids.

- **`bank_state`** (`dict`): Bank parameters from current round to end of game:
  - `gold_income_per_round`: List of gold income values. Index 0 is the current round.
  - `bank_interest_per_round`: List of interest rates. Index 0 is the current round.
  - `bank_limit_per_round`: List of bank limits (max gold that earns interest). Index 0 is the current round.
  - Example: On round 5 of a 10-round game, each list has 5 elements (rounds 5–9).

### Return Value

Return a dictionary with your bids and optional point-to-gold purchase:

```python
{
    "bids": {
        "auction_id_1": gold_amount,
        "auction_id_2": gold_amount,
        # ... bid on as many auctions as you want
    },
    "points_to_spend": points_to_spend  # optional; total points cannot fall below -100
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

- Run: `python -m dnd_auction_game.reset [PLAY_TOKEN] [HOST] [PORT]` (sends `POST /reset/{PLAY_TOKEN}`)
- Examples:
  - `python -m dnd_auction_game.reset`  (uses `AH_PLAY_TOKEN` env var or 'play123', host=localhost, port=8000)
  - `python -m dnd_auction_game.reset mytoken`  (host=localhost, port=8000)
  - `python -m dnd_auction_game.reset mytoken 10.0.0.5 9000`

The CLI uses `AH_PLAY_TOKEN` as the default token if none is given on the command line (see the Server section).

What reset does:

- Disconnects all connected clients.
- Clears all game state (players, rounds, auctions, and exchange rate).
- Makes the server ready to accept new players and start a new game.
