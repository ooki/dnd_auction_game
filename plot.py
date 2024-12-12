import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import json

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Auction Bot Analysis"

# Mapping of bot IDs to names
bot_name_mapping = {
    "d1c9fefb92d018c2b06b789799404f746f98ead8c6cf3ff1ba7d54a646efedc2": "Jordan_Belfort",
    "ea0bc833411b1d18308864a0cff138742bd6d443989c856b3e9a76dfd98da06e": "agent_LanaDelReyEnjoyer.py_546",
    "3f7c9b3c03a853c1e273e127974e5152df9611e710c8482baa94d448b764122c": "PiLE of FiSH",
    "026c35f4233972f67c366ec0870759d5e9ce30ebe495fce464d6c5b201c5e645": "Jenter med angst er fangst",
    "9db1ae8094acd24f43bb9047718cf932f32c683bd68a7bdbd1f8681750d41ddb": "Drammen",
    "d2e99e63c4c562a05b9ec909af5e048362d6f4858e909f1e1fa94985cd2ea5df": "Shadow Wizard Money Gang CEO_350",
    "f9f1387154999dfed03e7d14309e004676bc5aca0acc71832da92d4152f39ac8": "twelve",
    "8210b7a93a6b4fd721f6efdf16fbd572b9efa6b4404afa0f08d6ef3df2e695ad": "PST",
    "a37a628310b1c08a9a4278de49d960a8233e73bb8c67853dbd2238a81b712c6b": "Introvert sigma",
    "5f9c825bc42e5dea35d6603b5030cd7847fc3b7b1e90d2732d9632af7a1ac8de": "CautiousCapitalist",
    "917df59b5d20c51dc4a324fbd2a4236e6a4db21a125cd4ab7f996c958ea949db": "World, Hello",
    "4863fd78d27d1ea09655541e1b114e672d288ecb334bfefe7dda8b364b1ec6ed": "agent_006",
    "e50c0bf8df83667e9381ff7f3c12e32ead28a2b040908f1eadc27d257d20343e": "thunesiia",
    "ad9221974093fad4185f6e5da5c325ff739189a62bdc8a3a9a122dd7b362d3b4": "KLEE2.0",
    "e75c71f00ef0171b1c1f773b10f411a6ecd682c7aa356a6338e192809be33323": "Joy Boy",
    "b3cc963e31a232f82b3e0d7c0ec962e8ea90aa8c7725140ae75abe3638be2d6b": "CautiousCapitalist",
    "e302b33b9d7a134e980b854068970d59059397dde8fcbde722bdc1921adaca16": "Stonks_3000",
    "b7f44ef0f96259fea625bae7303d96326eca399b247ba457a1b2ba6c3ddb3bbf": "Snoopy_226651_final_123",
    "c466f45133b98760a04c250a3bd568e88496ef32bbb4fe473ef943280e97ddf9": "You Snooze You Lose",
    "f670a028fe231a4c4914d5920ddb901699617f54e8f129041880f9892d559991": "Ibbi.py_210",
    "c2678ce9be578c20f817ecd16107a5c6ce85d420fb585ee7fd74599e598deb6c": "agent_tiny_bid.py_69",
}

# Function to parse the JSONL logs into a DataFrame


def parse_logs(file_path):
    rounds = []
    states = []
    auctions = []
    bids = []

    # Reading the JSONL log file
    with open(file_path, "r") as file:
        for line in file:
            data = json.loads(line)
            round_num = data["round"]

            # Parse states for each bot
            for bot_id, state in data["states"].items():
                states.append(
                    {
                        "round": round_num,
                        "bot_id": bot_id,
                        "gold": state["gold"],
                        "points": state["points"],
                    }
                )
            # Parse current auctions
            for auction_id, auction in data["auctions"].items():
                auctions.append(
                    {
                        "round": round_num,
                        "auction_id": auction_id,
                        "die": auction["die"],
                        "num": auction["num"],
                        "bonus": auction["bonus"],
                    }
                )

            # Parse previous auctions with bids
            for auction_id, auction in data["prev_auctions"].items():
                reward = auction.get("reward", 0)
                for bid in auction.get("bids", []):
                    bids.append(
                        {
                            "round": round_num
                            - 1,  # Bids occurred in the previous round
                            "auction_id": auction_id,
                            "bot_id": bid["a_id"],
                            "gold_bid": bid["gold"],
                            "reward": reward,
                            "expected_value": auction["num"] * (auction["die"] + 1) / 2
                            + auction["bonus"],
                        }
                    )

    states_df = pd.DataFrame(states)
    auctions_df = pd.DataFrame(auctions)
    bids_df = pd.DataFrame(bids)

    return states_df, auctions_df, bids_df


# Load the data
states_df, auctions_df, bids_df = parse_logs(
    "logs/agent_local_rand_id_990316_n75.jsonl"
)

# Dash Layout
app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "padding": "20px"},
    children=[
        html.H1(
            "Auction Bot Performance Analysis",
            style={"textAlign": "center", "color": "#4A90E2"},
        ),
        dcc.Dropdown(
            id="bot-selector",
            options=[
                {"label": bot_name_mapping[bot_id], "value": bot_id}
                for bot_id in bot_name_mapping
            ],
            value=["e302b33b9d7a134e980b854068970d59059397dde8fcbde722bdc1921adaca16"],
            multi=True,
            style={"width": "60%", "margin": "auto"},
        ),
        html.Div(
            id="graphs-container",
            style={"display": "flex", "flexDirection": "column", "gap": "20px"},
        ),
        dcc.Graph(id="gold-over-time"),
        dcc.Graph(id="points-over-time"),
        dcc.Graph(id="bids-per-auction"),
        dcc.Graph(id="expected-vs-actual"),
        dcc.Graph(id="bid-success-rate"),
        dcc.Graph(id="total-bids-per-bot"),  # New plot for total bids per bot
    ],
)

# Update plots to use names instead of IDs and allow for bot selection


@app.callback(
    Output("gold-over-time", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_gold_over_time(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        bot_data = states_df[states_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(
                x=bot_data["round"],
                y=bot_data["gold"],
                mode="lines+markers",
                name=bot_name,  # Use bot name here
            )
        )
    fig.update_layout(
        title="Gold Over Time",
        xaxis_title="Round",
        yaxis_title="Gold",
        legend_title="Bots",
    )
    return fig


@app.callback(
    Output("points-over-time", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_points_over_time(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        bot_data = states_df[states_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(
                x=bot_data["round"],
                y=bot_data["points"],
                mode="lines+markers",
                name=bot_name,  # Use bot name here
            )
        )
    fig.update_layout(
        title="Points Over Time",
        xaxis_title="Round",
        yaxis_title="Points",
        legend_title="Bots",
    )
    return fig


@app.callback(
    Output("bids-per-auction", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_bids_per_auction(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        bot_bids = bids_df[bids_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Bar(
                x=bot_bids["auction_id"],
                y=bot_bids["gold_bid"],
                name=bot_name,  # Use bot name here
                text=bot_bids["gold_bid"],
                textposition="auto",
            )
        )
    fig.update_layout(
        title="Bids Per Auction",
        xaxis_title="Auction ID",
        yaxis_title="Gold Bid",
        legend_title="Bots",
    )
    return fig


@app.callback(
    Output("expected-vs-actual", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_expected_vs_actual(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        bot_bids = bids_df[bids_df["bot_id"] == bot_id]
        fig.add_trace(
            go.Scatter(
                x=bot_bids["auction_id"],
                y=bot_bids["expected_value"],
                mode="lines+markers",
                name=f"{bot_name} (Expected Value)",
                line=dict(dash="dash"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=bot_bids["auction_id"],
                y=bot_bids["reward"],
                mode="lines+markers",
                name=f"{bot_name} (Actual Reward)",
                line=dict(dash="solid"),
            )
        )
    fig.update_layout(
        title="Expected vs Actual Rewards",
        xaxis_title="Auction ID",
        yaxis_title="Value",
        legend_title="Bots",
    )
    return fig


@app.callback(
    Output("bid-success-rate", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_bid_success_rate(selected_bots):
    fig = go.Figure()
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        bot_bids = bids_df[bids_df["bot_id"] == bot_id]
        # Calculate success rate
        success_rate = (bot_bids["reward"] > 0).mean()
        fig.add_trace(go.Bar(x=[bot_name], y=[success_rate], name=bot_name))
    fig.update_layout(
        title="Bid Success Rate",
        xaxis_title="Bot",
        yaxis_title="Success Rate",
        legend_title="Bots",
    )
    return fig


@app.callback(
    Output("total-bids-per-bot", "figure"),
    Input("bot-selector", "value"),  # Update to respond to bot selection
)
def update_total_bids_per_bot(selected_bots):
    fig = go.Figure()
    total_bids = bids_df["bot_id"].value_counts().reindex(selected_bots).fillna(0)
    for bot_id in selected_bots:
        bot_name = bot_name_mapping.get(bot_id, bot_id)  # Use name from mapping
        fig.add_trace(go.Bar(x=[bot_name], y=[total_bids[bot_id]], name=bot_name))
    fig.update_layout(
        title="Total Bids Per Bot",
        xaxis_title="Bot",
        yaxis_title="Total Bids",
        legend_title="Bots",
    )
    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
