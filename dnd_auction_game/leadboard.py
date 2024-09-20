
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


def generate_leadboard(players, round, is_done):

    template = Template(jjinja_template)
    return template.render(players=players, round=round, is_done=is_done)




def generate_leadboard_old(leadboard, round, is_done):

    do_refresh = """<meta http-equiv="refresh" content="1">"""
    if is_done:
        do_refresh = ""
    html_head = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leadboard - Auction Game</title>
        {}
    </head>
    """.format(do_refresh)

    h = ""
    if is_done:
        h = " - FINISHED GAME"
    else:
        h = "Round: {}".format(round)
        
    html_body_top = """
    <body>
        <h2>Leadboard {}</h2>        
    """.format(h)
    
    html_body_bottom = """                
    </body>    
    </html>
    """
    board = []
    for rank, (a_name, points, gold, grade) in enumerate(leadboard):
        safe_name = html.escape(a_name)
        if rank == 0:
            board.append("<p>{}<b>#{} - {} : gold {} : points {}</b></p>".format(grade, rank+1, safe_name, gold, points))
        else:
            board.append("<p>{}#{} - {} : gold {} : <b>points {}</b></p>".format(grade, rank+1, safe_name, gold, points))
        
    return html_head + html_body_top + "\n".join(board) + html_body_bottom


