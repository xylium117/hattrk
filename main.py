import sys, os, unicodedata
from engine import fixture, team, listshow, STADIUM_MAP, get_stadium
from game import setup, game, load_clubs, find_club, POPULAR_CLUBS
from custom import getcustom
import customplayer

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except Exception:
		pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, 'variables', 'settings.txt')
if not os.path.exists(SETTINGS_FILE):
	SETTINGS_FILE = 'variables/settings.txt'

def _strip_accents(text):
	return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()

def print_banner():
	print("=" * 54)
	print("  HATTRK - Football Match Simulator")
	print("=" * 54)

def select_club_interactive(prompt_text, exclude_club=None):
	clubs = load_clubs()
	club_names = sorted(list(clubs.keys()))
	pop_clubs = [c for c in POPULAR_CLUBS if c in clubs]

	while True:
		val = input(prompt_text).strip()
		if not val:
			continue

		if val.lower() in ['list', 'all']:
			print('\nAll Available Clubs ({}):'.format(len(club_names)))
			for idx, name in enumerate(club_names, 1):
				print('  {:>3}. {:<28} ({} players)'.format(idx, name, len(clubs[name])))
			continue

		if val.lower().startswith('search ') or val.lower().startswith('s '):
			query = val.split(' ', 1)[1].strip()
			q_clean = _strip_accents(query)
			matches = [c for c in club_names if q_clean in _strip_accents(c)]
			if not matches:
				print("  No clubs matching '{}'.".format(query))
			else:
				print("\nSearch results for '{}':".format(query))
				for idx, name in enumerate(matches, 1):
					print('  {:>2}. {:<28} ({} players)'.format(idx, name, len(clubs[name])))
			continue

		if val.isdigit():
			idx = int(val)
			if 1 <= idx <= len(pop_clubs):
				chosen = pop_clubs[idx - 1]
				if chosen == exclude_club:
					print('  Team must be different from {}.'.format(exclude_club))
					continue
				return chosen
			elif 1 <= idx <= len(club_names):
				chosen = club_names[idx - 1]
				if chosen == exclude_club:
					print('  Team must be different from {}.'.format(exclude_club))
					continue
				return chosen
			else:
				print('  Invalid number.')
				continue

		matched = find_club(val)
		if matched:
			if matched == exclude_club:
				print('  Team must be different from {}.'.format(exclude_club))
				continue
			return matched

		print("  Club '{}' not found. Enter 1-{}, type club name, or 'search <name>'.".format(val, len(pop_clubs)))

def quick_match():
	clubs = load_clubs()
	if not clubs:
		print('No clubs found in database.')
		return

	pop_clubs = [c for c in POPULAR_CLUBS if c in clubs]

	print('\nFeatured Clubs:')
	col_split = (len(pop_clubs) + 1) // 2
	for i in range(col_split):
		left_idx = i + 1
		left_name = pop_clubs[i]
		line = '  {:>2}. {:<26}'.format(left_idx, left_name)
		if i + col_split < len(pop_clubs):
			right_idx = i + col_split + 1
			right_name = pop_clubs[i + col_split]
			line += '  {:>2}. {:<26}'.format(right_idx, right_name)
		print(line)

	print("\n(Enter number 1-{}, type club name, 'search <term>', or 'all' for all clubs)".format(len(pop_clubs)))

	home_name = select_club_interactive('\nSelect Home Team: ')
	away_name = select_club_interactive('Select Away Team: ', exclude_club=home_name)

	print('\nStarting Match: {} vs. {}\n'.format(home_name, away_name))
	fix = setup(home_name, away_name)
	game(fix)

def custom_match():
	print('\n-- Custom Match Setup --')
	chosen = []
	teams = []
	for i, side in enumerate(['Home', 'Away'], 1):
		print('\nConfigure {} Team:'.format(side))
		t = getcustom(already_chosen=chosen)
		teams.append(t)
		chosen.append(t.name)

	fix = fixture()
	fix.home = teams[0]
	fix.away = teams[1]
	fix.venue = get_stadium(fix.home.name)
	print('\nStarting Custom Match: {} vs. {}\n'.format(fix.home.name, fix.away.name))
	game(fix)

def settings_info():
	print('\n-- Settings Information --')
	if os.path.exists(SETTINGS_FILE):
		print('Contents of {}:'.format(SETTINGS_FILE))
		print('-' * 40)
		with open(SETTINGS_FILE, 'r') as f:
			print(f.read().rstrip())
		print('-' * 40)
	else:
		print('Settings file not found at {}.'.format(SETTINGS_FILE))

	print("""
Configuration Guide:
- Set 'active = true' to apply overrides.
- 'venue = <Stadium Name>' overrides the match venue.
- 'extra_time = true' enables 30 minutes of extra time on a draw.
- 'penalties = true' enables a penalty shootout after extra time.
- 'kickoff = home' or 'kickoff = away' forces toss winner.
""")

def main_menu():
	while True:
		print_banner()
		print("Main Menu:")
		print("  1. Quick match (pick from built-in clubs)")
		print("  2. Custom match (use custom.py)")
		print("  3. Edit player DB (customplayer.py)")
		print("  4. Settings info")
		print("  5. Quit")

		choice = input("\nEnter choice (1-5): ").strip()

		if choice == '1':
			quick_match()
			input("\nPress Enter to return to main menu...")
		elif choice == '2':
			custom_match()
			input("\nPress Enter to return to main menu...")
		elif choice == '3':
			customplayer.main()
		elif choice == '4':
			settings_info()
			input("\nPress Enter to return to main menu...")
		elif choice == '5':
			print("\nThank you for playing Hattrk! Goodbye.\n")
			break
		else:
			print("Invalid choice, please enter 1, 2, 3, 4, or 5.")

if __name__ == '__main__':
	main_menu()
