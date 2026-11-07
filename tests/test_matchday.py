import pytest
from matchday import Referee, Weather, VAREngine, SetPieceChoreography
import engine, game

def test_referee_initialization_and_profiles():
	ref = Referee("Test Ref", "disciplinarian", 1.30, 0.18, 0.10)
	assert ref.name == "Test Ref"
	assert ref.strictness == 1.30
	assert ref.should_call_foul(0.50, is_home=False, venue_attendance=60000) in [True, False]
	
	card_type = ref.evaluate_card(0.60, is_home=False, has_yellow=False)
	assert card_type in ["yellow", "red", "none"]

def test_weather_generation():
	w = Weather.generate_random()
	assert w.condition in ["Clear", "Wet / Heavy Rain", "Extreme Heat", "Freezing / Snow"]
	assert w.pass_mult > 0
	assert w.spill_mult > 0
	assert w.stamina_mult > 0

def test_var_engine_mechanics():
	var = VAREngine(overturn_rate=0.50)
	fix = game.setup("Arsenal", "Chelsea", savecard=False)
	is_overturned, reason, lines = var.check_candidate_goal(fix, "Saka", "Rice", shot_type="cutback")
	assert isinstance(is_overturned, bool)
	assert isinstance(lines, list)
	for line in lines:
		assert "(" not in line or "DECISION" in line or "VAR" in line

def test_set_piece_choreography():
	routine = SetPieceChoreography.select_routine("tiki_taka")
	assert routine in SetPieceChoreography.ROUTINES
	comm_goal = SetPieceChoreography.generate_commentary(routine, "Saka", "Saliba", "Raya", is_goal=True)
	assert "Saka" in comm_goal and "Saliba" in comm_goal
	assert "(" not in comm_goal

def test_fixture_matchday_integration():
	fix = game.setup("Real Madrid", "FC Barcelona", savecard=False)
	assert hasattr(fix, "referee")
	assert hasattr(fix, "weather")
	assert hasattr(fix, "var_engine")
	assert hasattr(fix, "stoppage_delays")
