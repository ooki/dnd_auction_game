import html
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


TEMPLATES_DIR = Path(__file__).parent / "templates"
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def generate_leadboard(players, round, is_done, bank_state, gold_in_pool):

    template = env.get_template("leadboard.html")
    return template.render(
        players=players,
        round=round,
        is_done=is_done,
        gold_income=bank_state["gold_income_per_round"],
        interest_rate=bank_state["bank_interest_per_round"],
        gold_limit=bank_state["bank_limit_per_round"],
        gold_in_pool=gold_in_pool,
    )




