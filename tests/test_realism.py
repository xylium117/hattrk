import io
import random
from contextlib import redirect_stdout
import pytest
import game

TEST_MATCHUPS = [
    ('Real Madrid', 'FC Barcelona'),
    ('Manchester City', 'Arsenal'),
    ('Inter Milan', 'AC Milan'),
    ('FC Bayern München', 'Borussia Dortmund'),
    ('Liverpool', 'Everton'),
    ('Chelsea', 'Fulham'),
    ('PSG', 'LOSC'),
    ('Atlético de Madrid', 'Getafe CF'),
    ('Manchester City', 'Ipswich'),
    ('Real Madrid', 'CD Leganés'),
    ('Brighton', 'Brentford'),
    ('ACF Fiorentina', 'Torino FC'),
    ('Como 1907', 'Venezia FC'),
    ('Leicester City', 'Wolves'),
    ('SV Werder Bremen', 'FC Augsburg')
]

EXPECTED_RESULTS = {
    'goals': [4, 1, 2, 1, 6, 3, 0, 0, 4, 2, 4, 3, 3, 4, 2],
    'margins': [0, 1, 2, 1, 2, 3, 0, 0, 2, 2, 2, 3, 1, 2, 2],
    'shots': [35, 33, 22, 26, 41, 22, 24, 27, 36, 29, 26, 28, 22, 33, 34],
    'shots_target': [10, 13, 8, 9, 11, 8, 7, 9, 12, 9, 8, 13, 9, 11, 11],
    'xgs': [
        4.102375639372525, 3.766074014514757, 1.8449232788191847, 3.181261862134664,
        5.599901245368254, 1.7739695100468453, 2.3189442403130895, 2.6660468474521477,
        4.495794881306416, 3.402254240241164, 2.5563871421710163, 2.4276247696126605,
        3.1495992746246007, 4.415456673233894, 3.9415258402278037
    ],
    'passes_comp': [929, 966, 993, 945, 914, 881, 895, 967, 893, 940, 1002, 980, 912, 879, 906],
    'passes_att': [1025, 1094, 1130, 1070, 1057, 1037, 1003, 1125, 1065, 1086, 1127, 1118, 1079, 1016, 1031],
    'corners': [19, 16, 9, 12, 14, 10, 13, 12, 14, 11, 14, 13, 12, 15, 19],
    'fouls': [23, 23, 20, 25, 24, 38, 17, 24, 21, 24, 21, 23, 29, 29, 34],
    'yellows': [3, 5, 6, 11, 6, 6, 3, 6, 2, 5, 0, 3, 8, 1, 0],
    'reds': [0, 0, 0, 0, 0, 1, 1, 0, 0, 2, 3, 0, 0, 0, 2],
}

AVG_GOALS = 2.600
AVG_SHOTS = 29.200
SOT_PCT = 33.790
XG_DIVERGENCE = 0.709
AVG_PASSES = 933.467
PASS_ACC = 87.169
AVG_CORNERS = 13.533
AVG_FOULS = 25.000
AVG_YELLOWS = 4.333


def _run_deterministic_sim():
    random.seed(42)
    goals = []
    shots = []
    shots_target = []
    xgs = []
    passes_comp = []
    passes_att = []
    corners = []
    fouls = []
    yellows = []
    reds = []
    margins = []

    for h, a in TEST_MATCHUPS:
        fix = game.setup(h, a, savecard=False)
        with redirect_stdout(io.StringIO()):
            game.game(fix)

        tot_g = fix.home_score + fix.away_score
        goals.append(tot_g)
        margins.append(abs(fix.home_score - fix.away_score))

        shots.append(fix.home_shots + fix.away_shots)
        shots_target.append(fix.home_shots_target + fix.away_shots_target)
        xgs.append(fix.home_xg + fix.away_xg)

        passes_comp.append(fix.home_passes_comp + fix.away_passes_comp)
        passes_att.append(fix.home_passes_att + fix.away_passes_att)

        corners.append(fix.home_corners + fix.away_corners)
        fouls.append(fix.home_fouls + fix.away_fouls)
        yellows.append(fix.home_yellows + fix.away_yellows)
        reds.append(fix.home_reds + fix.away_reds)

    return {
        'count': len(TEST_MATCHUPS),
        'goals': goals,
        'margins': margins,
        'shots': shots,
        'shots_target': shots_target,
        'xgs': xgs,
        'passes_comp': passes_comp,
        'passes_att': passes_att,
        'corners': corners,
        'fouls': fouls,
        'yellows': yellows,
        'reds': reds
    }


def test_deterministic_results():
    random.seed(42)
    results = _run_deterministic_sim()
    for key, expected in EXPECTED_RESULTS.items():
        actual = results[key]
        assert actual == expected, f"Mismatch in {key}: {actual} != {expected}"


def test_goal_realism():
    random.seed(42)
    results = _run_deterministic_sim()
    avg_goals = sum(results['goals']) / float(results['count'])
    assert avg_goals == pytest.approx(AVG_GOALS, abs=0.001)


def test_shot_realism():
    random.seed(42)
    results = _run_deterministic_sim()
    avg_shots = sum(results['shots']) / float(results['count'])
    assert avg_shots == pytest.approx(AVG_SHOTS, abs=0.001)


def test_shots_on_target_accuracy():
    random.seed(42)
    results = _run_deterministic_sim()
    tot_shots = sum(results['shots'])
    tot_sot = sum(results['shots_target'])
    if tot_shots > 0:
        sot_pct = (tot_sot / float(tot_shots)) * 100.0
        assert sot_pct == pytest.approx(SOT_PCT, abs=0.001)


def test_xg_calibration():
    random.seed(42)
    results = _run_deterministic_sim()
    avg_goals = sum(results['goals']) / float(results['count'])
    avg_xg = sum(results['xgs']) / float(results['count'])
    divergence = abs(avg_goals - avg_xg)
    assert divergence == pytest.approx(XG_DIVERGENCE, abs=0.001)


def test_pass_volume_and_accuracy():
    random.seed(42)
    results = _run_deterministic_sim()
    avg_passes = sum(results['passes_comp']) / float(results['count'])
    tot_comp = sum(results['passes_comp'])
    tot_att = sum(results['passes_att'])
    assert avg_passes == pytest.approx(AVG_PASSES, abs=0.001)
    if tot_att > 0:
        acc = (tot_comp / float(tot_att)) * 100.0
        assert acc == pytest.approx(PASS_ACC, abs=0.001)


def test_set_pieces_and_discipline():
    random.seed(42)
    results = _run_deterministic_sim()
    avg_corners = sum(results['corners']) / float(results['count'])
    avg_fouls = sum(results['fouls']) / float(results['count'])
    avg_yellows = sum(results['yellows']) / float(results['count'])
    assert avg_corners == pytest.approx(AVG_CORNERS, abs=0.001)
    assert avg_fouls == pytest.approx(AVG_FOULS, abs=0.001)
    assert avg_yellows == pytest.approx(AVG_YELLOWS, abs=0.001)


def test_anti_blowout_and_demolitions():
    random.seed(42)
    results = _run_deterministic_sim()
    margins = results['margins']
    demolitions = sum(1 for m in margins if m >= 5)
    demolition_rate = demolitions / float(len(margins))
    assert demolition_rate == 0.0