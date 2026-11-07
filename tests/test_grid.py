import pytest
import math
from grid import (
	zone_to_coord,
	coord_to_zone,
	invert_zone,
	zone_distance,
	get_zones_in_path,
	default_position_zones,
	PitchGrid
)

def test_zone_to_coord_and_back():
	for z in range(1, 19):
		r, c = zone_to_coord(z)
		assert 0 <= r <= 2
		assert 0 <= c <= 5
		assert coord_to_zone(r, c) == z

def test_invert_zone():
	assert invert_zone(1) == 18
	assert invert_zone(18) == 1
	assert invert_zone(7) == 12
	assert invert_zone(12) == 7
	for z in range(1, 19):
		assert invert_zone(invert_zone(z)) == z

def test_zone_distance():
	assert zone_distance(1, 1) == 0.0
	assert zone_distance(1, 2) == pytest.approx(0.7)
	assert zone_distance(1, 7) == pytest.approx(1.5)
	assert zone_distance(1, 8) == pytest.approx(math.sqrt(1.5**2 + 0.7**2))

def test_get_zones_in_path():
	path = get_zones_in_path(1, 3)
	assert 2 in path
	path_vert = get_zones_in_path(1, 13)
	assert 7 in path_vert
	assert get_zones_in_path(5, 5) == []

def test_default_position_zones():
	def_z, att_z = default_position_zones('GK')
	assert def_z == 3 and att_z == 3
	def_z, att_z = default_position_zones('CB')
	assert def_z in [3, 4]
	def_z, att_z = default_position_zones('ST')
	assert att_z in [15, 16]

class MockPlayer:
	def __init__(self, name, pos, ovr=75):
		self.name = name
		self.position = pos
		self.assigned_slot = pos
		self.primary_position = pos
		self.overall = ovr
		self.def_awareness = 75.0
		self.interceptions = 75.0
		self.standing_tackle = 75.0
		self.pace = 75.0
		self.fitness = 1.0
		self.short_passing = 75.0
		self.long_passing = 75.0
		self.vision = 75.0
		self.composure = 75.0

	def has_playstyle(self, style):
		return False

class MockTeam:
	def __init__(self, name, is_home=True):
		self.name = name
		self.is_home = is_home
		positions = ['GK', 'LB', 'CB', 'CB', 'RB', 'DMF', 'CM', 'CM', 'LW', 'RW', 'ST']
		self.xi = [MockPlayer(f'{name}_{p}_{i}', p) for i, p in enumerate(positions)]

def test_pitch_grid_positions_and_risk():
	grid = PitchGrid()
	home_team = MockTeam('Home', is_home=True)
	away_team = MockTeam('Away', is_home=False)

	grid.update_team_positions(home_team, is_home=True, in_possession=True, mentality='balanced', def_line='mid_block')
	grid.update_team_positions(away_team, is_home=False, in_possession=False, mentality='balanced', def_line='mid_block')

	for p in home_team.xi:
		z = grid.get_player_zone(p)
		assert 1 <= z <= 18

	passer = [p for p in home_team.xi if p.position == 'CM'][0]
	receiver = [p for p in home_team.xi if p.position == 'ST'][0]
	risk = grid.calculate_pass_interception_risk(passer, receiver, away_team, is_home=True)
	assert 0.04 <= risk <= 0.75

def test_pitch_grid_clear():
	grid = PitchGrid()
	team = MockTeam('Test')
	grid.update_team_positions(team, is_home=True, in_possession=True, mentality='balanced', def_line='mid_block')
	assert len(grid.player_zones) > 0
	grid.clear()
	assert len(grid.player_zones) == 0
	for z in range(1, 19):
		assert grid.zone_players[z] == []

