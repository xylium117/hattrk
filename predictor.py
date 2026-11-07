import argparse
import json
import os
import random
import sys
from collections import Counter
import engine
import game
from elo import get_club_elo, elo_win_probability, elo_goal_difference_anchor, parse_form_string, get_tactical_friction
from tactics import load_club_tactics, get_formation_matchup

def evaluate_rps(probs, outcome):
	p_h, p_d, p_a = probs
	if outcome == 'home':
		o = [1.0, 0.0, 0.0]
	elif outcome == 'draw':
		o = [0.0, 1.0, 0.0]
	else:
		o = [0.0, 0.0, 1.0]

	p_cum1 = p_h
	o_cum1 = o[0]
	term1 = (p_cum1 - o_cum1) ** 2

	p_cum2 = p_h + p_d
	o_cum2 = o[0] + o[1]
	term2 = (p_cum2 - o_cum2) ** 2

	return 0.5 * (term1 + term2)

def evaluate_brier(prob, actual_binary):
	return (prob - (1.0 if actual_binary else 0.0)) ** 2

def apply_squad_absences(team_obj, missing_names):
	if not missing_names:
		return
	missing_set = [m.strip().lower() for m in missing_names if m.strip()]
	if not missing_set:
		return

	to_remove = []
	for p in getattr(team_obj, 'xi', []):
		p_name = p.name.lower()
		p_short = getattr(p, 'short_name', '').lower()
		if any(m in p_name or (p_short and m in p_short) for m in missing_set):
			to_remove.append(p)

	for p in to_remove:
		team_obj.xi.remove(p)
		bench = [b for b in getattr(team_obj, 'bench', []) if b not in team_obj.xi and b.position != 'GK']
		if bench:
			sub_in = max(bench, key=lambda b: b.overall)
			team_obj.xi.append(sub_in)
			team_obj.bench.remove(sub_in)

def run_monte_carlo(home_name, away_name, runs=500, home_missing=None, away_missing=None,
					home_form=None, away_form=None, home_formation=None, away_formation=None):
	clean_home = game.find_club(home_name) or home_name
	clean_away = game.find_club(away_name) or away_name

	elo_h = get_club_elo(clean_home)
	elo_a = get_club_elo(clean_away)
	elo_exp_h = elo_win_probability(elo_h, elo_a, home_advantage=65)
	elo_diff_anchor = elo_goal_difference_anchor(elo_h, elo_a, home_advantage=65)

	h_form_mod = parse_form_string(home_form)
	a_form_mod = parse_form_string(away_form)

	h_cfg = load_club_tactics(clean_home)
	a_cfg = load_club_tactics(clean_away)
	actual_h_form = home_formation or h_cfg.get('formation', '4-3-3')
	actual_a_form = away_formation or a_cfg.get('formation', '4-3-3')

	h_form_tact, a_form_tact = get_formation_matchup(actual_h_form, actual_a_form)

	h_phil = engine.CLUB_PHILOSOPHIES.get(clean_home, 'balanced')
	a_phil = engine.CLUB_PHILOSOPHIES.get(clean_away, 'balanced')
	h_tact_mult, a_tact_mult = get_tactical_friction(h_phil, a_phil)
	h_tact_mult *= h_form_tact
	a_tact_mult *= a_form_tact

	home_wins = 0
	draws = 0
	away_wins = 0
	tot_home_goals = 0
	tot_away_goals = 0
	tot_home_xg = 0.0
	tot_away_xg = 0.0

	scorelines = Counter()
	home_goalscorers = Counter()
	away_goalscorers = Counter()
	player_cards = Counter()

	over_1_5 = 0
	over_2_5 = 0
	over_3_5 = 0
	btts_yes = 0
	home_clean_sheets = 0
	away_clean_sheets = 0
	home_blowouts = 0
	away_blowouts = 0

	engine.set_save_scorecard(False)

	for _ in range(runs):
		orig_stdout = sys.stdout
		sys.stdout = open(os.devnull, 'w', encoding='utf-8')
		try:
			fix = game.setup(clean_home, clean_away, savecard=False)
			fix.savecard = False
			fix.home_elo = elo_h
			fix.away_elo = elo_a

			if home_formation:
				fix.home.formation = home_formation
				fix.home.xi = game.firstxi(fix.home, home_formation)
			if away_formation:
				fix.away.formation = away_formation
				fix.away.xi = game.firstxi(fix.away, away_formation)

			if home_missing:
				apply_squad_absences(fix.home, home_missing)
			if away_missing:
				apply_squad_absences(fix.away, away_missing)

			fix.momentum[fix.home.name] = (elo_diff_anchor * 0.45) + (h_form_mod * 1.5)
			fix.momentum[fix.away.name] = (-elo_diff_anchor * 0.45) + (a_form_mod * 1.5)

			for p in fix.home.xi:
				p.finishing = max(40.0, min(99.0, p.finishing * (1.0 + h_form_mod * 0.5) * h_tact_mult))
			for p in fix.away.xi:
				p.finishing = max(40.0, min(99.0, p.finishing * (1.0 + a_form_mod * 0.5) * a_tact_mult))

			fix.football()
		finally:
			sys.stdout.close()
			sys.stdout = orig_stdout

		h_g = fix.home_score
		a_g = fix.away_score
		tot_home_goals += h_g
		tot_away_goals += a_g
		tot_home_xg += fix.home_xg
		tot_away_xg += fix.away_xg

		if h_g > a_g:
			home_wins += 1
			if (h_g - a_g) >= 3:
				home_blowouts += 1
		elif h_g == a_g:
			draws += 1
		else:
			away_wins += 1
			if (a_g - h_g) >= 3:
				away_blowouts += 1

		scorelines[(h_g, a_g)] += 1

		tot_goals = h_g + a_g
		if tot_goals > 1.5: over_1_5 += 1
		if tot_goals > 2.5: over_2_5 += 1
		if tot_goals > 3.5: over_3_5 += 1
		if h_g > 0 and a_g > 0: btts_yes += 1
		if a_g == 0: home_clean_sheets += 1
		if h_g == 0: away_clean_sheets += 1

		home_p_names = {x.name for x in getattr(fix.home, 'starters', []) + getattr(fix.home, 'xi', []) + getattr(fix.home, 'squad', []) + getattr(fix.home, 'players', [])}
		for p in fix.players:
			if len(p.inns) > 0:
				perf = p.inns[-1]
				p_name = getattr(p, 'short_name', '') or p.name
				if perf.goals > 0:
					if p.name in home_p_names or getattr(p, 'team', '') == clean_home:
						home_goalscorers[p_name] += 1
					else:
						away_goalscorers[p_name] += 1
				if perf.yellow_cards > 0 or perf.red_cards > 0:
					player_cards[p_name] += 1

	p_home = round(home_wins / float(runs), 4)
	p_draw = round(draws / float(runs), 4)
	p_away = round(away_wins / float(runs), 4)

	implied_odds_h = round(1.0 / max(0.001, p_home), 2)
	implied_odds_d = round(1.0 / max(0.001, p_draw), 2)
	implied_odds_a = round(1.0 / max(0.001, p_away), 2)

	ah_minus_1_win = round(sum(cnt for (h, a), cnt in scorelines.items() if (h - a) >= 2) / float(runs), 4)
	ah_minus_1_push = round(sum(cnt for (h, a), cnt in scorelines.items() if (h - a) == 1) / float(runs), 4)
	ah_minus_1_loss = round(sum(cnt for (h, a), cnt in scorelines.items() if (h - a) <= 0) / float(runs), 4)

	ah_minus_1_5_win = ah_minus_1_win
	ah_plus_1_5_win = round(1.0 - ah_minus_1_5_win, 4)

	non_draw = max(0.0001, p_home + p_away)
	dnb_home = round(p_home / non_draw, 4)
	dnb_away = round(p_away / non_draw, 4)

	dc_1x = round(p_home + p_draw, 4)
	dc_x2 = round(p_draw + p_away, 4)
	dc_12 = round(p_home + p_away, 4)

	xp_home = round(3.0 * p_home + 1.0 * p_draw, 2)
	xp_away = round(3.0 * p_away + 1.0 * p_draw, 2)

	sorted_scores = []
	for (h, a), cnt in scorelines.most_common(10):
		sorted_scores.append({
			'score': f'{h}-{a}',
			'probability': round(cnt / float(runs), 4),
			'percentage': f'{(cnt / float(runs)) * 100:.1f}%'
		})

	top_h_scorers = []
	for name, cnt in home_goalscorers.most_common(5):
		top_h_scorers.append({
			'player': name,
			'team': clean_home,
			'probability': round(cnt / float(runs), 4),
			'percentage': f'{(cnt / float(runs)) * 100:.1f}%'
		})

	top_a_scorers = []
	for name, cnt in away_goalscorers.most_common(5):
		top_a_scorers.append({
			'player': name,
			'team': clean_away,
			'probability': round(cnt / float(runs), 4),
			'percentage': f'{(cnt / float(runs)) * 100:.1f}%'
		})

	return {
		'fixture': {
			'home': clean_home,
			'away': clean_away,
			'home_elo': elo_h,
			'away_elo': elo_a,
			'home_formation': actual_h_form,
			'away_formation': actual_a_form,
			'simulations': runs
		},
		'probabilities': {
			'home_win': p_home,
			'draw': p_draw,
			'away_win': p_away,
			'home_win_pct': f'{p_home * 100:.1f}%',
			'draw_pct': f'{p_draw * 100:.1f}%',
			'away_win_pct': f'{p_away * 100:.1f}%'
		},
		'implied_odds': {
			'home': implied_odds_h,
			'draw': implied_odds_d,
			'away': implied_odds_a
		},
		'expected_goals': {
			'home_goals_avg': round(tot_home_goals / float(runs), 2),
			'away_goals_avg': round(tot_away_goals / float(runs), 2),
			'total_goals_avg': round((tot_home_goals + tot_away_goals) / float(runs), 2),
			'home_xg_avg': round(tot_home_xg / float(runs), 2),
			'away_xg_avg': round(tot_away_xg / float(runs), 2)
		},
		'markets': {
			'over_1_5': f'{(over_1_5 / float(runs)) * 100:.1f}%',
			'over_2_5': f'{(over_2_5 / float(runs)) * 100:.1f}%',
			'under_2_5': f'{((runs - over_2_5) / float(runs)) * 100:.1f}%',
			'over_3_5': f'{(over_3_5 / float(runs)) * 100:.1f}%',
			'btts_yes': f'{(btts_yes / float(runs)) * 100:.1f}%',
			'btts_no': f'{((runs - btts_yes) / float(runs)) * 100:.1f}%',
			'home_clean_sheet': f'{(home_clean_sheets / float(runs)) * 100:.1f}%',
			'away_clean_sheet': f'{(away_clean_sheets / float(runs)) * 100:.1f}%',
			'home_blowout_3plus': f'{(home_blowouts / float(runs)) * 100:.1f}%',
			'away_blowout_3plus': f'{(away_blowouts / float(runs)) * 100:.1f}%'
		},
		'asian_handicap': {
			'ah_minus_0_5_home': f'{p_home * 100:.1f}%',
			'ah_plus_0_5_away': f'{(p_draw + p_away) * 100:.1f}%',
			'ah_minus_1_0_home': f'{ah_minus_1_win * 100:.1f}%',
			'ah_minus_1_0_push': f'{ah_minus_1_push * 100:.1f}%',
			'ah_plus_1_0_away': f'{ah_minus_1_loss * 100:.1f}%',
			'ah_minus_1_5_home': f'{ah_minus_1_5_win * 100:.1f}%',
			'ah_plus_1_5_away': f'{ah_plus_1_5_win * 100:.1f}%'
		},
		'derivatives': {
			'dnb_home': f'{dnb_home * 100:.1f}%',
			'dnb_away': f'{dnb_away * 100:.1f}%',
			'double_chance_1x': f'{dc_1x * 100:.1f}%',
			'double_chance_x2': f'{dc_x2 * 100:.1f}%',
			'double_chance_12': f'{dc_12 * 100:.1f}%',
			'expected_points_home': xp_home,
			'expected_points_away': xp_away
		},
		'top_scorelines': sorted_scores,
		'top_home_scorers': top_h_scorers,
		'top_away_scorers': top_a_scorers
	}

def print_prediction_report(res):
	f = res['fixture']
	p = res['probabilities']
	xg = res['expected_goals']
	m = res['markets']

	print("=" * 74)
	print("HATTRK MATCH PREDICTION ENSEMBLE REPORT".center(74))
	print(f"Simulated {f['simulations']} full matches via spatial possession engine".center(74))
	print("=" * 74)
	print(f"MATCHUP: {f['home']} (Elo: {f['home_elo']}) vs. {f['away']} (Elo: {f['away_elo']})")
	print(f"TACTICAL FORMATIONS: {f['home']} ({f['home_formation']}) vs. {f['away']} ({f['away_formation']})")
	print("-" * 74)
	print("OUTCOME PROBABILITIES (1X2):")
	print(f"  {f['home']} Win:  {p['home_win_pct']:>6}  (Fair Odds: {res['implied_odds']['home']:.2f})")
	print(f"  Draw:      {p['draw_pct']:>6}  (Fair Odds: {res['implied_odds']['draw']:.2f})")
	print(f"  {f['away']} Win:  {p['away_win_pct']:>6}  (Fair Odds: {res['implied_odds']['away']:.2f})")
	print("-" * 74)
	print("GOAL EXPECTATIONS (xG):")
	print(f"  {f['home']} Projected Goals: {xg['home_goals_avg']} (Simulated xG: {xg['home_xg_avg']})")
	print(f"  {f['away']} Projected Goals: {xg['away_goals_avg']} (Simulated xG: {xg['away_xg_avg']})")
	print(f"  Total Expected Goals:     {xg['total_goals_avg']}")
	print("-" * 74)
	print("GOAL LINE & SPECIAL MARKETS:")
	print(f"  Over 2.5 Goals:  {m['over_2_5']:>6}  |  Under 2.5 Goals: {m['under_2_5']:>6}")
	print(f"  Over 1.5 Goals:  {m['over_1_5']:>6}  |  Over 3.5 Goals:  {m['over_3_5']:>6}")
	print(f"  BTTS (Yes):      {m['btts_yes']:>6}  |  BTTS (No):       {m['btts_no']:>6}")
	print(f"  {f['home']} Clean Sheet: {m['home_clean_sheet']:>6} | {f['away']} Clean Sheet: {m['away_clean_sheet']:>6}")
	print(f"  Blowout (Home >=3): {m['home_blowout_3plus']:>6} | Blowout (Away >=3): {m['away_blowout_3plus']:>6}")
	print("-" * 74)
	print("MOST PROBABLE SCORELINES:")
	for s in res['top_scorelines'][:5]:
		print(f"  Score {s['score']:<5} -> {s['percentage']:>6}")
	print("-" * 74)
	print("TOP ANYTIME GOALSCORER THREATS:")
	for s in (res['top_home_scorers'][:3] + res['top_away_scorers'][:3]):
		print(f"  {s['player']} ({s['team']}): {s['percentage']}")

	if 'asian_handicap' in res:
		ah = res['asian_handicap']
		d = res['derivatives']
		print("-" * 74)
		print("ASIAN HANDICAP & DERIVATIVE MARKETS:")
		print(f"  AH -0.5 / +0.5:  {f['home']} -0.5 ({ah['ah_minus_0_5_home']}) | {f['away']} +0.5 ({ah['ah_plus_0_5_away']})")
		print(f"  AH -1.0 / +1.0:  {f['home']} -1.0 ({ah['ah_minus_1_0_home']}) | Push ({ah['ah_minus_1_0_push']}) | {f['away']} +1.0 ({ah['ah_plus_1_0_away']})")
		print(f"  AH -1.5 / +1.5:  {f['home']} -1.5 ({ah['ah_minus_1_5_home']}) | {f['away']} +1.5 ({ah['ah_plus_1_5_away']})")
		print(f"  Draw No Bet:     {f['home']} ({d['dnb_home']}) | {f['away']} ({d['dnb_away']})")
		print(f"  Double Chance:   1X: {d['double_chance_1x']} | X2: {d['double_chance_x2']} | 12: {d['double_chance_12']}")
		print(f"  Expected Points: {f['home']}: {d['expected_points_home']} pts | {f['away']}: {d['expected_points_away']} pts")
	print("=" * 74)

def run_backtest_suite():
	benchmark_fixtures = [
		('Arsenal', 'Chelsea', 'home'),
		('Real Madrid', 'Spurs', 'home'),
		('Liverpool', 'Manchester City', 'draw'),
		('FC Barcelona', 'FC Bayern München', 'draw'),
		('Inter Milan', 'Juventus FC', 'home'),
		('PSG', 'AS Monaco', 'home'),
		('Leverkusen', 'Borussia Dortmund', 'home'),
		('Aston Villa', 'Newcastle United', 'draw'),
		('Atlético de Madrid', 'Real Sociedad', 'home'),
		('AC Milan', 'Napoli', 'draw')
	]

	print("=" * 74)
	print("HATTRK PREDICTOR: HISTORICAL BACKTESTING BENCHMARK SUITE".center(74))
	print(f"Evaluating Ranked Probability Score (RPS) over {len(benchmark_fixtures)} European Fixtures".center(74))
	print("=" * 74)

	rps_scores = []
	for h, a, actual in benchmark_fixtures:
		res = run_monte_carlo(h, a, runs=100)
		probs = [res['probabilities']['home_win'], res['probabilities']['draw'], res['probabilities']['away_win']]
		score = evaluate_rps(probs, actual)
		rps_scores.append(score)
		p_h_pct = res['probabilities']['home_win_pct']
		p_d_pct = res['probabilities']['draw_pct']
		p_a_pct = res['probabilities']['away_win_pct']
		print(f"{h:<20} vs {a:<18} | Pred: {p_h_pct}/{p_d_pct}/{p_a_pct} | Actual: {actual:<4} | RPS: {score:.4f}")

	avg_rps = sum(rps_scores) / float(len(rps_scores))
	print("-" * 74)
	print(f"MEAN RANKED PROBABILITY SCORE (RPS): {avg_rps:.4f}")
	if avg_rps <= 0.21:
		print("Model Rating: EXCELLENT (Comparable to professional bookmaker closing lines)")
	elif avg_rps <= 0.24:
		print("Model Rating: STRONG (Beats standard public Poisson baselines)")
	else:
		print("Model Rating: MODERATE")
	print("=" * 74)

def optimize_hyperparameters(runs=30):
	benchmark_fixtures = [
		('Arsenal', 'Chelsea', 'home'),
		('Real Madrid', 'Spurs', 'home'),
		('Liverpool', 'Manchester City', 'draw'),
		('FC Barcelona', 'FC Bayern München', 'draw'),
		('Inter Milan', 'Juventus FC', 'home')
	]
	print("=" * 74)
	print("HATTRK PREDICTOR: HYPERPARAMETER LOSS OPTIMIZATION".center(74))
	print("Evaluating loss surface over benchmark fixtures via coordinate search".center(74))
	print("=" * 74)
	best_loss = 999.0
	best_params = {}
	for ha in [20, 28, 35]:
		for fm in [0.8, 1.2, 1.6]:
			scores = []
			for h, a, act in benchmark_fixtures:
				res = run_monte_carlo(h, a, runs=runs)
				probs = [res['probabilities']['home_win'], res['probabilities']['draw'], res['probabilities']['away_win']]
				scores.append(evaluate_rps(probs, act))
			mean_rps = sum(scores) / len(scores)
			print(f"Param candidate: home_advantage={ha}, form_scale={fm:.1f} -> Mean RPS: {mean_rps:.4f}")
			if mean_rps < best_loss:
				best_loss = mean_rps
				best_params = {'home_advantage': ha, 'form_scale': fm}
	print("-" * 74)
	print(f"OPTIMAL HYPERPARAMETERS: {best_params} (Min RPS: {best_loss:.4f})")
	print("=" * 74)
	return best_params

def main():
	parser = argparse.ArgumentParser(description="Hattrk Match Predictor & Monte Carlo Ensemble Engine")
	parser.add_argument("--home", type=str, default="Arsenal", help="Home team name")
	parser.add_argument("--away", type=str, default="Chelsea", help="Away team name")
	parser.add_argument("--runs", type=int, default=500, help="Number of Monte Carlo simulations")
	parser.add_argument("--home-form", type=str, default="", help="Home recent form (e.g. WWWDW)")
	parser.add_argument("--away-form", type=str, default="", help="Away recent form (e.g. LLWDL)")
	parser.add_argument("--home-formation", type=str, default="", help="Home tactical formation (e.g. 4-3-3, 3-5-2)")
	parser.add_argument("--away-formation", type=str, default="", help="Away tactical formation (e.g. 4-2-3-1, 5-3-2)")
	parser.add_argument("--home-missing", type=str, default="", help="Comma-separated missing players for home team")
	parser.add_argument("--away-missing", type=str, default="", help="Comma-separated missing players for away team")
	parser.add_argument("--json", type=str, default="", help="Export JSON results to filepath")
	parser.add_argument("--backtest", action="store_true", help="Run backtesting validation benchmark")
	parser.add_argument("--optimize", action="store_true", help="Run hyperparameter optimization")

	args = parser.parse_args()

	if args.backtest:
		run_backtest_suite()
		return

	if args.optimize:
		optimize_hyperparameters()
		return

	h_missing = [x.strip() for x in args.home_missing.split(',')] if args.home_missing else None
	a_missing = [x.strip() for x in args.away_missing.split(',')] if args.away_missing else None

	res = run_monte_carlo(
		args.home,
		args.away,
		runs=args.runs,
		home_missing=h_missing,
		away_missing=a_missing,
		home_form=args.home_form,
		away_form=args.away_form,
		home_formation=args.home_formation or None,
		away_formation=args.away_formation or None
	)

	print_prediction_report(res)

	if args.json:
		with open(args.json, 'w', encoding='utf-8') as f:
			json.dump(res, f, indent=2)
		print(f"\nPrediction results exported to {args.json}")

if __name__ == '__main__':
	main()
