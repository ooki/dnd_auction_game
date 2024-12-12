import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
from collections import defaultdict
import threading
import time

class BotMonitor:
    def __init__(self):
        self.data = defaultdict(list)
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()

    def setup_layout(self):
        self.app.layout = html.Div([
            html.H1("Auction Bot Performance Monitor"),
            dcc.Graph(id='gold-over-time'),
            dcc.Graph(id='points-over-time'),
            dcc.Graph(id='gold-bid-vs-expected-value'),
            dcc.Graph(id='bids-vs-returns'),
            dcc.Graph(id='bids-over-time'),
            dcc.Graph(id='successful-vs-unsuccessful-bids'),
            dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
        ])

    def setup_callbacks(self):
        @self.app.callback(
            [Output('gold-over-time', 'figure'),
             Output('points-over-time', 'figure'),
             Output('gold-bid-vs-expected-value', 'figure'),
             Output('bids-vs-returns', 'figure'),
             Output('bids-over-time', 'figure'),
             Output('successful-vs-unsuccessful-bids', 'figure')],
            Input('interval-component', 'n_intervals')
        )
        def update_graphs(n):
            return self.create_figures()

    def create_figures(self):
        df = pd.DataFrame(self.data)
        figures = []

        # Gold Over Time
        figures.append(go.Figure(data=[go.Scatter(x=df['rounds'], y=df['gold'], mode='lines+markers', name='Gold Over Time')])
                         .update_layout(title='Gold Over Time', xaxis_title='Rounds', yaxis_title='Gold'))

        # Points Over Time
        figures.append(go.Figure(data=[go.Scatter(x=df['rounds'], y=df['points'], mode='lines+markers', name='Points Over Time')])
                         .update_layout(title='Points Over Time', xaxis_title='Rounds', yaxis_title='Points'))

        # Gold Bid vs Expected Value
        figures.append(go.Figure(data=[go.Scatter(x=df['expected_values'], y=df['gold_bid'], mode='markers', name='Gold Bid vs Expected Value')])
                         .update_layout(title='Gold Bid vs Expected Value', xaxis_title='Expected Value', yaxis_title='Gold Bid'))

        # Bids vs Returns
        figures.append(go.Figure(data=[go.Scatter(x=df['expected_values'], y=df['gold_bid'], mode='markers', name='Bids vs Returns')])
                         .update_layout(title='Bids vs Returns', xaxis_title='Expected Value', yaxis_title='Bid Amount'))

        # Bids Over Time
        figures.append(go.Figure(data=[go.Bar(x=df['rounds'], y=df['bids_count'], name='Bids Per Round')])
                         .update_layout(title='Number of Bids Over Time', xaxis_title='Rounds', yaxis_title='Number of Bids'))

        # Successful vs Unsuccessful Bids
        figures.append(go.Figure(data=[
            go.Bar(x=df['rounds'], y=df['successful_bids'], name='Successful Bids', marker_color='green'),
            go.Bar(x=df['rounds'], y=df['unsuccessful_bids'], name='Unsuccessful Bids', marker_color='red')
        ]).update_layout(title='Successful vs Unsuccessful Bids', barmode='group', xaxis_title='Rounds', yaxis_title='Number of Bids'))

        return figures

    def update_data(self, round_num, gold, points, gold_bid, expected_value, bids_count, successful_bids, unsuccessful_bids):
        self.data['rounds'].append(round_num)
        self.data['gold'].append(gold)
        self.data['points'].append(points)
        self.data['gold_bid'].append(gold_bid)
        self.data['expected_values'].append(expected_value)
        self.data['bids_count'].append(bids_count)
        self.data['successful_bids'].append(successful_bids)
        self.data['unsuccessful_bids'].append(unsuccessful_bids)

    def run(self):
        self.app.run_server(debug=True, use_reloader=False)

# Example usage
monitor = BotMonitor()

# Start the Dash app in a separate thread
threading.Thread(target=monitor.run, daemon=True).start()

# Simulating bot data updates
for i in range(100):
    monitor.update_data(
        round_num=i,
        gold=1000 + i * 10,
        points=i * 5,
        gold_bid=50 + i,
        expected_value=60 + i,
        bids_count=3,
        successful_bids=2,
        unsuccessful_bids=1
    )
    time.sleep(1)  # Simulate delay between rounds

# Keep the main thread running
while True:
    time.sleep(1)