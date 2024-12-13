import dash
from dash import dcc, html, Input, Output, State, dash_table
import plotly.express as px
import pandas as pd
import json
import os


def load_agent_logs(agent_ids, multiplier):
    """Load agent log files based on competition."""
    files = []
    data = []
    for agent_id in agent_ids:
        # Correct mapping: multiplier = 21 * (competition_num - 1)
        log_file = f"logs/agent_local_rand_id_{agent_id}_n{multiplier}.jsonl"
        files.append(log_file)
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                for line in f:
                    data.append(json.loads(line))
    return pd.DataFrame(data), files


def parse_logs(competition_num):
    """Parse logs for a specific competition."""
    # File names
    player_file = f"auction_house_log_player_id_{competition_num}.jsonln"
    auction_file = f"auction_house_log_{competition_num}.jsonln"

    # Verify file existence
    files_used = [player_file, auction_file]
    if not os.path.exists(player_file) or not os.path.exists(auction_file):
        return None, None, None, None, {}, files_used

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

    # Correct multiplier: 21 * (competition_num - 1)
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


# Default competition
default_competition = 1
states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used = parse_logs(
    default_competition
)


app = dash.Dash(__name__)

# Global variables
states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used = (
    None,
    None,
    None,
    None,
    {},
    [],
)

app.layout = html.Div(
    [
        html.H1("Auction Competition Dashboard"),
        dcc.Dropdown(
            id="competition-selector",
            options=[{"label": f"Competition {i}", "value": i} for i in range(1, 6)],
            placeholder="Select a competition",
        ),
        html.Div(id="file-display"),
        dcc.Dropdown(
            id="bot-selector", multi=True, placeholder="Select bots to analyze"
        ),
        dcc.Tabs(
            [
                dcc.Tab(
                    label="Player Statistics", children=[html.Div(id="player-stats")]
                ),
                dcc.Tab(
                    label="Performance Insights",
                    children=[
                        dcc.Graph(id="gold-plot"),
                        dcc.Graph(id="points-plot"),
                        dcc.Graph(id="bid-success-plot"),
                        dcc.Graph(id="auction-rewards-heatmap"),
                    ],
                ),
                dcc.Tab(
                    label="Textual Insights",
                    children=[
                        html.Div(
                            id="textual-insights",
                            style={"padding": "10px", "border": "1px solid #ccc"},
                        )
                    ],
                ),
            ]
        ),
    ]
)

# Helper Functions


def calculate_statistics():
    """Calculate statistics for each bot."""
    stats = (
        states_df.groupby("bot_id")
        .agg(
            total_gold=pd.NamedAgg(column="gold", aggfunc="sum"),
            total_points=pd.NamedAgg(column="points", aggfunc="sum"),
            avg_gold=pd.NamedAgg(column="gold", aggfunc="mean"),
            avg_points=pd.NamedAgg(column="points", aggfunc="mean"),
        )
        .reset_index()
    )

    # Merge player names
    stats["name"] = stats["bot_id"].map(player_mapping)
    return stats


def calculate_bid_success():
    """Calculate bid success rates."""
    success_rates = bids_df.groupby("bot_id").agg(
        total_bids=pd.NamedAgg(column="gold_bid", aggfunc="count"),
        successful_bids=pd.NamedAgg(column="reward", aggfunc=lambda x: (x > 0).sum()),
    )
    success_rates["success_rate"] = (
        success_rates["successful_bids"] / success_rates["total_bids"]
    ) * 100
    return success_rates.reset_index()


@app.callback(
    [
        Output("bot-selector", "options"),
        Output("file-display", "children"),
        Output("player-stats", "children"),
        Output("gold-plot", "figure"),
        Output("points-plot", "figure"),
        Output("bid-success-plot", "figure"),
        Output("auction-rewards-heatmap", "figure"),
        Output("textual-insights", "children"),
    ],
    Input("competition-selector", "value"),
)
def update_dashboard(competition_num):
    global states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used
    states_df, auctions_df, bids_df, agent_logs_df, player_mapping, files_used = (
        parse_logs(competition_num)
    )
    if states_df is None:
        return (
            [],
            f"No data available for Competition {competition_num}",
            "No data to display",
            {},
            {},
            {},
            {},
            "No insights available",
        )

    bot_options = [
        {"label": name, "value": bot_id} for bot_id, name in player_mapping.items()
    ]

    # Player stats
    stats_df = calculate_statistics()
    success_df = calculate_bid_success()
    stats_merged = pd.merge(stats_df, success_df, on="bot_id", how="left").fillna(0)
    stats_table = dash_table.DataTable(
        data=stats_merged.to_dict("records"),
        columns=[{"name": col, "id": col} for col in stats_merged.columns],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"},
    )

    # Gold vs. Time
    gold_fig = px.line(
        states_df,
        x="round",
        y="gold",
        color="bot_id",
        title="Gold Over Time",
        markers=True,
    )

    # Points vs. Time
    points_fig = px.line(
        states_df,
        x="round",
        y="points",
        color="bot_id",
        title="Points Over Time",
        markers=True,
    )

    # Bid Success Rates
    bid_success_fig = px.bar(
        success_df,
        x="bot_id",
        y="success_rate",
        color="bot_id",
        title="Bid Success Rates",
    )

    # Auction Rewards Heatmap
    heatmap_fig = px.density_heatmap(
        bids_df,
        x="auction_id",
        y="bot_id",
        z="reward",
        histfunc="avg",
        title="Auction Rewards Heatmap",
    )

    # Textual Insights
    top_bot = stats_df.sort_values(by="total_points", ascending=False).iloc[0]
    insights = f"""
    The top-performing bot was {top_bot['name']} with {top_bot['total_points']} total points.
    Their average gold was {top_bot['avg_gold']:.2f}, and they secured a success rate of {success_df.set_index('bot_id').loc[top_bot['bot_id'], 'success_rate']:.2f}%.
    """

    return (
        bot_options,
        f"Files loaded for Competition {competition_num}:<br>"
        + "<br>".join(files_used),
        stats_table,
        gold_fig,
        points_fig,
        bid_success_fig,
        heatmap_fig,
        insights,
    )


# Start server
if __name__ == "__main__":
    app.run_server(debug=True)
