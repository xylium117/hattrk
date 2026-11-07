import pytest
from tactics import (
	FORMATIONS,
	calculate_player_familiarity,
	calculate_team_fluidity,
	load_club_tactics,
	get_formation_matchup,
	ManagerPOV
)

def test_formations_structure():
	assert '4-3-3' in FORMATIONS
	assert '4-2-3-1' in FORMATIONS
	assert '3-5-2' in FORMATIONS
	for form_name, slots in FORMATIONS.items():
		assert len(slots) == 11
		assert slots[0] == 'GK'
		assert slots.count('GK') == 1

class MockPlayer:
	def __init__(self, name, prim_pos, gen_pos):
		self.name = name
		self.primary_position = prim_pos
		self.position = gen_pos
		self.position_familiarity = 1.0

def test_player_familiarity():
	gk = MockPlayer('Courtois', 'GK', 'GK')
	assert calculate_player_familiarity(gk, 'GK') == 1.0
	assert calculate_player_familiarity(gk, 'ST') == 0.15

	striker = MockPlayer('Haaland', 'ST', 'ATT')
	assert calculate_player_familiarity(striker, 'ST') == 1.0
	assert calculate_player_familiarity(striker, 'GK') == 0.15

	cf = MockPlayer('Benzema', 'CF', 'ATT')
	assert calculate_player_familiarity(cf, 'ST') == 0.95

	cdm = MockPlayer('Rodri', 'CDM', 'DMF')
	assert calculate_player_familiarity(cdm, 'CM') == 0.88

class MockTeam:
	def __init__(self, name):
		self.name = name
		self.xi = [MockPlayer(f'P_{i}', 'CM', 'MID') for i in range(11)]
		for p in self.xi:
			p.position_familiarity = 0.90

def test_team_fluidity():
	team = MockTeam('Arsenal')
	fluidity = calculate_team_fluidity(team, win_streak=2, games_together=30)
	assert 0.65 <= fluidity <= 1.25

def test_load_club_tactics():
	t_real = load_club_tactics('Real Madrid')
	assert isinstance(t_real, dict)
	assert 'formation' in t_real

	t_unknown = load_club_tactics('NonExistentFC')
	assert isinstance(t_unknown, dict)
	assert t_unknown['formation'] == '4-3-3'

def test_formation_matchup():
	h_mod, a_mod = get_formation_matchup('4-3-3', '4-2-3-1')
	assert 0.80 <= h_mod <= 1.25
	assert 0.80 <= a_mod <= 1.25

def test_manager_pov():
	t_dict = {
		'formation': '4-2-3-1',
		'defensive_line': 'high',
		'pressing_trigger': 'counterpress',
		'build_up_style': 'short_patient',
		'set_piece_focus': 'aerial_overload',
		'offside_trap': 'aggressive',
		'games_together': 35,
		'win_streak': 3
	}
	pov = ManagerPOV('Arsenal', **t_dict)
	assert pov.formation == '4-2-3-1'
	assert pov.defensive_line == 'high'
	assert pov.get_pressing_modifier() > 1.0
	assert pov.get_build_up_modifier() > 1.0
	assert pov.get_offside_trap_risk() > 0.0

