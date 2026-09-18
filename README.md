# dnd-auction-game

## How to set up and run locally

**Requires Python 3.10 or newer.** From a terminal, create and activate a standard Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install the released package from PyPI with pip:

```bash
python -m pip install --upgrade pip
python -m pip install dnd_auction_game
```

If you cloned this repository and want to run its current source code and bundled example agents, install the checkout instead:

```bash
python -m pip install -e .
```

Then use three terminals (with `.venv` activated in each):

```bash
# Terminal 1: start the server
python -m dnd_auction_game.server

# Terminal 2: connect 20 example bots
python example_agents/run_multi_agents.py -n 20

# Terminal 3: start a 20-round game after the bots have connected
python -m dnd_auction_game.play 20
```

Open the live leaderboard at <http://127.0.0.1:8000/>. After a completed game, launch the bots first and then run the game runner again; the first new connection automatically resets the finished game.

## The game

Your goal is to score as many points as possible by participating in auctions.

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

The local virtual-environment setup above is recommended. For a global installation of the released package, run:

```bash
python3 -m pip install dnd_auction_game
```

**Upgrading to 0.5.0 (breaking):** agents built on `dnd_auction_game < 0.5.0` can no longer connect.
Agents now send a per-agent `secret` (derived from the machine id) alongside their `a_id`, and the
server uses it to verify reconnects so nobody can bid as someone else. Just `pip install -U dnd_auction_game`
on every machine running an agent - no code changes are needed in your agent.

# Flow

A game is done in the following order:

1. start the server: `python -m dnd_auction_game.server`
2. start&connect all agents, e.g. `python example_agents/run_multi_agents.py -n 4`
3. run the game runner: `python -m dnd_auction_game.play 20`
4. Observe the leadboard at '/' on the server (http://localhost:8000 if running default & local)
5. The logs of all the games is stored in /logs - Use these to train & improve your agent.
6. (Reset the server if you want to play again : you can also just turn it on and off)

# Server

To run the server locally:

```bash
python -m dnd_auction_game.server
```

This listens on `localhost:8000`, which is exactly where the example agents, the game runner and the reset CLI
connect by default - so for local testing nothing needs to be configured. Ctrl+C stops it cleanly.

Options (`python -m dnd_auction_game.server --help`):

- `--host 0.0.0.0` accept agents from other machines (default: `127.0.0.1`, local only)
- `--port 8000`
- `--ssl-keyfile ... --ssl-certfile ...` serve over TLS (`wss://`)
- `--ws-max-size 65536` maximum websocket message size in bytes
- `--no-access-log` hide uvicorn's per-request log lines

When started this way the game/play tokens are redacted from uvicorn's log output. You can also run uvicorn
directly: `uvicorn dnd_auction_game.server:app` (same defaults for host and port, but uvicorn's 16 MiB message
limit applies and the tokens will appear in its log lines).

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
- Tokens travel in the URL path, so serve over TLS. Either let uvicorn terminate TLS directly:

  ```bash
  AH_GAME_TOKEN=... AH_PLAY_TOKEN=... AH_LOG_DIR=~/ah_logs \
  python -m dnd_auction_game.server --host 0.0.0.0 --port 8022 \
      --ssl-keyfile ~/certs/privkey.pem --ssl-certfile ~/certs/fullchain.pem
  ```

  (`uvicorn dnd_auction_game.server:app ...` with the same flags works too, but add `--ws-max-size 65536` and be
  aware that the tokens then show up in uvicorn's request log.)

  or put it behind a reverse proxy (nginx/Caddy) that terminates `https://`/`wss://`. The certificate must be issued
  for the DNS name that agents will use as `host` (an IP address will fail certificate verification).
- Agents, the runner and the reset CLI pick `wss://`/`https://` automatically for any host other than
  `localhost`/`127.0.0.1`, so students only need to change `host` and `port` (see below).
- `--ws-max-size 65536` limits incoming websocket messages (default 16 MiB). A bid message is a few hundred bytes.
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

## Local testing vs. the real game server

The client picks the connection type from `host`:

| `host`                        | Connection | When |
|-------------------------------|------------|------|
| `localhost` / `127.0.0.1`     | `ws://` (no encryption) | Testing on your own machine with `uvicorn dnd_auction_game.server:app` - no certificates needed. |
| anything else                 | `wss://` (TLS)          | The real game server, which runs with a certificate. |

So for local testing keep the example agents as they are, and to play for real change only the two lines:

```python
host = "auction.example.org"   # the DNS name the organiser gave you
port = 8022                    # the port the organiser gave you
```

If you ever need to override the automatic choice (e.g. a plain, non-TLS server on your LAN), pass it explicitly:

```python
game = AuctionGameClient(host=host, agent_name=agent_name, player_id=player_id, port=port, use_ssl=False)
```

The runner and reset CLIs accept the same override as flags: `--ssl` / `--no-ssl`.

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

- Run: `python -m dnd_auction_game.reset [PLAY_TOKEN] [HOST] [PORT] [--ssl|--no-ssl]` (sends `POST /reset/{PLAY_TOKEN}`)
- Examples:
  - `python -m dnd_auction_game.reset`  (uses `AH_PLAY_TOKEN` env var or 'play123', host=localhost, port=8000, http)
  - `python -m dnd_auction_game.reset mytoken`  (host=localhost, port=8000)
  - `python -m dnd_auction_game.reset mytoken auction.example.org 5566`  (https, automatic for non-local hosts)
  - `python -m dnd_auction_game.reset mytoken 10.0.0.5 9000 --no-ssl`  (plain http to a LAN server)
- The game runner takes the same optional arguments: `python -m dnd_auction_game.play [N_ROUNDS] [PLAY_TOKEN] [HOST] [PORT] [--ssl|--no-ssl]`

The CLI uses `AH_PLAY_TOKEN` as the default token if none is given on the command line (see the Server section).

What reset does:

- Disconnects all connected clients.
- Clears all game state (players, rounds, auctions, and exchange rate).
- Makes the server ready to accept new players and start a new game.

# Example agents: location and local use

The example agents are in [`example_agents/`](example_agents/):

- `agent_tiny_bid.py` bids small amounts on every auction and occasionally sells points.
- `agent_random_single.py` bids on one random auction and aggressively cashes out points above its reserve.
- `agent_random_walk.py` adjusts a single bid based on previous results and sells points when it needs future gold.
- `agent_print_info.py` only prints the public round information; it does not bid or sell points.

To run one agent locally, keep the server running and, with the virtual environment activated, run for example:

```bash
python example_agents/agent_tiny_bid.py
```

To launch several bidding agents, use the helper from the repository root. It chooses from the three bidding agents above and deliberately excludes `agent_print_info.py`:

```bash
python example_agents/run_multi_agents.py -n 20
```

Connect agents before starting the runner. For a local game, the complete order is: start `python -m dnd_auction_game.server`, launch agents, then run `python -m dnd_auction_game.play 20`.
