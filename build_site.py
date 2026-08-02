#!/usr/bin/env python3
"""
Gera, todos os dias, um site estatico com um "stat battle" para cada jogo
ATP/WTA do dia, usando a API Tennis (https://api-tennis.com).

Corre localmente com:
    APIKEY=xxxx python scripts/build_site.py

No GitHub Actions, a chave vem do secret API_TENNIS_KEY (ver workflow).
"""

import os
import sys
import json
import datetime
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode

API_BASE = "https://api.api-tennis.com/tennis/"
API_KEY = os.environ.get("APIKEY") or os.environ.get("API_TENNIS_KEY")

# Tipos de evento que nos interessam (singulares ATP e WTA).
# Confirma estes valores com o endpoint get_events caso a API os altere.
EVENT_TYPES = {
    "265": "ATP",
    "266": "WTA",
}

OUT_DIR = Path(__file__).resolve().parent.parent / "docs"
LAST_N = 10  # "ultimos 10 jogos"


def api_call(method: str, **params) -> dict:
    if not API_KEY:
        sys.exit("Falta a variavel de ambiente APIKEY / API_TENNIS_KEY.")
    qs = {"method": method, "APIkey": API_KEY, **params}
    url = API_BASE + "?" + urlencode(qs)
    with urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("success") != 1:
        print(f"Aviso: chamada {method} falhou: {data}", file=sys.stderr)
        return {}
    return data.get("result", {})


def get_today_fixtures(date_str: str) -> list:
    fixtures = api_call("get_fixtures", date_start=date_str, date_stop=date_str)
    if isinstance(fixtures, dict):
        fixtures = list(fixtures.values())
    return [
        f for f in fixtures
        if f.get("event_type_type") in ("Atp Singles", "Wta Singles")
    ]


def get_h2h(p1: str, p2: str) -> dict:
    return api_call("get_H2H", first_player_key=p1, second_player_key=p2)


def get_player(player_key: str) -> dict:
    res = api_call("get_players", player_key=player_key)
    if isinstance(res, list) and res:
        return res[0]
    return {}


def player_win_loss(results: list, player_name: str, n: int = LAST_N) -> dict:
    """A partir da lista de jogos passados de um jogador (get_H2H), calcula
    vitorias/derrotas nos ultimos n jogos terminados (mais recente primeiro)."""
    finished = [r for r in results if r.get("event_status") == "Finished"]
    finished.sort(key=lambda r: (r.get("event_date", ""), r.get("event_time", "")), reverse=True)
    last = finished[:n]
    wins = 0
    for r in last:
        is_first = r.get("event_first_player") == player_name
        won_first = r.get("event_winner") == "First Player"
        if (is_first and won_first) or (not is_first and not won_first):
            wins += 1
    return {"wins": wins, "played": len(last), "matches": last}


def surface_stats(player: dict, season: str) -> dict:
    """Extrai Vitorias-Derrotas por piso na epoca atual a partir de get_players."""
    out = {"hard": (0, 0), "clay": (0, 0), "grass": (0, 0)}
    for s in player.get("stats", []):
        if s.get("season") == season and s.get("type") == "singles":
            for surface in ("hard", "clay", "grass"):
                w = s.get(f"{surface}_won") or 0
                l = s.get(f"{surface}_lost") or 0
                try:
                    out[surface] = (int(w), int(l))
                except (TypeError, ValueError):
                    pass
    return out


CARD_TEMPLATE = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{p1} vs {p2} - {tournament}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<a class="back" href="../index.html">&larr; Jogos de hoje</a>
<div class="card">
  <div class="head">
    <div class="tour">{tournament} &middot; {round_name} &middot; {event_type}</div>
    <div class="matchup">
      <span class="player">{p1}</span>
      <span class="vs">vs</span>
      <span class="player">{p2}</span>
    </div>
    <div class="h2h">Confrontos diretos: {h2h_summary}</div>
  </div>

  <h3>Ultimos {n} jogos (forma recente)</h3>
  <div class="row">
    <div class="stat {p1_form_hi}">{p1_form}</div>
    <div class="label">Vitorias / derrotas</div>
    <div class="stat {p2_form_hi}">{p2_form}</div>
  </div>

  <h3>Registo por piso (epoca {season})</h3>
  <div class="row"><div class="stat">{p1_hard}</div><div class="label">Piso duro</div><div class="stat">{p2_hard}</div></div>
  <div class="row"><div class="stat">{p1_clay}</div><div class="label">Terra batida</div><div class="stat">{p2_clay}</div></div>
  <div class="row"><div class="stat">{p1_grass}</div><div class="label">Relva</div><div class="stat">{p2_grass}</div></div>

  <h3>Ultimos resultados - {p1}</h3>
  <ul class="results">{p1_results_html}</ul>

  <h3>Ultimos resultados - {p2}</h3>
  <ul class="results">{p2_results_html}</ul>

  <p class="src">Dados: API Tennis. Gerado em {generated_at} (UTC).</p>
</div>
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jogos de hoje - {date}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<h1>Jogos ATP / WTA - {date}</h1>
<p class="src">Atualizado automaticamente todos os dias. {count} jogos encontrados.</p>
<div class="list">
{items}
</div>
</body>
</html>
"""

STYLE_CSS = """
:root { color-scheme: dark; }
body { background:#0b0e12; color:#e7e9ec; font-family: system-ui, sans-serif; max-width:720px; margin:0 auto; padding:24px 16px 60px; }
h1 { font-size:22px; font-weight:600; }
h3 { font-size:14px; color:#9aa3ad; margin:22px 0 8px; font-weight:600; text-transform:uppercase; letter-spacing:.03em;}
.back { color:#7fb0ff; text-decoration:none; font-size:14px; }
.card { background:#131820; border:1px solid #232a35; border-radius:14px; padding:20px; margin-top:16px; }
.tour { font-size:12px; color:#9aa3ad; margin-bottom:6px; }
.matchup { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.player { font-size:17px; font-weight:600; flex:1; }
.vs { color:#5f6773; font-size:12px; }
.h2h { font-size:12px; color:#9aa3ad; margin-top:6px; }
.row { display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid #1c2230; }
.row .stat { flex:1; text-align:center; font-size:15px; font-weight:600; padding:4px 10px; border-radius:8px; background:#1a212c; }
.row .stat.hi { background:#16321f; color:#5fd987; }
.row .label { flex:1.3; text-align:center; font-size:12px; color:#9aa3ad; }
.results { list-style:none; padding:0; margin:0; font-size:13px; }
.results li { padding:6px 0; border-bottom:1px solid #1c2230; display:flex; justify-content:space-between; gap:8px; }
.results li span.res { font-weight:600; }
.results li span.res.w { color:#5fd987; }
.results li span.res.l { color:#f08787; }
.src { font-size:11px; color:#5f6773; margin-top:24px; }
.list { display:flex; flex-direction:column; gap:10px; }
.list a { display:block; background:#131820; border:1px solid #232a35; border-radius:12px; padding:14px 16px; color:#e7e9ec; text-decoration:none; }
.list a:hover { border-color:#3a4356; }
.list .t { font-size:12px; color:#9aa3ad; }
.list .m { font-size:15px; font-weight:600; margin-top:2px; }
"""


def results_to_html(results: list, player_name: str) -> str:
    items = []
    for r in results:
        is_first = r.get("event_first_player") == player_name
        opponent = r.get("event_second_player") if is_first else r.get("event_first_player")
        won_first = r.get("event_winner") == "First Player"
        won = won_first if is_first else not won_first
        res_class = "w" if won else "l"
        res_label = "V" if won else "D"
        items.append(
            f'<li><span>{r.get("event_date","")} vs {opponent} '
            f'({r.get("tournament_name","")})</span>'
            f'<span class="res {res_class}">{res_label} {r.get("event_final_result","")}</span></li>'
        )
    return "\n".join(items) if items else "<li>Sem dados suficientes.</li>"


def fmt_wl(w: int, l: int) -> str:
    return f"{w}-{l}"


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "matches").mkdir(exist_ok=True)
    (OUT_DIR / "style.css").write_text(STYLE_CSS, encoding="utf-8")

    today = datetime.date.today().isoformat()
    season = str(datetime.date.today().year)
    fixtures = get_today_fixtures(today)

    index_items = []
    generated_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    for fx in fixtures:
        p1_name = fx.get("event_first_player", "")
        p2_name = fx.get("event_second_player", "")
        p1_key = fx.get("first_player_key")
        p2_key = fx.get("second_player_key")
        tournament = fx.get("tournament_name", "")
        round_name = fx.get("tournament_round", "")
        event_type = fx.get("event_type_type", "")
        event_key = fx.get("event_key")

        h2h = get_h2h(p1_key, p2_key) if p1_key and p2_key else {}
        h2h_list = h2h.get("H2H", []) if isinstance(h2h, dict) else []
        p1_results = h2h.get("firstPlayerResults", []) if isinstance(h2h, dict) else []
        p2_results = h2h.get("secondPlayerResults", []) if isinstance(h2h, dict) else []

        p1_form = player_win_loss(p1_results, p1_name)
        p2_form = player_win_loss(p2_results, p2_name)

        p1_player = get_player(p1_key) if p1_key else {}
        p2_player = get_player(p2_key) if p2_key else {}
        p1_surf = surface_stats(p1_player, season)
        p2_surf = surface_stats(p2_player, season)

        h2h_wins_p1 = sum(1 for m in h2h_list if m.get("event_winner") == "First Player")
        h2h_wins_p2 = sum(1 for m in h2h_list if m.get("event_winner") == "Second Player")
        h2h_summary = f"{p1_name} {h2h_wins_p1}-{h2h_wins_p2} {p2_name}" if h2h_list else "primeiro confronto"

        html = CARD_TEMPLATE.format(
            p1=p1_name, p2=p2_name, tournament=tournament, round_name=round_name,
            event_type=event_type, h2h_summary=h2h_summary, n=LAST_N, season=season,
            p1_form=fmt_wl(p1_form["wins"], p1_form["played"] - p1_form["wins"]),
            p2_form=fmt_wl(p2_form["wins"], p2_form["played"] - p2_form["wins"]),
            p1_form_hi="hi" if p1_form["wins"] >= p2_form["wins"] else "",
            p2_form_hi="hi" if p2_form["wins"] >= p1_form["wins"] else "",
            p1_hard=fmt_wl(*p1_surf["hard"]), p2_hard=fmt_wl(*p2_surf["hard"]),
            p1_clay=fmt_wl(*p1_surf["clay"]), p2_clay=fmt_wl(*p2_surf["clay"]),
            p1_grass=fmt_wl(*p1_surf["grass"]), p2_grass=fmt_wl(*p2_surf["grass"]),
            p1_results_html=results_to_html(p1_form["matches"], p1_name),
            p2_results_html=results_to_html(p2_form["matches"], p2_name),
            generated_at=generated_at,
        )

        fname = f"{event_key}.html"
        (OUT_DIR / "matches" / fname).write_text(html, encoding="utf-8")
        index_items.append(
            f'<a href="matches/{fname}"><div class="t">{tournament} &middot; {event_type}</div>'
            f'<div class="m">{p1_name} vs {p2_name}</div></a>'
        )

    index_html = INDEX_TEMPLATE.format(
        date=today, count=len(fixtures), items="\n".join(index_items) or "<p>Sem jogos encontrados hoje.</p>"
    )
    (OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"Gerados {len(fixtures)} jogos para {today}.")


if __name__ == "__main__":
    build()
