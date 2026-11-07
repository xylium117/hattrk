import os, sys, json, random
from collections import defaultdict
import game, engine
from elo import get_club_elo, parse_form_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

class LeagueEntry:
	def __init__(self, club_name):
		self.club_name = club_name
		self.played = 0
		self.won = 0
		self.drawn = 0
		self.lost = 0
		self.gf = 0
		self.ga = 0
		self.gd = 0
		self.points = 0
		self.form = []
		self.clean_sheets = 0
		self.scorers = defaultdict(int)
		self.assisters = defaultdict(int)

	def record_result(self, gf, ga, is_home=True):
		self.played += 1
		self.gf += gf
		self.ga += ga
		self.gd = self.gf - self.ga
		if ga == 0:
			self.clean_sheets += 1
		if gf > ga:
			self.won += 1
			self.points += 3
			self.form.append('W')
		elif gf == ga:
			self.drawn += 1
			self.points += 1
			self.form.append('D')
		else:
			self.lost += 1
			self.form.append('L')
		if len(self.form) > 5:
			self.form.pop(0)

	@property
	def form_str(self):
		return "".join(self.form) if self.form else "-----"

class League:
	def __init__(self, league_id, name, country, continent, gender, tier, clubs, ucl_spots=4, uel_spots=2, uecl_spots=1, rel_spots=3):
		self.league_id = league_id
		self.name = name
		self.country = country
		self.continent = continent
		self.gender = gender
		self.tier = tier
		self.club_names = list(clubs)
		self.ucl_spots = ucl_spots
		self.uel_spots = uel_spots
		self.uecl_spots = uecl_spots
		self.rel_spots = rel_spots
		self.entries = {name: LeagueEntry(name) for name in self.club_names}
		self.fixtures = []
		self.current_round = 0
		self._generate_schedule()

	def _generate_schedule(self):
		teams = list(self.club_names)
		if len(teams) % 2 == 1:
			teams.append(None)
		n = len(teams)
		rounds = []
		for r in range(n - 1):
			round_matches = []
			for i in range(n // 2):
				t1 = teams[i]
				t2 = teams[n - 1 - i]
				if t1 is not None and t2 is not None:
					if r % 2 == 0:
						round_matches.append((t1, t2))
					else:
						round_matches.append((t2, t1))
			rounds.append(round_matches)
			teams = [teams[0]] + [teams[-1]] + teams[1:-1]
		
		return_rounds = []
		for r_matches in rounds:
			rev_round = [(t2, t1) for (t1, t2) in r_matches]
			return_rounds.append(rev_round)
		self.fixtures = rounds + return_rounds

	def simulate_matchday(self, round_idx, quiet=True):
		if round_idx >= len(self.fixtures):
			return []
		round_matches = self.fixtures[round_idx]
		results = []
		saved_savecard = engine.SAVE_SCORECARD
		engine.set_save_scorecard(False)
		
		old_stdout = None
		devnull = None
		if quiet:
			old_stdout = sys.stdout
			devnull = open(os.devnull, 'w', encoding='utf-8')
			sys.stdout = devnull

		for h_name, a_name in round_matches:
			h_entry = self.entries[h_name]
			a_entry = self.entries[a_name]
			h_form = h_entry.form_str
			a_form = a_entry.form_str

			try:
				fix = game.setup(h_name, a_name, savecard=False)
				h_boost = parse_form_string(h_form)
				a_boost = parse_form_string(a_form)
				if hasattr(fix, 'home_elo'):
					fix.home_elo += (h_boost * 25.0)
				if hasattr(fix, 'away_elo'):
					fix.away_elo += (a_boost * 25.0)
				game.game(fix)
				hg = fix.home_score
				ag = fix.away_score
			except Exception:
				h_elo = get_club_elo(h_name)
				a_elo = get_club_elo(a_name)
				diff = h_elo - a_elo + 28
				if diff > 150:
					hg, ag = random.choice([(2, 0), (3, 1), (1, 0), (2, 1)])
				elif diff < -150:
					hg, ag = random.choice([(0, 2), (1, 3), (0, 1), (1, 2)])
				else:
					hg, ag = random.choice([(1, 1), (2, 1), (1, 2), (0, 0), (2, 2)])
				fix = None

			h_entry.record_result(hg, ag, is_home=True)
			a_entry.record_result(ag, hg, is_home=False)

			if fix and hasattr(fix, 'periods'):
				for per in fix.periods:
					for g in getattr(per, 'goals', []):
						scorer, assister, team, minute = g
						if scorer:
							s_name = getattr(scorer, 'short_name', '') or scorer.name
							if team == fix.home:
								h_entry.scorers[s_name] += 1
							else:
								a_entry.scorers[s_name] += 1
						if assister:
							ast_name = getattr(assister, 'short_name', '') or assister.name
							if team == fix.home:
								h_entry.assisters[ast_name] += 1
							else:
								a_entry.assisters[ast_name] += 1

			results.append((h_name, hg, ag, a_name))

		if quiet and old_stdout is not None:
			sys.stdout = old_stdout
			if devnull is not None:
				devnull.close()
		engine.set_save_scorecard(saved_savecard)
		self.current_round += 1
		return results

	def simulate_season(self, quiet=True, progress_cb=None, max_matchdays=None):
		limit = len(self.fixtures) if max_matchdays is None else min(max_matchdays, len(self.fixtures))
		for r_idx in range(limit):
			res = self.simulate_matchday(r_idx, quiet=quiet)
			if progress_cb:
				progress_cb(r_idx + 1, limit, res)
		return self.get_standings()

	def get_standings(self):
		sorted_entries = sorted(
			self.entries.values(),
			key=lambda e: (e.points, e.gd, e.gf, e.won, -e.lost),
			reverse=True
		)
		return sorted_entries

	def get_top_scorers(self, limit=10):
		total_scorers = defaultdict(int)
		for entry in self.entries.values():
			for player, cnt in entry.scorers.items():
				total_scorers[(player, entry.club_name)] += cnt
		return sorted(total_scorers.items(), key=lambda x: x[1], reverse=True)[:limit]

	def get_top_assisters(self, limit=10):
		total_assisters = defaultdict(int)
		for entry in self.entries.values():
			for player, cnt in entry.assisters.items():
				total_assisters[(player, entry.club_name)] += cnt
		return sorted(total_assisters.items(), key=lambda x: x[1], reverse=True)[:limit]

	def print_standings(self):
		standings = self.get_standings()
		print("\n" + "=" * 88)
		print(f"{self.name.upper()} STANDINGS ({self.country})".center(88))
		print("=" * 88)
		print(f"{'Pos':<4} {'Club':<26} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}  {'Form':<6} {'Status'}")
		print("-" * 88)
		for idx, e in enumerate(standings, 1):
			status = ""
			if idx == 1:
				status = "Champion / UCL" if self.continent == "Europe" else "Champion"
			elif idx <= self.ucl_spots:
				status = "UCL" if self.continent == "Europe" else "Continental"
			elif idx <= (self.ucl_spots + self.uel_spots):
				status = "UEL" if self.continent == "Europe" else "Secondary Cup"
			elif idx <= (self.ucl_spots + self.uel_spots + self.uecl_spots):
				status = "UECL"
			elif idx > (len(standings) - self.rel_spots):
				status = "Relegation Zone"
			
			print(f"{idx:<4} {e.club_name:<26} {e.played:>3} {e.won:>3} {e.drawn:>3} {e.lost:>3} {e.gf:>4} {e.ga:>4} {e.gd:>+4} {e.points:>4}  {e.form_str:<6} {status}")
		print("=" * 88)

		top_sc = self.get_top_scorers(5)
		if top_sc:
			print("\nTOP GOALSCORERS:")
			for rank, ((p_name, c_name), goals) in enumerate(top_sc, 1):
				print(f"  {rank}. {p_name:<24} ({c_name}) - {goals} goals")

def load_all_leagues():
	path = os.path.join(DATA_DIR, 'leagues.json')
	with open(path, 'r', encoding='utf-8') as f:
		return json.load(f)

def load_all_clubs():
	path = os.path.join(DATA_DIR, 'clubs.json')
	with open(path, 'r', encoding='utf-8') as f:
		return json.load(f)

def get_league(league_name_or_id):
	leagues = load_all_leagues()
	target = league_name_or_id.strip().lower()
	for l_id, data in leagues.items():
		if l_id == target or data['name'].lower() == target:
			return League(
				l_id, data['name'], data['country'], data['continent'],
				data['gender'], data['tier'], data['clubs'],
				data.get('ucl_spots', 4), data.get('uel_spots', 2),
				data.get('uecl_spots', 1), data.get('relegation_spots', 3)
			)
	for l_id, data in leagues.items():
		if target in data['name'].lower() or target in l_id:
			return League(
				l_id, data['name'], data['country'], data['continent'],
				data['gender'], data['tier'], data['clubs'],
				data.get('ucl_spots', 4), data.get('uel_spots', 2),
				data.get('uecl_spots', 1), data.get('relegation_spots', 3)
			)
	return None
