#!/usr/bin/env python3
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from src.data_fetcher import DataAggregator
from src.props_calculator import MoneyLineCalculator, PropsCalculator
from src.player_utils import extract_players_from_event, build_player_features_from_history, suggest_line_from_features

def run_for_date(date_str):
    agg = DataAggregator()
    ml = MoneyLineCalculator()
    pc = PropsCalculator()

    data = agg.get_daily_props_data("nba", date_str)
    games = (data or {}).get("games") or {}
    events = games.get("events") if isinstance(games, dict) else None
    if not events:
        print("No NBA games found for", date_str)
        return

    ml_picks = []
    prop_picks = []

    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            continue

        home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors)>1 else competitors[0])
        home_team = home.get("team",{}).get("displayName") or home.get("team",{}).get("name") or "Home"
        away_team = away.get("team",{}).get("displayName") or away.get("team",{}).get("name") or "Away"

        # placeholder team stats (replace with actual stats pipeline later)
        home_stats = {"name": home_team, "ppg": 110, "def_ppg": 108}
        away_stats = {"name": away_team, "ppg": 105, "def_ppg": 110}

        ml_pred = ml.calculate_moneyline(home_stats, away_stats, sport="nba")
        conf = ml_pred["home_win_probability"] if ml_pred["prediction"] == "HOME" else ml_pred["away_win_probability"]
        ml_picks.append({
            "home": home_team,
            "away": away_team,
            "prediction": ml_pred["prediction"],
            "confidence": round(conf, 3)
        })

        # PLAYER PROPS: extract players from event JSON and compute 1-2 top props
        players = extract_players_from_event(ev)
        for p in players:
            # attempt to build features from last_game_stats (we only have last_game in free scrapers)
            recent_games = []
            last = p.get("last_game_stats") or {}
            # create a minimal recent_games entry if last exists (ESPN free data may only have last game)
            if last and any(v is not None for v in last.values()):
                recent_games = [last]  # best-effort; replace with full history when available

            feats = build_player_features_from_history(recent_games)
            line = suggest_line_from_features(feats, prop_type='points')
            player_stats = {"points": feats.get("avg_pts", 5.0), "points_std": feats.get("std_pts", 3.0)}
            pred = pc.calculate_player_prop('nba', {"points": player_stats["points"], "points_std": player_stats["points_std"]}, 'points', line)
            prop_picks.append({
                "player": p.get("name"),
                "team": p.get("team"),
                "prop": "points",
                "line": line,
                "prediction": pred["prediction"],
                "over_probability": round(pred["over_probability"], 3),
                "confidence": round(pred["confidence"], 3)
            })

    # sort and print
    ml_sorted = sorted(ml_picks, key=lambda x: x["confidence"], reverse=True)
    prop_sorted = sorted(prop_picks, key=lambda x: x["confidence"], reverse=True)

    print(f"NBA moneyline picks for {date_str}:")
    for m in ml_sorted:
        print(f"- {m['home']} vs {m['away']}: {m['prediction']} (conf {m['confidence']:.3f})")

    print("\nTop player points props (high confidence):")
    # show top 15 player props
    for p in prop_sorted[:15]:
        print(f"- {p['player']} ({p['team']}): {p['prop']} {p['line']} -> {p['prediction']} (p_over={p['over_probability']:.3f}, conf={p['confidence']:.3f})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
    else:
        date_arg = datetime.now().strftime("%Y%m%d")
    run_for_date(date_arg)
