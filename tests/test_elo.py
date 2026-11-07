import pytest
from elo import (
	calculate_team_elo,
	get_club_elo,
	elo_win_probability,
	elo_goal_difference_anchor,
	parse_form_string,
	get_tactical_friction
)

class MockPlayer:
	def __init__(self, ovr):
		self.overall = ovr

class MockTeam:
	def __init__(self, avg_ovr):
		self.starters = [MockPlayer(avg_ovr) for _ in range(11)]
		self.bench = [MockPlayer(avg_ovr) for _ in range(5)]

def test_calculate_team_elo():
	elite_team = MockTeam(85.0)
	mid_team = MockTeam(75.0)
	low_team = MockTeam(65.0)

	elite_elo = calculate_team_elo(elite_team)
	mid_elo = calculate_team_elo(mid_team)
	low_elo = calculate_team_elo(low_team)

	assert elite_elo > mid_elo
	assert mid_elo > low_elo
	assert mid_elo == 1500

def test_get_club_elo():
	elo_city = get_club_elo('Manchester City')
	assert isinstance(elo_city, (int, float))
	assert elo_city > 1500

	elo_unknown = get_club_elo('NonExistentFC')
	assert elo_unknown == 1650

def test_elo_win_probability():
	prob_equal = elo_win_probability(1700, 1700, home_advantage=0)
	assert prob_equal == pytest.approx(0.50)

	prob_strong_fav = elo_win_probability(2100, 1500, home_advantage=0)
	assert prob_strong_fav > 0.90

	prob_underdog = elo_win_probability(1500, 2100, home_advantage=0)
	assert prob_underdog < 0.10

def test_elo_goal_difference_anchor():
	gd_equal = elo_goal_difference_anchor(1700, 1700, home_advantage=0)
	assert gd_equal == pytest.approx(0.0)

	gd_fav = elo_goal_difference_anchor(2000, 1600, home_advantage=0)
	assert gd_fav > 0.0

def test_parse_form_string():
	assert parse_form_string('') == 0.0
	assert parse_form_string('WWWWW') > 0.0
	assert parse_form_string('LLLLL') < 0.0
	assert parse_form_string('WWWWW') > parse_form_string('WWDDL')

def test_get_tactical_friction():
	fric = get_tactical_friction('tiki-taka', 'low_block')
	assert isinstance(fric, tuple) and len(fric) == 2
	assert isinstance(fric[0], float) and isinstance(fric[1], float)
	assert 0.80 <= fric[0] <= 1.25
	assert 0.80 <= fric[1] <= 1.25

