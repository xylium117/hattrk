import os, sys, random, json
from collections import defaultdict
from tqdm import tqdm
import game, engine
from league import get_league, load_all_leagues, load_all_clubs


CONTINENTAL_TOURNAMENTS = {
    "Europe": [
        {
            "name": "UEFA Champions League",
            "tier": "primary",
            "format": "uefa_modern",
            "league_phase_size": 36,
            "league_phase_matches": 8,
            "direct_ko_slots": 8,
            "playoff_range": (9, 24),
            "gender": "Male",
            "sources": [
                ("premier_league", 4),
                ("laliga_ea_sports", 4),
                ("serie_a_enilive", 4),
                ("bundesliga", 4),
                ("ligue_1_mcdonald_s", 3),
                ("liga_portugal", 3),
                ("eredivisie", 2),
                ("scottish_premiership", 2),
                ("1a_pro_league", 2),
                ("trendyol_s_per_lig", 1),
            ]
        },
        {
            "name": "UEFA Europa League",
            "tier": "secondary",
            "format": "uefa_modern",
            "league_phase_size": 36,
            "league_phase_matches": 8,
            "direct_ko_slots": 8,
            "playoff_range": (9, 24),
            "gender": "Male",
            "sources": [
                ("premier_league", 1),
                ("laliga_ea_sports", 1),
                ("serie_a_enilive", 1),
                ("bundesliga", 1),
                ("ligue_1_mcdonald_s", 2),
                ("liga_portugal", 2),
                ("eredivisie", 2),
                ("scottish_premiership", 1),
                ("1a_pro_league", 1),
                ("pko_bank_polski_ekstraklasa", 1),
                ("credit_suisse_super_league", 1),
                ("_sterreichische_fu_ball_bundesliga", 1),
            ]
        },
        {
            "name": "UEFA Conference League",
            "tier": "tertiary",
            "format": "uefa_modern",
            "league_phase_size": 36,
            "league_phase_matches": 8,
            "direct_ko_slots": 8,
            "playoff_range": (9, 24),
            "gender": "Male",
            "sources": [
                ("premier_league", 1),
                ("laliga_ea_sports", 1),
                ("serie_a_enilive", 1),
                ("bundesliga", 1),
                ("ligue_1_mcdonald_s", 1),
                ("liga_portugal", 1),
                ("eredivisie", 1),
                ("pko_bank_polski_ekstraklasa", 1),
                ("credit_suisse_super_league", 1),
                ("_sterreichische_fu_ball_bundesliga", 1),
                ("3f_superliga", 1),
                ("allsvenskan", 1),
                ("eliteserien", 1),
            ]
        },
        {
            "name": "UEFA Women's Champions League",
            "tier": "primary",
            "format": "uefa_womens",
            "league_phase_size": 16,
            "league_phase_matches": 6,
            "direct_ko_slots": 4,
            "playoff_range": (5, 12),
            "gender": "Female",
            "sources": [
                ("barclays_women_s_super_league", 3),
                ("liga_f", 3),
                ("google_pixel_frauen_bundesliga", 3),
                ("arkema_premi_re_ligue", 2),
                ("calcio_a_femminile", 1),
            ]
        }
    ],
    "South America": [
        {
            "name": "Copa Libertadores",
            "tier": "primary",
            "format": "conmebol",
            "groups": 8,
            "group_size": 4,
            "ko_from_group": 2,
            "gender": "Male",
            "sources": [
                ("liga_do_brasil", 7),
                ("liga_profesional_de_f_tbol", 6),
                ("liga_colombia", 4),
                ("primera_division_uruguay", 2),
                ("liga_pro_ecuador", 2),
                ("primera_division_chile", 2),
                ("liga_1_peru", 2),
                ("liga_profesional_bolivia", 2),
            ]
        },
        {
            "name": "Copa Sudamericana",
            "tier": "secondary",
            "format": "conmebol",
            "groups": 8,
            "group_size": 4,
            "ko_from_group": 2,
            "gender": "Male",
            "sources": [
                ("liga_do_brasil", 5),
                ("liga_profesional_de_f_tbol", 5),
                ("liga_colombia", 3),
                ("primera_division_uruguay", 1),
                ("liga_pro_ecuador", 1),
                ("primera_division_chile", 1),
                ("liga_1_peru", 1),
                ("liga_profesional_bolivia", 1),
            ]
        }
    ],
    "North America": [
        {
            "name": "CONCACAF Champions Cup",
            "tier": "primary",
            "format": "concacaf",
            "round_one_slots": 27,
            "gender": "Male",
            "sources": [
                ("major_league_soccer", 10),
                ("liga_bbva_mx", 6),
                ("canadian_premier_league", 1),
                ("us_open_cup", 1),
                ("liga_mx_copa", 1),
                ("leagues_cup", 3),
                ("central_american_cup", 3),
                ("caribbean_cup", 2),
            ]
        }
    ],
    "Asia": [
        {
            "name": "AFC Champions League Elite",
            "tier": "primary",
            "format": "afc_modern",
            "league_phase_size": 24,
            "league_phase_matches": 8,
            "direct_ko_slots": 8,
            "playoff_range": (9, 16),
            "gender": "Male",
            "sources": [
                ("roshn_saudi_league", 3),
                ("k_league_1", 3),
                ("isuzu_ute_a_league", 2),
                ("chinese_football_association_super_league", 2),
                ("indian_super_league", 1),
                ("j1_league", 3),
                ("persian_gulf_pro_league", 2),
                ("qatar_stars_league", 2),
            ]
        },
        {
            "name": "AFC Champions League Two",
            "tier": "secondary",
            "format": "afc_modern",
            "league_phase_size": 24,
            "league_phase_matches": 6,
            "direct_ko_slots": 8,
            "playoff_range": (9, 16),
            "gender": "Male",
            "sources": [
                ("roshn_saudi_league", 1),
                ("k_league_1", 1),
                ("isuzu_ute_a_league", 1),
                ("chinese_football_association_super_league", 1),
                ("indian_super_league", 1),
                ("j1_league", 1),
                ("persian_gulf_pro_league", 1),
                ("qatar_stars_league", 1),
                ("thaipro_league", 1),
                ("a_league_men", 1),
            ]
        }
    ],
    "Africa": [
        {
            "name": "CAF Champions League",
            "tier": "primary",
            "format": "caf",
            "groups": 8,
            "group_size": 4,
            "ko_from_group": 2,
            "gender": "Male",
            "sources": [
                ("egyptian_premier_league", 2),
                ("botola_pro", 2),
                ("algerian_ligue_1", 2),
                ("tunisian_ligue_1", 2),
                ("south_african_premiership", 2),
                ("npl", 1),
                ("ghana_premier_league", 1),
                ("ivorian_ligue_1", 1),
            ]
        },
        {
            "name": "CAF Confederation Cup",
            "tier": "secondary",
            "format": "caf",
            "groups": 8,
            "group_size": 4,
            "ko_from_group": 2,
            "gender": "Male",
            "sources": [
                ("egyptian_premier_league", 1),
                ("botola_pro", 1),
                ("algerian_ligue_1", 1),
                ("tunisian_ligue_1", 1),
                ("south_african_premiership", 1),
            ]
        }
    ]
}

FLAGSHIP_DOMESTIC_LEAGUES = {
    "Europe": [
        "premier_league", "laliga_ea_sports", "serie_a_enilive", "bundesliga", "ligue_1_mcdonald_s", "liga_portugal", "eredivisie",
        "barclays_women_s_super_league", "liga_f", "google_pixel_frauen_bundesliga", "arkema_premi_re_ligue", "calcio_a_femminile",
        "scottish_women_s_league", "damallsvenskan", "ceska_liga_en", "sland_kvennadeild"
    ],
    "South America": ["liga_do_brasil", "liga_profesional_de_f_tbol", "liga_colombia"],
    "North America": ["major_league_soccer", "liga_bbva_mx", "national_women_s_soccer_league"],
    "Asia": ["roshn_saudi_league", "k_league_1", "isuzu_ute_a_league", "j1_league"],
    "Africa": ["egyptian_premier_league", "botola_pro", "algerian_ligue_1"],
}

def _simulate_match(home_name, away_name, save_scorecard=False, is_final=False, is_ko_leg=False, scorecard_dir=None,
                     ko_aggregate_home=0, ko_aggregate_away=0):
    """Simulate a single match between two teams, return fix object for stats
    is_final: single-match final (extra time + penalties if tied after 90)
    is_ko_leg: knockout second leg (extra time + penalties if aggregate tied after 90)
    ko_aggregate_home: aggregate goals for home team from first leg
    ko_aggregate_away: aggregate goals for away team from first leg
    """
    saved_savecard = engine.SAVE_SCORECARD
    if save_scorecard and scorecard_dir:
        os.makedirs(scorecard_dir, exist_ok=True)
        engine.set_save_scorecard(True)
    else:
        engine.set_save_scorecard(False)

    old_stdout = sys.stdout
    devnull = open(os.devnull, 'w', encoding='utf-8')
    sys.stdout = devnull

    try:
        if save_scorecard and scorecard_dir:
            safe_home = "".join(c for c in home_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            safe_away = "".join(c for c in away_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            scorecard_file = os.path.join(scorecard_dir, f"{safe_home}_vs_{safe_away}.txt")
            fix = game.setup(home_name, away_name, savecard=True)
            fix.scorecard = scorecard_file
        else:
            fix = game.setup(home_name, away_name, savecard=save_scorecard)
        if is_final or is_ko_leg:
            fix.extra_time_opt = True
            fix.penalties_opt = True
        if is_ko_leg:
            fix.is_ko_leg = True
            fix.ko_aggregate_home = ko_aggregate_home
            fix.ko_aggregate_away = ko_aggregate_away
        game.game(fix)
        h_score = fix.home_score
        a_score = fix.away_score
    except Exception:
        h_score, a_score = (1, 0) if random.random() < 0.55 else (0, 1)
        fix = None

    sys.stdout = old_stdout
    devnull.close()
    engine.set_save_scorecard(saved_savecard)

    return h_score, a_score, fix


def _simulate_two_legged_tie(t1_name, t2_name, is_final=False, save_scorecard=False, scorecard_dir=None):
    """Simulate a two-legged knockout tie"""
    if is_final:
        h_score, a_score, fix = _simulate_match(t1_name, t2_name, save_scorecard=save_scorecard, is_final=True, scorecard_dir=scorecard_dir)
        if fix and fix.win and fix.win != 'Draw':
            winner = fix.win.name
            result_desc = fix.resultdesc
        elif h_score > a_score:
            winner = t1_name
            result_desc = f"{h_score} - {a_score}"
        elif a_score > h_score:
            winner = t2_name
            result_desc = f"{h_score} - {a_score}"
        else:
            winner = t1_name if random.random() < 0.50 else t2_name
            result_desc = f"{h_score} - {a_score} (pens)"
        return winner, result_desc, fix, None

    leg1_dir = None
    leg2_dir = None
    if save_scorecard and scorecard_dir:
        leg1_dir = os.path.join(scorecard_dir, "Leg_1")
        leg2_dir = os.path.join(scorecard_dir, "Leg_2")
        os.makedirs(leg1_dir, exist_ok=True)
        os.makedirs(leg2_dir, exist_ok=True)

    l1_h, l1_a, fix1 = _simulate_match(t1_name, t2_name, save_scorecard=save_scorecard, scorecard_dir=leg1_dir)
    l2_h, l2_a, fix2 = _simulate_match(t2_name, t1_name, save_scorecard=save_scorecard, is_ko_leg=True, scorecard_dir=leg2_dir,
                                       ko_aggregate_home=l1_a, ko_aggregate_away=l1_h)

    agg_t1 = l1_h + l2_a
    agg_t2 = l1_a + l2_h

    if agg_t1 > agg_t2:
        winner = t1_name
        result_desc = f"{agg_t1} - {agg_t2} (agg)"
    elif agg_t2 > agg_t1:
        winner = t2_name
        result_desc = f"{agg_t1} - {agg_t2} (agg)"
    else:
        if fix2 and fix2.win and fix2.win != 'Draw':
            winner = fix2.win.name
            result_desc = fix2.resultdesc
        else:
            winner = t1_name if random.random() < 0.50 else t2_name
            result_desc = f"{agg_t1} - {agg_t2} (pens)"

    return winner, result_desc, fix1, fix2


class UEFAModernTournament:
    """Modern UEFA format (2024/25+): League phase + Knockout rounds"""

    def __init__(self, name, teams, league_phase_size=36, league_phase_matches=8,
                 direct_ko_slots=8, playoff_range=(9, 24), save_scorecards=False):
        self.name = name
        self.all_teams = list(teams)
        self.league_phase_size = min(league_phase_size, len(self.all_teams))
        self.league_phase_matches = league_phase_matches
        self.direct_ko_slots = direct_ko_slots
        self.playoff_start, self.playoff_end = playoff_range
        self.save_scorecards = save_scorecards
        self.league_table = {}
        self.ko_results = {}
        self.winner = None
        self.runner_up = None
        self.final_score = ""
        self.scorers = defaultdict(lambda: defaultdict(int))
        self.assisters = defaultdict(lambda: defaultdict(int))
        self.keepers_saves = defaultdict(lambda: defaultdict(int))
        self.keepers_clean_sheets = defaultdict(lambda: defaultdict(int))
        self.keepers_minutes = defaultdict(lambda: defaultdict(int))
        self.player_minutes = defaultdict(lambda: defaultdict(int))
        self.player_ratings = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'count': 0}))

    def _init_league_table(self):
        for team in self.all_teams[:self.league_phase_size]:
            self.league_table[team] = {
                'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0
            }

    def _generate_league_phase_fixtures(self):
        """Generate Swiss-model style fixtures for league phase"""
        teams = self.all_teams[:self.league_phase_size]
        n = len(teams)

        random.shuffle(teams)

        from elo import get_club_elo
        teams_sorted = sorted(teams, key=lambda t: get_club_elo(t), reverse=True)
        pots = []
        pot_size = max(1, n // 4)
        for i in range(0, n, pot_size):
            pots.append(teams_sorted[i:i+pot_size])

        fixtures = {team: [] for team in teams}

        for team in teams:
            team_pot_idx = next(i for i, p in enumerate(pots) if team in p)
            opponents = []

            for pot_idx, pot in enumerate(pots):
                available = [t for t in pot if t != team and t not in opponents]
                if available:
                    picks = min(2, len(available))
                    selected = random.sample(available, picks)
                    opponents.extend(selected)

            while len(opponents) < self.league_phase_matches:
                remaining = [t for t in teams if t != team and t not in opponents]
                if not remaining:
                    break
                opponents.append(random.choice(remaining))

            opponents = opponents[:self.league_phase_matches]

            for i, opp in enumerate(opponents):
                if i % 2 == 0:
                    fixtures[team].append(('H', opp))
                else:
                    fixtures[team].append(('A', opp))

        matches = []
        seen = set()
        for team in teams:
            for ha, opp in fixtures[team]:
                key = tuple(sorted([team, opp]))
                if key not in seen:
                    seen.add(key)
                    if ha == 'H':
                        matches.append((team, opp))
                    else:
                        matches.append((opp, team))

        return matches

    def run_league_phase(self, quiet=True, scorecard_dir=None):
        """Run the league phase matches"""
        self._init_league_table()
        matches = self._generate_league_phase_fixtures()

        if not quiet:
            print(f"  {self.name} League Phase: {len(matches)} matches, {self.league_phase_size} teams")

        old_stdout = None
        devnull = None
        if quiet:
            old_stdout = sys.stdout
            devnull = open(os.devnull, 'w', encoding='utf-8')
            sys.stdout = devnull

        league_phase_dir = None
        if self.save_scorecards and scorecard_dir:
            league_phase_dir = os.path.join(scorecard_dir, "League_Phase")
            os.makedirs(league_phase_dir, exist_ok=True)

        for home, away in matches:
            h_score, a_score, fix = _simulate_match(home, away, save_scorecard=self.save_scorecards, scorecard_dir=league_phase_dir)

            for team, gf, ga in [(home, h_score, a_score), (away, a_score, h_score)]:
                self.league_table[team]['played'] += 1
                self.league_table[team]['gf'] += gf
                self.league_table[team]['ga'] += ga
                self.league_table[team]['gd'] = self.league_table[team]['gf'] - self.league_table[team]['ga']
                if gf > ga:
                    self.league_table[team]['won'] += 1
                    self.league_table[team]['pts'] += 3
                elif gf == ga:
                    self.league_table[team]['drawn'] += 1
                    self.league_table[team]['pts'] += 1
                else:
                    self.league_table[team]['lost'] += 1

            if fix and hasattr(fix, 'periods') and fix.periods:
                self._track_match_stats(fix, home, away)

        if quiet and old_stdout is not None:
            sys.stdout = old_stdout
            if devnull:
                devnull.close()

        sorted_table = sorted(
            self.league_table.items(),
            key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']),
            reverse=True
        )
        return sorted_table

    def _track_match_stats(self, fix, home_name, away_name):
        """Track player stats from a match fix object"""
        if not fix or not hasattr(fix, 'periods') or not fix.periods:
            return

        for p in fix.home.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[home_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[home_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[home_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[home_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[home_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[home_name][p_name] += perf.saves
                    self.keepers_minutes[home_name][p_name] += 90
                    if fix.away_score == 0:
                        self.keepers_clean_sheets[home_name][p_name] += 1

        for p in fix.away.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[away_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[away_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[away_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[away_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[away_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[away_name][p_name] += perf.saves
                    self.keepers_minutes[away_name][p_name] += 90
                    if fix.home_score == 0:
                        self.keepers_clean_sheets[away_name][p_name] += 1

    def run_knockout_phase(self, league_table, quiet=True, scorecard_dir=None):
        """Run knockout phase: playoffs -> R16 -> QF -> SF -> Final"""
        direct_qualifiers = [team for team, _ in league_table[:self.direct_ko_slots]]

        playoff_teams = [team for team, _ in league_table[self.playoff_start-1:self.playoff_end]]

        playoff_winners = []
        n_playoff = len(playoff_teams)
        for i in range(n_playoff // 2):
            t1 = playoff_teams[i]
            t2 = playoff_teams[n_playoff - 1 - i]
            tie_dir = None
            if self.save_scorecards and scorecard_dir:
                tie_dir = os.path.join(scorecard_dir, f"Playoff_{t1}_vs_{t2}".replace(' ', '_'))
                os.makedirs(tie_dir, exist_ok=True)
            winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, save_scorecard=self.save_scorecards, scorecard_dir=tie_dir)
            playoff_winners.append(winner)
            self.ko_results[f'Playoff: {t1} vs {t2}'] = score
            if fix1:
                self._track_match_stats(fix1, t1, t2)
            if fix2:
                self._track_match_stats(fix2, t2, t1)

        r16_teams = direct_qualifiers + playoff_winners
        random.shuffle(r16_teams)

        n_teams = len(r16_teams)
        if n_teams >= 16:
            round_names = ['Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
        elif n_teams >= 8:
            round_names = ['Quarter-finals', 'Semi-finals', 'Final']
        elif n_teams >= 4:
            round_names = ['Semi-finals', 'Final']
        else:
            round_names = ['Final']

        current_round = r16_teams

        for round_name in round_names:
            next_round = []
            is_final = (round_name == 'Final')
            for i in range(0, len(current_round), 2):
                if i + 1 < len(current_round):
                    t1 = current_round[i]
                    t2 = current_round[i + 1]
                    tie_dir = None
                    if self.save_scorecards and scorecard_dir:
                        tie_dir = os.path.join(scorecard_dir, f"{round_name}_{t1}_vs_{t2}".replace(' ', '_'))
                        os.makedirs(tie_dir, exist_ok=True)
                    winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, is_final=is_final, save_scorecard=self.save_scorecards, scorecard_dir=tie_dir)
                    next_round.append(winner)
                    self.ko_results[f'{round_name}: {t1} vs {t2}'] = score
                    if fix1:
                        self._track_match_stats(fix1, t1, t2)
                    if fix2:
                        self._track_match_stats(fix2, t2, t1)
                    if is_final:
                        self.winner = winner
                        self.runner_up = t2 if winner == t1 else t1
                        self.final_score = score
                else:
                    next_round.append(current_round[i])
            current_round = next_round

        return self.winner, self.runner_up

    def run(self, quiet=True, scorecard_dir=None):
        league_table = self.run_league_phase(quiet=quiet, scorecard_dir=scorecard_dir)
        return self.run_knockout_phase(league_table, quiet=quiet, scorecard_dir=scorecard_dir)

    def get_tournament_golden_boot(self):
        """Return (player_name, club_name, goals) for top scorer in this tournament"""
        total_scorers = defaultdict(int)
        for club, scorers in self.scorers.items():
            for player, goals in scorers.items():
                total_scorers[(player, club)] += goals

        if total_scorers:
            (player, club), goals = max(total_scorers.items(), key=lambda x: x[1])
            return player, club, goals
        return None, None, 0

    def get_tournament_golden_glove(self):
        """Return (keeper_name, club_name, clean_sheets, saves) for best GK"""
        total_keepers = defaultdict(lambda: {'saves': 0, 'clean_sheets': 0, 'minutes': 0})
        for club in self.all_teams[:self.league_phase_size]:
            for keeper, saves in self.keepers_saves[club].items():
                total_keepers[(keeper, club)]['saves'] += saves
            for keeper, cs in self.keepers_clean_sheets[club].items():
                total_keepers[(keeper, club)]['clean_sheets'] += cs
            for keeper, mins in self.keepers_minutes[club].items():
                total_keepers[(keeper, club)]['minutes'] += mins

        best = None
        best_score = -1
        for (keeper, club), stats in total_keepers.items():
            if stats['minutes'] >= 270:
                score = stats['clean_sheets'] * 3 + stats['saves'] * 0.5
                if score > best_score:
                    best_score = score
                    best = (keeper, club, stats['clean_sheets'], stats['saves'])
        return best

    def get_tournament_playmaker(self):
        """Return (player_name, club_name, assists) for top assister"""
        total_assisters = defaultdict(int)
        for club, assisters in self.assisters.items():
            for player, assists in assisters.items():
                total_assisters[(player, club)] += assists

        if total_assisters:
            (player, club), assists = max(total_assisters.items(), key=lambda x: x[1])
            return player, club, assists
        return None, None, 0

    def get_tournament_best_player(self):
        """Return (player_name, club_name, avg_rating) for best overall player"""
        player_stats = defaultdict(lambda: {'rating_total': 0.0, 'rating_count': 0, 'minutes': 0, 'club': ''})
        for club in self.all_teams[:self.league_phase_size]:
            for player, rating_data in self.player_ratings[club].items():
                player_stats[(player, club)]['rating_total'] += rating_data['total']
                player_stats[(player, club)]['rating_count'] += rating_data['count']
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins

        best = None
        best_rating = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 270 and stats['rating_count'] >= 3:
                avg_rating = stats['rating_total'] / stats['rating_count']
                if avg_rating > best_rating:
                    best_rating = avg_rating
                    best = (player, club, round(avg_rating, 1))
        return best

    def print_awards(self):
        """Print all end-of-tournament awards"""
        print("\n" + "=" * 70)
        print(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS".center(70))
        print("=" * 70)

        boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
        if boot_player:
            print(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals")

        glove = self.get_tournament_golden_glove()
        if glove:
            keeper, club, cs, saves = glove
            print(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves")

        pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
        if pm_player:
            print(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists")

        bp = self.get_tournament_best_player()
        if bp:
            bp_player, bp_club, bp_score = bp
            print(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating")

    def save_results_to_file(self, base_dir="scorecards", season_num=1):
        """Save tournament results to a text file"""
        import os
        from datetime import datetime
        safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        save_dir = os.path.join(base_dir, f"Season_{season_num}", safe_name)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "tournament_results.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name.upper()} SEASON {season_num} RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("[TOURNAMENT WINNER]\n")
            if self.winner:
                f.write(f"  Champion: {self.winner}\n")
            if self.runner_up:
                f.write(f"  Runner-up: {self.runner_up}\n")
            if self.final_score:
                f.write(f"  Final Score: {self.final_score}\n")

            f.write("\n[KNOCKOUT RESULTS]\n")
            for tie, score in self.ko_results.items():
                f.write(f"  {tie}: {score}\n")

            if hasattr(self, 'league_table') and self.league_table:
                f.write("\n[LEAGUE PHASE TABLE]\n")
                f.write(f"{'Pos':<4} {'Team':<30} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}\n")
                f.write("-" * 80 + "\n")
                sorted_table = sorted(
                    self.league_table.items(),
                    key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']),
                    reverse=True
                )
                for idx, (team, stats) in enumerate(sorted_table, 1):
                    f.write(f"{idx:<4} {team:<30} {stats['played']:>3} {stats['won']:>3} {stats['drawn']:>3} {stats['lost']:>3} {stats['gf']:>4} {stats['ga']:>4} {stats['gd']:>+4} {stats['pts']:>4}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS\n")
            f.write("=" * 70 + "\n")

            boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
            if boot_player:
                f.write(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals\n")

            glove = self.get_tournament_golden_glove()
            if glove:
                keeper, club, cs, saves = glove
                f.write(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves\n")

            pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
            if pm_player:
                f.write(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists\n")

            bp = self.get_tournament_best_player()
            if bp:
                bp_player, bp_club, bp_score = bp
                f.write(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating\n")

            f.write("=" * 70 + "\n")

        return filepath


class CONMEBOLTournament:
    """Copa Libertadores/Sudamericana: Group stage + Knockout"""

    def __init__(self, name, teams, groups=8, group_size=4, ko_from_group=2, save_scorecards=False):
        self.name = name
        self.all_teams = list(teams)
        self.groups = groups
        self.group_size = group_size
        self.ko_from_group = ko_from_group
        self.save_scorecards = save_scorecards
        self.group_tables = {}
        self.ko_results = {}
        self.winner = None
        self.runner_up = None
        self.scorers = defaultdict(lambda: defaultdict(int))
        self.assisters = defaultdict(lambda: defaultdict(int))
        self.keepers_saves = defaultdict(lambda: defaultdict(int))
        self.keepers_clean_sheets = defaultdict(lambda: defaultdict(int))
        self.keepers_minutes = defaultdict(lambda: defaultdict(int))
        self.player_minutes = defaultdict(lambda: defaultdict(int))
        self.player_ratings = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'count': 0}))

    def _create_groups(self):
        """Create balanced groups using pot system"""
        n_teams = self.groups * self.group_size
        teams = self.all_teams[:n_teams]

        from elo import get_club_elo
        teams_sorted = sorted(teams, key=lambda t: get_club_elo(t), reverse=True)

        pots = []
        for i in range(self.group_size):
            start = i * self.groups
            end = start + self.groups
            pots.append(teams_sorted[start:end])

        groups = {f'Group {chr(65+i)}': [] for i in range(self.groups)}
        for pot in pots:
            random.shuffle(pot)
            for i, team in enumerate(pot):
                groups[f'Group {chr(65+i)}'].append(team)

        return groups

    def run_group_stage(self, quiet=True, scorecard_dir=None):
        groups = self._create_groups()

        if not quiet:
            print(f"  {self.name} Group Stage: {self.groups} groups of {self.group_size}")

        old_stdout = None
        devnull = None
        if quiet:
            old_stdout = sys.stdout
            devnull = open(os.devnull, 'w', encoding='utf-8')
            sys.stdout = devnull

        group_stage_dir = None
        if self.save_scorecards and scorecard_dir:
            group_stage_dir = os.path.join(scorecard_dir, "Group_Stage")
            os.makedirs(group_stage_dir, exist_ok=True)

        for group_name, teams in groups.items():
            self.group_tables[group_name] = {team: {'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0} for team in teams}

            group_dir = None
            if self.save_scorecards and group_stage_dir:
                group_dir = os.path.join(group_stage_dir, group_name.replace(' ', '_'))
                os.makedirs(group_dir, exist_ok=True)

            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    t1, t2 = teams[i], teams[j]
                    for home, away in [(t1, t2), (t2, t1)]:
                        h_score, a_score, fix = _simulate_match(home, away, save_scorecard=self.save_scorecards, scorecard_dir=group_dir)

                        for team, gf, ga in [(home, h_score, a_score), (away, a_score, h_score)]:
                            self.group_tables[group_name][team]['played'] += 1
                            self.group_tables[group_name][team]['gf'] += gf
                            self.group_tables[group_name][team]['ga'] += ga
                            self.group_tables[group_name][team]['gd'] = self.group_tables[group_name][team]['gf'] - self.group_tables[group_name][team]['ga']
                            if gf > ga:
                                self.group_tables[group_name][team]['won'] += 1
                                self.group_tables[group_name][team]['pts'] += 3
                            elif gf == ga:
                                self.group_tables[group_name][team]['drawn'] += 1
                                self.group_tables[group_name][team]['pts'] += 1
                            else:
                                self.group_tables[group_name][team]['lost'] += 1

                        if fix:
                            self._track_match_stats(fix, home, away)

        if quiet and old_stdout is not None:
            sys.stdout = old_stdout
            if devnull:
                devnull.close()

        qualifiers = []
        for group_name in sorted(groups.keys()):
            table = sorted(
                self.group_tables[group_name].items(),
                key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']),
                reverse=True
            )
            qualifiers.extend([team for team, _ in table[:self.ko_from_group]])

        return qualifiers

    def run_knockout(self, qualifiers, quiet=True, scorecard_dir=None):
        group_winners = qualifiers[::self.ko_from_group]
        runners_up = qualifiers[1::self.ko_from_group]

        random.shuffle(group_winners)
        random.shuffle(runners_up)

        r16 = list(zip(group_winners, runners_up))

        round_names = ['Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
        current_round = r16

        for round_name in round_names:
            next_round = []
            is_final = (round_name == 'Final')
            for t1, t2 in current_round:
                tie_dir = None
                if self.save_scorecards and scorecard_dir:
                    tie_dir = os.path.join(scorecard_dir, f"{round_name}_{t1}_vs_{t2}".replace(' ', '_'))
                    os.makedirs(tie_dir, exist_ok=True)
                winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, is_final=is_final, save_scorecard=self.save_scorecards, scorecard_dir=tie_dir)
                next_round.append(winner)
                self.ko_results[f'{round_name}: {t1} vs {t2}'] = score
                if fix1:
                    self._track_match_stats(fix1, t1, t2)
                if fix2:
                    self._track_match_stats(fix2, t2, t1)
                if is_final:
                    self.winner = winner
                    self.runner_up = t2 if winner == t1 else t1
                    self.final_score = score
            current_round = [(next_round[i], next_round[i+1]) for i in range(0, len(next_round), 2)] if not is_final else []

        return self.winner, self.runner_up

    def run(self, quiet=True, scorecard_dir=None):
        qualifiers = self.run_group_stage(quiet=quiet, scorecard_dir=scorecard_dir)
        return self.run_knockout(qualifiers, quiet=quiet, scorecard_dir=scorecard_dir)

    def get_tournament_golden_boot(self):
        total_scorers = defaultdict(int)
        for club, scorers in self.scorers.items():
            for player, goals in scorers.items():
                total_scorers[(player, club)] += goals
        if total_scorers:
            (player, club), goals = max(total_scorers.items(), key=lambda x: x[1])
            return player, club, goals
        return None, None, 0

    def get_tournament_golden_glove(self):
        total_keepers = defaultdict(lambda: {'saves': 0, 'clean_sheets': 0, 'minutes': 0})
        n_teams = self.groups * self.group_size
        for club in self.all_teams[:n_teams]:
            for keeper, saves in self.keepers_saves[club].items():
                total_keepers[(keeper, club)]['saves'] += saves
            for keeper, cs in self.keepers_clean_sheets[club].items():
                total_keepers[(keeper, club)]['clean_sheets'] += cs
            for keeper, mins in self.keepers_minutes[club].items():
                total_keepers[(keeper, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (keeper, club), stats in total_keepers.items():
            if stats['minutes'] >= 180:
                score = stats['clean_sheets'] * 3 + stats['saves'] * 0.5
                if score > best_score:
                    best_score = score
                    best = (keeper, club, stats['clean_sheets'], stats['saves'])
        return best

    def get_tournament_playmaker(self):
        total_assisters = defaultdict(int)
        for club, assisters in self.assisters.items():
            for player, assists in assisters.items():
                total_assisters[(player, club)] += assists
        if total_assisters:
            (player, club), assists = max(total_assisters.items(), key=lambda x: x[1])
            return player, club, assists
        return None, None, 0

    def get_tournament_best_player(self):
        player_stats = defaultdict(lambda: {'goals': 0, 'assists': 0, 'minutes': 0, 'club': ''})
        n_teams = self.groups * self.group_size
        for club in self.all_teams[:n_teams]:
            for player, goals in self.scorers[club].items():
                player_stats[(player, club)]['goals'] += goals
                player_stats[(player, club)]['club'] = club
            for player, assists in self.assisters[club].items():
                player_stats[(player, club)]['assists'] += assists
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 180:
                score = stats['goals'] * 2.0 + stats['assists'] * 1.5
                if score > best_score:
                    best_score = score
                    best = (player, club, score)
        return best

    def print_awards(self):
        print("\n" + "=" * 70)
        print(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS".center(70))
        print("=" * 70)
        boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
        if boot_player:
            print(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals")
        glove = self.get_tournament_golden_glove()
        if glove:
            keeper, club, cs, saves = glove
            print(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves")
        pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
        if pm_player:
            print(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists")
        bp = self.get_tournament_best_player()
        if bp:
            bp_player, bp_club, bp_score = bp
            print(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating")

    def save_results_to_file(self, base_dir="scorecards", season_num=1):
        import os
        from datetime import datetime
        safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        save_dir = os.path.join(base_dir, f"Season_{season_num}", safe_name)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "tournament_results.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name.upper()} SEASON {season_num} RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("[TOURNAMENT WINNER]\n")
            if self.winner:
                f.write(f"  Champion: {self.winner}\n")
            if self.runner_up:
                f.write(f"  Runner-up: {self.runner_up}\n")
            if self.final_score:
                f.write(f"  Final Score: {self.final_score}\n")

            f.write("\n[KNOCKOUT RESULTS]\n")
            for tie, score in self.ko_results.items():
                f.write(f"  {tie}: {score}\n")

            if hasattr(self, 'group_tables') and self.group_tables:
                f.write("\n[GROUP STAGE TABLES]\n")
                for group_name in sorted(self.group_tables.keys()):
                    f.write(f"\n  {group_name}:\n")
                    table = sorted(
                        self.group_tables[group_name].items(),
                        key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']),
                        reverse=True
                    )
                    f.write(f"    {'Pos':<4} {'Team':<30} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}\n")
                    for idx, (team, stats) in enumerate(table, 1):
                        f.write(f"    {idx:<4} {team:<30} {stats['played']:>3} {stats['won']:>3} {stats['drawn']:>3} {stats['lost']:>3} {stats['gf']:>4} {stats['ga']:>4} {stats['gd']:>+4} {stats['pts']:>4}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS\n")
            f.write("=" * 70 + "\n")

            boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
            if boot_player:
                f.write(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals\n")

            glove = self.get_tournament_golden_glove()
            if glove:
                keeper, club, cs, saves = glove
                f.write(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves\n")

            pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
            if pm_player:
                f.write(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists\n")

            bp = self.get_tournament_best_player()
            if bp:
                bp_player, bp_club, bp_score = bp
                f.write(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating\n")

            f.write("=" * 70 + "\n")

        return filepath


class CONCACAFChampionsCup:
    """CONCACAF Champions Cup: Round One -> Round of 16 -> QF -> SF -> Final"""

    def __init__(self, name, teams, round_one_slots=27, save_scorecards=False):
        self.name = name
        self.all_teams = list(teams)
        self.round_one_slots = round_one_slots
        self.save_scorecards = save_scorecards
        self.ko_results = {}
        self.winner = None
        self.runner_up = None
        self.scorers = defaultdict(lambda: defaultdict(int))
        self.assisters = defaultdict(lambda: defaultdict(int))
        self.keepers_saves = defaultdict(lambda: defaultdict(int))
        self.keepers_clean_sheets = defaultdict(lambda: defaultdict(int))
        self.keepers_minutes = defaultdict(lambda: defaultdict(int))
        self.player_minutes = defaultdict(lambda: defaultdict(int))
        self.player_ratings = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'count': 0}))

    def run(self, quiet=True, scorecard_dir=None):
        teams = self.all_teams[:self.round_one_slots]
        n_byes = max(0, 16 - len(teams))
        byes = teams[:n_byes] if n_byes > 0 else []
        round_one_teams = teams[n_byes:]

        round_one_winners = []
        for i in range(0, len(round_one_teams), 2):
            if i + 1 < len(round_one_teams):
                t1, t2 = round_one_teams[i], round_one_teams[i+1]
                tie_dir = None
                if self.save_scorecards and scorecard_dir:
                    tie_dir = os.path.join(scorecard_dir, f"Round_One_{t1}_vs_{t2}".replace(' ', '_'))
                    os.makedirs(tie_dir, exist_ok=True)
                winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, save_scorecard=self.save_scorecards, scorecard_dir=tie_dir)
                round_one_winners.append(winner)
                self.ko_results[f'Round One: {t1} vs {t2}'] = score
                if fix1:
                    self._track_match_stats(fix1, t1, t2)
                if fix2:
                    self._track_match_stats(fix2, t2, t1)
            else:
                round_one_winners.append(round_one_teams[i])

        r16 = byes + round_one_winners
        random.shuffle(r16)

        round_names = ['Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
        current_round = []
        for i in range(0, len(r16), 2):
            if i + 1 < len(r16):
                current_round.append((r16[i], r16[i+1]))
            else:
                current_round.append((r16[i], None))

        for round_name in round_names:
            next_round = []
            is_final = (round_name == 'Final')
            for t1, t2 in current_round:
                if t2 is None:
                    next_round.append(t1)
                    continue
                tie_dir = None
                if self.save_scorecards and scorecard_dir:
                    tie_dir = os.path.join(scorecard_dir, f"{round_name}_{t1}_vs_{t2}".replace(' ', '_'))
                    os.makedirs(tie_dir, exist_ok=True)
                winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, is_final=is_final, save_scorecard=self.save_scorecards, scorecard_dir=tie_dir)
                next_round.append(winner)
                self.ko_results[f'{round_name}: {t1} vs {t2}'] = score
                if fix1:
                    self._track_match_stats(fix1, t1, t2)
                if fix2:
                    self._track_match_stats(fix2, t2, t1)
                if is_final:
                    self.winner = winner
                    self.runner_up = t2 if winner == t1 else t1
                    self.final_score = score
            if not is_final:
                new_current = []
                for i in range(0, len(next_round), 2):
                    if i + 1 < len(next_round):
                        new_current.append((next_round[i], next_round[i+1]))
                    else:
                        new_current.append((next_round[i], None))
                current_round = new_current

        return self.winner, self.runner_up

    def _track_match_stats(self, fix, home_name, away_name):
        if not fix or not hasattr(fix, 'periods') or not fix.periods:
            return
        for p in fix.home.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[home_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[home_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[home_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[home_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[home_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[home_name][p_name] += perf.saves
                    self.keepers_minutes[home_name][p_name] += 90
                    if fix.away_score == 0:
                        self.keepers_clean_sheets[home_name][p_name] += 1
        for p in fix.away.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[away_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[away_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[away_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[away_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[away_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[away_name][p_name] += perf.saves
                    self.keepers_minutes[away_name][p_name] += 90
                    if fix.home_score == 0:
                        self.keepers_clean_sheets[away_name][p_name] += 1

    def get_tournament_best_player(self):
        """Return (player_name, club_name, avg_rating) for best overall player"""
        player_stats = defaultdict(lambda: {'rating_total': 0.0, 'rating_count': 0, 'minutes': 0, 'club': ''})
        for club in self.all_teams[:self.round_one_slots]:
            for player, rating_data in self.player_ratings[club].items():
                player_stats[(player, club)]['rating_total'] += rating_data['total']
                player_stats[(player, club)]['rating_count'] += rating_data['count']
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins

        best = None
        best_rating = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 180 and stats['rating_count'] >= 3:
                avg_rating = stats['rating_total'] / stats['rating_count']
                if avg_rating > best_rating:
                    best_rating = avg_rating
                    best = (player, club, round(avg_rating, 1))
        return best

    def get_tournament_golden_boot(self):
        total_scorers = defaultdict(int)
        for club, scorers in self.scorers.items():
            for player, goals in scorers.items():
                total_scorers[(player, club)] += goals
        if total_scorers:
            (player, club), goals = max(total_scorers.items(), key=lambda x: x[1])
            return player, club, goals
        return None, None, 0

    def get_tournament_golden_glove(self):
        total_keepers = defaultdict(lambda: {'saves': 0, 'clean_sheets': 0, 'minutes': 0})
        for club in self.all_teams[:self.round_one_slots]:
            for keeper, saves in self.keepers_saves[club].items():
                total_keepers[(keeper, club)]['saves'] += saves
            for keeper, cs in self.keepers_clean_sheets[club].items():
                total_keepers[(keeper, club)]['clean_sheets'] += cs
            for keeper, mins in self.keepers_minutes[club].items():
                total_keepers[(keeper, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (keeper, club), stats in total_keepers.items():
            if stats['minutes'] >= 180:
                score = stats['clean_sheets'] * 3 + stats['saves'] * 0.5
                if score > best_score:
                    best_score = score
                    best = (keeper, club, stats['clean_sheets'], stats['saves'])
        return best

    def get_tournament_playmaker(self):
        total_assisters = defaultdict(int)
        for club, assisters in self.assisters.items():
            for player, assists in assisters.items():
                total_assisters[(player, club)] += assists
        if total_assisters:
            (player, club), assists = max(total_assisters.items(), key=lambda x: x[1])
            return player, club, assists
        return None, None, 0

    def get_tournament_best_player(self):
        player_stats = defaultdict(lambda: {'goals': 0, 'assists': 0, 'minutes': 0, 'club': ''})
        for club in self.all_teams[:self.round_one_slots]:
            for player, goals in self.scorers[club].items():
                player_stats[(player, club)]['goals'] += goals
                player_stats[(player, club)]['club'] = club
            for player, assists in self.assisters[club].items():
                player_stats[(player, club)]['assists'] += assists
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 180:
                score = stats['goals'] * 2.0 + stats['assists'] * 1.5
                if score > best_score:
                    best_score = score
                    best = (player, club, score)
        return best

    def print_awards(self):
        print("\n" + "=" * 70)
        print(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS".center(70))
        print("=" * 70)
        boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
        if boot_player:
            print(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals")
        glove = self.get_tournament_golden_glove()
        if glove:
            keeper, club, cs, saves = glove
            print(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves")
        pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
        if pm_player:
            print(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists")
        bp = self.get_tournament_best_player()
        if bp:
            bp_player, bp_club, bp_score = bp
            print(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating")

    def save_results_to_file(self, base_dir="scorecards", season_num=1):
        import os
        from datetime import datetime
        safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        save_dir = os.path.join(base_dir, f"Season_{season_num}", safe_name)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "tournament_results.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name.upper()} SEASON {season_num} RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("[TOURNAMENT WINNER]\n")
            if self.winner:
                f.write(f"  Champion: {self.winner}\n")
            if self.runner_up:
                f.write(f"  Runner-up: {self.runner_up}\n")
            if self.final_score:
                f.write(f"  Final Score: {self.final_score}\n")

            f.write("\n[KNOCKOUT RESULTS]\n")
            for tie, score in self.ko_results.items():
                f.write(f"  {tie}: {score}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS\n")
            f.write("=" * 70 + "\n")

            boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
            if boot_player:
                f.write(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals\n")

            glove = self.get_tournament_golden_glove()
            if glove:
                keeper, club, cs, saves = glove
                f.write(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves\n")

            pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
            if pm_player:
                f.write(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists\n")

            bp = self.get_tournament_best_player()
            if bp:
                bp_player, bp_club, bp_score = bp
                f.write(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating\n")

            f.write("=" * 70 + "\n")

        return filepath


class AFCModernTournament:
    """AFC Champions League Elite/Two: League phase + Knockout"""

    def __init__(self, name, teams, league_phase_size=24, league_phase_matches=8,
                 direct_ko_slots=8, playoff_range=(9, 16), save_scorecards=False):
        self.name = name
        self.all_teams = list(teams)
        self.league_phase_size = min(league_phase_size, len(self.all_teams))
        self.league_phase_matches = league_phase_matches
        self.direct_ko_slots = direct_ko_slots
        self.playoff_start, self.playoff_end = playoff_range
        self.save_scorecards = save_scorecards
        self.league_table = {}
        self.ko_results = {}
        self.winner = None
        self.runner_up = None
        self.scorers = defaultdict(lambda: defaultdict(int))
        self.assisters = defaultdict(lambda: defaultdict(int))
        self.keepers_saves = defaultdict(lambda: defaultdict(int))
        self.keepers_clean_sheets = defaultdict(lambda: defaultdict(int))
        self.keepers_minutes = defaultdict(lambda: defaultdict(int))
        self.player_minutes = defaultdict(lambda: defaultdict(int))
        self.player_ratings = defaultdict(lambda: defaultdict(lambda: {'total': 0.0, 'count': 0}))

    def run_league_phase(self, quiet=True):
        teams = self.all_teams[:self.league_phase_size]
        n = len(teams)

        self.league_table = {team: {'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0} for team in teams}

        matches = []
        for i in range(n):
            for j in range(i+1, min(i+1 + self.league_phase_matches//2, n)):
                if len(matches) >= n * self.league_phase_matches // 2:
                    break
                matches.append((teams[i], teams[j]))

        if not quiet:
            print(f"  {self.name} League Phase: {len(matches)} matches")

        old_stdout = None
        devnull = None
        if quiet:
            old_stdout = sys.stdout
            devnull = open(os.devnull, 'w', encoding='utf-8')
            sys.stdout = devnull

        for home, away in matches:
            h_score, a_score, fix = _simulate_match(home, away, save_scorecard=self.save_scorecards)
            for team, gf, ga in [(home, h_score, a_score), (away, a_score, h_score)]:
                self.league_table[team]['played'] += 1
                self.league_table[team]['gf'] += gf
                self.league_table[team]['ga'] += ga
                self.league_table[team]['gd'] = self.league_table[team]['gf'] - self.league_table[team]['ga']
                if gf > ga:
                    self.league_table[team]['won'] += 1
                    self.league_table[team]['pts'] += 3
                elif gf == ga:
                    self.league_table[team]['drawn'] += 1
                    self.league_table[team]['pts'] += 1
                else:
                    self.league_table[team]['lost'] += 1
            if fix:
                self._track_match_stats(fix, home, away)

        if quiet and old_stdout is not None:
            sys.stdout = old_stdout
            if devnull:
                devnull.close()

        return sorted(self.league_table.items(), key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']), reverse=True)

    def _track_match_stats(self, fix, home_name, away_name):
        if not fix or not hasattr(fix, 'periods') or not fix.periods:
            return
        for p in fix.home.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[home_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[home_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[home_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[home_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[home_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[home_name][p_name] += perf.saves
                    self.keepers_minutes[home_name][p_name] += 90
                    if fix.away_score == 0:
                        self.keepers_clean_sheets[home_name][p_name] += 1
        for p in fix.away.xi:
            p_name = getattr(p, 'short_name', '') or p.name
            self.player_minutes[away_name][p_name] += 90
            if hasattr(p, 'inns') and p.inns:
                perf = p.inns[-1]
                self.player_ratings[away_name][p_name]['total'] += getattr(perf, 'rating', 6.0)
                self.player_ratings[away_name][p_name]['count'] += 1
                if perf.goals > 0:
                    self.scorers[away_name][p_name] += perf.goals
                if perf.assists > 0:
                    self.assisters[away_name][p_name] += perf.assists
                if getattr(p, 'position', '') == 'GK':
                    self.keepers_saves[away_name][p_name] += perf.saves
                    self.keepers_minutes[away_name][p_name] += 90
                    if fix.home_score == 0:
                        self.keepers_clean_sheets[away_name][p_name] += 1

    def get_tournament_best_player(self):
        """Return (player_name, club_name, avg_rating) for best overall player"""
        player_stats = defaultdict(lambda: {'rating_total': 0.0, 'rating_count': 0, 'minutes': 0, 'club': ''})
        for club in self.all_teams[:self.league_phase_size]:
            for player, rating_data in self.player_ratings[club].items():
                player_stats[(player, club)]['rating_total'] += rating_data['total']
                player_stats[(player, club)]['rating_count'] += rating_data['count']
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins

        best = None
        best_rating = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 270 and stats['rating_count'] >= 3:
                avg_rating = stats['rating_total'] / stats['rating_count']
                if avg_rating > best_rating:
                    best_rating = avg_rating
                    best = (player, club, round(avg_rating, 1))
        return best

    def run_knockout(self, league_table, quiet=True):
        direct = [team for team, _ in league_table[:self.direct_ko_slots]]
        playoff = [team for team, _ in league_table[self.playoff_start-1:self.playoff_end]]

        playoff_winners = []
        for i in range(len(playoff) // 2):
            t1 = playoff[i]
            t2 = playoff[len(playoff) - 1 - i]
            winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, save_scorecard=self.save_scorecards)
            playoff_winners.append(winner)
            self.ko_results[f'Playoff: {t1} vs {t2}'] = score
            if fix1:
                self._track_match_stats(fix1, t1, t2)
            if fix2:
                self._track_match_stats(fix2, t2, t1)

        ko_teams = direct + playoff_winners
        random.shuffle(ko_teams)

        round_names = ['Round of 16', 'Quarter-finals', 'Semi-finals', 'Final']
        current_round = ko_teams

        for round_name in round_names:
            next_round = []
            is_final = (round_name == 'Final')
            for i in range(0, len(current_round), 2):
                if i + 1 < len(current_round):
                    t1 = current_round[i]
                    t2 = current_round[i + 1]
                    winner, score, fix1, fix2 = _simulate_two_legged_tie(t1, t2, is_final=is_final, save_scorecard=self.save_scorecards)
                    next_round.append(winner)
                    self.ko_results[f'{round_name}: {t1} vs {t2}'] = score
                    if fix1:
                        self._track_match_stats(fix1, t1, t2)
                    if fix2:
                        self._track_match_stats(fix2, t2, t1)
                    if is_final:
                        self.winner = winner
                        self.runner_up = t2 if winner == t1 else t1
                        self.final_score = score
            current_round = next_round

        return self.winner, self.runner_up

    def run(self, quiet=True):
        league_table = self.run_league_phase(quiet=quiet)
        return self.run_knockout(league_table, quiet=quiet)

    def get_tournament_golden_boot(self):
        total_scorers = defaultdict(int)
        for club, scorers in self.scorers.items():
            for player, goals in scorers.items():
                total_scorers[(player, club)] += goals
        if total_scorers:
            (player, club), goals = max(total_scorers.items(), key=lambda x: x[1])
            return player, club, goals
        return None, None, 0

    def get_tournament_golden_glove(self):
        total_keepers = defaultdict(lambda: {'saves': 0, 'clean_sheets': 0, 'minutes': 0})
        for club in self.all_teams[:self.league_phase_size]:
            for keeper, saves in self.keepers_saves[club].items():
                total_keepers[(keeper, club)]['saves'] += saves
            for keeper, cs in self.keepers_clean_sheets[club].items():
                total_keepers[(keeper, club)]['clean_sheets'] += cs
            for keeper, mins in self.keepers_minutes[club].items():
                total_keepers[(keeper, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (keeper, club), stats in total_keepers.items():
            if stats['minutes'] >= 270:
                score = stats['clean_sheets'] * 3 + stats['saves'] * 0.5
                if score > best_score:
                    best_score = score
                    best = (keeper, club, stats['clean_sheets'], stats['saves'])
        return best

    def get_tournament_playmaker(self):
        total_assisters = defaultdict(int)
        for club, assisters in self.assisters.items():
            for player, assists in assisters.items():
                total_assisters[(player, club)] += assists
        if total_assisters:
            (player, club), assists = max(total_assisters.items(), key=lambda x: x[1])
            return player, club, assists
        return None, None, 0

    def get_tournament_best_player(self):
        player_stats = defaultdict(lambda: {'goals': 0, 'assists': 0, 'minutes': 0, 'club': ''})
        for club in self.all_teams[:self.league_phase_size]:
            for player, goals in self.scorers[club].items():
                player_stats[(player, club)]['goals'] += goals
                player_stats[(player, club)]['club'] = club
            for player, assists in self.assisters[club].items():
                player_stats[(player, club)]['assists'] += assists
                player_stats[(player, club)]['club'] = club
            for player, mins in self.player_minutes[club].items():
                player_stats[(player, club)]['minutes'] += mins
        best = None
        best_score = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 270:
                score = stats['goals'] * 2.0 + stats['assists'] * 1.5
                if score > best_score:
                    best_score = score
                    best = (player, club, score)
        return best

    def print_awards(self):
        print("\n" + "=" * 70)
        print(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS".center(70))
        print("=" * 70)
        boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
        if boot_player:
            print(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals")
        glove = self.get_tournament_golden_glove()
        if glove:
            keeper, club, cs, saves = glove
            print(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves")
        pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
        if pm_player:
            print(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists")
        bp = self.get_tournament_best_player()
        if bp:
            bp_player, bp_club, bp_score = bp
            print(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating")

    def save_results_to_file(self, base_dir="scorecards", season_num=1):
        import os
        from datetime import datetime
        safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        save_dir = os.path.join(base_dir, f"Season_{season_num}", safe_name)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "tournament_results.txt")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name.upper()} SEASON {season_num} RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("[TOURNAMENT WINNER]\n")
            if self.winner:
                f.write(f"  Champion: {self.winner}\n")
            if self.runner_up:
                f.write(f"  Runner-up: {self.runner_up}\n")
            if self.final_score:
                f.write(f"  Final Score: {self.final_score}\n")

            f.write("\n[KNOCKOUT RESULTS]\n")
            for tie, score in self.ko_results.items():
                f.write(f"  {tie}: {score}\n")

            if hasattr(self, 'league_table') and self.league_table:
                f.write("\n[LEAGUE PHASE TABLE]\n")
                f.write(f"{'Pos':<4} {'Team':<30} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}\n")
                f.write("-" * 80 + "\n")
                sorted_table = sorted(
                    self.league_table.items(),
                    key=lambda x: (x[1]['pts'], x[1]['gd'], x[1]['gf']),
                    reverse=True
                )
                for idx, (team, stats) in enumerate(sorted_table, 1):
                    f.write(f"{idx:<4} {team:<30} {stats['played']:>3} {stats['won']:>3} {stats['drawn']:>3} {stats['lost']:>3} {stats['gf']:>4} {stats['ga']:>4} {stats['gd']:>+4} {stats['pts']:>4}\n")

            f.write("\n" + "=" * 70 + "\n")
            f.write(f"{self.name.upper()} END-OF-TOURNAMENT AWARDS\n")
            f.write("=" * 70 + "\n")

            boot_player, boot_club, boot_goals = self.get_tournament_golden_boot()
            if boot_player:
                f.write(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals\n")

            glove = self.get_tournament_golden_glove()
            if glove:
                keeper, club, cs, saves = glove
                f.write(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves\n")

            pm_player, pm_club, pm_assists = self.get_tournament_playmaker()
            if pm_player:
                f.write(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists\n")

            bp = self.get_tournament_best_player()
            if bp:
                bp_player, bp_club, bp_score = bp
                f.write(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating\n")

            f.write("=" * 70 + "\n")

        return filepath


class CAFTournament:
    """CAF Champions League/Confederation Cup: Group stage + Knockout"""

    def __init__(self, name, teams, groups=8, group_size=4, ko_from_group=2, save_scorecards=False):
        self.tournament = CONMEBOLTournament(name, teams, groups, group_size, ko_from_group, save_scorecards)
        self.tournament.name = name
        self.winner = None
        self.runner_up = None
        self.ko_results = {}

    def run(self, quiet=True):
        w, ru = self.tournament.run(quiet=quiet)
        self.winner = w
        self.runner_up = ru
        self.ko_results = self.tournament.ko_results
        self.group_tables = self.tournament.group_tables
        return w, ru

    def get_tournament_golden_boot(self):
        return self.tournament.get_tournament_golden_boot()

    def get_tournament_golden_glove(self):
        return self.tournament.get_tournament_golden_glove()

    def get_tournament_playmaker(self):
        return self.tournament.get_tournament_playmaker()

    def get_tournament_best_player(self):
        return self.tournament.get_tournament_best_player()

    def print_awards(self):
        self.tournament.print_awards()

    def save_results_to_file(self, base_dir="scorecards", season_num=1):
        return self.tournament.save_results_to_file(base_dir, season_num)


class ContinentalSeasonSimulator:
    def __init__(self, continents, seasons_count=1, max_domestic_rounds=None, save_scorecards=False, scorecard_root="scorecards", save_results=False):
        self.continents = continents
        self.seasons_count = seasons_count
        self.max_domestic_rounds = max_domestic_rounds
        self.save_scorecards = save_scorecards
        self.scorecard_root = scorecard_root
        self.save_results = save_results
        self.history = []
        self.trophy_cabinet = defaultdict(lambda: defaultdict(int))

    def _create_tournament(self, t_meta, participants):
        """Factory method to create appropriate tournament instance"""
        fmt = t_meta.get('format', 'knockout')
        save_sc = self.save_scorecards

        if fmt == 'uefa_modern':
            return UEFAModernTournament(
                t_meta['name'], participants,
                league_phase_size=t_meta.get('league_phase_size', 36),
                league_phase_matches=t_meta.get('league_phase_matches', 8),
                direct_ko_slots=t_meta.get('direct_ko_slots', 8),
                playoff_range=t_meta.get('playoff_range', (9, 24)),
                save_scorecards=save_sc
            )
        elif fmt == 'uefa_womens':
            return UEFAModernTournament(
                t_meta['name'], participants,
                league_phase_size=t_meta.get('league_phase_size', 16),
                league_phase_matches=t_meta.get('league_phase_matches', 6),
                direct_ko_slots=t_meta.get('direct_ko_slots', 4),
                playoff_range=t_meta.get('playoff_range', (5, 12)),
                save_scorecards=save_sc
            )
        elif fmt == 'conmebol':
            return CONMEBOLTournament(
                t_meta['name'], participants,
                groups=t_meta.get('groups', 8),
                group_size=t_meta.get('group_size', 4),
                ko_from_group=t_meta.get('ko_from_group', 2),
                save_scorecards=save_sc
            )
        elif fmt == 'concacaf':
            return CONCACAFChampionsCup(
                t_meta['name'], participants,
                round_one_slots=t_meta.get('round_one_slots', 27),
                save_scorecards=save_sc
            )
        elif fmt == 'afc_modern':
            return AFCModernTournament(
                t_meta['name'], participants,
                league_phase_size=t_meta.get('league_phase_size', 24),
                league_phase_matches=t_meta.get('league_phase_matches', 8),
                direct_ko_slots=t_meta.get('direct_ko_slots', 8),
                playoff_range=t_meta.get('playoff_range', (9, 16)),
                save_scorecards=save_sc
            )
        elif fmt == 'caf':
            return CAFTournament(
                t_meta['name'], participants,
                groups=t_meta.get('groups', 8),
                group_size=t_meta.get('group_size', 4),
                ko_from_group=t_meta.get('ko_from_group', 2),
                save_scorecards=save_sc
            )
        else:
            from season import KnockoutTournament
            return KnockoutTournament(t_meta['name'], participants[:t_meta.get('size', 16)])

    def run(self, show_progress=True):
        all_leagues = load_all_leagues()
        all_clubs = load_all_clubs()

        season_iterator = tqdm(range(1, self.seasons_count + 1), desc="Simulating seasons", unit="season") if show_progress else range(1, self.seasons_count + 1)
        for s_num in season_iterator:
            season_data = {
                'season': s_num,
                'domestic_winners': {},
                'continental_winners': {},
                'domestic_leagues': {},
                'continental_cups': {}
            }

            qualified_for_cups = defaultdict(list)

            for cont in self.continents:
                flagship_ids = FLAGSHIP_DOMESTIC_LEAGUES.get(cont, [])
                if not flagship_ids:
                    flagship_ids = [l_id for l_id, l_data in all_leagues.items() if l_data['continent'] == cont and l_data['tier'] == 1][:3]

                domestic_leagues = flagship_ids
                for l_id in tqdm(domestic_leagues, desc=f"  {cont} domestic leagues", unit="league", leave=False):
                    lg = get_league(l_id)
                    if not lg:
                        continue
                    lg_scorecard_dir = None
                    if self.save_scorecards:
                        import datetime
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        safe_lg_name = "".join(c for c in lg.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                        lg_scorecard_dir = os.path.join(self.scorecard_root, f"Season_{s_num}", safe_lg_name)
                        os.makedirs(lg_scorecard_dir, exist_ok=True)
                    standings = lg.simulate_season(quiet=True, max_matchdays=self.max_domestic_rounds,
                                                  save_scorecards=self.save_scorecards, scorecard_base_dir=lg_scorecard_dir)
                    if standings:
                        champ = standings[0].club_name
                        season_data['domestic_winners'][lg.name] = champ
                        season_data['domestic_leagues'][lg.name] = lg
                        self.trophy_cabinet[champ]['Domestic League'] += 1

                        for idx, entry in enumerate(standings[:8]):
                            qualified_for_cups[l_id].append(entry.club_name)

                tournaments = CONTINENTAL_TOURNAMENTS.get(cont, [])
                teams_already_assigned = set()
                for t_meta in tqdm(tournaments, desc=f"  {cont} tournaments", unit="tournament", leave=False):
                    t_name = t_meta['name']
                    participants = []
                    for src_id, count in t_meta['sources']:
                        cands = qualified_for_cups.get(src_id, [])
                        if cands:
                            available = [c for c in cands if c not in teams_already_assigned]
                            participants.extend(available[:count])
                        else:
                            l_obj = all_leagues.get(src_id)
                            if l_obj and l_obj.get('clubs'):
                                available = [c for c in l_obj['clubs'] if c not in teams_already_assigned]
                                participants.extend(available[:count])

                    if len(participants) < 4:
                        cont_pool = [c['name'] for c in all_clubs.values() if c['continent'] == cont and c['gender'] == t_meta['gender'] and c['name'] not in teams_already_assigned]
                        if cont_pool:
                            participants.extend(random.sample(cont_pool, min(len(cont_pool), t_meta.get('league_phase_size', t_meta.get('size', 16)) - len(participants))))

                    if len(participants) >= 4:
                        for p in participants:
                            teams_already_assigned.add(p)
                        cup = self._create_tournament(t_meta, participants)
                        t_scorecard_dir = None
                        if self.save_scorecards:
                            import datetime
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            safe_t_name = "".join(c for c in t_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                            t_scorecard_dir = os.path.join(self.scorecard_root, f"Season_{s_num}", safe_t_name)
                            os.makedirs(t_scorecard_dir, exist_ok=True)
                        w, ru = cup.run(scorecard_dir=t_scorecard_dir)
                        season_data['continental_winners'][t_name] = (w, ru)
                        season_data['continental_cups'][t_name] = cup
                        self.trophy_cabinet[w][t_name] += 1

                        if self.save_results:
                            cup.save_results_to_file(self.scorecard_root, s_num)
                            if hasattr(cup, 'print_awards'):
                                cup.print_awards()

            self.history.append(season_data)

        if self.save_results:
            for s in self.history:
                for l_name, lg in s.get('domestic_leagues', {}).items():
                    lg.save_results_to_file(self.scorecard_root, s['season'])

        return self.history

    def print_awards(self):
        """Print all awards for the last simulated season"""
        if not self.history:
            return
        latest = self.history[-1]
        print(f"\n{'='*88}")
        print(f"END-OF-SEASON AWARDS - SEASON {latest['season']}".center(88))
        print(f"{'='*88}")
        print(f"\nDOMESTIC LEAGUE AWARDS:")
        for l_name, lg in latest.get('domestic_leagues', {}).items():
            lg.print_awards()
        print(f"\nCONTINENTAL TOURNAMENT AWARDS:")
        for t_name, cup in latest.get('continental_cups', {}).items():
            cup.print_awards()

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
            if club is None:
                continue
            total = sum(honours.values())
            breakdown = ", ".join([f"{count}x {h}" for h, count in honours.items()])
            print(f"{club:<30} {total:>15}  {breakdown}")
        print("=" * 88)

        self._print_domestic_standings()
        self.print_awards()

    def _print_domestic_standings(self):
        """Print standings for all domestic leagues from the last season"""
        if not self.history:
            return
        latest = self.history[-1]
        print(f"\n{'='*88}")
        print(f"DOMESTIC LEAGUE STANDINGS - SEASON {latest['season']}".center(88))
        print(f"{'='*88}")
        for l_name, lg in latest.get('domestic_leagues', {}).items():
            lg.print_standings()