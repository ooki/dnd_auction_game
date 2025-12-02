import html
from jinja2 import Template



jjinja_template = """
{% if is_done is false %}
<meta http-equiv="refresh" content="1">
{% endif %}

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    {% if is_done is true%}
    <title>Scoreboard - Auction Game : Round {{ round }}</title>
    {% else %}
    <title>Scoreboard - Auction Game : Finished</title>
    {% endif %}
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
            border-top: 2px solid #ddd;
        }
        tr:last-child td {
            border-bottom: none;
        }
        .grade-A { background-color: #a0c15a; }
        .grade-B { background-color: #add633; }
        .grade-C { background-color: #ffd934; }
        .grade-D { background-color: #ffb234; }
        .grade-E { background-color: #ff8c5a; }
        .grade-F { background-color: #94161a; }
    </style>
</head>
<body>
    {% if is_done is true%}
    <h1>Scoreboard - Finished</h1>
    {% else %}
    <h1>Scoreboard - Round {{ round }}</h1>
    {% endif %}
    <b>Gold Income: {{ gold_income }} | Interest Rate: {{ "%.2f"|format(interest_rate) }} | Limit: {{gold_limit}} | Gold in Pool: {{gold_in_pool}}</b>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Name</th>
                <th>Grade</th>
                <th>Gold</th>
                <th>Points</th>
            </tr>
        </thead>
        <tbody>
        {% for player in players|sort(attribute='points', reverse=True) %}
            <tr class="grade-{{ player.grade|e }}">
                <td>{{ loop.index }}</td>
                <td>{{ player.name|e }}</td>
                <td>{{ player.grade|e }}</td>
                <td>{{ player.gold|e }}</td>
                <td><b>{{ player.points|e }}</b></td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>

"""


def generate_leadboard(players, round, is_done, bank_state, gold_in_pool):

    template = Template(jjinja_template)
    return template.render(players=players,
                            round=round,
        is_done=is_done,
        gold_income=bank_state["gold_income_per_round"],
        interest_rate=bank_state["bank_interest_per_round"],
        gold_limit=bank_state["bank_limit_per_round"],
        gold_in_pool=gold_in_pool)




