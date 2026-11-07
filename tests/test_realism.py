import io
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

@pytest.fixture(scope='module')
def simulation_results():
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

def test_goal_realism(simulation_results):
	avg_goals = sum(simulation_results['goals']) / float(simulation_results['count'])
	assert 1.8 <= avg_goals <= 3.6

def test_shot_realism(simulation_results):
	avg_shots = sum(simulation_results['shots']) / float(simulation_results['count'])
	assert 18.0 <= avg_shots <= 34.0

def test_shots_on_target_accuracy(simulation_results):
	tot_shots = sum(simulation_results['shots'])
	tot_sot = sum(simulation_results['shots_target'])
	if tot_shots > 0:
		sot_pct = (tot_sot / float(tot_shots)) * 100.0
		assert 26.0 <= sot_pct <= 45.0

def test_xg_calibration(simulation_results):
	avg_goals = sum(simulation_results['goals']) / float(simulation_results['count'])
	avg_xg = sum(simulation_results['xgs']) / float(simulation_results['count'])
	divergence = abs(avg_goals - avg_xg)
	assert divergence <= 0.65

def test_pass_volume_and_accuracy(simulation_results):
	avg_passes = sum(simulation_results['passes_comp']) / float(simulation_results['count'])
	tot_comp = sum(simulation_results['passes_comp'])
	tot_att = sum(simulation_results['passes_att'])
	assert 700 <= avg_passes <= 1050
	if tot_att > 0:
		acc = (tot_comp / float(tot_att)) * 100.0
		assert 80.0 <= acc <= 92.0

def test_set_pieces_and_discipline(simulation_results):
	avg_corners = sum(simulation_results['corners']) / float(simulation_results['count'])
	avg_fouls = sum(simulation_results['fouls']) / float(simulation_results['count'])
	avg_yellows = sum(simulation_results['yellows']) / float(simulation_results['count'])
	assert 6.0 <= avg_corners <= 16.0
	assert 14.0 <= avg_fouls <= 28.0
	assert 2.0 <= avg_yellows <= 5.5

def test_anti_blowout_and_demolitions(simulation_results):
	margins = simulation_results['margins']
	demolitions = sum(1 for m in margins if m >= 5)
	assert (demolitions / float(len(margins))) <= 0.10

