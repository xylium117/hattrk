import json
import math
import os

_CACHED_CLUB_ELO = None

def calculate_team_elo(team_obj):
	if not team_obj:
		return 1650

	players = []
	if hasattr(team_obj, 'starters') and team_obj.starters:
		players.extend(team_obj.starters)
	elif hasattr(team_obj, 'xi') and team_obj.xi:
		players.extend(team_obj.xi)

	if hasattr(team_obj, 'bench') and team_obj.bench:
		players.extend(team_obj.bench)

	if not players:
		squad = getattr(team_obj, 'squad', []) or getattr(team_obj, 'active', []) or getattr(team_obj, 'players', [])
		players = squad[:16]

	if not players:
		return 1650

	avg_ovr = sum(float(getattr(p, 'overall', 75.0)) for p in players) / float(len(players))
	return int(round(1500 + (avg_ovr - 75.0) * 45.0))

def _load_elo_file():
	global _CACHED_CLUB_ELO
	if _CACHED_CLUB_ELO is not None:
		return _CACHED_CLUB_ELO

	base_dir = os.path.dirname(os.path.abspath(__file__))
	path = os.path.join(base_dir, 'data', 'elo.json')
	if not os.path.exists(path):
		path = 'data/elo.json'

	if os.path.exists(path):
		try:
			with open(path, 'r', encoding='utf-8') as f:
				_CACHED_CLUB_ELO = json.load(f)
				return _CACHED_CLUB_ELO
		except Exception:
			pass

	_CACHED_CLUB_ELO = {}
	return _CACHED_CLUB_ELO

def get_club_elo(club_name, team_obj=None):
	if team_obj and (getattr(team_obj, 'xi', None) or getattr(team_obj, 'starters', None)):
		return calculate_team_elo(team_obj)

	data = _load_elo_file()
	clean_name = str(club_name).strip()

	if clean_name in data:
		return data[clean_name]

	for k, v in data.items():
		if k.lower() == clean_name.lower():
			return v

	for k, v in data.items():
		if k.lower() in clean_name.lower() or clean_name.lower() in k.lower():
			return v

	if team_obj:
		return calculate_team_elo(team_obj)

	return 1650

def elo_win_probability(elo_a, elo_b, home_advantage=65):
	diff = (elo_a + home_advantage) - elo_b
	return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

def elo_goal_difference_anchor(elo_home, elo_away, home_advantage=65):
	diff = (elo_home + home_advantage) - elo_away
	return (diff / 400.0) * 1.25

def parse_form_string(form_str):
	if not form_str:
		return 0.0
	clean = form_str.strip().upper()
	score = 0.0
	weight = 1.0
	for ch in reversed(clean[-5:]):
		if ch == 'W':
			score += 0.035 * weight
		elif ch == 'D':
			score += 0.005 * weight
		elif ch == 'L':
			score -= 0.035 * weight
		weight *= 0.85
	return max(-0.15, min(0.15, score))

def get_tactical_friction(home_philosophy, away_philosophy):
	h_phil = str(home_philosophy).strip().lower()
	a_phil = str(away_philosophy).strip().lower()

	h_bonus = 1.0
	a_bonus = 1.0

	if h_phil == 'high_press' and a_phil == 'tiki_taka':
		h_bonus *= 1.06
		a_bonus *= 0.96
	elif h_phil == 'tiki_taka' and a_phil == 'low_block':
		h_bonus *= 0.95
		a_bonus *= 1.04
	elif h_phil == 'direct_counter' and a_phil in ['high_press', 'tiki_taka']:
		h_bonus *= 1.08
		a_bonus *= 0.94
	elif a_phil == 'direct_counter' and h_phil in ['high_press', 'tiki_taka']:
		a_bonus *= 1.08
		h_bonus *= 0.94

	return h_bonus, a_bonus
