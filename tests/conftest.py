import random
import pytest
import io
from contextlib import redirect_stdout
import game
import engine


@pytest.fixture(scope="session")
def seeded_random():
    """Ensure deterministic random state for all tests."""
    random.seed(42)
    yield random
    random.seed(42)


@pytest.fixture
def seeded_game_setup():
    """Create a game fixture with deterministic seeding."""
    def _setup(home_team, away_team, seed=12345):
        random.seed(seed)
        fix = game.setup(home_team, away_team, savecard=False)
        fix.savecard = False
        with redirect_stdout(io.StringIO()):
            game.game(fix)
        return fix
    return _setup


@pytest.fixture
def silent_game_setup():
    """Create a game fixture without running the match, with deterministic seeding."""
    def _setup(home_team, away_team, seed=12345):
        random.seed(seed)
        fix = game.setup(home_team, away_team, savecard=False)
        fix.savecard = False
        return fix
    return _setup


@pytest.fixture
def xi_and_bench(silent_game_setup):
    """Get starting XI and bench for a team."""
    def _get(team_name, formation, seed=12345):
        random.seed(seed)
        fix = game.setup(team_name, "Dummy Opponent", savecard=False)
        with redirect_stdout(io.StringIO()):
            xi = game.firstxi(fix.home, formation)
            bench = game.pick_bench(fix.home, xi, count=5)
        for p in xi + bench:
            engine.MatchPerformance(p, fix)
        return xi, bench
    return _get