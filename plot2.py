import os
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import json

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Auction Bot Dashboard"

# Helper Functions


def load_agent_logs(agent_ids, multiplier):
    """Load agent log files based on competition."""
    data = []
    for agent_id in agent_ids:
        log_file = f"logs/agent_local_rand_id_{
            agent_id}_n{multiplier * 21}.jsonl"
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                for line in f:
                    data.append(json.loads(line))
    return pd.DataFrame(data)


def parse_logs(competition_num):
    """Parse logs for a specific competition."""
    # File names
    player_file = f"auction_house_log_player_id_{competition_num}.jsonln"
    auction_file = f"auction_house_log_{competition_num}.jsonln"

    # Load player mappings
    with open(player_file, "r") as f:
        player_data = [json.loads(line) for line in f]
    player_mapping = {p["agent_id"]: p["name"] for p in player_data}
    agent_ids = [p["agent_id"] for p in player_data]

    # Load auction logs
    with open(auction_file, "r") as f:
        log_data = [json.loads(line) for line in f]

    # Create dataframes
    states = []
    auctions = []
    bids = []

    for entry in log_data:
        round_num = entry["round"]

        # States data
        for bot_id, state in entry["states"].items():
            states.append(
                {
                    "round": round_num,
                    "bot_id": bot_id,
                    "gold": state["gold"],
                    "points": state["points"],
                }
            )

        # Current auctions
        for auction_id, auction in entry.get("auctions", {}).items():
            auctions.append(
                {
                    "round": round_num,
                    "auction_id": auction_id,
                    "die": auction["die"],
                    "num": auction["num"],
                    "bonus": auction["bonus"],
                }
            )

        # Bids
        for auction_id, auction in entry.get("prev_auctions", {}).items():
            reward = auction.get("reward", 0)
            for bid in auction.get("bids", []):
                bids.append(
                    {
                        "round": round_num - 1,
                        "auction_id": auction_id,
                        "bot_id": bid["a_id"],
                        "gold_bid": bid["gold"],
                        "reward": reward,
                    }
                )

    # Load agent logs
    agent_logs_df = load_agent_logs(agent_ids, competition_num)

    return (
        pd.DataFrame(states),
        pd.DataFrame(auctions),
        pd.DataFrame(bids),
        pd.DataFrame(agent_logs_df),
        player_mapping,
    )


# Default competition
default_competition = 1
states_df, auctions_df, bids_df, agent_logs_df, player_mapping = parse_logs(
    default_competition
)

# Layout
app.layout = html.Div(
    [
        html.H1("Auction Bot Dashboard", style={"textAlign": "center"}),
        # Competition selector
        html.Div(
            [
                html.Label("Select Competition"),
                dcc.Dropdown(
                    id="competition-selector",
                    options=[
                        {"label": f"Competition {i}", "value": i} for i in range(1, 11)
                    ],  # Example: 10 competitions
                    value=default_competition,
                    style={"width": "50%"},
                ),
            ],
            style={"textAlign": "center", "marginBottom": "20px"},
        ),
        # Bot selector
        dcc.Dropdown(
            id="bot-selector",
            options=[
                {"label": name, "value": bot_id}
                for bot_id, name in player_mapping.items()
            ],
            value=list(player_mapping.keys())[:3],  # Default selection
            multi=True,
            style={"width": "60%", "margin": "auto"},
        ),
        html.Div(id="graphs-container"),
        dcc.Graph(id="gold-over-time"),
        dcc.Graph(id="points-over-time"),
        dcc.Graph(id="bids-per-auction"),
        dcc.Graph(id="expected-vs-actual"),
    ]
)

# Callbacks


@app.callback(
    Output("bot-selector", "options"),
    Input("competition-selector", "value"),
)
def update_bots(competition_num):
    global states_df, auctions_df, bids_df, agent_logs_df, player_mapping
    states_df, auctions_df, bids_df, agent_logs_df, player_mapping = parse_logs(
        competition_num
    )
    return [{"label": name, "value": bot_id} for bot_id, name in player_mapping.items()]


@app.callback(Output("gold-over-time", "figure"), [Input("bot-selector", "value")])
def update_gold(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = player_mapping.get(bot_id, bot_id)
        data = states_df[states_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(x=data["round"], y=data["gold"], mode="lines", name=bot_name)
        )
    fig.update_layout(title="Gold Over Time", xaxis_title="Round", yaxis_title="Gold")
    return fig


@app.callback(Output("points-over-time", "figure"), [Input("bot-selector", "value")])
def update_points(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = player_mapping.get(bot_id, bot_id)
        data = states_df[states_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(x=data["round"], y=data["points"], mode="lines", name=bot_name)
        )
    fig.update_layout(
        title="Points Over Time", xaxis_title="Round", yaxis_title="Points"
    )
    return fig


@app.callback(Output("bids-per-auction", "figure"), [Input("bot-selector", "value")])
def update_bids(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = player_mapping.get(bot_id, bot_id)
        data = bids_df[bids_df["bot_id"] == bot_id]
        fig.add_trace(go.Bar(x=data["auction_id"], y=data["gold_bid"], name=bot_name))
    fig.update_layout(
        title="Bids Per Auction", xaxis_title="Auction ID", yaxis_title="Gold Bid"
    )
    return fig


@app.callback(Output("expected-vs-actual", "figure"), [Input("bot-selector", "value")])
def update_expected_vs_actual(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = player_mapping.get(bot_id, bot_id)
        data = bids_df[bids_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(
                x=data["auction_id"],
                y=data["reward"],
                mode="markers",
                name=f"{bot_name} Reward",
            )
        )
    fig.update_layout(
        title="Expected vs Actual Rewards",
        xaxis_title="Auction ID",
        yaxis_title="Reward",
    )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
