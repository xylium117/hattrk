import sys, os, unicodedata
from engine import fixture, team, listshow, STADIUM_MAP, get_stadium
from game import setup, game, load_clubs, find_club, POPULAR_CLUBS
from custom import getcustom
import customplayer
from league import get_league, load_all_leagues
from predictor import predict_league_outcomes, print_league_prediction_report
from season import ContinentalSeasonSimulator

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
    print("=" * 64)
    print("  HATTRK - Football Match & Season Simulator")
    print("=" * 64)

def select_club_interactive(prompt_text, exclude_club=None):
    clubs = load_clubs()
    club_names = sorted(list(clubs.keys()))
    pop_clubs = [c for c in POPULAR_CLUBS if c in clubs]

    while True:
        val = input(prompt_text).strip()
        if not val:
            continue

        if val.lower() in ['list', 'all']:
            print(f'\nAll Available Clubs ({len(club_names)}):')
            for idx, name in enumerate(club_names, 1):
                print(f'  {idx:>3}. {name:<32} ({len(clubs[name])} players)')
            continue

        if val.lower().startswith('search ') or val.lower().startswith('s '):
            query = val.split(' ', 1)[1].strip()
            q_clean = _strip_accents(query)
            matches = [c for c in club_names if q_clean in _strip_accents(c)]
            if not matches:
                print(f"  No clubs matching '{query}'.")
            else:
                print(f"\nSearch results for '{query}':")
                for idx, name in enumerate(matches, 1):
                    print(f'  {idx:>2}. {name:<32} ({len(clubs[name])} players)')
            continue

        if val.isdigit():
            idx = int(val)
            if 1 <= idx <= len(pop_clubs):
                chosen = pop_clubs[idx - 1]
                if chosen == exclude_club:
                    print(f'  Team must be different from {exclude_club}.')
                    continue
                return chosen
            elif 1 <= idx <= len(club_names):
                chosen = club_names[idx - 1]
                if chosen == exclude_club:
                    print(f'  Team must be different from {exclude_club}.')
                    continue
                return chosen
            else:
                print('  Invalid number.')
                continue

        matched = find_club(val)
        if matched:
            if matched == exclude_club:
                print(f'  Team must be different from {exclude_club}.')
                continue
            return matched

        print(f"  Club '{val}' not found. Enter 1-{len(pop_clubs)}, type club name, or 'search <name>'.")

def get_yes_no(prompt, default=True):
    """Get yes/no input from user."""
    default_str = 'Y/n' if default else 'y/N'
    while True:
        val = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not val:
            return default
        if val in ('y', 'yes'):
            return True
        if val in ('n', 'no'):
            return False
        print("  Please enter 'y' or 'n'.")

def get_int(prompt, default, min_val=None, max_val=None):
    """Get integer input from user with validation."""
    while True:
        val = input(f"{prompt} (default: {default}): ").strip()
        if not val:
            return default
        try:
            ival = int(val)
            if min_val is not None and ival < min_val:
                print(f"  Value must be at least {min_val}.")
                continue
            if max_val is not None and ival > max_val:
                print(f"  Value must be at most {max_val}.")
                continue
            return ival
        except ValueError:
            print("  Please enter a valid number.")

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
        line = f'  {left_idx:>2}. {left_name:<30}'
        if i + col_split < len(pop_clubs):
            right_idx = i + col_split + 1
            right_name = pop_clubs[i + col_split]
            line += f'  {right_idx:>2}. {right_name:<30}'
        print(line)

    print(f"\n(Enter 1-{len(pop_clubs)}, type club name, 'search <term>', or 'all' for all clubs)")

    home_name = select_club_interactive('\nSelect Home Team: ')
    away_name = select_club_interactive('Select Away Team: ', exclude_club=home_name)

    save_scorecard = get_yes_no('\nSave match scorecard to file?', default=False)
    scorecard_dir = None
    if save_scorecard:
        scorecard_dir = os.path.join(BASE_DIR, 'scorecards', 'single_matches')
        os.makedirs(scorecard_dir, exist_ok=True)

    print(f'\nStarting Match: {home_name} vs. {away_name}\n')
    fix = setup(home_name, away_name, savecard=save_scorecard)
    if save_scorecard:
        safe_home = "".join(c for c in home_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        safe_away = "".join(c for c in away_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fix.scorecard = os.path.join(scorecard_dir, f"{safe_home}_vs_{safe_away}_{timestamp}.txt")
    game(fix)

def custom_match():
    print('\n-- Custom Match Setup --')
    chosen = []
    teams = []
    for i, side in enumerate(['Home', 'Away'], 1):
        print(f'\nConfigure {side} Team:')
        t = getcustom(already_chosen=chosen)
        teams.append(t)
        chosen.append(t.name)

    save_scorecard = get_yes_no('\nSave match scorecard to file?', default=False)
    scorecard_dir = None
    if save_scorecard:
        scorecard_dir = os.path.join(BASE_DIR, 'scorecards', 'single_matches')
        os.makedirs(scorecard_dir, exist_ok=True)

    fix = fixture()
    fix.home = teams[0]
    fix.away = teams[1]
    fix.venue = get_stadium(fix.home.name)
    print(f'\nStarting Custom Match: {fix.home.name} vs. {fix.away.name}\n')
    if save_scorecard:
        safe_home = "".join(c for c in fix.home.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        safe_away = "".join(c for c in fix.away.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fix.scorecard = os.path.join(scorecard_dir, f"{safe_home}_vs_{safe_away}_{timestamp}.txt")
    game(fix)

def select_league_interactive(prompt_text):
    all_leagues = load_all_leagues()
    popular_leagues = [
        ("Premier League", "England"),
        ("LALIGA EA SPORTS", "Spain"),
        ("Serie A Enilive", "Italy"),
        ("Bundesliga", "Germany"),
        ("Ligue 1 McDonald's", "France"),
        ("Major League Soccer", "USA"),
        ("ROSHN Saudi League", "Saudi Arabia"),
        ("Liga Profesional de Fútbol", "Argentina"),
        ("Liga do Brasil", "Brazil"),
        ("Barclays Women's Super League", "England (Women)"),
        ("Liga F", "Spain (Women)")
    ]
    print("\nPopular Leagues:")
    for i, (l_name, country) in enumerate(popular_leagues, 1):
        print(f"  {i:>2}. {l_name:<32} ({country})")
    print("\n(Enter 1-11, or type full/partial league name, or 'list' for all leagues)")
    while True:
        raw = input(prompt_text).strip()
        if not raw:
            continue
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(popular_leagues):
                return popular_leagues[idx][0]
        if raw.lower() == 'list':
            for l_id, l_data in sorted(all_leagues.items(), key=lambda x: x[1]['name']):
                print(f"  * {l_data['name']} ({l_data['country']} - {l_data['continent']})")
            continue
        match = get_league(raw)
        if match:
            return match.name
        print(f"No league found matching '{raw}'. Please try again.")

def league_sim_interactive():
    print("\n" + "=" * 64)
    print("  DOMESTIC LEAGUE SEASON SIMULATOR")
    print("=" * 64)
    league_name = select_league_interactive("Select League: ")
    lg = get_league(league_name)
    if not lg:
        print("Failed to initialize league.")
        return

    print(f"\nLeague: {lg.name} ({len(lg.club_names)} clubs, {len(lg.fixtures)} matchdays)")
    print(f"  Tier: {lg.tier} | UCL spots: {lg.ucl_spots} | UEL spots: {lg.uel_spots} | UECL spots: {lg.uecl_spots} | Relegation: {lg.rel_spots}")

    save_scorecards = get_yes_no("\nGenerate detailed match scorecards and season results? (creates folder with all match files + season summary)", default=False)
    scorecard_dir = None
    if save_scorecards:
        scorecard_dir = os.path.join(BASE_DIR, 'scorecards')
        import shutil
        if os.path.exists(scorecard_dir):
            shutil.rmtree(scorecard_dir)
        os.makedirs(scorecard_dir, exist_ok=True)
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_lg_name = "".join(c for c in lg.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        scorecard_dir = os.path.join(scorecard_dir, f"{safe_lg_name}_Season_{timestamp}")

    max_matchdays = None
    if get_yes_no("\nSimulate full season?", default=True):
        pass
    else:
        max_matchdays = get_int("Number of matchdays to simulate", len(lg.fixtures), 1, len(lg.fixtures))

    use_poisson = get_yes_no("\nUse fast Poisson simulation (no spatial engine, much faster)?", default=True)

    print(f"\nSimulating {lg.name} season...")
    lg.simulate_season(quiet=use_poisson, max_matchdays=max_matchdays,
                       save_scorecards=save_scorecards, scorecard_base_dir=scorecard_dir, use_poisson=use_poisson, save_results=save_scorecards)
    lg.print_standings()
    lg.print_season_summary()
    if save_scorecards:
        lg.save_results_to_file(BASE_DIR)

def league_pred_interactive():
    print("\n" + "=" * 64)
    print("  PREDICT THE LEAGUE")
    print("=" * 64)
    league_name = select_league_interactive("Select League to Predict: ")
    runs = get_int("Number of full season simulations", 30, 1, 100)
    print(f"\nForecasting {league_name} finish probabilities across {runs} seasons with dynamic rolling form...")
    res = predict_league_outcomes(league_name, runs=runs)
    if res:
        print_league_prediction_report(res)
    else:
        print("Error generating prediction report.")

def continental_season_interactive():
    print("\n" + "=" * 64)
    print("  SIMULATE SEASON")
    print("=" * 64)
    print("Continents:")
    print("  1. Europe")
    print("  2. South America")
    print("  3. North America")
    print("  4. Asia")
    print("  5. Africa")
    print("  6. Europe + South America")
    print("  7. Europe + Asia")
    print("  8. All Continents")

    cont_choice = input("\nSelect option (1-8, default 6): ").strip() or "6"
    cont_map = {
        "1": ["Europe"],
        "2": ["South America"],
        "3": ["North America"],
        "4": ["Asia"],
        "5": ["Africa"],
        "6": ["Europe", "South America"],
        "7": ["Europe", "Asia"],
        "8": ["Europe", "South America", "North America", "Asia", "Africa"]
    }
    continents = cont_map.get(cont_choice, ["Europe", "South America"])

    seasons = get_int("Number of consecutive seasons to simulate", 1, 1, 5)

    save_scorecards = get_yes_no("\nGenerate detailed scorecards and season results for ALL matches (domestic + continental)?", default=False)
    scorecard_root = os.path.join(BASE_DIR, 'scorecards') if save_scorecards else None
    if save_scorecards:
        import shutil
        if os.path.exists(scorecard_root):
            shutil.rmtree(scorecard_root)
        os.makedirs(scorecard_root, exist_ok=True)

    max_domestic = None
    if not get_yes_no("Simulate full domestic seasons?", default=True):
        max_domestic = get_int("Max domestic matchdays per league", 10, 1, 38)

    use_poisson = get_yes_no("\nUse fast Poisson simulation for domestic leagues?", default=True)

    print(f"\nSimulating {seasons} season(s) across {', '.join(continents)} with domestic leagues & continental cups...")
    sim = ContinentalSeasonSimulator(continents, seasons_count=seasons, max_domestic_rounds=max_domestic,
                                     save_scorecards=save_scorecards, scorecard_root=scorecard_root, save_results=save_scorecards)
    sim.run(show_progress=True)
    sim.print_summary()
    if save_scorecards:
        sim.print_awards()

def settings_info():
    print('\n-- Settings Information --')
    if os.path.exists(SETTINGS_FILE):
        print(f'Contents of {SETTINGS_FILE}:')
        print('-' * 40)
        with open(SETTINGS_FILE, 'r') as f:
            print(f.read().rstrip())
        print('-' * 40)
    else:
        print(f'Settings file not found at {SETTINGS_FILE}.')

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
        print("  1. Quick match")
        print("  2. Custom match")
        print("  3. Simulate a Domestic League Season")
        print("  4. Predict the League")
        print("  5. Simulate Season")
        print("  6. Edit player DB")
        print("  7. Settings info")
        print("  8. Quit")

        choice = input("\nEnter choice (1-8): ").strip()

        if choice == '1':
            quick_match()
            input("\nPress Enter to return to main menu...")
        elif choice == '2':
            custom_match()
            input("\nPress Enter to return to main menu...")
        elif choice == '3':
            league_sim_interactive()
            input("\nPress Enter to return to main menu...")
        elif choice == '4':
            league_pred_interactive()
            input("\nPress Enter to return to main menu...")
        elif choice == '5':
            continental_season_interactive()
            input("\nPress Enter to return to main menu...")
        elif choice == '6':
            customplayer.main()
        elif choice == '7':
            settings_info()
            input("\nPress Enter to return to main menu...")
        elif choice == '8':
            print("\nThank you for playing Hattrk! Goodbye.\n")
            break
        else:
            print("Invalid choice, please enter a number from 1 to 8.")

if __name__ == '__main__':
    main_menu()