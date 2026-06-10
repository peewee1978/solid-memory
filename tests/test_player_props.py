from src.player_utils import build_player_features_from_history, suggest_line_from_features

def test_build_features_empty():
    feats = build_player_features_from_history([])
    assert 'avg_pts' in feats
    assert feats['games_count'] == 0

def test_build_features_sample():
    recent = [{'pts': 24, 'min': 35}, {'pts': 18, 'min': 30}, {'pts': 20, 'min': 32}]
    feats = build_player_features_from_history(recent)
    assert feats['games_count'] == 3
    assert feats['avg_pts'] == (24+18+20)/3

def test_suggest_line():
    recent = [{'pts': 10}, {'pts': 12}, {'pts': 8}, {'pts': 11}, {'pts': 9}]
    feats = build_player_features_from_history(recent)
    line = suggest_line_from_features(feats, 'points')
    assert isinstance(line, float)
