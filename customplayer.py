import pickle, sys, os, copy, unicodedata
from engine import player, pos_to_role
from game import load_clubs, POPULAR_CLUBS, find_club

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except Exception:
		pass

VALID_POSITIONS = [
	'GK', 'CB', 'LB', 'RB', 'LWB', 'RWB',
	'CDM', 'CM', 'CAM', 'LM', 'RM',
	'LW', 'RW', 'CF', 'ST',
	'DEF', 'DMF', 'MID', 'AMF', 'ATT'
]

CLUBS = POPULAR_CLUBS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYERS_FILE = os.path.join(BASE_DIR, 'players')
if not os.path.exists(PLAYERS_FILE) and os.path.exists('players'):
	PLAYERS_FILE = 'players'

def _strip_accents(text):
	return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

def load_players():
	if os.path.exists(PLAYERS_FILE):
		try:
			with open(PLAYERS_FILE, 'rb') as f:
				return pickle.load(f)
		except Exception as e:
			print('Error loading players database: {}'.format(e))
			sys.exit(1)

	clubs = load_clubs()
	all_players = []
	for team_name, p_list in clubs.items():
		all_players.extend(p_list)

	try:
		with open(PLAYERS_FILE, 'wb') as f:
			pickle.dump(all_players, f)
	except Exception:
		pass
	return all_players

def save_players(players):
	backup_file = PLAYERS_FILE + '.bak'
	if os.path.exists(PLAYERS_FILE):
		try:
			with open(PLAYERS_FILE, 'rb') as f:
				backup_data = f.read()
			with open(backup_file, 'wb') as f:
				f.write(backup_data)
		except Exception:
			pass

	with open(PLAYERS_FILE, 'wb') as f:
		pickle.dump(players, f)
	print('  Saved {} players to database (backup at {}).'.format(len(players), backup_file))

def get_str(prompt, required=True, default=None):
	while True:
		suffix = ' [{}]'.format(default) if default else ''
		val = input('{}{}: '.format(prompt, suffix)).strip()
		if val == '' and default is not None:
			return default
		if val == '' and required:
			print('  Cannot be empty.')
			continue
		return val

def get_int(prompt, lo=None, hi=None, default=None):
	while True:
		suffix = ' [{}]'.format(default) if default is not None else ''
		val_str = input('{}{}: '.format(prompt, suffix)).strip()
		if val_str == '' and default is not None:
			return default
		try:
			val = int(val_str)
		except ValueError:
			print('  Please enter an integer.')
			continue
		if lo is not None and val < lo:
			print('  Must be >= {}'.format(lo))
			continue
		if hi is not None and val > hi:
			print('  Must be <= {}'.format(hi))
			continue
		return val

def get_float(prompt, lo=None, hi=None, default=None):
	while True:
		suffix = ' [{}]'.format(default) if default is not None else ''
		val_str = input('{}{}: '.format(prompt, suffix)).strip()
		if val_str == '' and default is not None:
			return default
		try:
			val = float(val_str)
		except ValueError:
			print('  Please enter a number.')
			continue
		if lo is not None and val < lo:
			print('  Must be >= {}'.format(lo))
			continue
		if hi is not None and val > hi:
			print('  Must be <= {}'.format(hi))
			continue
		return val

def make_fresh_player():
	p = player()
	p.name = ''
	p.team = ''
	p.club = ''
	p.gender = 'Male'
	p.position = 'MID'
	p.primary_position = 'CM'
	p.overall = 75.0
	p.face_pace = 70.0
	p.face_shooting = 65.0
	p.face_passing = 70.0
	p.face_dribbling = 70.0
	p.face_defending = 60.0
	p.face_physicality = 65.0
	p.pace = 70.0
	p.shooting = 65.0
	p.passing = 70.0
	p.dribbling = 70.0
	p.defending = 60.0
	p.physicality = 65.0
	p.attack = 65.0
	p.defense = 60.0
	p.finishing = 65.0
	p.shot_power = 65.0
	p.long_shots = 65.0
	p.vision = 70.0
	p.short_passing = 70.0
	p.long_passing = 70.0
	p.crossing = 65.0
	p.dribbling_stat = 70.0
	p.ball_control = 70.0
	p.agility = 70.0
	p.def_awareness = 60.0
	p.standing_tackle = 60.0
	p.sliding_tackle = 60.0
	p.interceptions = 60.0
	p.strength = 65.0
	p.stamina_stat = 70.0
	p.aggression = 60.0
	p.acceleration = 70.0
	p.sprint_speed = 70.0
	p.positioning = 65.0
	p.heading = 60.0
	p.gk_overall = 70.0
	p.gk_reactions = 70.0
	p.gk_positioning = 70.0
	p.playstyles = set()
	p.playstyles_plus = []
	p.playstyles_base = []
	p.stamina = 1.0
	p.capt = 0
	p.games = 0
	p.goals = 0
	p.assists = 0
	p.clean_sheets = 0
	p.motm = 0
	p.match_goals = 0
	p.match_assists = 0
	p.fitness = 1.0
	p.inns = []
	return p

def sync_player_stats(p):
	p.short_name = getattr(p, 'short_name', '') or p.name
	p.position = pos_to_role(getattr(p, 'primary_position', p.position))
	p.pace = getattr(p, 'face_pace', 70.0)
	p.shooting = getattr(p, 'face_shooting', 65.0)
	p.passing = getattr(p, 'face_passing', 70.0)
	p.dribbling = getattr(p, 'face_dribbling', 70.0)
	p.defending = getattr(p, 'face_defending', 60.0)
	p.physicality = getattr(p, 'face_physicality', 65.0)

	p.finishing = p.shooting
	p.shot_power = p.shooting
	p.long_shots = p.shooting
	p.vision = p.passing
	p.short_passing = p.passing
	p.long_passing = p.passing
	p.crossing = p.passing
	p.dribbling_stat = p.dribbling
	p.ball_control = p.dribbling
	p.agility = p.dribbling
	p.def_awareness = p.defending
	p.standing_tackle = p.defending
	p.sliding_tackle = p.defending
	p.interceptions = p.defending
	p.strength = p.physicality
	p.stamina_stat = p.physicality
	p.aggression = p.physicality
	p.acceleration = p.pace
	p.sprint_speed = p.pace
	p.positioning = p.shooting if p.position in ['ATT', 'AMF'] else p.passing
	p.heading = p.defending * 0.5 + p.physicality * 0.5
	p.attack = p.shooting * 0.5 + p.passing * 0.3 + p.pace * 0.2
	p.defense = p.defending * 0.7 + p.physicality * 0.3

	if p.position == 'GK':
		p.gk_overall = p.overall
		p.gk_reactions = p.overall
		p.gk_positioning = p.overall

def print_player(p, verbose=False):
	pos_str = getattr(p, 'primary_position', p.position)
	gen_tag = getattr(p, 'gender', 'Male')[0]
	print('  {:<22} {:<24} [{:<3}] [{}] OVR:{:<2.0f} PAC:{:<2.0f} SHO:{:<2.0f} PAS:{:<2.0f} DRI:{:<2.0f} DEF:{:<2.0f} PHY:{:<2.0f} Capt:{}'.format(
		p.name, p.team or p.club, pos_str, gen_tag, p.overall,
		getattr(p, 'face_pace', 60.0), getattr(p, 'face_shooting', 60.0),
		getattr(p, 'face_passing', 60.0), getattr(p, 'face_dribbling', 60.0),
		getattr(p, 'face_defending', 60.0), getattr(p, 'face_physicality', 60.0),
		p.capt
	))
	if verbose:
		print('    Detailed: Finishing={:.0f}, Vision={:.0f}, DefAwareness={:.0f}, Stamina={:.0f}'.format(
			getattr(p, 'finishing', 60.0), getattr(p, 'vision', 60.0),
			getattr(p, 'def_awareness', 60.0), getattr(p, 'stamina_stat', 60.0)
		))
		if getattr(p, 'playstyles', None):
			print('    Playstyles: {}'.format(', '.join(sorted(list(p.playstyles)))))
		print('    Career: {} games, {} goals, {} assists, {} clean sheets, {} MOTM'.format(
			p.games, p.goals, p.assists, p.clean_sheets, p.motm
		))

def add_player(players):
	print('\n-- Add Player to Database --')
	print('  1. Create a custom player from scratch')
	print('  2. Duplicate / import an existing player card from database')
	mode = get_str('Choice (1 or 2)', default='1')

	if mode == '2':
		query = get_str('Search player to duplicate').lower()
		q_clean = _strip_accents(query)
		matches = [p for p in players if q_clean in _strip_accents(p.name) or q_clean in _strip_accents(getattr(p, 'short_name', ''))]
		if not matches:
			print('  No players found matching "{}".'.format(query))
			return False
		matches.sort(key=lambda p: p.overall, reverse=True)
		top_matches = matches[:10]
		print('\nSelect player to duplicate:')
		for i, m in enumerate(top_matches, 1):
			print('  {:>2}.'.format(i), end=' ')
			print_player(m)
		idx = get_int('Enter number (0 to cancel)', lo=0, hi=len(top_matches), default=0)
		if idx == 0:
			return False

		chosen = top_matches[idx - 1]
		p = copy.deepcopy(chosen)
		p.name = get_str('Player name', default=p.name)
		p.team = get_str('Club / Team', default=p.team or p.club)
		p.club = p.team
		p.capt = get_int('Captaincy score (0-20)', lo=0, hi=20, default=p.capt)
		p.inns = []
		p.fitness = 1.0
		players.append(p)
		print('  Added: {} to {}'.format(p.name, p.team))
		return True

	p = make_fresh_player()
	p.name = get_str('Player Name')
	p.gender = get_str('Gender (Male/Female)', default='Male')
	print('  Clubs hint: {}'.format(', '.join(CLUBS[:8])))
	p.team = get_str('Team / Club', default=CLUBS[0])
	p.club = p.team

	print('  Positions: {}'.format(', '.join(VALID_POSITIONS)))
	while True:
		pos = get_str('Primary Position', default='CM').upper()
		if pos in VALID_POSITIONS:
			p.primary_position = pos
			p.position = pos_to_role(pos)
			break
		print('  Invalid position. Must be one of {}'.format(VALID_POSITIONS))

	p.overall = get_float('Overall rating (40-99)', lo=40, hi=99, default=75.0)
	p.face_pace = get_float('Pace [PAC] (20-99)', lo=20, hi=99, default=70.0)
	p.face_shooting = get_float('Shooting [SHO] (20-99)', lo=20, hi=99, default=65.0)
	p.face_passing = get_float('Passing [PAS] (20-99)', lo=20, hi=99, default=70.0)
	p.face_dribbling = get_float('Dribbling [DRI] (20-99)', lo=20, hi=99, default=70.0)
	p.face_defending = get_float('Defending [DEF] (20-99)', lo=20, hi=99, default=60.0)
	p.face_physicality = get_float('Physicality [PHY] (20-99)', lo=20, hi=99, default=65.0)
	p.capt = get_int('Captaincy score (0-20)', lo=0, hi=20, default=0)

	sync_player_stats(p)
	players.append(p)
	print('  Added: {} [{}] (OVR:{:.0f}) to {}'.format(p.name, p.primary_position, p.overall, p.team))
	return True

def search_players(players, query=None):
	if query is None:
		query = get_str('Search by name or team').lower()
	q_clean = _strip_accents(query)
	results = [p for p in players if q_clean in _strip_accents(p.name) or q_clean in _strip_accents(p.team or p.club)]
	if not results:
		print('  No players found.')
		return []
	results.sort(key=lambda p: p.overall, reverse=True)
	if len(results) > 15:
		print('\n  Showing top 15 of {} result(s) (sorted by OVR):'.format(len(results)))
		display = results[:15]
	else:
		print('\n  {} result(s):'.format(len(results)))
		display = results
	for i, p in enumerate(display, 1):
		print('  {:>3}.'.format(i), end=' ')
		print_player(p)
	return display

def edit_player(players):
	results = search_players(players)
	if not results:
		return False

	idx = get_int('Number to edit (0 to cancel)', lo=0, hi=len(results), default=0)
	if idx == 0:
		return False

	p = results[idx - 1]
	print('\nEditing: {} ({})'.format(p.name, p.team or p.club))
	print('Editable fields: name, team, position, gender, overall, pace, shooting, passing, dribbling, defending, physicality, capt')

	field = get_str('Field to edit').lower()

	changed = True
	if field == 'name':
		p.name = get_str('New name', default=p.name)
	elif field == 'gender':
		p.gender = get_str('New gender (Male/Female)', default=getattr(p, 'gender', 'Male'))
	elif field in ['team', 'club']:
		p.team = get_str('New team', default=p.team or p.club)
		p.club = p.team
	elif field == 'position':
		print('  Positions: {}'.format(', '.join(VALID_POSITIONS)))
		pos = get_str('New position', default=getattr(p, 'primary_position', p.position)).upper()
		if pos in VALID_POSITIONS:
			p.primary_position = pos
			p.position = pos_to_role(pos)
			sync_player_stats(p)
		else:
			print('  Invalid position - keeping current.')
			changed = False
	elif field in ['overall', 'ovr']:
		p.overall = get_float('New overall (40-99)', lo=40, hi=99, default=p.overall)
	elif field in ['pace', 'pac']:
		p.face_pace = get_float('New pace (20-99)', lo=20, hi=99, default=getattr(p, 'face_pace', 70.0))
		sync_player_stats(p)
	elif field in ['shooting', 'sho']:
		p.face_shooting = get_float('New shooting (20-99)', lo=20, hi=99, default=getattr(p, 'face_shooting', 65.0))
		sync_player_stats(p)
	elif field in ['passing', 'pas']:
		p.face_passing = get_float('New passing (20-99)', lo=20, hi=99, default=getattr(p, 'face_passing', 70.0))
		sync_player_stats(p)
	elif field in ['dribbling', 'dri']:
		p.face_dribbling = get_float('New dribbling (20-99)', lo=20, hi=99, default=getattr(p, 'face_dribbling', 70.0))
		sync_player_stats(p)
	elif field in ['defending', 'def']:
		p.face_defending = get_float('New defending (20-99)', lo=20, hi=99, default=getattr(p, 'face_defending', 60.0))
		sync_player_stats(p)
	elif field in ['physicality', 'phy']:
		p.face_physicality = get_float('New physicality (20-99)', lo=20, hi=99, default=getattr(p, 'face_physicality', 65.0))
		sync_player_stats(p)
	elif field == 'capt':
		p.capt = get_int('New captaincy score (0-20)', lo=0, hi=20, default=p.capt)
	else:
		print('  Unknown field - no changes made.')
		changed = False

	if changed:
		print('  Updated {}.'.format(p.name))
	return changed

def delete_player(players):
	results = search_players(players)
	if not results:
		return False

	idx = get_int('Number to delete (0 to cancel)', lo=0, hi=len(results), default=0)
	if idx == 0:
		return False

	p = results[idx - 1]
	print_player(p, verbose=True)
	confirm = get_str('Delete {}? This cannot be undone. (y/n)'.format(p.name), default='n').lower()
	if confirm == 'y':
		players.remove(p)
		print('  Deleted {}.'.format(p.name))
		return True
	print('  Cancelled.')
	return False

def list_teams(players):
	counts = {}
	for p in players:
		tname = p.team or p.club or 'Unattached'
		counts[tname] = counts.get(tname, 0) + 1
	print('\n  {:<26} Players'.format('Team'))
	print('  {:<26} -------'.format('--------------------------'))
	for team_name, n in sorted(counts.items(), key=lambda x: x[0]):
		print('  {:<26} {}'.format(team_name, n))

MENU = """
Commands:
  a  - add a new player (create or duplicate from DB)
  e  - edit an existing player
  d  - delete a player
  s  - search / browse players
  t  - list teams and player counts
  q  - quit (you will be prompted to save)
"""

def main():
	print('=' * 50)
	print('  Hattrk Football Player Database Editor')
	print('=' * 50)

	players = load_players()
	print('  Loaded {} players.\n'.format(len(players)))

	modified = False

	while True:
		print(MENU)
		cmd = get_str('Command', required=False, default='').lower()

		if cmd == 'a':
			if add_player(players):
				modified = True
		elif cmd == 'e':
			if edit_player(players):
				modified = True
		elif cmd == 'd':
			if delete_player(players):
				modified = True
		elif cmd == 's':
			search_players(players)
		elif cmd == 't':
			list_teams(players)
		elif cmd == 'q':
			if modified:
				ans = get_str('Save changes before quitting? (y/n)', default='y').lower()
				if ans == 'y':
					save_players(players)
			print('  Goodbye!')
			break
		else:
			print('  Unknown command.')

if __name__ == '__main__':
	main()
