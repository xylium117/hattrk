import random
import pytest
import os
import json
import csv
from league import get_league, load_all_leagues, load_all_clubs, League
from predictor import predict_league_outcomes
from season import ContinentalSeasonSimulator

def test_data_files_exist():
	assert os.path.exists('data/clubs.json')
	assert os.path.exists('data/leagues.json')
	assert os.path.exists('data/league_clubs.csv')

	with open('data/clubs.json', encoding='utf-8') as f:
		clubs = json.load(f)
		assert len(clubs) >= 400

	with open('data/leagues.json', encoding='utf-8') as f:
		leagues = json.load(f)
		assert len(leagues) >= 60

def test_league_initialization_and_schedule():
	lg = get_league("Premier League")
	assert lg is not None
	assert lg.country == "England"
	assert lg.continent == "Europe"
	assert len(lg.club_names) >= 18
	assert len(lg.fixtures) == (len(lg.club_names) - 1) * 2

def test_league_matchday_simulation():
	random.seed(333)
	lg = get_league("Scottish Premiership")
	assert lg is not None
	results = lg.simulate_matchday(0, quiet=True)
	assert len(results) > 0
	for h, hg, ag, a, events in results:
		assert hg >= 0 and ag >= 0
		# Check events dict structure
		assert 'xg' in events
		assert 'goals' in events
		assert 'cards' in events
	standings = lg.get_standings()
	assert len(standings) == len(lg.club_names)
	assert standings[0].points >= 0

def test_predictor_league_outcomes():
	random.seed(444)
	res = predict_league_outcomes("Scottish Premiership", runs=10)
	assert res is not None
	assert res['league'] == "Scottish Premiership"
	assert res['simulations'] == 10
	assert len(res['table']) == 12
	champ_sum = sum(r['champion_pct'] for r in res['table'])
	assert 99.0 <= champ_sum <= 101.0

def test_continental_season_simulation():
	random.seed(555)
	sim = ContinentalSeasonSimulator(["Europe"], seasons_count=1, max_domestic_rounds=2)
	history = sim.run()
	assert len(history) == 1
	season1 = history[0]
	assert "UEFA Champions League" in season1['continental_winners']
	winner, runner_up = season1['continental_winners']["UEFA Champions League"]
	assert winner != runner_up
	assert len(sim.trophy_cabinet) > 0
