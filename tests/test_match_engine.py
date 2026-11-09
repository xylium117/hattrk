import io
import random
from contextlib import redirect_stdout
import pytest
import game

def test_setup_fixture():
	fix = game.setup('Manchester City', 'Arsenal', savecard=False)
	assert fix.home.name == 'Manchester City'
	assert fix.away.name == 'Arsenal'
	assert len(fix.home.active) > 11
	assert len(fix.away.active) > 11
	assert fix.venue is not None
	assert 'Etihad' in fix.venue

def test_firstxi_selection():
	fix = game.setup('Real Madrid', 'FC Barcelona', savecard=False)
	with redirect_stdout(io.StringIO()):
		xi = game.firstxi(fix.home, '4-3-3')
	assert len(xi) == 11
	gk_count = sum(1 for p in xi if getattr(p, 'position', '') == 'GK' or getattr(p, 'assigned_slot', '') == 'GK')
	assert gk_count == 1
	for p in xi:
		assert hasattr(p, 'assigned_slot')
		assert hasattr(p, 'position_familiarity')
		assert hasattr(p, 'effective_overall')

def test_pick_bench():
	fix = game.setup('Real Madrid', 'FC Barcelona', savecard=False)
	with redirect_stdout(io.StringIO()):
		xi = game.firstxi(fix.home, '4-3-3')
		bench = game.pick_bench(fix.home, xi, count=5)
	assert len(bench) == 5
	for b in bench:
		assert b not in xi

def test_full_match_simulation():
	random.seed(123)
	fix = game.setup('Liverpool', 'Everton', savecard=False)
	with redirect_stdout(io.StringIO()):
		game.game(fix)

	assert isinstance(fix.home_score, int) and fix.home_score >= 0
	assert isinstance(fix.away_score, int) and fix.away_score >= 0
	assert fix.minute >= 90
	assert fix.home_shots >= 0
	assert fix.away_shots >= 0
	assert fix.home_passes_comp > 100
	assert fix.away_passes_comp > 100
	assert fix.home_corners >= 0
	assert fix.away_corners >= 0

	for p in fix.home.xi:
		if len(p.inns) > 0:
			assert p.inns[-1].minutes_played > 0
			assert hasattr(p.inns[-1], 'rating')

