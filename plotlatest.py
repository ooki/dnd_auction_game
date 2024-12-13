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
    files = []
    data = []
    for agent_id in agent_ids:
        log_file = f"logs/agent_local_rand_id_{agent_id}_n{multiplier}.jsonl"
        files.append(log_file)
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                for line in f:
                    data.append(json.loads(line))
    return pd.DataFrame(data), files


def parse_logs(competition_num):
    """Parse logs for a specific competition."""
    player_file = f"auction_house_log_player_id_{competition_num}.jsonln"
    auction_file = f"auction_house_log_{competition_num}.jsonln"

    files_used = [player_file, auction_file]
    if not os.path.exists(player_file) or not os.path.exists(auction_file):
        return None, None, None, None, {}, files_used

    with open(player_file, "r") as f:
        player_data = [json.loads(line) for line in f]
    player_mapping = {p["agent_id"]: p["name"] for p in player_data}
    agent_ids = [p["agent_id"] for p in player_data]

    with open(auction_file, "r") as f:
        log_data = [json.loads(line) for line in f]

    states, auctions, bids = [], [], []
    for entry in log_data:
        round_num = entry["round"]
        for bot_id, state in entry["states"].items():
            states.append(
                {
                    "round": round_num,
                    "bot_id": bot_id,
                    "gold": state["gold"],
                    "points": state["points"],
                }
            )
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

    multiplier = 21 * (competition_num - 1)
    agent_logs_df, agent_files = load_agent_logs(agent_ids, multiplier)
    files_used.extend(agent_files)

    return (
        pd.DataFrame(states),
        pd.DataFrame(auctions),
        pd.DataFrame(bids),
        pd.DataFrame(agent_logs_df),
        player_mapping,
        files_used,
    )


def create_dropdown_options(mapping):
    return [{"label": name, "value": bot_id} for bot_id, name in mapping.items()]


def build_graph(title, x_label, y_label, traces):
    fig = go.Figure()
    for trace in traces:
        fig.add_trace(trace)
    fig.update_layout(title=title, xaxis_title=x_label, yaxis_title=y_label)
    return fig


# Default competition
default_competition = 1
states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used = parse_logs(
    default_competition
)

# Layout
app.layout = html.Div(
    [
        html.H1("Auction Bot Dashboard", style={"textAlign": "center"}),
        html.Div(
            [
                html.Label("Select Competition"),
                dcc.Dropdown(
                    id="competition-selector",
                    options=[
                        {"label": f"Competition {i}", "value": i} for i in range(1, 11)
                    ],
                    value=default_competition,
                    style={"width": "50%"},
                ),
            ],
            style={"textAlign": "center", "marginBottom": "20px"},
        ),
        html.Div(
            id="file-display", style={"textAlign": "center", "marginBottom": "20px"}
        ),
        dcc.Dropdown(
            id="bot-selector",
            options=create_dropdown_options(player_mapping),
            value=list(player_mapping.keys())[:3],
            multi=True,
            style={"width": "60%", "margin": "auto"},
        ),
        dcc.Graph(id="gold-over-time"),
        dcc.Graph(id="points-over-time"),
        dcc.Graph(id="bids-per-auction"),
        dcc.Graph(id="expected-vs-actual"),
    ]
)

# Callbacks


@app.callback(
    [Output("bot-selector", "options"), Output("file-display", "children")],
    [Input("competition-selector", "value")],
)
def update_dashboard(competition_num):
    global states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used
    states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used = (
        parse_logs(competition_num)
    )
    if states_df is None:
        return [], f"No data available for Competition {competition_num}"

    file_text = html.Div(
        [html.H4(f"Files loaded for Competition {competition_num}:")]
        + [html.P(file) for file in files_used]
    )

    return create_dropdown_options(player_mapping), file_text


@app.callback(Output("gold-over-time", "figure"), [Input("bot-selector", "value")])
def update_gold(selected_bots):
    traces = [
        go.Scatter(
            x=data["round"], y=data["gold"], mode="lines", name=player_mapping[bot_id]
        )
        for bot_id in selected_bots
        for data in [states_df[states_df["bot_id"] == bot_id]]
    ]
    return build_graph("Gold Over Time", "Round", "Gold", traces)


@app.callback(Output("points-over-time", "figure"), [Input("bot-selector", "value")])
def update_points(selected_bots):
    traces = [
        go.Scatter(
            x=data["round"], y=data["points"], mode="lines", name=player_mapping[bot_id]
        )
        for bot_id in selected_bots
        for data in [states_df[states_df["bot_id"] == bot_id]]
    ]
    return build_graph("Points Over Time", "Round", "Points", traces)


@app.callback(Output("bids-per-auction", "figure"), [Input("bot-selector", "value")])
def update_bids(selected_bots):
    traces = [
        go.Bar(x=data["auction_id"], y=data["gold_bid"], name=player_mapping[bot_id])
        for bot_id in selected_bots
        for data in [bids_df[bids_df["bot_id"] == bot_id]]
    ]
    return build_graph("Bids Per Auction", "Auction ID", "Gold Bid", traces)


@app.callback(Output("expected-vs-actual", "figure"), [Input("bot-selector", "value")])
def update_expected_vs_actual(selected_bots):
    traces = [
        go.Scatter(
            x=data["auction_id"],
            y=data["reward"],
            mode="markers",
            name=f"{player_mapping[bot_id]} Reward",
        )
        for bot_id in selected_bots
        for data in [bids_df[bids_df["bot_id"] == bot_id]]
    ]
    return build_graph("Expected vs Actual Rewards", "Auction ID", "Reward", traces)


if __name__ == "__main__":
    app.run_server(debug=True)
