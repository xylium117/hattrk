import random
import pytest
import io
from contextlib import redirect_stdout
import game
import engine


# Module to store the pristine random state after session initialization
_pristine_state = None


def pytest_sessionstart(session):
    """Capture the random state after pytest initialization but before any tests run."""
    global _pristine_state
    random.seed(42)
    _pristine_state = random.getstate()


def pytest_sessionfinish(session):
    """Restore the pristine random state at the end."""
    if _pristine_state is not None:
        random.setstate(_pristine_state)


@pytest.fixture(autouse=True)
def restore_pristine_random():
    """Restore pristine random state before each test and clear module caches."""
    global _pristine_state
    if _pristine_state is not None:
        random.setstate(_pristine_state)
    # Clear game.py's module-level club cache so club data regenerates with restored random state
    game._CACHED_CLUBS = None
    game._CACHED_LEAGUES = {}
    yield


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