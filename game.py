import random, os, sys, csv, unicodedata
from engine import fixture, team, player, pos_order, pos_to_role, listshow, STADIUM_MAP, get_stadium
from tactics import FORMATIONS, calculate_player_familiarity, calculate_team_fluidity, load_club_tactics

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except Exception:
		pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, 'data', 'database.csv')
if not os.path.exists(DATABASE_FILE):
	DATABASE_FILE = 'data/database.csv'

_CACHED_CLUBS = None
_CACHED_LEAGUES = {}

CLUB_NAME_REPLACEMENTS = {
	'Lombardia FC': 'Inter Milan',
	'Milano FC': 'AC Milan',
	'Bergamo Calcio': 'Atalanta BC',
}

POPULAR_CLUBS = [
	'Real Madrid', 'Manchester City', 'Liverpool', 'FC Barcelona',
	'Arsenal', 'FC Bayern München', 'PSG', 'Chelsea',
	'Man Utd', 'Inter Milan', 'AC Milan', 'Juventus FC',
	'Borussia Dortmund', 'Atlético de Madrid', 'Atalanta BC', 'Spurs',
	'Real Madrid F', 'FC Barcelona F', 'Chelsea Women', 'Arsenal Women'
]

def _strip_accents(text):
	return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

CLUB_ALIASES = {
	'man city': 'Manchester City',
	'city': 'Manchester City',
	'mancity': 'Manchester City',
	'man united': 'Man Utd',
	'united': 'Man Utd',
	'man utd': 'Man Utd',
	'manutd': 'Man Utd',
	'barca': 'FC Barcelona',
	'barcelona': 'FC Barcelona',
	'madrid': 'Real Madrid',
	'real': 'Real Madrid',
	'bayern': 'FC Bayern München',
	'bayern munich': 'FC Bayern München',
	'munchen': 'FC Bayern München',
	'atletico': 'Atlético de Madrid',
	'atleti': 'Atlético de Madrid',
	'atletico madrid': 'Atlético de Madrid',
	'psg': 'PSG',
	'paris': 'PSG',
	'paris saint-germain': 'PSG',
	'paris sg': 'PSG',
	'tottenham': 'Spurs',
	'spurs': 'Spurs',
	'inter': 'Inter Milan',
	'inter milan': 'Inter Milan',
	'lombardia': 'Inter Milan',
	'lombardia fc': 'Inter Milan',
	'milan': 'AC Milan',
	'ac milan': 'AC Milan',
	'milano': 'AC Milan',
	'milano fc': 'AC Milan',
	'atalanta': 'Atalanta BC',
	'atalanta bc': 'Atalanta BC',
	'bergamo': 'Atalanta BC',
	'bergamo calcio': 'Atalanta BC',
	'inter miami': 'Inter Miami CF',
	'miami': 'Inter Miami CF',
	'juve': 'Juventus FC',
	'juventus': 'Juventus FC',
	'dortmund': 'Borussia Dortmund',
	'bvb': 'Borussia Dortmund',
	'leverkusen': 'Leverkusen',
	'bayer leverkusen': 'Leverkusen',
	'bayer 04 leverkusen': 'Leverkusen',
	'bayer 04': 'Leverkusen',
	'arsenal': 'Arsenal',
	'liverpool': 'Liverpool',
	'chelsea': 'Chelsea',
	'sporting': 'Sporting CP',
	'benfica': 'SL Benfica',
	'porto': 'FC Porto',
	'real madrid f': 'Real Madrid F',
	'real f': 'Real Madrid F',
	'madrid f': 'Real Madrid F',
	'barca f': 'FC Barcelona F',
	'barcelona f': 'FC Barcelona F',
	'atletico f': 'Atlético de Madrid F',
	'atleti f': 'Atlético de Madrid F',
	'chelsea women': 'Chelsea Women',
	'chelsea w': 'Chelsea Women',
	'chelsea f': 'Chelsea Women',
	'arsenal women': 'Arsenal Women',
	'arsenal w': 'Arsenal Women',
	'arsenal f': 'Arsenal Women',
	'man city women': 'Manchester City Women',
	'man city w': 'Manchester City Women',
	'man city f': 'Manchester City Women',
	'city women': 'Manchester City Women',
	'liverpool women': 'Liverpool Women',
	'liverpool w': 'Liverpool Women',
	'liverpool f': 'Liverpool Women',
	'man utd women': 'Man Utd Women',
	'man united women': 'Man Utd Women',
	'bayern women': 'FC Bayern München Frauen',
	'bayern frauen': 'FC Bayern München Frauen',
	'bayern f': 'FC Bayern München Frauen',
	'psg women': 'PSG Féminine',
	'psg f': 'PSG Féminine',
	'juve women': 'Juventus FC Women',
	'juventus women': 'Juventus FC Women',
	'juve f': 'Juventus FC Women',
	'juventus f': 'Juventus FC Women',
	'roma women': 'AS Roma Women',
	'roma f': 'AS Roma Women',
	'wolfsburg': 'VfL Wolfsburg Frauen',
	'wolfsburg women': 'VfL Wolfsburg Frauen',
	'wolfsburg frauen': 'VfL Wolfsburg Frauen',
	'lyon': 'OL Féminin',
	'lyon women': 'OL Féminin',
	'thorns': 'Portland Thorns',
	'portland thorns': 'Portland Thorns',
	'pride': 'Orlando Pride',
	'orlando pride': 'Orlando Pride',
	'reign': 'Seattle Reign',
	'seattle reign': 'Seattle Reign',
	'gotham': 'Gotham FC',
	'gotham fc': 'Gotham FC',
	'san diego wave': 'San Diego Wave',
	'wave': 'San Diego Wave',
	'icon f': 'ICON F',
	'icon women': 'ICON F',
}

def card_selection_score(rarity_str, overall_val):
	r = str(rarity_str).strip().lower()
	try:
		ovr = float(overall_val)
	except (ValueError, TypeError):
		ovr = 60.0

	if r in ['base icon', 'base hero', 'rare', 'base hall of fut', 'common']:
		tier = 1000
	elif 'debut' in r and 'icon' in r:
		tier = 500
	elif 'totw' in r or 'week' in r:
		tier = 400
	elif 'potm' in r:
		tier = 350
	else:
		tier = 300

	return (tier, ovr)

def load_clubs(filepath=None, min_players=11):
	global _CACHED_CLUBS, _CACHED_LEAGUES
	if _CACHED_CLUBS is not None and filepath is None:
		return _CACHED_CLUBS

	if filepath is None:
		filepath = DATABASE_FILE
	if not os.path.exists(filepath):
		alt_path = os.path.join(BASE_DIR, 'data', 'database.csv')
		if os.path.exists(alt_path):
			filepath = alt_path

	clubs = {}
	leagues = {}
	if not os.path.exists(filepath):
		return clubs

	with open(filepath, 'r', encoding='utf-8-sig') as f:
		reader = csv.DictReader(f)
		for row in reader:
			club_name = row.get('club', '').strip()
			if not club_name or club_name in ['—']:
				continue
			club_name = CLUB_NAME_REPLACEMENTS.get(club_name, club_name)

			pname = row.get('player_name', '').strip() or row.get('full_name', '').strip()
			if not pname:
				continue

			try:
				ovr = float(row.get('overall', 60.0))
			except (ValueError, TypeError):
				ovr = 60.0

			if club_name not in clubs:
				clubs[club_name] = {}
				leagues[club_name] = row.get('league', '').strip()

			score = card_selection_score(row.get('rarity', ''), ovr)
			if pname not in clubs[club_name] or score > getattr(clubs[club_name][pname], '_card_score', (0, 0)):
				p = player(row)
				p._card_score = score
				p.club = club_name
				p.team = club_name
				clubs[club_name][pname] = p

	result = {}
	for c_name, p_dict in clubs.items():
		squad = list(p_dict.values())
		if len(squad) >= min_players or c_name in POPULAR_CLUBS:
			squad.sort(key=lambda p: p.overall, reverse=True)
			result[c_name] = squad

	if filepath == DATABASE_FILE or filepath == os.path.join(BASE_DIR, 'data', 'database.csv'):
		_CACHED_CLUBS = result
		_CACHED_LEAGUES = leagues

	return result

def get_all_club_names():
	clubs = load_clubs()
	return sorted(list(clubs.keys()))

def find_club(query):
	clubs = load_clubs()
	q = query.strip().lower()
	if not q:
		return None

	if q in CLUB_ALIASES and CLUB_ALIASES[q] in clubs:
		return CLUB_ALIASES[q]

	for c in clubs:
		if c.lower() == q:
			return c

	q_clean = _strip_accents(q)

	for c in clubs:
		if _strip_accents(c) == q_clean:
			return c

	for c in clubs:
		if _strip_accents(c).startswith(q_clean):
			return c

	matches = [c for c in clubs if q_clean in _strip_accents(c)]
	if len(matches) == 1:
		return matches[0]
	elif len(matches) > 1:
		for pop in POPULAR_CLUBS:
			if pop in matches:
				return pop
		return matches[0]

	return None

def playerwrite(p):
	return "[{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]".format(
		p.name, p.team, p.primary_position, p.overall,
		p.face_pace, p.face_shooting, p.face_passing,
		p.face_dribbling, p.face_defending, p.face_physicality,
		p.capt, getattr(p, 'gender', 'Male')
	)

def playermake(raw_line, t):
	line = raw_line.strip()
	if line.startswith('[') and line.endswith(']'):
		line = line[1:-1]
	parts = [x.strip() for x in line.split(',')]

	p = player()
	p.name = parts[0].strip('"').strip("'")
	p.short_name = p.name
	p.team = t.name if hasattr(t, 'name') else str(t)
	p.club = p.team

	if len(parts) >= 11:
		p.primary_position = parts[2].strip('"').strip("'")
		p.position = pos_to_role(p.primary_position)
		p.overall = float(parts[3])
		p.face_pace = float(parts[4])
		p.face_shooting = float(parts[5])
		p.face_passing = float(parts[6])
		p.face_dribbling = float(parts[7])
		p.face_defending = float(parts[8])
		p.face_physicality = float(parts[9])
		p.capt = int(parts[10])
		if len(parts) >= 12:
			p.gender = parts[11].strip('"').strip("'")
		else:
			p.gender = 'Male'
		p.pace = p.face_pace
		p.finishing = p.face_shooting
		p.short_passing = p.face_passing
		p.def_awareness = p.face_defending
		p.standing_tackle = p.face_defending
		p.attack = p.face_shooting * 0.5 + p.face_passing * 0.3 + p.face_pace * 0.2
		p.defense = p.face_defending * 0.7 + p.face_physicality * 0.3
	elif len(parts) >= 7:
		p.attack = float(parts[1])
		p.defense = float(parts[2])
		p.pace = float(parts[3])
		p.stamina = float(parts[4])
		p.position = parts[5].strip('"').strip("'")
		p.primary_position = p.position
		p.capt = int(parts[6])
		p.overall = (p.attack + p.defense) / 2.0
		p.face_pace = p.pace
		p.face_shooting = p.attack
		p.face_passing = p.attack * 0.8
		p.face_dribbling = p.attack * 0.9
		p.face_defending = p.defense
		p.face_physicality = p.defense * 0.9

	p.fitness = 1.0
	p.inns = []
	return p

def showteam(t):
	capt = getattr(t, 'gamecapt', '')
	formation = getattr(t, 'formation', '4-3-3')
	print('\n{} Starting XI ({})'.format(t.name, formation))
	print('=' * 84)
	print(' #  Pos Player Name            OVR  PAC/DIV SHO/HAN PAS/KIC DRI/REF DEF/SPD PHY/POS')
	print('-' * 84)
	for i, p in enumerate(t.xi, 1):
		c = ' (C)' if p == capt else ''
		pos_tag = getattr(p, 'assigned_slot', getattr(p, 'primary_position', p.position)).center(3)
		disp_name = getattr(p, 'short_name', '') or p.name
		name_str = (disp_name + c)[:24].ljust(24)
		print('{:>2}. [{}] {} {:>3.0f}    {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}'.format(
			i, pos_tag, name_str, p.overall,
			p.face_pace, p.face_shooting, p.face_passing,
			p.face_dribbling, p.face_defending, p.face_physicality
		))
	if hasattr(t, 'bench') and t.bench:
		print('-' * 84)
		print('Substitutes (Bench):')
		for i, p in enumerate(t.bench, 1):
			pos_tag = getattr(p, 'primary_position', p.position).center(3)
			disp_name = getattr(p, 'short_name', '') or p.name
			name_str = disp_name[:24].ljust(24)
			print(' S{:>1}. [{}] {} {:>3.0f}    {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}     {:>3.0f}'.format(
				i, pos_tag, name_str, p.overall,
				p.face_pace, p.face_shooting, p.face_passing,
				p.face_dribbling, p.face_defending, p.face_physicality
			))
	print('=' * 84)

def value(p, role):
	if role == 'GK':
		diving = getattr(p, 'gk_diving', p.overall)
		reflexes = getattr(p, 'gk_reflexes', getattr(p, 'gk_reactions', p.overall))
		positioning = getattr(p, 'gk_positioning', p.overall)
		handling = getattr(p, 'gk_handling', p.overall)
		val = p.gk_overall * 1.0 + diving * 0.3 + reflexes * 0.3 + positioning * 0.2 + handling * 0.2
		if p.position == 'GK' or p.primary_position == 'GK':
			val += 150
		else:
			val -= 200
	elif role == 'DEF':
		val = p.def_awareness * 0.35 + p.standing_tackle * 0.30 + p.strength * 0.20 + p.pace * 0.15
		if p.position == 'DEF': val += 30
		elif p.position == 'DMF': val += 15
	elif role == 'DMF':
		val = p.interceptions * 0.35 + p.standing_tackle * 0.25 + p.short_passing * 0.25 + p.strength * 0.15
		if p.primary_position == 'CDM' or p.position == 'DMF': val += 30
		elif p.position in ['DEF', 'MID']: val += 10
	elif role == 'MID':
		val = p.short_passing * 0.35 + p.vision * 0.30 + p.ball_control * 0.20 + p.pace * 0.15
		if p.position == 'MID': val += 30
		elif p.position in ['DMF', 'AMF']: val += 15
	elif role == 'AMF':
		val = p.vision * 0.35 + p.dribbling_stat * 0.25 + p.short_passing * 0.25 + p.shooting * 0.15
		if p.primary_position == 'CAM' or p.position == 'AMF': val += 30
		elif p.position in ['MID', 'ATT']: val += 15
	elif role == 'ATT':
		val = p.finishing * 0.40 + p.positioning * 0.25 + p.pace * 0.20 + p.shot_power * 0.15
		if p.position == 'ATT': val += 30
		elif p.position == 'AMF': val += 15
	else:
		val = p.overall

	return val + 3.0 * random.random()

def firstxi(team_obj, formation=None):
	if len(team_obj.squad) > 0:
		pool = list(team_obj.squad)
	elif len(team_obj.active) > 0:
		pool = list(team_obj.active)
	else:
		pool = list(team_obj.players)

	t_name = getattr(team_obj, 'name', '') or str(team_obj)
	if not formation:
		formation = getattr(team_obj, 'formation', None) or load_club_tactics(t_name).get('formation', '4-3-3')

	if formation not in FORMATIONS:
		formation = '4-3-3'

	slots = FORMATIONS[formation]
	xi = []

	for slot in slots:
		if not pool:
			break

		def _candidate_score(cand):
			fam = calculate_player_familiarity(cand, slot)
			if slot == 'GK':
				attr = getattr(cand, 'gk_overall', cand.overall)
			elif slot == 'CB':
				attr = cand.def_awareness * 0.40 + cand.standing_tackle * 0.35 + cand.overall * 0.25
			elif slot in ['LB', 'RB', 'LWB', 'RWB']:
				attr = cand.pace * 0.30 + cand.def_awareness * 0.25 + cand.crossing * 0.25 + cand.overall * 0.20
			elif slot in ['CDM']:
				attr = cand.interceptions * 0.35 + cand.standing_tackle * 0.35 + cand.overall * 0.30
			elif slot in ['CM']:
				attr = cand.short_passing * 0.35 + cand.vision * 0.30 + cand.overall * 0.35
			elif slot in ['CAM']:
				attr = cand.vision * 0.35 + cand.short_passing * 0.30 + cand.dribbling_stat * 0.35
			elif slot in ['LM', 'RM', 'LW', 'RW']:
				attr = cand.pace * 0.35 + cand.crossing * 0.30 + cand.dribbling_stat * 0.35
			elif slot in ['ST', 'CF']:
				attr = cand.finishing * 0.45 + cand.positioning * 0.35 + cand.shot_power * 0.20
			else:
				attr = cand.overall

			return (attr * (fam ** 1.3)) + 3.0 * random.random()

		best_p = max(pool, key=_candidate_score)
		best_p.assigned_slot = slot
		best_p.position_familiarity = calculate_player_familiarity(best_p, slot)
		best_p.effective_overall = round(best_p.overall * best_p.position_familiarity, 1)
		xi.append(best_p)
		pool.remove(best_p)

	pool.sort(key=lambda p: (p.overall + 3.0 * random.random()) if p.position != 'GK' else -100, reverse=True)
	while len(xi) < 11 and len(pool) > 0:
		extra_p = pool.pop(0)
		extra_p.assigned_slot = getattr(extra_p, 'primary_position', extra_p.position)
		extra_p.position_familiarity = 0.65
		extra_p.effective_overall = round(extra_p.overall * 0.65, 1)
		xi.append(extra_p)

	team_obj.formation = formation
	team_obj.fluidity = calculate_team_fluidity(team_obj)
	xi.sort(key=lambda p: pos_order(getattr(p, 'primary_position', p.position)))
	return xi

def pick_bench(team_obj, xi, count=5):
	if len(team_obj.squad) > 0:
		pool = [p for p in team_obj.squad if p not in xi]
	elif len(team_obj.active) > 0:
		pool = [p for p in team_obj.active if p not in xi]
	else:
		pool = [p for p in getattr(team_obj, 'players', []) if p not in xi]

	bench = []

	gks = [p for p in pool if (p.position == 'GK' or p.primary_position == 'GK') and p not in bench]
	if gks:
		best_gk = max(gks, key=lambda p: p.overall)
		bench.append(best_gk)

	defs = [p for p in pool if p.position == 'DEF' and p not in bench]
	if defs:
		best_def = max(defs, key=lambda p: p.overall)
		bench.append(best_def)

	mids = [p for p in pool if p.position in ['MID', 'DMF', 'AMF'] and p not in bench]
	mids.sort(key=lambda p: p.overall, reverse=True)
	for m in mids[:2]:
		bench.append(m)

	atts = [p for p in pool if p.position in ['ATT', 'AMF'] and p not in bench]
	if atts:
		best_att = max(atts, key=lambda p: p.overall)
		bench.append(best_att)

	remaining = [p for p in pool if p not in bench]
	remaining.sort(key=lambda p: p.overall, reverse=True)
	while len(bench) < count and remaining:
		bench.append(remaining.pop(0))

	bench.sort(key=lambda p: pos_order(getattr(p, 'primary_position', p.position)))
	return bench

def setup(home_name, away_name, savecard=None):
	clubs = load_clubs()

	matched_home = find_club(home_name) or home_name
	matched_away = find_club(away_name) or away_name

	t = fixture()
	if savecard is not None:
		t.savecard = bool(savecard)
	t.home = team()
	t.home.name = matched_home
	t.home.active = list(clubs.get(matched_home, []))
	t.home.squad = list(t.home.active)
	t.home.players = list(t.home.active)
	t.home.league = _CACHED_LEAGUES.get(matched_home, '')

	t.away = team()
	t.away.name = matched_away
	t.away.active = list(clubs.get(matched_away, []))
	t.away.squad = list(t.away.active)
	t.away.players = list(t.away.active)
	t.away.league = _CACHED_LEAGUES.get(matched_away, '')

	t.home.formation = load_club_tactics(matched_home).get('formation', '4-3-3')
	t.away.formation = load_club_tactics(matched_away).get('formation', '4-3-3')
	t.venue = get_stadium(matched_home)
	return t

def game(fixture_obj, savecard=None):
	if savecard is not None:
		fixture_obj.savecard = bool(savecard)
	for i in [fixture_obj.home, fixture_obj.away]:
		if not getattr(i, 'formation', None):
			i.formation = load_club_tactics(i.name).get('formation', '4-3-3')
		if len(i.active) != 11:
			i.xi = firstxi(i, i.formation)
		else:
			i.xi = list(i.active)
			i.xi.sort(key=lambda p: pos_order(getattr(p, 'primary_position', p.position)))
			for p in i.xi:
				if not hasattr(p, 'position_familiarity'):
					p.position_familiarity = 1.0
					p.effective_overall = p.overall

		i.starters = list(i.xi)
		i.fluidity = calculate_team_fluidity(i)
		i.bench = pick_bench(i, i.xi, count=5)
		i.subs_used = []

		capts = [x for x in i.xi if x.capt == max([y.capt for y in i.xi])]
		i.gamecapt = capts[0] if capts else i.xi[0]
		showteam(i)
		print()

	fixture_obj.football()
	return fixture_obj
