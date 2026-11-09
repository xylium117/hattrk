import os, sys, json, random, math
from collections import defaultdict
import game, engine
from elo import get_club_elo, parse_form_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

LEAGUE_PARAMS = {
    1: {
        'home_advantage': 0.20,
        'avg_goals': 2.80,
        'draw_rate': 0.265,
        'fatigue_factor': 0.10,
        'form_weight': 0.12,
        'beach_threshold': 0.68,
        'survival_intensity': 5.00,
        'elo_to_goals': 0.145,
        'elo_home_adv_pts': 120,
    },
    2: {
        'home_advantage': 0.20,
        'avg_goals': 2.65,
        'draw_rate': 0.275,
        'fatigue_factor': 0.09,
        'form_weight': 0.09,
        'beach_threshold': 0.78,
        'survival_intensity': 1.50,
        'elo_to_goals': 0.095,
        'elo_home_adv_pts': 50,
    },
    3: {
        'home_advantage': 0.18,
        'avg_goals': 2.55,
        'draw_rate': 0.29,
        'fatigue_factor': 0.10,
        'form_weight': 0.08,
        'beach_threshold': 0.75,
        'survival_intensity': 1.50,
        'elo_to_goals': 0.092,
        'elo_home_adv_pts': 45,
    },
    4: {
        'home_advantage': 0.16,
        'avg_goals': 2.50,
        'draw_rate': 0.30,
        'fatigue_factor': 0.11,
        'form_weight': 0.07,
        'beach_threshold': 0.70,
        'survival_intensity': 1.60,
        'elo_to_goals': 0.098,
        'elo_home_adv_pts': 40,
    },
}

GOAL_TIMING = [
    (0, 15, 0.11), (15, 30, 0.14), (30, 45, 0.16),
    (45, 60, 0.18), (60, 75, 0.20), (75, 90, 0.21)
]

INJURY_TYPES = {
    'knock': {'prob': 0.45, 'days': (1, 3), 'severity': 0.15},
    'strain': {'prob': 0.25, 'days': (3, 7), 'severity': 0.35},
    'sprain': {'prob': 0.15, 'days': (5, 14), 'severity': 0.50},
    'serious': {'prob': 0.10, 'days': (14, 42), 'severity': 0.80},
    'season_ending': {'prob': 0.05, 'days': (30, 999), 'severity': 1.0},
}

class LeagueEntry:
    def __init__(self, club_name, tier=1):
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
        self.keepers_saves = defaultdict(int)
        self.keepers_clean_sheets = defaultdict(int)
        self.keepers_minutes = defaultdict(int)
        self.player_minutes = defaultdict(int)
        self.player_ratings = defaultdict(lambda: {'total': 0.0, 'count': 0})
        self.tier = tier
        self.xg = 0.0
        self.xga = 0.0
        self.home_won = 0
        self.home_drawn = 0
        self.home_lost = 0
        self.away_won = 0
        self.away_drawn = 0
        self.away_lost = 0
        self.penalties_scored = 0
        self.penalties_conceded = 0
        self.red_cards = 0
        self.yellow_cards = 0
        self.injuries = []
        self.suspended = []
        self.fatigue = 0.0
        self.club_squad = []
        self.manager_sacked = False
        self.manager_name = None
        self.season_goals = []
        self.comeback_wins = 0
        self.blown_leads = 0

    def record_result(self, gf, ga, is_home=True, xg=0.0, xga=0.0):
        self.played += 1
        self.gf += gf
        self.ga += ga
        self.gd = self.gf - self.ga
        self.xg += xg
        self.xga += xga

        if ga == 0:
            self.clean_sheets += 1

        if gf > ga:
            self.won += 1
            self.points += 3
            self.form.append('W')
            if is_home:
                self.home_won += 1
            else:
                self.away_won += 1
        elif gf == ga:
            self.drawn += 1
            self.points += 1
            self.form.append('D')
            if is_home:
                self.home_drawn += 1
            else:
                self.away_drawn += 1
        else:
            self.lost += 1
            self.form.append('L')
            if is_home:
                self.home_lost += 1
            else:
                self.away_lost += 1

        if len(self.form) > 5:
            self.form.pop(0)

    @property
    def form_str(self):
        return "".join(self.form) if self.form else "-----"

    @property
    def form_points(self):
        """Points from last 5 matches"""
        pts = 0
        for f in self.form:
            if f == 'W': pts += 3
            elif f == 'D': pts += 1
        return pts

    @property
    def home_form(self):
        return f"{self.home_won}-{self.home_drawn}-{self.home_lost}"

    @property
    def away_form(self):
        return f"{self.away_won}-{self.away_drawn}-{self.away_lost}"

    @property
    def ppd(self):
        """Points per game"""
        return self.points / self.played if self.played > 0 else 0

    def get_form_factor(self, league_params):
        """Calculate form momentum factor for next match"""
        if len(self.form) < 3:
            return 1.0
        recent = self.form[-3:]
        momentum = 0
        for i, r in enumerate(recent):
            weight = (i + 1) / 6
            if r == 'W': momentum += weight * 0.08
            elif r == 'D': momentum += weight * 0.02
            else: momentum -= weight * 0.06
        return max(0.75, min(1.25, 1.0 + momentum * league_params['form_weight']))

    def decay_fatigue(self, matchday_gap):
        """Reduce fatigue based on rest days"""
        recovery_per_day = 0.02
        self.fatigue = max(0.0, self.fatigue - matchday_gap * recovery_per_day)

    def add_fatigue(self, intensity=1.0, league_params=None):
        """Increase fatigue after match"""
        base_fatigue = 0.12 * intensity
        if league_params:
            base_fatigue *= league_params['fatigue_factor']
        self.fatigue = min(1.0, self.fatigue + base_fatigue)

    def process_injuries_and_suspensions(self, current_matchday):
        """Update injury/suspension lists, return available players count reduction"""
        active_injuries = []
        for name, inj_type, recovery_day in self.injuries:
            if current_matchday < recovery_day:
                active_injuries.append((name, inj_type, recovery_day))
        self.injuries = active_injuries

        active_suspensions = []
        for name, return_day in self.suspended:
            if current_matchday < return_day:
                active_suspensions.append((name, return_day))
        self.suspended = active_suspensions

        return len(self.injuries) + len(self.suspended)

    def maybe_suffer_injury(self, current_matchday, intensity=1.0):
        """Random chance of injury during match"""
        if random.random() < 0.08 * intensity:
            roll = random.random()
            cum = 0
            for inj_type, data in INJURY_TYPES.items():
                cum += data['prob']
                if roll < cum:
                    days = random.randint(*data['days'])
                    recovery_day = current_matchday + days
                    self.injuries.append(('unknown', inj_type, recovery_day))
                    return data['severity']
        return 0.0

    def maybe_suspension(self, current_matchday, red_cards=0, yellow_cards=0):
        """Process cards into suspensions"""
        self.red_cards += red_cards
        self.yellow_cards += yellow_cards

        for _ in range(red_cards):
            ban = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            self.suspended.append(('unknown', current_matchday + ban))

        if self.yellow_cards >= 5 and self.yellow_cards % 5 == 0:
            self.suspended.append(('unknown', current_matchday + 1))


class League:
    def __init__(self, league_id, name, country, continent, gender, tier, clubs,
                 ucl_spots=4, uel_spots=2, uecl_spots=1, rel_spots=3):
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
        self.params = LEAGUE_PARAMS.get(tier, LEAGUE_PARAMS[1])

        self.entries = {name: LeagueEntry(name, tier) for name in self.club_names}
        self.fixtures = []
        self.current_round = 0
        self.matchday = 0
        self.total_matchdays = 0
        self.season_events = []
        self._generate_schedule()
        self._load_club_squads()

    def _load_club_squads(self):
        clubs_data = game.load_clubs()
        for name, entry in self.entries.items():
            if name in clubs_data:
                entry.club_squad = clubs_data[name]

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
        self.total_matchdays = len(self.fixtures)

    def _calculate_match_strength(self, h_entry, a_entry, h_elo, a_elo, is_matchday_start=True):
        """Calculate realistic goal expectations for both teams - calibrated to Opta benchmark"""
        elo_diff = h_elo - a_elo

        elo_diff += self.params.get('elo_home_adv_pts', 45)

        h_form = h_entry.get_form_factor(self.params)
        a_form = a_entry.get_form_factor(self.params)
        elo_diff += math.log(h_form / a_form) * 80

        h_fatigue_penalty = h_entry.fatigue * 50
        a_fatigue_penalty = a_entry.fatigue * 50
        elo_diff -= h_fatigue_penalty - a_fatigue_penalty

        h_inj_impact = len(h_entry.injuries) * 12 + len(h_entry.suspended) * 20
        a_inj_impact = len(a_entry.injuries) * 12 + len(a_entry.suspended) * 20
        elo_diff -= h_inj_impact - a_inj_impact

        season_progress = self.matchday / max(1, self.total_matchdays)
        if season_progress > 0.75:
            h_ppd = h_entry.ppd
            a_ppd = a_entry.ppd
            max_ppd = 3.0
            beach_threshold = self.params['beach_threshold']

            if h_ppd / max_ppd > beach_threshold and h_entry.points > (self.matchday * 1.2):
                elo_diff -= 40
            if a_ppd / max_ppd > beach_threshold and a_entry.points > (self.matchday * 1.2):
                elo_diff += 40

            survival_cutoff = len(self.entries) - self.rel_spots + 2
            h_pos_est = max(1, int(len(self.entries) * (1 - h_entry.ppd / 3.0)) + 1)
            a_pos_est = max(1, int(len(self.entries) * (1 - a_entry.ppd / 3.0)) + 1)

            if h_pos_est >= survival_cutoff:
                elo_diff += 30 * self.params['survival_intensity']
            if a_pos_est >= survival_cutoff:
                elo_diff -= 30 * self.params['survival_intensity']

        elo_to_goals = self.params.get('elo_to_goals', 0.083)
        goal_diff = elo_diff * elo_to_goals / 100.0

        avg_goals = self.params['avg_goals']

        home_xg = (avg_goals / 2.0) * (1.0 + goal_diff)
        away_xg = (avg_goals / 2.0) * (1.0 - goal_diff)

        home_xg = max(0.4, min(3.0, home_xg))
        away_xg = max(0.3, min(2.5, away_xg))

        total_xg = home_xg + away_xg
        if abs(total_xg - avg_goals) > 0.3:
            scale = avg_goals / total_xg
            home_xg *= scale
            away_xg *= scale

        return home_xg, away_xg, elo_diff

    def _poisson_pmf(self, k, lam):
        """Poisson probability mass function"""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return math.exp(-lam) * (lam ** k) / math.factorial(k)

    def _sample_goals(self, home_xg, away_xg):
        """Sample goals from Poisson distribution with draw adjustment"""
        max_goals = 8
        probs = {}
        for hg in range(max_goals + 1):
            for ag in range(max_goals + 1):
                prob = self._poisson_pmf(hg, home_xg) * self._poisson_pmf(ag, away_xg)
                probs[(hg, ag)] = prob

        current_draw_prob = sum(p for (hg, ag), p in probs.items() if hg == ag)
        target_draw_rate = self.params['draw_rate']

        if current_draw_prob > 0:
            draw_multiplier = target_draw_rate / current_draw_prob
            for (hg, ag), p in probs.items():
                if hg == ag:
                    probs[(hg, ag)] *= draw_multiplier
                else:
                    probs[(hg, ag)] *= (1 - (draw_multiplier - 1) * current_draw_prob / (1 - current_draw_prob))

        total = sum(probs.values())
        probs = {k: v/total for k, v in probs.items()}

        r = random.random()
        cum = 0
        for (hg, ag), p in sorted(probs.items()):
            cum += p
            if r < cum:
                return hg, ag

        return int(round(home_xg)), int(round(away_xg))

    def _simulate_match_events(self, fix, h_name, a_name, hg, ag):
        """Generate realistic match events (goals, cards, injuries) from fixture"""
        events = {
            'goals': [],
            'cards': {'home_yellow': 0, 'away_yellow': 0, 'home_red': 0, 'away_red': 0},
            'injuries': {'home': 0, 'away': 0},
            'xg': {'home': 0.0, 'away': 0.0},
            'shots': {'home': 0, 'away': 0},
            'shots_target': {'home': 0, 'away': 0},
            'possession': {'home': 50.0, 'away': 50.0},
            'corners': {'home': 0, 'away': 0},
        }

        if fix and hasattr(fix, 'periods') and fix.periods:
            for per in fix.periods:
                for g in getattr(per, 'goals', []):
                    scorer, assister, team, minute = g
                    if scorer:
                        s_name = getattr(scorer, 'short_name', '') or scorer.name
                        events['goals'].append((s_name, getattr(assister, 'short_name', '') if assister else '', team, minute))

            if hasattr(fix, 'home_xg'):
                events['xg']['home'] = fix.home_xg
                events['xg']['away'] = fix.away_xg
            if hasattr(fix, 'home_shots'):
                events['shots']['home'] = fix.home_shots
                events['shots']['away'] = fix.away_shots
            if hasattr(fix, 'home_shots_target'):
                events['shots_target']['home'] = fix.home_shots_target
                events['shots_target']['away'] = fix.away_shots_target
            if hasattr(fix, 'home_poss'):
                events['possession']['home'] = fix.home_poss
                events['possession']['away'] = fix.away_poss
            if hasattr(fix, 'home_corners'):
                events['corners']['home'] = fix.home_corners
                events['corners']['away'] = fix.away_corners

            if hasattr(fix, 'home_yellows'):
                events['cards']['home_yellow'] = fix.home_yellows
                events['cards']['away_yellow'] = fix.away_yellows
            if hasattr(fix, 'home_reds'):
                events['cards']['home_red'] = fix.home_reds
                events['cards']['away_red'] = fix.away_reds

        if not events['goals'] and (hg > 0 or ag > 0):
            goal_timing = [
                (0, 15, 0.11), (15, 30, 0.14), (30, 45, 0.16),
                (45, 60, 0.18), (60, 75, 0.20), (75, 90, 0.21)
            ]

            for i in range(hg):
                r = random.random()
                cum = 0
                for start, end, prob in goal_timing:
                    cum += prob
                    if r < cum:
                        minute = random.randint(start, min(end, 90))
                        break
                events['goals'].append((f"Home Scorer {i+1}", "", h_name, minute))

            for i in range(ag):
                r = random.random()
                cum = 0
                for start, end, prob in goal_timing:
                    cum += prob
                    if r < cum:
                        minute = random.randint(start, min(end, 90))
                        break
                events['goals'].append((f"Away Scorer {i+1}", "", a_name, minute))

            events['goals'].sort(key=lambda x: x[3])

            events['shots']['home'] = random.randint(max(5, hg*3), max(15, hg*5))
            events['shots']['away'] = random.randint(max(5, ag*3), max(15, ag*5))
            events['shots_target']['home'] = random.randint(hg, events['shots']['home'])
            events['shots_target']['away'] = random.randint(ag, events['shots']['away'])
            events['possession']['home'] = random.uniform(40, 60)
            events['possession']['away'] = 100 - events['possession']['home']
            events['corners']['home'] = random.randint(2, 10)
            events['corners']['away'] = random.randint(2, 10)
            events['cards']['home_yellow'] = random.randint(0, 3)
            events['cards']['away_yellow'] = random.randint(0, 3)
            events['cards']['home_red'] = 1 if random.random() < 0.05 else 0
            events['cards']['away_red'] = 1 if random.random() < 0.05 else 0

        return events

    def simulate_matchday(self, round_idx, quiet=True, save_scorecards=False, scorecard_dir=None, use_poisson=False):
        if round_idx >= len(self.fixtures):
            return []
        round_matches = self.fixtures[round_idx]
        results = []


        self.matchday = round_idx + 1

        old_stdout = None
        devnull = None
        if quiet and not use_poisson:
            old_stdout = sys.stdout
            devnull = open(os.devnull, 'w', encoding='utf-8')
            sys.stdout = devnull

        for h_name, a_name in round_matches:
            h_entry = self.entries[h_name]
            a_entry = self.entries[a_name]

            h_entry.process_injuries_and_suspensions(self.matchday)
            a_entry.process_injuries_and_suspensions(self.matchday)

            h_entry.decay_fatigue(1)
            a_entry.decay_fatigue(1)

            h_elo = get_club_elo(h_name)
            a_elo = get_club_elo(a_name)

            home_xg, away_xg, elo_diff = self._calculate_match_strength(h_entry, a_entry, h_elo, a_elo)

            if use_poisson:
                hg, ag = self._sample_goals(home_xg, away_xg)

                all_goals = []
                for _ in range(hg):
                    scorer = random.choice(h_entry.club_squad[:11]) if h_entry.club_squad else None
                    assister = random.choice(h_entry.club_squad[:11]) if h_entry.club_squad and random.random() < 0.6 else None
                    scorer_name = getattr(scorer, 'short_name', '') or (scorer.name if scorer else 'Unknown')
                    assister_name = getattr(assister, 'short_name', '') or (assister.name if assister else None)
                    all_goals.append((scorer_name, assister_name, h_name, random.randint(1, 90)))
                for _ in range(ag):
                    scorer = random.choice(a_entry.club_squad[:11]) if a_entry.club_squad else None
                    assister = random.choice(a_entry.club_squad[:11]) if a_entry.club_squad and random.random() < 0.6 else None
                    scorer_name = getattr(scorer, 'short_name', '') or (scorer.name if scorer else 'Unknown')
                    assister_name = getattr(assister, 'short_name', '') or (assister.name if assister else None)
                    all_goals.append((scorer_name, assister_name, a_name, random.randint(1, 90)))

                events = {
                    'goals': all_goals,
                    'shots': {'home': max(1, int(home_xg * 5 + random.uniform(-3, 3))), 'away': max(1, int(away_xg * 5 + random.uniform(-3, 3)))},
                    'shots_target': {'home': max(0, int(home_xg * 2 + random.uniform(-1, 2))), 'away': max(0, int(away_xg * 2 + random.uniform(-1, 2)))},
                    'possession': {'home': 50 + int(elo_diff * 0.03 + random.uniform(-10, 10)), 'away': 50 - int(elo_diff * 0.03 + random.uniform(-10, 10))},
                    'corners': {'home': random.randint(2, 10), 'away': random.randint(2, 10)},
                    'cards': {
                        'home_yellow': random.randint(0, 3), 'away_yellow': random.randint(0, 3),
                        'home_red': 1 if random.random() < 0.05 else 0,
                        'away_red': 1 if random.random() < 0.05 else 0
                    }
                }
            else:
                if save_scorecards and scorecard_dir:
                    safe_home = "".join(c for c in h_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                    safe_away = "".join(c for c in a_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
                    scorecard_file = os.path.join(scorecard_dir, f"MD{self.matchday:02d}_{safe_home}_vs_{safe_away}.txt")
                    fix = game.setup(h_name, a_name, savecard=True)
                    fix.scorecard = scorecard_file
                else:
                    fix = game.setup(h_name, a_name, savecard=False)

                game.game(fix, savecard=(save_scorecards and scorecard_dir is not None))

                hg = fix.home_score
                ag = fix.away_score
                home_xg = fix.home_xg
                away_xg = fix.away_xg

                all_goals = []
                for period in fix.periods:
                    for scorer, assister, team, minute in period.goals:
                        scorer_name = getattr(scorer, 'short_name', '') or (scorer.name if scorer else 'Unknown')
                        assister_name = getattr(assister, 'short_name', '') or (assister.name if assister else None)
                        all_goals.append((scorer_name, assister_name, team.name, minute))

                events = {
                    'goals': all_goals,
                    'shots': {'home': fix.home_shots, 'away': fix.away_shots},
                    'shots_target': {'home': fix.home_shots_target, 'away': fix.away_shots_target},
                    'possession': {'home': fix.home_poss, 'away': fix.away_poss},
                    'corners': {'home': fix.home_corners, 'away': fix.away_corners},
                    'cards': {
                        'home_yellow': fix.home_yellows, 'away_yellow': fix.away_yellows,
                        'home_red': fix.home_reds, 'away_red': fix.away_reds
                    },
                    'xg': {'home': fix.home_xg, 'away': fix.away_xg}
                }

            h_entry.record_result(hg, ag, is_home=True, xg=home_xg, xga=away_xg)
            a_entry.record_result(ag, hg, is_home=False, xg=away_xg, xga=home_xg)

            for scorer, assister, team, minute in events['goals']:
                if team == h_name:
                    h_entry.scorers[scorer] += 1
                    if assister:
                        h_entry.assisters[assister] += 1
                else:
                    a_entry.scorers[scorer] += 1
                    if assister:
                        a_entry.assisters[assister] += 1

            if not use_poisson and 'fix' in locals():
                for p in fix.home.xi:
                    p_name = getattr(p, 'short_name', '') or p.name
                    h_entry.player_minutes[p_name] += 90
                    if hasattr(p, 'inns') and p.inns:
                        perf = p.inns[-1]
                        h_entry.player_ratings[p_name]['total'] += getattr(perf, 'rating', 6.0)
                        h_entry.player_ratings[p_name]['count'] += 1
                        if getattr(p, 'position', '') == 'GK':
                            h_entry.keepers_saves[p_name] += getattr(perf, 'saves', 0)
                            h_entry.keepers_minutes[p_name] += 90
                            if ag == 0:
                                h_entry.keepers_clean_sheets[p_name] += 1
                for p in fix.away.xi:
                    p_name = getattr(p, 'short_name', '') or p.name
                    a_entry.player_minutes[p_name] += 90
                    if hasattr(p, 'inns') and p.inns:
                        perf = p.inns[-1]
                        a_entry.player_ratings[p_name]['total'] += getattr(perf, 'rating', 6.0)
                        a_entry.player_ratings[p_name]['count'] += 1
                        if getattr(p, 'position', '') == 'GK':
                            a_entry.keepers_saves[p_name] += getattr(perf, 'saves', 0)
                            a_entry.keepers_minutes[p_name] += 90
                            if hg == 0:
                                a_entry.keepers_clean_sheets[p_name] += 1
            else:
                for p in h_entry.club_squad:
                    if getattr(p, 'position', '') == 'GK':
                        p_name = getattr(p, 'short_name', '') or p.name
                        h_entry.player_minutes[p_name] += 90
                        est_saves = max(0, int(events['shots_target']['away'] * 0.7 + random.uniform(-2, 2)))
                        h_entry.keepers_saves[p_name] += est_saves
                        h_entry.keepers_minutes[p_name] += 90
                        if ag == 0:
                            h_entry.keepers_clean_sheets[p_name] += 1
                        break
                for p in a_entry.club_squad:
                    if getattr(p, 'position', '') == 'GK':
                        p_name = getattr(p, 'short_name', '') or p.name
                        a_entry.player_minutes[p_name] += 90
                        est_saves = max(0, int(events['shots_target']['home'] * 0.7 + random.uniform(-2, 2)))
                        a_entry.keepers_saves[p_name] += est_saves
                        a_entry.keepers_minutes[p_name] += 90
                        if hg == 0:
                            a_entry.keepers_clean_sheets[p_name] += 1
                        break

                for p in h_entry.club_squad[:11]:
                    p_name = getattr(p, 'short_name', '') or p.name
                    h_entry.player_minutes[p_name] += 90
                for p in a_entry.club_squad[:11]:
                    p_name = getattr(p, 'short_name', '') or p.name
                    a_entry.player_minutes[p_name] += 90

            intensity = 1.0 + abs(hg - ag) * 0.1
            h_entry.add_fatigue(intensity, self.params)
            a_entry.add_fatigue(intensity, self.params)

            h_severity = h_entry.maybe_suffer_injury(self.matchday, intensity)
            a_severity = a_entry.maybe_suffer_injury(self.matchday, intensity)

            h_entry.maybe_suspension(self.matchday, events['cards']['home_red'], events['cards']['home_yellow'])
            a_entry.maybe_suspension(self.matchday, events['cards']['away_red'], events['cards']['away_yellow'])

            self._track_narrative(h_name, a_name, hg, ag, h_entry, a_entry, events, round_idx)

            results.append((h_name, hg, ag, a_name, events))

        if quiet and old_stdout is not None:
            sys.stdout = old_stdout
            if devnull is not None:
                devnull.close()
        self.current_round += 1
        return results

    def _track_narrative(self, h_name, a_name, hg, ag, h_entry, a_entry, events, round_idx):
        """Track narrative events for end-of-season storylines"""
        if hasattr(self, '_half_time_scores'):
            ht_hg, ht_ag = self._half_time_scores.get((h_name, a_name), (0, 0))
            if ht_hg < ht_ag and hg > ag:
                h_entry.comeback_wins += 1
                self.season_events.append({
                    'matchday': round_idx + 1,
                    'type': 'comeback',
                    'team': h_name,
                    'opponent': a_name,
                    'score': f"{hg}-{ag}",
                    'ht_score': f"{ht_hg}-{ht_ag}"
                })
            elif ht_hg > ht_ag and hg < ag:
                a_entry.blown_leads += 1
                self.season_events.append({
                    'matchday': round_idx + 1,
                    'type': 'blown_lead',
                    'team': h_name,
                    'opponent': a_name,
                    'score': f"{hg}-{ag}",
                    'ht_score': f"{ht_hg}-{ht_ag}"
                })

        if hg - ag >= 4:
            self.season_events.append({
                'matchday': round_idx + 1,
                'type': 'thrashing',
                'team': h_name,
                'opponent': a_name,
                'score': f"{hg}-{ag}"
            })
        elif ag - hg >= 4:
            self.season_events.append({
                'matchday': round_idx + 1,
                'type': 'thrashing',
                'team': a_name,
                'opponent': h_name,
                'score': f"{ag}-{hg}"
            })

        if hg + ag >= 6:
            self.season_events.append({
                'matchday': round_idx + 1,
                'type': 'goal_fest',
                'teams': f"{h_name} {hg}-{ag} {a_name}",
                'score': f"{hg}-{ag}"
            })

    def simulate_season(self, quiet=True, progress_cb=None, max_matchdays=None, save_scorecards=False, scorecard_base_dir=None, use_poisson=False, save_results=False, save_results_dir=None, season_num=1):
        for entry in self.entries.values():
            entry.played = 0
            entry.won = 0
            entry.drawn = 0
            entry.lost = 0
            entry.gf = 0
            entry.ga = 0
            entry.gd = 0
            entry.points = 0
            entry.form = []
            entry.clean_sheets = 0
            entry.scorers = defaultdict(int)
            entry.assisters = defaultdict(int)
            entry.xg = 0.0
            entry.xga = 0.0
            entry.home_won = 0
            entry.home_drawn = 0
            entry.home_lost = 0
            entry.away_won = 0
            entry.away_drawn = 0
            entry.away_lost = 0
            entry.penalties_scored = 0
            entry.penalties_conceded = 0
            entry.red_cards = 0
            entry.yellow_cards = 0
            entry.injuries = []
            entry.suspended = []
            entry.fatigue = 0.0
            entry.manager_sacked = False
            entry.season_goals = []
            entry.comeback_wins = 0
            entry.blown_leads = 0
            entry.keepers_saves = defaultdict(int)
            entry.keepers_clean_sheets = defaultdict(int)
            entry.keepers_minutes = defaultdict(int)
            entry.player_minutes = defaultdict(int)
            entry.player_ratings = defaultdict(lambda: {'total': 0.0, 'count': 0})

        limit = len(self.fixtures) if max_matchdays is None else min(max_matchdays, len(self.fixtures))
        self._half_time_scores = {}
        self.season_events = []

        season_scorecard_dir = None
        if save_scorecards and scorecard_base_dir:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_league_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            season_folder = f"{safe_league_name}_Season_{timestamp}"
            season_scorecard_dir = os.path.join(scorecard_base_dir, season_folder)
            os.makedirs(season_scorecard_dir, exist_ok=True)

        for r_idx in range(limit):
            md_scorecard_dir = None
            if save_scorecards and season_scorecard_dir:
                md_scorecard_dir = os.path.join(season_scorecard_dir, f"Matchday_{r_idx + 1:02d}")
                os.makedirs(md_scorecard_dir, exist_ok=True)

            res = self.simulate_matchday(r_idx, quiet=quiet, save_scorecards=save_scorecards, scorecard_dir=md_scorecard_dir, use_poisson=use_poisson)
            for h_name, hg, ag, a_name, events in res:
                ht_hg = max(0, hg - random.randint(0, max(0, hg - 1)))
                ht_ag = max(0, ag - random.randint(0, max(0, ag - 1)))
                self._half_time_scores[(h_name, a_name)] = (ht_hg, ht_ag)

            if progress_cb:
                progress_cb(r_idx + 1, limit, res)
        return self.get_standings()

    def get_standings(self):
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.points, e.gd, e.gf, e.won, e.home_won, -e.lost, -e.ga),
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

    def get_league_golden_boot(self):
        """Return (player_name, club_name, goals) for top scorer in this league"""
        top_sc = self.get_top_scorers(1)
        if top_sc:
            (p_name, c_name), goals = top_sc[0]
            return p_name, c_name, goals
        return None, None, 0

    def get_league_golden_glove(self):
        """Return (keeper_name, club_name, clean_sheets, saves) for best GK in this league"""
        total_keepers = defaultdict(lambda: {'saves': 0, 'clean_sheets': 0, 'minutes': 0})
        for entry in self.entries.values():
            for keeper, saves in entry.keepers_saves.items():
                total_keepers[(keeper, entry.club_name)]['saves'] += saves
            for keeper, cs in entry.keepers_clean_sheets.items():
                total_keepers[(keeper, entry.club_name)]['clean_sheets'] += cs
            for keeper, mins in entry.keepers_minutes.items():
                total_keepers[(keeper, entry.club_name)]['minutes'] += mins

        best = None
        best_score = -1
        for (keeper, club), stats in total_keepers.items():
            if stats['minutes'] >= 450:
                score = stats['clean_sheets'] * 3 + stats['saves'] * 0.5
                if score > best_score:
                    best_score = score
                    best = (keeper, club, stats['clean_sheets'], stats['saves'])
        return best

    def get_league_playmaker(self):
        """Return (player_name, club_name, assists) for top assister in this league"""
        top_as = self.get_top_assisters(1)
        if top_as:
            (p_name, c_name), assists = top_as[0]
            return p_name, c_name, assists
        return None, None, 0

    def get_league_best_player(self):
        """Return (player_name, club_name, avg_rating) for best overall player (Ballon d'Or style)"""
        player_stats = defaultdict(lambda: {'rating_total': 0.0, 'rating_count': 0, 'minutes': 0, 'club': ''})
        for entry in self.entries.values():
            for player, rating_data in entry.player_ratings.items():
                player_stats[(player, entry.club_name)]['rating_total'] += rating_data['total']
                player_stats[(player, entry.club_name)]['rating_count'] += rating_data['count']
                player_stats[(player, entry.club_name)]['club'] = entry.club_name
            for player, mins in entry.player_minutes.items():
                player_stats[(player, entry.club_name)]['minutes'] += mins

        best = None
        best_rating = -1
        for (player, club), stats in player_stats.items():
            if stats['minutes'] >= 450 and stats['rating_count'] >= 5:
                avg_rating = stats['rating_total'] / stats['rating_count']
                if avg_rating > best_rating:
                    best_rating = avg_rating
                    best = (player, club, round(avg_rating, 1))
        return best

    def print_awards(self):
        """Print all end-of-season awards for this league"""
        boot_player, boot_club, boot_goals = self.get_league_golden_boot()
        glove = self.get_league_golden_glove()
        pm_player, pm_club, pm_assists = self.get_league_playmaker()
        bp = self.get_league_best_player()

        if not (boot_player or glove or pm_player or bp):
            return

        print("\n" + "=" * 70)
        print(f"{self.name.upper()} END-OF-SEASON AWARDS".center(70))
        print("=" * 70)

        if boot_player:
            print(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals")

        if glove:
            keeper, club, cs, saves = glove
            print(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves")

        if pm_player:
            print(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists")

        if bp:
            bp_player, bp_club, bp_score = bp
            print(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating")

        print("=" * 70)

    def get_xg_table(self):
        """Expected goals table"""
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.xg - e.xga, e.xg, -e.xga),
            reverse=True
        )
        return sorted_entries

    def print_standings(self, show_xg=False):
        standings = self.get_standings()
        print("\n" + "=" * 100)
        print(f"{self.name.upper()} STANDINGS ({self.country}) - Matchday {self.current_round}/{self.total_matchdays}".center(100))
        print("=" * 100)

        if show_xg:
            print(f"{'Pos':<4} {'Club':<26} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4} {'xG':>6} {'xGA':>6} {'xGD':>6}  {'Form':<6} {'Status'}")
            print("-" * 100)
            for idx, e in enumerate(standings, 1):
                status = self._get_status_string(idx, len(standings))
                xgd = e.xg - e.xga
                print(f"{idx:<4} {e.club_name:<26} {e.played:>3} {e.won:>3} {e.drawn:>3} {e.lost:>3} {e.gf:>4} {e.ga:>4} {e.gd:>+4} {e.points:>4}  {e.xg:>5.1f} {e.xga:>5.1f} {xgd:>+5.1f}  {e.form_str:<6} {status}")
        else:
            print(f"{'Pos':<4} {'Club':<26} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}  {'Form':<6} {'Home':<8} {'Away':<8} {'Status'}")
            print("-" * 100)
            for idx, e in enumerate(standings, 1):
                status = self._get_status_string(idx, len(standings))
                print(f"{idx:<4} {e.club_name:<26} {e.played:>3} {e.won:>3} {e.drawn:>3} {e.lost:>3} {e.gf:>4} {e.ga:>4} {e.gd:>+4} {e.points:>4}  {e.form_str:<6} {e.home_form:<8} {e.away_form:<8} {status}")
        print("=" * 100)

        top_sc = self.get_top_scorers(10)
        if top_sc:
            print("\nTOP GOALSCORERS:")
            for rank, ((p_name, c_name), goals) in enumerate(top_sc, 1):
                print(f"  {rank:>2}. {p_name:<24} ({c_name:<22}) - {goals} goals")

        top_as = self.get_top_assisters(5)
        if top_as:
            print("\nTOP ASSISTERS:")
            for rank, ((p_name, c_name), assists) in enumerate(top_as, 1):
                print(f"  {rank:>2}. {p_name:<24} ({c_name:<22}) - {assists} assists")

    def _get_status_string(self, idx, total):
        if idx == 1:
            if self.continent == "Europe":
                return "[CHAMPION / UCL]"
            return "[CHAMPION]"
        elif idx <= self.ucl_spots:
            if self.continent == "Europe":
                return "[UCL]"
            return "[CONTINENTAL]"
        elif idx <= (self.ucl_spots + self.uel_spots):
            if self.continent == "Europe":
                return "[UEL]"
            return "[SECONDARY CUP]"
        elif idx <= (self.ucl_spots + self.uel_spots + self.uecl_spots):
            return "[UECL]"
        elif idx > (total - self.rel_spots):
            return "[RELEGATION ZONE]"
        return ""

    def print_season_summary(self):
        """Print detailed end-of-season summary"""
        standings = self.get_standings()
        print("\n" + "=" * 80)
        print(f"{self.name.upper()} SEASON SUMMARY".center(80))
        print("=" * 80)

        champ = standings[0]
        print(f"\n[CHAMPION]: {champ.club_name} ({champ.points} pts, {champ.gd:+d} GD)")

        print(f"\n[UCL QUALIFICATION] ({self.ucl_spots} spots):")
        for i in range(min(self.ucl_spots, len(standings))):
            e = standings[i]
            print(f"  {i+1}. {e.club_name} - {e.points} pts")

        if self.uel_spots > 0:
            print(f"\n[UEL QUALIFICATION] ({self.uel_spots} spots):")
            for i in range(self.ucl_spots, min(self.ucl_spots + self.uel_spots, len(standings))):
                e = standings[i]
                print(f"  {i+1}. {e.club_name} - {e.points} pts")

        if self.uecl_spots > 0:
            print(f"\n[UECL QUALIFICATION] ({self.uecl_spots} spots):")
            for i in range(self.ucl_spots + self.uel_spots, min(self.ucl_spots + self.uel_spots + self.uecl_spots, len(standings))):
                e = standings[i]
                print(f"  {i+1}. {e.club_name} - {e.points} pts")

        if self.rel_spots > 0:
            print(f"\n[RELEGATED] ({self.rel_spots} spots):")
            for i in range(len(standings) - self.rel_spots, len(standings)):
                e = standings[i]
                print(f"  {i+1}. {e.club_name} - {e.points} pts")

        total_goals = sum(e.gf for e in standings)
        total_matches = sum(e.played for e in standings) // 2
        avg_goals = total_goals / max(1, total_matches)
        draws = sum(e.drawn for e in standings) // 2
        draw_pct = draws / max(1, total_matches) * 100
        home_wins = sum(e.home_won for e in standings)
        away_wins = sum(e.away_won for e in standings)

        print(f"\n[SEASON STATISTICS]:")
        print(f"  Matches played: {total_matches}")
        print(f"  Total goals: {total_goals} ({avg_goals:.2f} per match)")
        print(f"  Draws: {draws} ({draw_pct:.1f}%)")
        print(f"  Home wins: {home_wins} ({home_wins/max(1,total_matches)*100:.1f}%)")
        print(f"  Away wins: {away_wins} ({away_wins/max(1,total_matches)*100:.1f}%)")
        print(f"  Home advantage: {(home_wins-away_wins)/max(1,total_matches)*100:+.1f}%")

        self.print_awards()

        if self.season_events:
            print(f"\n[SEASON HIGHLIGHTS]:")
            for evt in self.season_events[-10:]:
                if evt['type'] == 'comeback':
                    print(f"  MD{evt['matchday']:>2}: {evt['team']} came back from {evt['ht_score']} to beat {evt['opponent']} {evt['score']}!")
                elif evt['type'] == 'blown_lead':
                    print(f"  MD{evt['matchday']:>2}: {evt['team']} blew {evt['ht_score']} lead, lost to {evt['opponent']} {evt['score']}")
                elif evt['type'] == 'thrashing':
                    print(f"  MD{evt['matchday']:>2}: {evt['team']} thrashed {evt['opponent']} {evt['score']}!")
                elif evt['type'] == 'goal_fest':
                    print(f"  MD{evt['matchday']:>2}: Goal fest! {evt['teams']}")

    def save_results_to_file(self, base_dir="scorecards", season_num=1, include_awards=True):
        """Save league season results to a text file"""
        import os
        from datetime import datetime
        safe_name = "".join(c for c in self.name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        if os.path.basename(base_dir) != "scorecards":
            save_dir = os.path.join(base_dir, "scorecards", f"Season_{season_num}", safe_name)
        else:
            save_dir = os.path.join(base_dir, f"Season_{season_num}", safe_name)
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, "season_results.txt")

        standings = self.get_standings()

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"{self.name.upper()} SEASON {season_num} RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

            f.write("[FINAL STANDINGS]\n")
            f.write(f"{'Pos':<4} {'Club':<26} {'P':>3} {'W':>3} {'D':>3} {'L':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'Pts':>4}\n")
            f.write("-" * 80 + "\n")
            for idx, e in enumerate(standings, 1):
                f.write(f"{idx:<4} {e.club_name:<26} {e.played:>3} {e.won:>3} {e.drawn:>3} {e.lost:>3} {e.gf:>4} {e.ga:>4} {e.gd:>+4} {e.points:>4}\n")

            champ = standings[0]
            f.write(f"\n[CHAMPION]: {champ.club_name} ({champ.points} pts, {champ.gd:+d} GD)\n")

            f.write(f"\n[UCL QUALIFICATION] ({self.ucl_spots} spots):\n")
            for i in range(min(self.ucl_spots, len(standings))):
                e = standings[i]
                f.write(f"  {i+1}. {e.club_name} - {e.points} pts\n")

            if self.uel_spots > 0:
                f.write(f"\n[UEL QUALIFICATION] ({self.uel_spots} spots):\n")
                for i in range(self.ucl_spots, min(self.ucl_spots + self.uel_spots, len(standings))):
                    e = standings[i]
                    f.write(f"  {i+1}. {e.club_name} - {e.points} pts\n")

            if self.uecl_spots > 0:
                f.write(f"\n[UECL QUALIFICATION] ({self.uecl_spots} spots):\n")
                for i in range(self.ucl_spots + self.uel_spots, min(self.ucl_spots + self.uel_spots + self.uecl_spots, len(standings))):
                    e = standings[i]
                    f.write(f"  {i+1}. {e.club_name} - {e.points} pts\n")

            if self.rel_spots > 0:
                f.write(f"\n[RELEGATED] ({self.rel_spots} spots):\n")
                for i in range(len(standings) - self.rel_spots, len(standings)):
                    e = standings[i]
                    f.write(f"  {i+1}. {e.club_name} - {e.points} pts\n")

            total_goals = sum(e.gf for e in standings)
            total_matches = sum(e.played for e in standings) // 2
            avg_goals = total_goals / max(1, total_matches)
            draws = sum(e.drawn for e in standings) // 2
            draw_pct = draws / max(1, total_matches) * 100
            home_wins = sum(e.home_won for e in standings)
            away_wins = sum(e.away_won for e in standings)

            f.write(f"\n[SEASON STATISTICS]:\n")
            f.write(f"  Matches played: {total_matches}\n")
            f.write(f"  Total goals: {total_goals} ({avg_goals:.2f} per match)\n")
            f.write(f"  Draws: {draws} ({draw_pct:.1f}%)\n")
            f.write(f"  Home wins: {home_wins} ({home_wins/max(1,total_matches)*100:.1f}%)\n")
            f.write(f"  Away wins: {away_wins} ({away_wins/max(1,total_matches)*100:.1f}%)\n")
            f.write(f"  Home advantage: {(home_wins-away_wins)/max(1,total_matches)*100:+.1f}%\n")

            if include_awards:
                boot_player, boot_club, boot_goals = self.get_league_golden_boot()
                glove = self.get_league_golden_glove()
                pm_player, pm_club, pm_assists = self.get_league_playmaker()
                bp = self.get_league_best_player()

                if boot_player or glove or pm_player or bp:
                    f.write("\n" + "=" * 70 + "\n")
                    f.write(f"{self.name.upper()} END-OF-SEASON AWARDS\n")
                    f.write("=" * 70 + "\n")

                    if boot_player:
                        f.write(f"\n[GOLDEN BOOT]  {boot_player:<24} ({boot_club:<22}) - {boot_goals} goals\n")

                    if glove:
                        keeper, club, cs, saves = glove
                        f.write(f"[GOLDEN GLOVE] {keeper:<24} ({club:<22}) - {cs} CS, {saves} saves\n")

                    if pm_player:
                        f.write(f"[PLAYMAKER]    {pm_player:<24} ({pm_club:<22}) - {pm_assists} assists\n")

                    if bp:
                        bp_player, bp_club, bp_score = bp
                        f.write(f"[BEST PLAYER]  {bp_player:<24} ({bp_club:<22}) - {bp_score:.1f} rating\n")

                    f.write("=" * 70 + "\n")

        return filepath


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