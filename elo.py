import math

CLUB_ELO = {
	'Real Madrid': 2030,
	'Manchester City': 2025,
	'Arsenal': 1990,
	'Liverpool': 1995,
	'FC Barcelona': 1980,
	'FC Bayern München': 1975,
	'Inter Milan': 1965,
	'Paris Saint-Germain': 1940,
	'Bayer 04 Leverkusen': 1935,
	'Atlético de Madrid': 1910,
	'Chelsea': 1890,
	'Juventus FC': 1885,
	'Spurs': 1870,
	'Borussia Dortmund': 1875,
	'AC Milan': 1860,
	'Aston Villa': 1855,
	'Newcastle United': 1850,
	'Atalanta': 1845,
	'Sporting CP': 1840,
	'SL Benfica': 1835,
	'Manchester United': 1830,
	'Napoli': 1825,
	'AS Monaco': 1820,
	'RB Leipzig': 1815,
	'Lazio': 1810,
	'Roma': 1805,
	'Athletic Club': 1800,
	'Real Sociedad': 1795,
	'Eintracht Frankfurt': 1790,
	'Brighton & Hove Albion': 1785,
	'West Ham United': 1775,
	'Villarreal CF': 1780,
	'AFC Bournemouth': 1740,
	'Fulham': 1745,
	'Everton': 1730,
	'Brentford': 1735,
	'Crystal Palace': 1730,
	'Wolverhampton Wanderers': 1720,
	'Nottingham Forest': 1725,
	'Leicester City': 1710,
	'Ipswich Town': 1680,
	'Southampton': 1675
}

def get_club_elo(club_name, team_obj=None):
	clean_name = str(club_name).strip()
	if clean_name in CLUB_ELO:
		return CLUB_ELO[clean_name]

	for k, v in CLUB_ELO.items():
		if k.lower() == clean_name.lower():
			return v
		if k.lower() in clean_name.lower() or clean_name.lower() in k.lower():
			return v

	if team_obj and hasattr(team_obj, 'xi') and team_obj.xi:
		ovrs = [p.overall for p in team_obj.xi]
		avg_ovr = sum(ovrs) / float(len(ovrs))
		return int(1200 + (avg_ovr - 65.0) * 35.0)

	return 1700

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

