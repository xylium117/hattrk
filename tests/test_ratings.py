import pytest
from engine import MatchPerformance
import game

def test_match_rating_baseline():
	fix = game.setup("Arsenal", "Chelsea", savecard=False)
	p = fix.home.active[0]
	perf = MatchPerformance(p, fix)
	rating = perf.calculate_rating(fix)
	assert 5.5 <= rating <= 7.0

def test_match_rating_good_performance():
	fix = game.setup("Arsenal", "Chelsea", savecard=False)
	p = fix.home.active[0]
	perf = MatchPerformance(p, fix)
	perf.goals = 1
	perf.shots_on_target = 2
	perf.passes_completed = 45
	perf.passes_attempted = 50
	perf.key_passes = 2
	rating = perf.calculate_rating(fix)
	assert 7.0 <= rating <= 8.5

def test_match_rating_brace_not_ten():
	fix = game.setup("Arsenal", "Chelsea", savecard=False)
	p = fix.home.active[-1]
	perf = MatchPerformance(p, fix)
	perf.goals = 2
	perf.shots_on_target = 3
	perf.shots = 4
	perf.passes_completed = 25
	perf.passes_attempted = 30
	rating = perf.calculate_rating(fix)
	assert rating < 9.5
	assert rating != 10.0

def test_ten_point_zero_is_historic():
	fix = game.setup("Arsenal", "Chelsea", savecard=False)
	p = fix.home.active[-1]
	perf = MatchPerformance(p, fix)
	perf.goals = 4
	perf.assists = 2
	perf.shots_on_target = 6
	perf.passes_completed = 60
	perf.passes_attempted = 65
	perf.key_passes = 5
	perf.xg = 2.5
	perf.xa = 1.2
	rating = perf.calculate_rating(fix)
	assert rating >= 9.5
