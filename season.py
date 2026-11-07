import os, sys, random, json
from collections import defaultdict
import game, engine
from league import get_league, load_all_leagues, load_all_clubs

CONTINENTAL_TOURNAMENTS = {
	"Europe": [
		{
			"name": "UEFA Champions League",
			"tier": "primary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("premier_league", 4),
				("laliga_ea_sports", 4),
				("serie_a_enilive", 4),
				("bundesliga", 4)
			]
		},
		{
			"name": "UEFA Europa League",
			"tier": "secondary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("ligue_1_mcdonald_s", 3),
				("liga_portugal", 3),
				("eredivisie", 3),
				("scottish_premiership", 3),
				("1a_pro_league", 2),
				("trendyol_s_per_lig", 2)
			]
		},
		{
			"name": "UEFA Conference League",
			"tier": "tertiary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("pko_bank_polski_ekstraklasa", 3),
				("credit_suisse_super_league", 3),
				("_sterreichische_fu_ball_bundesliga", 3),
				("3f_superliga", 3),
				("allsvenskan", 2),
				("eliteserien", 2)
			]
		},
		{
			"name": "UEFA Women's Champions League",
			"tier": "primary",
			"size": 8,
			"gender": "Female",
			"sources": [
				("barclays_women_s_super_league", 2),
				("liga_f", 2),
				("google_pixel_frauen_bundesliga", 2),
				("arkema_premi_re_ligue", 2)
			]
		}
	],
	"South America": [
		{
			"name": "Copa Libertadores",
			"tier": "primary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("liga_do_brasil", 6),
				("liga_profesional_de_f_tbol", 6),
				("liga_colombia", 4)
			]
		},
		{
			"name": "Copa Sudamericana",
			"tier": "secondary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("conmebol_libertadores", 8),
				("conmebol_sudamericana", 8)
			]
		}
	],
	"North America": [
		{
			"name": "CONCACAF Champions Cup",
			"tier": "primary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("major_league_soccer", 8),
				("liga_bbva_mx", 8)
			]
		}
	],
	"Asia": [
		{
			"name": "AFC Champions League Elite",
			"tier": "primary",
			"size": 16,
			"gender": "Male",
			"sources": [
				("roshn_saudi_league", 5),
				("k_league_1", 4),
				("isuzu_ute_a_league", 3),
				("chinese_football_association_super_league", 2),
				("indian_super_league", 2)
			]
		}
	],
	"Africa": [
		{
			"name": "CAF Champions League",
			"tier": "primary",
			"size": 8,
			"gender": "Male",
			"sources": [
				("al_ahly", 1),
				("zamalek", 1),
				("mamelodi_sundowns", 1),
				("wydad_ac", 1),
				("raja_casablanca", 1),
				("esperance_de_tunis", 1),
				("tp_mazembe", 1),
				("simba_sc", 1)
			]
		}
	]
}

def _simulate_two_legged_tie(t1_name, t2_name, is_final=False):
	saved_savecard = engine.SAVE_SCORECARD
	engine.set_save_scorecard(False)
	old_stdout = sys.stdout
	devnull = open(os.devnull, 'w', encoding='utf-8')
	sys.stdout = devnull

	if is_final:
		try:
			fix = game.setup(t1_name, t2_name, savecard=False)
			fix.extra_time_opt = True
			fix.penalties_opt = True
			game.game(fix)
			h_score = fix.home_score
			a_score = fix.away_score
			if h_score > a_score:
				winner = t1_name
			elif a_score > h_score:
				winner = t2_name
			else:
				winner = t1_name if random.random() < 0.50 else t2_name
		except Exception:
			winner = t1_name if random.random() < 0.52 else t2_name
			h_score, a_score = 1, 0

		sys.stdout = old_stdout
		devnull.close()
		engine.set_save_scorecard(saved_savecard)
		return winner, f"{h_score} - {a_score}"

	try:
		fix1 = game.setup(t1_name, t2_name, savecard=False)
		game.game(fix1)
		l1_t1, l1_t2 = fix1.home_score, fix1.away_score
	except Exception:
		l1_t1, l1_t2 = (2, 1)

	try:
		fix2 = game.setup(t2_name, t1_name, savecard=False)
		game.game(fix2)
		l2_t2, l2_t1 = fix2.home_score, fix2.away_score
	except Exception:
		l2_t2, l2_t1 = (1, 1)

	sys.stdout = old_stdout
	devnull.close()
	engine.set_save_scorecard(saved_savecard)

	agg_t1 = l1_t1 + l2_t1
	agg_t2 = l1_t2 + l2_t2
	if agg_t1 > agg_t2:
		winner = t1_name
	elif agg_t2 > agg_t1:
		winner = t2_name
	else:
		winner = t1_name if random.random() < 0.50 else t2_name
	return winner, f"{agg_t1} - {agg_t2} (agg)"

class KnockoutTournament:
	def __init__(self, name, clubs):
		self.name = name
		self.clubs = list(clubs)
		self.winner = None
		self.runner_up = None

	def run(self):
		pool = list(self.clubs)
		random.shuffle(pool)
		target_size = 16 if len(pool) >= 16 else (8 if len(pool) >= 8 else 4)
		pool = pool[:target_size]

		while len(pool) > 1:
			next_round = []
			is_final = (len(pool) == 2)
			for i in range(0, len(pool), 2):
				if i + 1 < len(pool):
					t1 = pool[i]
					t2 = pool[i + 1]
					advancer, score_desc = _simulate_two_legged_tie(t1, t2, is_final=is_final)
					next_round.append(advancer)
					if is_final:
						self.winner = advancer
						self.runner_up = t2 if advancer == t1 else t1
				else:
					next_round.append(pool[i])
			pool = next_round
		return self.winner, self.runner_up

FLAGSHIP_DOMESTIC_LEAGUES = {
	"Europe": ["premier_league", "laliga_ea_sports", "serie_a_enilive", "bundesliga"],
	"South America": ["liga_do_brasil", "liga_profesional_de_f_tbol", "liga_colombia"],
	"North America": ["major_league_soccer", "liga_bbva_mx"],
	"Asia": ["roshn_saudi_league", "k_league_1", "isuzu_ute_a_league"],
	"Africa": []
}

class ContinentalSeasonSimulator:
	def __init__(self, continents, seasons_count=1, max_domestic_rounds=None):
		self.continents = continents
		self.seasons_count = seasons_count
		self.max_domestic_rounds = max_domestic_rounds
		self.history = []
		self.trophy_cabinet = defaultdict(lambda: defaultdict(int))

	def run(self):
		all_leagues = load_all_leagues()
		all_clubs = load_all_clubs()

		for s_num in range(1, self.seasons_count + 1):
			season_data = {
				'season': s_num,
				'domestic_winners': {},
				'continental_winners': {}
			}

			qualified_for_cups = defaultdict(list)

			for cont in self.continents:
				flagship_ids = FLAGSHIP_DOMESTIC_LEAGUES.get(cont, [])
				if not flagship_ids:
					flagship_ids = [l_id for l_id, l_data in all_leagues.items() if l_data['continent'] == cont and l_data['tier'] == 1][:3]
				for l_id in flagship_ids:
					lg = get_league(l_id)
					if not lg:
						continue
					standings = lg.simulate_season(quiet=True, max_matchdays=self.max_domestic_rounds)
					if standings:
						champ = standings[0].club_name
						season_data['domestic_winners'][lg.name] = champ
						self.trophy_cabinet[champ]['Domestic League'] += 1

						for idx, entry in enumerate(standings[:8]):
							qualified_for_cups[l_id].append(entry.club_name)

				tournaments = CONTINENTAL_TOURNAMENTS.get(cont, [])
				for t_meta in tournaments:
					t_name = t_meta['name']
					participants = []
					for src_id, count in t_meta['sources']:
						cands = qualified_for_cups.get(src_id, [])
						if cands:
							participants.extend(cands[:count])
						else:
							l_obj = all_leagues.get(src_id)
							if l_obj and l_obj.get('clubs'):
								participants.extend(l_obj['clubs'][:count])

					if len(participants) < 4:
						cont_pool = [c['name'] for c in all_clubs.values() if c['continent'] == cont and c['gender'] == t_meta['gender']]
						if cont_pool:
							participants.extend(random.sample(cont_pool, min(len(cont_pool), t_meta['size'] - len(participants))))

					if len(participants) >= 4:
						cup = KnockoutTournament(t_name, participants[:t_meta['size']])
						w, ru = cup.run()
						season_data['continental_winners'][t_name] = (w, ru)
						self.trophy_cabinet[w][t_name] += 1

			self.history.append(season_data)
		return self.history

	def print_summary(self):
		print("\n" + "=" * 88)
		print("MULTI-CONTINENTAL SEASON SIMULATION SUMMARY".center(88))
		print(f"Continents: {', '.join(self.continents)} | Total Seasons: {self.seasons_count}".center(88))
		print("=" * 88)

		for s in self.history:
			print(f"\n[ SEASON {s['season']} ]")
			print("  DOMESTIC LEAGUE CHAMPIONS:")
			for l_name, champ in list(s['domestic_winners'].items())[:6]:
				print(f"    • {l_name:<36} : {champ}")
			print("  CONTINENTAL TOURNAMENT CHAMPIONS:")
			for t_name, (winner, runner_up) in s['continental_winners'].items():
				print(f"    ★ {t_name:<32} : {winner} (Runner-up: {runner_up})")

		print("\n" + "=" * 88)
		print("TROPHY CABINET & DYNASTY HALL OF FAME".center(88))
		print("=" * 88)
		ranked_clubs = sorted(
			self.trophy_cabinet.items(),
			key=lambda x: sum(x[1].values()),
			reverse=True
		)[:15]

		print(f"{'Club':<30} {'Total Trophies':>15}  {'Honours Breakdown'}")
		print("-" * 88)
		for club, honours in ranked_clubs:
			total = sum(honours.values())
			breakdown = ", ".join([f"{count}x {h}" for h, count in honours.items()])
			print(f"{club:<30} {total:>15}  {breakdown}")
		print("=" * 88)
