import math
import random
import pytest
import game
import engine
from possession import PossessionEngine
from grid import PitchGrid
from gamestate import GameStateManager
from predictor import evaluate_rps, evaluate_brier, run_monte_carlo

def test_dynamic_stoppage_time():
	random.seed(789)
	fix = game.setup('Arsenal', 'Chelsea', savecard=False)
	fix.savecard = False
	p1 = engine.period(fix, 1)
	stoppage_h1 = p1.calculate_dynamic_stoppage()
	assert 1 <= stoppage_h1 <= 4

	p2 = engine.period(fix, 2)
	fix.home_score = 2
	fix.away_score = 1
	fix.home_yellows = 2
	fix.away_yellows = 2
	fix.home_subs_made = 3
	fix.away_subs_made = 3
	stoppage_h2 = p2.calculate_dynamic_stoppage()
	assert 3 <= stoppage_h2 <= 8

def test_stamina_tactical_and_positional_decay():
	random.seed(999)
	fix = game.setup('Liverpool', 'Everton', savecard=False)
	fix.savecard = False
	fix.home.xi = game.firstxi(fix.home, fix.home.formation)
	fix.away.xi = game.firstxi(fix.away, fix.away.formation)
	for p in fix.home.xi + fix.away.xi:
		engine.MatchPerformance(p, fix)
	grid = PitchGrid()
	h_mgr = GameStateManager(fix.home, fix)
	a_mgr = GameStateManager(fix.away, fix)
	poss = PossessionEngine(fix, grid, h_mgr, a_mgr)

	gk = next(p for p in fix.home.xi if p.position == 'GK')
	mid = next(p for p in fix.home.xi if p.position in ['MID', 'CM', 'DMF'])
	cb = next(p for p in fix.home.xi if p.position in ['CB', 'DEF'])

	gk.fitness = 1.0
	mid.fitness = 1.0
	cb.fitness = 1.0

	poss._decay_fitness(60)

	assert gk.fitness > mid.fitness
	assert cb.fitness > mid.fitness
	assert mid.fitness < 1.0

def test_coach_ai_max_subs_and_fortress():
	random.seed(111)
	fix = game.setup('Manchester City', 'Tottenham', savecard=False)
	fix.savecard = False
	fix.home.xi = game.firstxi(fix.home, fix.home.formation)
	fix.home.bench = game.pick_bench(fix.home, fix.home.xi)
	for p in fix.home.xi + fix.home.bench:
		engine.MatchPerformance(p, fix)
	coach = engine.CoachAI(fix.home, fix)
	assert coach.max_subs == 5
	assert coach.subs_made == 0

	coach.make_tactical_substitution(75, 1)
	assert coach.subs_made == 1
	assert len(fix.home.subs_used) == 1
	sub_in = fix.home.subs_used[0][0]
	assert sub_in.fitness == 1.0

def test_super_sub_flagging():
	random.seed(222)
	fix = game.setup('Real Madrid', 'FC Barcelona', savecard=False)
	fix.savecard = False
	fix.home.xi = game.firstxi(fix.home, fix.home.formation)
	fix.home.bench = game.pick_bench(fix.home, fix.home.xi)
	for p in fix.home.xi + fix.home.bench:
		engine.MatchPerformance(p, fix)
	coach = engine.CoachAI(fix.home, fix)
	coach.make_tactical_substitution(70, -1)
	sub_in = fix.home.subs_used[0][0]
	assert getattr(sub_in, 'is_super_sub', False) is True

def test_prediction_derivatives_and_handicaps():
	random.seed(456)
	res = run_monte_carlo('Arsenal', 'Chelsea', runs=100)
	assert 'asian_handicap' in res
	assert 'derivatives' in res
	d = res['derivatives']
	assert 'dnb_home' in d
	assert 'dnb_away' in d
	assert 'expected_points_home' in d
	assert 'expected_points_away' in d
	assert 0.0 <= d['expected_points_home'] <= 3.0
	assert 0.0 <= d['expected_points_away'] <= 3.0

def test_rps_calculation():
	assert evaluate_rps([1.0, 0.0, 0.0], 'home') == pytest.approx(0.0)
	assert evaluate_rps([0.0, 1.0, 0.0], 'draw') == pytest.approx(0.0)
	assert evaluate_rps([0.0, 0.0, 1.0], 'away') == pytest.approx(0.0)
	assert evaluate_rps([0.0, 0.0, 1.0], 'home') == pytest.approx(1.0)
	score_mixed = evaluate_rps([0.6, 0.2, 0.2], 'home')
	assert 0.0 < score_mixed < 0.5
