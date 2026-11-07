import os, sys, pickle, copy, unicodedata
from engine import player, team, fixture, listshow, STADIUM_MAP, get_stadium
from game import game, setup, playerwrite, playermake, load_clubs

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except Exception:
		pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_TEAMS_FILE = os.path.join(BASE_DIR, 'variables', 'customteams.txt')
if not os.path.exists(CUSTOM_TEAMS_FILE):
	CUSTOM_TEAMS_FILE = 'variables/customteams.txt'

def _strip_accents(text):
	return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

def possible():
	if not os.path.exists(CUSTOM_TEAMS_FILE):
		return [], []

	with open(CUSTOM_TEAMS_FILE, 'r') as f:
		lines = [line.rstrip('\n') for line in f]

	team_names = []
	for i, line in enumerate(lines):
		if line.startswith('#'):
			continue
		if line == '' and i + 1 < len(lines) and lines[i + 1] != '' and not lines[i + 1].startswith('#'):
			team_names.append(lines[i + 1])
		elif i == 0 and line != '' and not line.startswith('#'):
			team_names.append(line)

	return team_names, lines

def find(team_name, all_lines):
	players = []
	reading = False
	for line in all_lines:
		if line.strip() == team_name:
			reading = True
			continue
		if reading:
			if line.strip() == '':
				break
			if not line.startswith('#'):
				players.append(line)
	return players

def playermake_custom(raw_line, t):
	p = playermake(raw_line, t)
	p.inns = []
	p.fitness = 1.0
	return p

def getplayers():
	pickle_path = os.path.join(BASE_DIR, 'players')
	if not os.path.exists(pickle_path) and os.path.exists('players'):
		pickle_path = 'players'

	if os.path.exists(pickle_path):
		try:
			with open(pickle_path, 'rb') as f:
				return pickle.load(f)
		except Exception:
			pass

	clubs = load_clubs()
	all_players = []
	for c_name, p_list in clubs.items():
		all_players.extend(p_list)

	try:
		with open(pickle_path, 'wb') as f:
			pickle.dump(all_players, f)
	except Exception:
		pass

	return all_players

def load(t, already_chosen):
	available, all_lines = possible()

	if not available:
		print('No saved custom teams found.')
		return None

	choices = [name for name in available if name not in already_chosen]

	if not choices:
		print('All saved teams have already been selected.')
		return None

	while True:
		t.name = input('Select a team from: {} -- '.format(listshow(choices))).strip()
		if t.name in choices:
			break
		print('  Invalid selection, please try again.')

	for raw_line in find(t.name, all_lines):
		t.active.append(playermake_custom(raw_line, t))
	t.squad = list(t.active)
	t.players = list(t.active)

	return t

def _show_roster(active):
	if not active:
		print('  (no players yet)')
		return
	print('  Current squad ({}):'.format(len(active)))
	for i, p in enumerate(active, 1):
		pos_str = getattr(p, 'primary_position', p.position)
		gen_tag = getattr(p, 'gender', 'Male')[0]
		print('    {:>2}. [{:<3}] [{}] {:<22} OVR:{:<2.0f} PAC:{:<2.0f} SHO:{:<2.0f} PAS:{:<2.0f} DEF:{:<2.0f}'.format(
			i, pos_str, gen_tag, p.name, p.overall,
			getattr(p, 'face_pace', 60.0), getattr(p, 'face_shooting', 60.0),
			getattr(p, 'face_passing', 60.0), getattr(p, 'face_defending', 60.0)
		))

def _pick_from_matches(team_obj, matches, db_players):
	if len(matches) == 1:
		chosen = matches[0]
	else:
		matches.sort(key=lambda p: p.overall, reverse=True)
		display_matches = matches[:15] if len(matches) > 15 else matches
		if len(matches) > 15:
			print('  Multiple matches (showing top 15 of {} by OVR):'.format(len(matches)))
		else:
			print('  Multiple matches:')
		for i, p in enumerate(display_matches, 1):
			pos_str = getattr(p, 'primary_position', p.position)
			gen_tag = getattr(p, 'gender', 'Male')[0]
			disp_name = getattr(p, 'short_name', '') or p.name
			print('    {}. [{}] [{}] {} ({}) OVR:{:.0f} PAC:{:.0f} SHO:{:.0f} DEF:{:.0f}'.format(
				i, pos_tag if 'pos_tag' in locals() else pos_str, gen_tag, disp_name, p.club or p.team, p.overall,
				getattr(p, 'face_pace', 60.0), getattr(p, 'face_shooting', 60.0), getattr(p, 'face_defending', 60.0)
			))
		raw = input('  Enter number to select (or Enter to cancel): ').strip()
		if not raw:
			return False
		try:
			chosen = display_matches[int(raw) - 1]
		except (ValueError, IndexError):
			print('  Invalid selection.')
			return False

	if any(p.name == chosen.name for p in team_obj.active):
		print('  {} is already in the squad.'.format(chosen.name))
		return False

	new_p = copy.deepcopy(chosen)
	new_p.team = team_obj.name
	new_p.club = team_obj.name
	new_p.fitness = 1.0
	new_p.inns = []

	team_obj.active.append(new_p)
	pos_str = getattr(new_p, 'primary_position', new_p.position)
	print('  Added: {} [{}] (OVR:{:.0f}, PAC:{:.0f}, SHO:{:.0f}, DEF:{:.0f})'.format(
		new_p.name, pos_str, new_p.overall,
		getattr(new_p, 'face_pace', 60.0), getattr(new_p, 'face_shooting', 60.0), getattr(new_p, 'face_defending', 60.0)
	))
	return True

def make(team_obj):
	db = getplayers()

	while len(team_obj.active) < 11:
		print()
		_show_roster(team_obj.active)
		print('  You need at least 11 players. Currently have: {}'.format(len(team_obj.active)))

		query = input("Player name to search (or Enter to cancel): ").strip()
		if not query:
			if len(team_obj.active) >= 11:
				break
			print('  You need at least 11 players before finishing.')
			continue

		q_clean = _strip_accents(query)
		exact = [p for p in db if _strip_accents(p.name) == q_clean or _strip_accents(getattr(p, 'short_name', '')) == q_clean]
		partial = [p for p in db if (q_clean in _strip_accents(p.name) or q_clean in _strip_accents(getattr(p, 'short_name', ''))) and p not in exact]

		if exact:
			_pick_from_matches(team_obj, exact, db)
		elif partial:
			_pick_from_matches(team_obj, partial, db)
		else:
			print('  Player not found.')

	while True:
		ans = input("\nAdd another player to squad? (y/n): ").strip().lower()
		if ans != 'y':
			break
		query = input("Player name to search: ").strip()
		if not query:
			continue
		q_clean = _strip_accents(query)
		exact = [p for p in db if _strip_accents(p.name) == q_clean or _strip_accents(getattr(p, 'short_name', '')) == q_clean]
		partial = [p for p in db if (q_clean in _strip_accents(p.name) or q_clean in _strip_accents(getattr(p, 'short_name', ''))) and p not in exact]
		if exact:
			_pick_from_matches(team_obj, exact, db)
		elif partial:
			_pick_from_matches(team_obj, partial, db)
		else:
			print('  Player not found.')

	team_obj.squad = list(team_obj.active)
	team_obj.players = list(team_obj.active)

	os.makedirs(os.path.dirname(os.path.abspath(CUSTOM_TEAMS_FILE)), exist_ok=True)
	with open(CUSTOM_TEAMS_FILE, 'a') as f:
		f.write('\n')
		f.write(team_obj.name + '\n')
		for p in team_obj.active:
			f.write(playerwrite(p) + '\n')

	print('\n  Team "{}" saved ({} players).'.format(team_obj.name, len(team_obj.active)))
	return team_obj

def getcustom(already_chosen=None):
	if already_chosen is None:
		already_chosen = []

	while True:
		o = input("Type 'l' to load a saved custom team, or 'n' to create a new one: ").strip().lower()
		if o in ('l', 'n'):
			break

	if o == 'l':
		t = team()
		result = load(t, already_chosen)
		if result is None:
			print('Falling back to new team creation.')
			o = 'n'
		else:
			print()
			return result

	if o == 'n':
		while True:
			name = input('Team name: ').strip()
			if name:
				break
			print('  Name cannot be empty.')
		t = team()
		t.name = name
		make(t)

	print()
	return t

if __name__ == '__main__':
	chosen_names = []
	teams = []
	for i in range(2):
		print('\nSelect Team {}:'.format(i + 1))
		t = getcustom(already_chosen=chosen_names)
		teams.append(t)
		chosen_names.append(t.name)

	fix = fixture()
	fix.home = teams[0]
	fix.away = teams[1]
	fix.venue = get_stadium(fix.home.name)
	game(fix)
