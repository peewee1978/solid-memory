import math
import numpy as np
from typing import List, Dict

# Helpers to extract players and build features from ESPN event/boxscore JSON.
# The ESPN JSON shapes vary; functions are forgiving and try several fields.

def extract_players_from_event(event_json: Dict) -> List[Dict]:
    """
    Return list of players for an event. Each player dict:
    { player_id, name, team, status, last_game_stats }
    last_game_stats may include pts, reb, ast, min (if available).
    """
    players = []
    try:
        comp = event_json.get("competitions", [{}])[0]
        # Try 'competitors' -> 'players' or 'athletes'
        for team_comp in comp.get("competitors", []):
            team_name = team_comp.get("team", {}).get("displayName") or team_comp.get("team", {}).get("name")
            # Prefer 'players' key (some ESPN payloads)
            roster = team_comp.get("players") or team_comp.get("athletes") or []
            # roster items may be nested differently
            for p in roster:
                # athlete object may be under 'athlete'
                athlete = p.get("athlete") if isinstance(p, dict) and "athlete" in p else p
                pid = athlete.get("id") or athlete.get("athleteId") or athlete.get("personId") or None
                name = athlete.get("displayName") or athlete.get("fullName") or athlete.get("name")
                status = p.get("status") or athlete.get("status") or None

                # Try to find last game stats inside p or athlete
                last_stats = {}
                stats_source = p.get("stats") or athlete.get("stats") or {}
                # look for common stat keys
                last_stats['pts'] = _safe_get_stat(stats_source, ['points', 'pts'])
                last_stats['reb'] = _safe_get_stat(stats_source, ['rebounds', 'reb'])
                last_stats['ast'] = _safe_get_stat(stats_source, ['assists', 'ast'])
                last_stats['min'] = _safe_get_stat(stats_source, ['minutes', 'min'])

                players.append({
                    "player_id": str(pid) if pid is not None else None,
                    "name": name,
                    "team": team_name,
                    "status": status,
                    "last_game_stats": last_stats
                })
    except Exception:
        # If structure unexpected, return empty list
        return players
    return players

def _safe_get_stat(source, keys):
    if not source:
        return None
    for k in keys:
        v = source.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                try:
                    return float(v.get('value')) if isinstance(v, dict) and 'value' in v else None
                except Exception:
                    return None
    return None

def build_player_features_from_history(recent_games: List[Dict], min_games: int = 3) -> Dict:
    """
    Given recent_games (list of dicts with keys 'pts','reb','ast','min'), compute features:
    - avg_pts, std_pts, avg_min, recent_5_avg_pts etc.
    Returns dictionary of numeric features.
    """
    feats = {}
    if not recent_games or len(recent_games) == 0:
        # defaults for players with no history
        feats['avg_pts'] = 5.0
        feats['std_pts'] = 3.0
        feats['avg_min'] = 20.0
        feats['recent_5_avg_pts'] = 5.0
        feats['games_count'] = 0
        return feats

    pts = [float(g.get('pts', 0)) for g in recent_games if g]
    mins = [float(g.get('min', 0)) for g in recent_games if g]
    feats['games_count'] = len(pts)
    feats['avg_pts'] = float(np.mean(pts)) if len(pts) > 0 else 0.0
    feats['std_pts'] = float(max(np.std(pts, ddof=0), 0.01)) if len(pts) > 0 else 0.01
    feats['avg_min'] = float(np.mean(mins)) if len(mins) > 0 else 20.0
    # recent 5 average
    last5 = pts[-5:] if len(pts) >= 1 else pts
    feats['recent_5_avg_pts'] = float(np.mean(last5)) if len(last5) > 0 else feats['avg_pts']
    # a simple minutes-adjusted scoring expectation
    feats['min_adj_pts'] = feats['avg_pts'] * (feats['avg_min'] / 30.0)
    return feats

def suggest_line_from_features(feats: Dict, prop_type: str = 'points') -> float:
    """
    Suggest a market line for a given prop type from features.
    For points: use recent_5_avg_pts rounded to .5 and add small buffer.
    """
    if prop_type == 'points':
        base = feats.get('recent_5_avg_pts', feats.get('avg_pts', 5.0))
        # bias up slightly to create a realistic market line
        line = base + 0.5 * (feats.get('std_pts', 1.0) / max(1.0, math.sqrt(max(1, feats.get('games_count',1)))))
        # round to nearest .5
        return round(line * 2) / 2.0
    # fallback
    return round((feats.get('avg_pts', 5.0)) * 2) / 2.0
