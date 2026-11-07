import pytest
from gamestate import GameStateManager

class MockLogger:
	def __init__(self):
		self.logs = []

	def __call__(self, msg):
		self.logs.append(msg)

class MockPlayer:
	def __init__(self, name, pos, heading=75, jumping=75, strength=75):
		self.name = name
		self.position = pos
		self.primary_position = pos
		self.heading = heading
		self.jumping = jumping
		self.strength = strength

class MockTeam:
	def __init__(self, name):
		self.name = name
		self.xi = [
			MockPlayer('GK', 'GK'),
			MockPlayer('CB1', 'CB', 80, 80, 85),
			MockPlayer('CB2', 'CB', 75, 75, 75),
			MockPlayer('LB', 'LB'),
			MockPlayer('RB', 'RB'),
			MockPlayer('CM', 'CM'),
			MockPlayer('ST', 'ST')
		]
		self.manager_pov = None

class MockMatch:
	def __init__(self):
		self.logger = MockLogger()

def test_gamestate_initialization():
	team = MockTeam('Arsenal')
	match = MockMatch()
	gsm = GameStateManager(team, match, is_home=True)
	assert gsm.name == 'Arsenal'
	assert gsm.mentality == 'balanced'
	assert gsm.urgency == 0.0
	assert gsm.target_man is None

def test_calculate_urgency():
	team = MockTeam('Arsenal')
	match = MockMatch()
	gsm = GameStateManager(team, match, is_home=True)

	u_draw_early = gsm.calculate_urgency(10, 0)
	assert u_draw_early == 0.0

	u_losing_late = gsm.calculate_urgency(85, -1)
	assert u_losing_late > 0.0

	u_winning_late = gsm.calculate_urgency(85, 2)
	assert u_winning_late < 0.0

def test_evaluate_mentality_shifts():
	team = MockTeam('Arsenal')
	match = MockMatch()
	gsm = GameStateManager(team, match, is_home=True)

	assert gsm.evaluate_mentality(20, 0, 11, 11) == 'balanced'

	assert gsm.evaluate_mentality(70, -1, 11, 11) == 'attacking_overload'

	assert gsm.evaluate_mentality(85, -1, 11, 11) == 'desperation_hail_mary'
	assert gsm.target_man is not None
	assert gsm.target_man.name == 'CB1'

	assert gsm.evaluate_mentality(80, 1, 11, 11) == 'park_the_bus'

	assert gsm.evaluate_mentality(60, 2, 11, 11) == 'controlled_counter'

def test_modifiers():
	team = MockTeam('Arsenal')
	match = MockMatch()
	gsm = GameStateManager(team, match, is_home=True)

	gsm.mentality = 'balanced'
	assert gsm.get_press_modifier() == 1.0
	assert gsm.get_pass_risk_modifier() == 1.0
	assert gsm.get_backline_depth() == 'mid_block'

	gsm.mentality = 'park_the_bus'
	assert gsm.get_press_modifier() == 0.70
	assert gsm.get_pass_risk_modifier() == 0.65
	assert gsm.get_backline_depth() == 'deep'

	gsm.mentality = 'attacking_overload'
	assert gsm.get_press_modifier() == 1.25
	assert gsm.get_pass_risk_modifier() == 1.20
	assert gsm.get_backline_depth() == 'high'

	gsm.mentality = 'desperation_hail_mary'
	assert gsm.get_press_modifier() == 1.40
	assert gsm.get_pass_risk_modifier() == 1.50
	assert gsm.get_backline_depth() == 'high'

