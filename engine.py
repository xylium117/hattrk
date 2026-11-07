import random, shutil, datetime, os, sys
from grid import PitchGrid
from gamestate import GameStateManager
from possession import PossessionEngine
from elo import get_club_elo
from tactics import ManagerPOV, get_formation_matchup, calculate_team_fluidity, load_club_tactics

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
	try:
		sys.stdout.reconfigure(encoding='utf-8')
	except Exception:
		pass

CHANCE_PER_MIN = 0.14
GOAL_GIVEN_SHOT = 0.30
SAVE_SCORECARD = True

def set_save_scorecard(enabled: bool):
	global SAVE_SCORECARD
	SAVE_SCORECARD = bool(enabled)

def get_minute_intensity(minute):
	if minute <= 15:
		return 1.06
	elif minute <= 35:
		return 0.90
	elif minute <= 45:
		return 1.14
	elif minute <= 55:
		return 0.94
	elif minute <= 75:
		return 1.10
	elif minute <= 85:
		return 1.16
	else:
		return 1.25

def listshow(x, end=False):
	a = ''
	for i in x:
		if i is not x[-1]: a = a + '{}, '.format(i)
		else:
			if end == False: a = a + '{}'.format(i)
			else: a = a + '{} {}'.format(end, i)
	return a

def pos_to_role(pos):
	pos = str(pos).strip().upper()
	if pos == 'GK':
		return 'GK'
	elif pos in ['CB', 'LB', 'RB', 'LWB', 'RWB', 'DEF']:
		return 'DEF'
	elif pos in ['CDM', 'DMF']:
		return 'DMF'
	elif pos in ['CM', 'LM', 'RM', 'MID']:
		return 'MID'
	elif pos in ['CAM', 'AMF']:
		return 'AMF'
	elif pos in ['ST', 'CF', 'LW', 'RW', 'ATT']:
		return 'ATT'
	return 'MID'

def pos_order(pos):
	order_map = {
		'GK': 0,
		'RB': 1, 'RWB': 1,
		'CB': 2, 'DEF': 2,
		'LB': 3, 'LWB': 3,
		'CDM': 4, 'DMF': 4,
		'CM': 5, 'MID': 5,
		'CAM': 6, 'AMF': 6,
		'RM': 7, 'RW': 8,
		'LM': 9, 'LW': 10,
		'CF': 11, 'ST': 12, 'ATT': 12
	}
	return order_map.get(str(pos).strip().upper(), 6)

def att_strength(xi):
	total = 0.0
	for p in xi:
		fit = getattr(p, 'fitness', 1.0)
		role = getattr(p, 'position', 'MID')

		if role == 'ATT':
			w = 1.0
			stat_val = p.finishing * 0.35 + p.positioning * 0.25 + p.pace * 0.20 + p.dribbling * 0.20
		elif role == 'AMF':
			w = 0.85
			stat_val = p.vision * 0.30 + p.short_passing * 0.25 + p.dribbling * 0.25 + p.shooting * 0.20
		elif role == 'MID':
			w = 0.65
			stat_val = p.short_passing * 0.35 + p.vision * 0.25 + p.long_passing * 0.20 + p.ball_control * 0.20
		elif role == 'DMF':
			w = 0.35
			stat_val = p.short_passing * 0.40 + p.long_passing * 0.30 + p.vision * 0.30
		elif role == 'DEF':
			w = 0.20
			stat_val = p.crossing * 0.40 + p.pace * 0.30 + p.short_passing * 0.30
		else:
			w = 0.05
			stat_val = p.long_passing * 0.50 + p.vision * 0.50

		bonus = 1.0
		if p.has_playstyle('incisive pass') or p.has_playstyle('tiki taka'): bonus += 0.08
		if p.has_playstyle('quick step') or p.has_playstyle('rapid'): bonus += 0.06
		if p.has_playstyle('technical') or p.has_playstyle('first touch'): bonus += 0.05
		if p.has_playstyle('finesse shot') or p.has_playstyle('power shot'): bonus += 0.05

		total += stat_val * w * bonus * fit
	if len(xi) < 11:
		total *= (len(xi) / 11.0) ** 1.30
	return total

def def_strength(xi):
	total = 0.0
	for p in xi:
		fit = getattr(p, 'fitness', 1.0)
		role = getattr(p, 'position', 'MID')

		if role == 'GK':
			w = 1.4
			diving = getattr(p, 'gk_diving', p.overall)
			reflexes = getattr(p, 'gk_reflexes', p.overall)
			positioning = getattr(p, 'gk_positioning', p.overall)
			handling = getattr(p, 'gk_handling', p.overall)
			stat_val = p.overall * 0.35 + diving * 0.25 + reflexes * 0.20 + positioning * 0.15 + handling * 0.05
		elif role == 'DEF':
			w = 1.0
			stat_val = p.def_awareness * 0.30 + p.standing_tackle * 0.25 + p.interceptions * 0.20 + p.strength * 0.15 + p.pace * 0.10
		elif role == 'DMF':
			w = 0.80
			stat_val = p.interceptions * 0.35 + p.standing_tackle * 0.30 + p.def_awareness * 0.20 + p.strength * 0.15
		elif role == 'MID':
			w = 0.45
			stat_val = p.interceptions * 0.35 + p.standing_tackle * 0.35 + p.aggression * 0.30
		elif role == 'AMF':
			w = 0.20
			stat_val = p.defending * 0.50 + p.aggression * 0.50
		else:
			w = 0.10
			stat_val = p.aggression * 0.60 + p.strength * 0.40

		bonus = 1.0
		if p.has_playstyle('anticipate') or p.has_playstyle('intercept'): bonus += 0.08
		if p.has_playstyle('block') or p.has_playstyle('bruiser'): bonus += 0.06
		if p.has_playstyle('aerial fortress') or p.has_playstyle('slide tackle'): bonus += 0.05
		if role == 'GK' and (p.has_playstyle('1v1 close down') or p.has_playstyle('far reach')): bonus += 0.08

		total += stat_val * w * bonus * fit
	if len(xi) < 11:
		total *= (len(xi) / 11.0) ** 1.20
	return total

def formation_parse(f):
	parts = [int(x) for x in f.strip().split('-') if x.strip().isdigit()]
	if len(parts) == 3:
		return {'DEF': parts[0], 'MID': parts[1], 'ATT': parts[2]}
	elif len(parts) == 4:
		return {'DEF': parts[0], 'DMF': parts[1], 'AMF': parts[2], 'ATT': parts[3], 'MID': parts[1] + parts[2]}
	elif len(parts) == 5:
		return {'DEF': parts[0], 'DMF': parts[1], 'MID': parts[2], 'AMF': parts[3], 'ATT': parts[4]}
	return {'DEF': 4, 'MID': 3, 'ATT': 3}

class MatchPerformance:
	def __init__(self, p, match, goals=0, assists=0, shots=0, saves=0, tackles=0, out=False):
		self.player = p
		self.name = getattr(p, 'short_name', '') or p.name
		self.match = match
		self.team = p.team
		self.goals = goals
		self.assists = assists
		self.shots = shots
		self.shots_on_target = 0
		self.saves = saves
		self.tackles = tackles
		self.interceptions = 0
		self.key_passes = 0
		self.aerials_won = 0
		self.fouls_committed = 0
		self.yellow_cards = 0
		self.red_cards = 0
		self.passes_completed = 0
		self.passes_attempted = 0
		self.xg = 0.0
		self.xa = 0.0
		self.out = out
		self.minutes_played = 90
		self.subbed_in = False
		self.subbed_out = False
		self.sub_minute = 0
		self.rating = 6.0
		p.inns.append(self)

	def calculate_rating(self, match=None):
		p = self.player
		mins = getattr(self, 'minutes_played', 90)

		r = 6.0

		if self.passes_attempted >= 8:
			acc = self.passes_completed / float(self.passes_attempted)
			acc_delta = (acc - 0.82) * 1.6
			vol_bonus = min(0.65, (self.passes_completed / 55.0) * 0.45)
			r += acc_delta + vol_bonus

		r += self.tackles * 0.16
		r += self.interceptions * 0.18
		r += self.aerials_won * 0.12

		r += self.goals * 1.35
		r += self.assists * 0.85
		r += self.key_passes * 0.22
		r += self.shots_on_target * 0.12
		r += max(0, self.shots - self.shots_on_target) * 0.04
		r += self.xg * 0.15
		r += self.xa * 0.15

		if p and (p.position == 'GK' or getattr(p, 'primary_position', '') == 'GK'):
			r += self.saves * 0.32

		r -= self.fouls_committed * 0.08
		r -= self.yellow_cards * 0.45
		r -= self.red_cards * 2.2

		if match and p and p.position in ['GK', 'DEF', 'DMF']:
			home_team_name = match.home.name if hasattr(match.home, 'name') else str(match.home)
			opp_score = match.away_score if (p.team == home_team_name or p.team == match.home) else match.home_score
			if opp_score == 0:
				r += 0.5
			elif opp_score >= 2:
				r -= min(0.6, (opp_score - 1) * 0.15)

		ovr_bias = (p.overall - 80) * 0.008
		seed_val = (hash(p.name + str(self.passes_completed) + str(mins)) % 31) - 15
		noise = (seed_val / 100.0)
		r += ovr_bias + noise

		if mins < 35 and (self.goals + self.assists) == 0:
			r = 6.0 + (r - 6.0) * 0.65

		r = max(4.0, min(10.0, r))
		self.rating = round(r, 1)
		return self.rating

	def report(self, match=None):
		a = []
		if self.goals >= 3:
			a += ['magnificent', 'sensational', 'unbelievable', 'heroic', 'masterclass']
		elif self.goals == 2:
			a += ['clinical', 'deadly', 'superb', 'sharp', 'fine']
		elif self.goals == 1 and self.assists >= 1:
			a += ['all-action', 'dynamic', 'lively', 'influential']
		elif self.goals == 1:
			a += ['decisive', 'crucial', 'smart', 'well-taken']

		if self.assists >= 2:
			a += ['creative', 'visionary', 'playmaking']
		if self.saves >= 5:
			a += ['heroic', 'rock-solid', 'outstanding', 'impassable']
		if self.tackles >= 4:
			a += ['commanding', 'imperious', 'resolute']

		disp_name = getattr(self.player, 'short_name', '') or self.name
		if self.goals >= 3:
			adj = random.choice(a) if a else 'stunning'
			return '{} scored a {} hat-trick'.format(disp_name, adj)
		elif self.goals == 2:
			adj = random.choice(a) if a else 'clinical'
			return '{} scored a {} brace'.format(disp_name, adj)
		elif self.goals == 1 and self.assists >= 1:
			return '{} contributed a goal and an assist in a lively display'.format(disp_name)
		elif self.goals == 1:
			adj = random.choice(a) if a else 'neat'
			return '{} slotted home a {} goal'.format(disp_name, adj)
		elif self.assists >= 2:
			return '{} pulled the strings with {} assists'.format(disp_name, self.assists)
		elif self.assists == 1:
			return '{} registered a fine assist'.format(disp_name)
		elif self.saves >= 4:
			return '{} made {} crucial saves between the posts'.format(disp_name, self.saves)
		elif self.tackles >= 3:
			return '{} anchored the defense with {} timely tackles'.format(disp_name, self.tackles)
		return '{} worked hard for the team'.format(disp_name)

	def stats(self):
		p = self.player
		p.games += 1
		p.goals += self.goals
		p.assists += self.assists
		if self.match != '' and hasattr(self.match, 'clean_sheet'):
			if self.match.clean_sheet(p.team):
				if p.position in ['GK', 'DEF', 'DMF']:
					p.clean_sheets += 1
		if self.match != '' and hasattr(self.match, 'motm'):
			if self.match.motm == p:
				p.motm += 1

	name = ''
	player = ''
	match = ''
	team = ''
	goals = 0
	assists = 0
	shots = 0
	shots_on_target = 0
	saves = 0
	tackles = 0
	interceptions = 0
	key_passes = 0
	aerials_won = 0
	fouls_committed = 0
	yellow_cards = 0
	red_cards = 0
	passes_completed = 0
	passes_attempted = 0
	xg = 0.0
	xa = 0.0
	out = False
	minutes_played = 90
	rating = 6.0

class player:
	def __init__(self, data=None):
		self.name = ''
		self.short_name = ''
		self.full_name = ''
		self.team = ''
		self.club = ''
		self.league = ''
		self.nation = ''
		self.gender = 'Male'
		self.overall = 70.0
		self.rarity = 'Common'
		self.positions = ['MID']
		self.primary_position = 'CM'
		self.position = 'MID'
		self.age = 25
		self.height = ''
		self.weight = ''
		self.preferred_foot = 'Right'
		self.weak_foot = 3
		self.skill_moves = 3
		self.accelerate_type = 'Controlled'

		self.playstyles_plus = ''
		self.playstyles_base = ''
		self.playstyles = set()

		self.face_pace = 70.0
		self.face_shooting = 65.0
		self.face_passing = 68.0
		self.face_dribbling = 70.0
		self.face_defending = 60.0
		self.face_physicality = 68.0
		self.shooting = self.face_shooting
		self.passing = self.face_passing
		self.dribbling = self.face_dribbling
		self.defending = self.face_defending
		self.physicality = self.face_physicality

		self.finishing = 65.0
		self.positioning = 65.0
		self.shot_power = 70.0
		self.long_shots = 65.0
		self.volleys = 60.0
		self.penalties = 65.0

		self.vision = 68.0
		self.crossing = 65.0
		self.free_kick = 60.0
		self.short_passing = 70.0
		self.long_passing = 68.0
		self.curve = 65.0

		self.dribbling_stat = 70.0
		self.agility = 70.0
		self.balance = 70.0
		self.reactions = 70.0
		self.ball_control = 70.0
		self.composure = 70.0

		self.interceptions = 60.0
		self.heading = 60.0
		self.def_awareness = 60.0
		self.standing_tackle = 60.0
		self.sliding_tackle = 58.0

		self.acceleration = 70.0
		self.sprint_speed = 70.0
		self.jumping = 68.0
		self.stamina_stat = 75.0
		self.strength = 68.0
		self.aggression = 65.0

		self.gk_overall = 70.0
		self.gk_diving = 70.0
		self.gk_handling = 70.0
		self.gk_kicking = 70.0
		self.gk_reflexes = 70.0
		self.gk_speed = 50.0
		self.gk_positioning = 70.0

		self.attack = 65.0
		self.defense = 60.0
		self.pace = 70.0
		self.stamina = 1.0
		self.capt = 0
		self.games = 0
		self.goals = 0
		self.assists = 0
		self.clean_sheets = 0
		self.motm = 0
		self.match_goals = 0
		self.match_assists = 0
		self.fitness = 1.0
		self.inns = []

		if data is not None:
			self.from_dict(data)

	def from_dict(self, r):
		def _flt(key, default=50.0):
			val = r.get(key)
			if val is None or val == '':
				return default
			try:
				return float(val)
			except (ValueError, TypeError):
				return default

		def _int(key, default=0):
			val = r.get(key)
			if val is None or val == '':
				return default
			try:
				return int(float(val))
			except (ValueError, TypeError):
				return default

		self.name = r.get('player_name', '').strip() or r.get('full_name', '').strip()
		self.full_name = r.get('full_name', '').strip()
		self.short_name = self.name
		self.club = r.get('club', '').strip()
		self.team = self.club
		self.league = r.get('league', '').strip()
		self.nation = r.get('nation', '').strip()
		self.gender = r.get('gender', 'Male').strip()
		self.overall = _flt('overall', 70.0)
		self.rarity = r.get('rarity', 'Common').strip()
		self.age = _int('age', 25)
		self.height = r.get('height', '').strip()
		self.weight = r.get('weight', '').strip()
		self.preferred_foot = r.get('preferred_foot', 'Right').strip()
		self.weak_foot = _int('weak_foot', 3)
		self.skill_moves = _int('skill_moves', 3)
		self.accelerate_type = r.get('accelerate_type', 'Controlled').strip()

		pos_raw = r.get('positions', 'MID')
		self.positions = [p.strip() for p in pos_raw.split(',') if p.strip()]
		self.primary_position = self.positions[0] if self.positions else 'MID'
		self.position = pos_to_role(self.primary_position)

		self.playstyles_plus = r.get('playstyles_plus', '').strip()
		self.playstyles_base = r.get('playstyles_base', '').strip()
		self.playstyles = set()
		for ps in [self.playstyles_plus, self.playstyles_base]:
			if ps:
				for item in ps.split(','):
					item = item.strip().lower()
					if item:
						self.playstyles.add(item)

		self.acceleration = _flt('stat_acceleration', self.overall)
		self.sprint_speed = _flt('stat_sprint_speed', self.overall)
		self.positioning = _flt('stat_positioning', self.overall)
		self.finishing = _flt('stat_finishing', self.overall)
		self.shot_power = _flt('stat_shot_power', self.overall)
		self.long_shots = _flt('stat_long_shots', self.overall)
		self.volleys = _flt('stat_volleys', self.overall)
		self.penalties = _flt('stat_penalties', self.overall)

		self.vision = _flt('stat_vision', self.overall)
		self.crossing = _flt('stat_crossing', self.overall)
		self.free_kick = _flt('stat_free_kick_accuracy', self.overall)
		self.short_passing = _flt('stat_short_passing', self.overall)
		self.long_passing = _flt('stat_long_passing', self.overall)
		self.curve = _flt('stat_curve', self.overall)

		self.dribbling_stat = _flt('stat_dribbling', self.overall)
		self.agility = _flt('stat_agility', self.overall)
		self.balance = _flt('stat_balance', self.overall)
		self.reactions = _flt('stat_reactions', self.overall)
		self.ball_control = _flt('stat_ball_control', self.overall)
		self.composure = _flt('stat_composure', self.overall)

		self.interceptions = _flt('stat_interceptions', self.overall)
		self.heading = _flt('stat_heading_accuracy', self.overall)
		self.def_awareness = _flt('stat_defensive_awareness', self.overall)
		self.standing_tackle = _flt('stat_standing_tackle', self.overall)
		self.sliding_tackle = _flt('stat_sliding_tackle', self.overall)

		self.jumping = _flt('stat_jumping', self.overall)
		self.stamina_stat = _flt('stat_stamina', 75.0)
		self.strength = _flt('stat_strength', self.overall)
		self.aggression = _flt('stat_aggression', self.overall)

		is_gk = (self.primary_position == 'GK' or self.position == 'GK')
		if is_gk:
			self.gk_overall = self.overall
			self.gk_diving = _flt('face_pace', self.overall)
			self.gk_handling = _flt('face_shooting', self.overall)
			self.gk_kicking = _flt('face_passing', int(self.overall * 0.85))
			self.gk_reflexes = _flt('face_dribbling', self.overall)
			self.gk_speed = _flt('face_defending', 45.0)
			self.gk_positioning = _flt('face_physicality', self.overall)
			self.gk_reactions = self.gk_reflexes

			self.face_pace = self.gk_diving
			self.face_shooting = self.gk_handling
			self.face_passing = self.gk_kicking
			self.face_dribbling = self.gk_reflexes
			self.face_defending = self.gk_speed
			self.face_physicality = self.gk_positioning

			self.attack = 15.0
			self.defense = self.gk_overall
			self.pace = self.gk_speed
			self.finishing = 15.0
			self.shot_power = 40.0
			self.long_shots = 15.0
			self.volleys = 15.0
			self.penalties = 30.0
			self.free_kick = 15.0
			self.curve = 20.0
			self.heading = 20.0
			self.crossing = 20.0
			self.standing_tackle = 20.0
			self.sliding_tackle = 15.0
			self.interceptions = 20.0
			self.def_awareness = 20.0
		else:
			self.face_pace = _flt('face_pace', (self.acceleration + self.sprint_speed) / 2.0)
			self.face_shooting = _flt('face_shooting', (self.finishing + self.shot_power) / 2.0)
			self.face_passing = _flt('face_passing', (self.short_passing + self.vision) / 2.0)
			self.face_dribbling = _flt('face_dribbling', (self.dribbling_stat + self.ball_control) / 2.0)
			self.face_defending = _flt('face_defending', (self.def_awareness + self.standing_tackle) / 2.0)
			self.face_physicality = _flt('face_physicality', (self.stamina_stat + self.strength) / 2.0)

			if self.position in ['ATT', 'AMF']:
				self.attack = self.face_shooting * 0.40 + self.finishing * 0.25 + self.face_dribbling * 0.20 + self.face_pace * 0.15
				self.defense = self.face_defending * 0.70 + self.aggression * 0.30
			elif self.position == 'MID':
				self.attack = self.face_passing * 0.40 + self.face_dribbling * 0.30 + self.face_shooting * 0.20 + self.face_pace * 0.10
				self.defense = self.face_defending * 0.50 + self.interceptions * 0.25 + self.face_physicality * 0.25
			elif self.position == 'DMF':
				self.attack = self.face_passing * 0.50 + self.face_shooting * 0.20 + self.face_pace * 0.30
				self.defense = self.face_defending * 0.45 + self.standing_tackle * 0.25 + self.interceptions * 0.20 + self.strength * 0.10
			else:
				self.attack = self.crossing * 0.40 + self.face_passing * 0.30 + self.face_pace * 0.30
				self.defense = self.face_defending * 0.45 + self.def_awareness * 0.25 + self.standing_tackle * 0.15 + self.strength * 0.15

			self.pace = self.face_pace

		self.shooting = self.face_shooting
		self.passing = self.face_passing
		self.dribbling = self.face_dribbling
		self.defending = self.face_defending
		self.physicality = self.face_physicality

		self.stamina = max(0.7, min(1.3, self.stamina_stat / 80.0))

		age_bonus = max(0, self.age - 24) * 0.6
		capt_calc = (self.composure * 0.40 + self.reactions * 0.30 + self.overall * 0.30 + age_bonus) / 10.0
		self.capt = int(capt_calc)

		return self

	def has_playstyle(self, style_name):
		s = style_name.strip().lower()
		return (s in self.playstyles) or (s in self.playstyles_plus.lower())

	def stats(self, match):
		self.match_goals = 0
		self.match_assists = 0

	def perf_desc(self):
		if len(self.inns) > 0:
			perf = self.inns[-1]
			parts = []
			if perf.goals > 0:
				parts.append('{}G'.format(perf.goals))
			if perf.assists > 0:
				parts.append('{}A'.format(perf.assists))
			if perf.saves > 0:
				parts.append('{}S'.format(perf.saves))
			if len(parts) > 0:
				return ' '.join(parts)
		return ''

	def short_desc(self):
		disp_name = getattr(self, 'short_name', '') or self.name
		c = ' (C)' if self.capt >= 10 else ''
		return "[{:<3}] {:<20} OVR:{:<2.0f} PAC:{:<2.0f} SHO:{:<2.0f} PAS:{:<2.0f} DRI:{:<2.0f} DEF:{:<2.0f} PHY:{:<2.0f}{}".format(
			self.primary_position, disp_name[:20], self.overall,
			self.face_pace, self.face_shooting, self.face_passing,
			self.face_dribbling, self.face_defending, self.face_physicality, c
		)

	name = ''
	short_name = ''
	full_name = ''
	team = ''
	club = ''
	league = ''
	nation = ''
	overall = 70.0
	rarity = ''
	positions = []
	primary_position = 'CM'
	position = 'MID'
	age = 25
	height = ''
	weight = ''
	preferred_foot = 'Right'
	weak_foot = 3
	skill_moves = 3
	accelerate_type = 'Controlled'
	playstyles_plus = ''
	playstyles_base = ''
	face_pace = 70.0
	face_shooting = 65.0
	face_passing = 68.0
	face_dribbling = 70.0
	face_defending = 60.0
	face_physicality = 68.0
	finishing = 65.0
	positioning = 65.0
	shot_power = 70.0
	long_shots = 65.0
	volleys = 60.0
	penalties = 65.0
	vision = 68.0
	crossing = 65.0
	free_kick = 60.0
	short_passing = 70.0
	long_passing = 68.0
	curve = 65.0
	dribbling_stat = 70.0
	agility = 70.0
	balance = 70.0
	reactions = 70.0
	ball_control = 70.0
	composure = 70.0
	interceptions = 60.0
	heading = 60.0
	def_awareness = 60.0
	standing_tackle = 60.0
	sliding_tackle = 58.0
	acceleration = 70.0
	sprint_speed = 70.0
	jumping = 68.0
	stamina_stat = 75.0
	strength = 68.0
	aggression = 65.0
	gk_overall = 70.0
	gk_positioning = 70.0
	gk_reactions = 70.0
	attack = 65.0
	defense = 60.0
	pace = 70.0
	stamina = 1.0
	capt = 0
	games = 0
	goals = 0
	assists = 0
	clean_sheets = 0
	motm = 0
	match_goals = 0
	match_assists = 0
	fitness = 1.0
	inns = []

class team:
	def __init__(self):
		self.name = ''
		self.league = ''
		self.players = []
		self.active = []
		self.squad = []
		self.xi = []
		self.formation = '4-3-3'
		self.captain = ''
		self.gamecapt = ''
		self.rating = 0
		self.subs_made = 0

	name = ''
	league = ''
	players = []
	active = []
	squad = []
	xi = []
	formation = '4-3-3'
	captain = ''
	gamecapt = ''
	rating = 0
	subs_made = 0

def _load_stadium_map():
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stadiums.json')
	if not os.path.exists(path):
		path = 'data/stadiums.json'
	if os.path.exists(path):
		try:
			import json
			with open(path, 'r', encoding='utf-8') as f:
				return json.load(f)
		except Exception:
			pass
	return {}

STADIUM_MAP = _load_stadium_map()

def _strip_accents(text):
	import unicodedata as _ud
	return ''.join(c for c in _ud.normalize('NFD', str(text)) if _ud.category(c) != 'Mn').lower()

def get_stadium(club_name):
	if not club_name:
		return 'Stadium'
	clean = str(club_name).strip()
	if clean in STADIUM_MAP:
		return STADIUM_MAP[clean]
	lower = clean.lower()
	if lower in _CSV_TO_INTERNAL:
		mapped = _CSV_TO_INTERNAL[lower]
		if mapped in STADIUM_MAP:
			return STADIUM_MAP[mapped]
	norm = _strip_accents(lower)
	for k, v in STADIUM_MAP.items():
		if _strip_accents(k.lower()) == norm:
			return v
	for k, v in STADIUM_MAP.items():
		k_norm = _strip_accents(k.lower())
		if len(norm) >= 4 and (norm in k_norm or k_norm in norm):
			return v
	return clean + ' Ground'

_WOMEN_TEAM_KEYS = {
    'Chelsea': 'Chelsea Women',
    'Arsenal': 'Arsenal Women',
    'Manchester United': 'Man Utd Women',
    'West Ham United': 'West Ham Women',
    'Birmingham City': 'Birmingham City Women',
    'Crystal Palace': 'Crystal Palace Women',
    'Charlton Athletic': 'Charlton Athletic Women',
    'FC Zürich': 'FC Zürich Women',
    'TSG 1899 Hoffenheim': 'TSG 1899 Hoffenheim Frauen',
    '1. FC Union Berlin': '1. FC Union Berlin Women',
    'Werder Bremen': 'Werder Bremen Frauen',
    'Ajax': 'Ajax Women',
    '1. FC Köln': '1. FC Köln Frauen',
    'RCD Espanyol': 'Espanyol F',
    'SK Brann': 'SK Brann Women',
    'BK Häcken': 'BK Häcken Women',
    'FC Twente': 'FC Twente Women',
    'Glasgow City': 'Glasgow City Women',
    'Deportivo Alavés': 'Deportivo Alavés F',
    'England Women': 'England Women',
    'Spain Women': 'Spain Women',
    'Scotland Women': 'Scotland Women',
    'Norway Women': 'Norway Women',
}

_CSV_TO_INTERNAL = {
    'manchester united': 'Man Utd',
    'tottenham hotspur': 'Spurs',
    'newcastle united': 'Newcastle Utd',
    'nottingham forest': "Nott'm Forest",
    'west ham united': 'West Ham',
    'wolverhampton wanderers': 'Wolves',
    'brighton & hove albion': 'Brighton',
    'queens park rangers': 'QPR',
    'paris saint-germain': 'PSG',
    'olympique de marseille': 'Marseille',
    'olympique lyonnais': 'Lyon',
    'as monaco': 'Monaco',
    'lille osc': 'LOSC Lille',
    'losc lille': 'LOSC Lille',
    'inter milan': 'Inter Milan',
    'inter': 'Inter Milan',
    'juventus': 'Juventus FC',
    'atalanta': 'Atalanta BC',
    'bayer 04 leverkusen': 'Leverkusen',
    'bayer leverkusen': 'Leverkusen',
    'f.c. københavn': 'F.C. København',
    'fc københavn': 'F.C. København',
    'rsc anderlecht': 'Anderlecht',
    'athletic club': 'Athletic Club',
    'rcd mallorca': 'Mallorca',
    'real sociedad': 'Real Sociedad',
    'ud almería': 'Almería',
    'ud almeria': 'Almería',
    'celta vigo': 'Celta Vigo',
    'rc celta': 'Celta Vigo',
    'rayo vallecano': 'Rayo Vallecano',
    'getafe cf': 'Getafe',
    'ud las palmas': 'Las Palmas',
    'deportivo alavés': 'Deportivo Alavés',
    'girona fc': 'Girona',
    'real valladolid': 'Valladolid',
    'sd eibar': 'SD Eibar',
    'ca osasuna': 'Osasuna',
    'levante ud': 'Levante',
    'cd leganés': 'Leganés',
    'deportivo de la coruña': 'Deportivo',
    'sporting cp': 'Sporting CP',
    'sl benfica': 'Benfica',
    'vitória sc': 'Vitória SC',
    'sc braga': 'Braga',
    'fc porto': 'FC Porto',
    'boavista fc': 'Boavista',
    'rb salzburg': 'RB Salzburg',
    'red bull salzburg': 'RB Salzburg',
    'fc red bull salzburg': 'RB Salzburg',
    'sk rapid wien': 'Rapid Wien',
    'lask': 'LASK',
    'sk sturm graz': 'Sturm Graz',
    'austria wien': 'Austria Wien',
    'galatasaray a.ş.': 'Galatasaray',
    'galatasaray': 'Galatasaray',
    'fenerbahçe sk': 'Fenerbahçe',
    'fenerbahce': 'Fenerbahçe',
    'beşiktaş jk': 'Beşiktaş',
    'besiktas': 'Beşiktaş',
    'trabzonspor': 'Trabzonspor',
    'başakşehir': 'İstanbul Başakşehir',
    'istanbul başakşehir fk': 'İstanbul Başakşehir',
    'türkiye': 'Turkey',
    'al-nassr': 'Al Nassr',
    'al nassr fc': 'Al Nassr',
    'al-hilal': 'Al Hilal',
    'al hilal sfc': 'Al Hilal',
    'al-ittihad': 'Al Ittihad',
    'al ittihad club': 'Al Ittihad',
    'al-ahli': 'Al Ahli',
    'al ahli saudi fc': 'Al Ahli',
    'mamelodi sundowns fc': 'Mamelodi Sundowns',
    'kaizer chiefs fc': 'Kaizer Chiefs',
    'cf montréal': 'CF Montréal',
    'los angeles galaxy': 'LA Galaxy',
    'la galaxy': 'LA Galaxy',
    'new york red bulls': 'New York Red Bulls',
    'ny red bulls': 'New York Red Bulls',
    'atlético de madrid': 'Atlético Madrid',
    'atletico madrid': 'Atlético Madrid',
    'rc deportivo': 'Deportivo',
    'bayern münchen': 'FC Bayern München',
    'fc bayern münchen': 'FC Bayern München',
    'fc bayern munich': 'FC Bayern München',
    'borussia dortmund': 'Dortmund',
    'rb leipzig': 'RB Leipzig',
    'eintracht frankfurt': 'Eintracht Frankfurt',
    'vfl wolfsburg': 'VfL Wolfsburg',
    'sc freiburg': 'SC Freiburg',
    'vfb stuttgart': 'VfB Stuttgart',
    '1. fsv mainz 05': 'FSV Mainz 05',
    'mainz 05': 'FSV Mainz 05',
    'sv werder bremen': 'Werder Bremen',
    'tsg 1899 hoffenheim': 'Hoffenheim',
    'fc augsburg': 'FC Augsburg',
    'fc schalke 04': 'Schalke 04',
    'hamburger sv': 'Hamburger SV',
    'hertha bsc': 'Hertha BSC',
    'fortuna düsseldorf': 'Fortuna Düsseldorf',
    'vfl bochum': 'VfL Bochum',
    'spvgg greuther fürth': 'SpVgg Greuther Fürth',
    '1. fc nürnberg': '1. FC Nürnberg',
    'hannover 96': 'Hannover 96',
    'holstein kiel': 'Holstein Kiel',
    'sc paderborn 07': 'SC Paderborn 07',
    'heidenheim': '1. FC Heidenheim',
    'paris saint-germain féminine': 'PSG Féminine',
    'olympique lyonnais féminin': 'OL Féminin',
    'ol féminin': 'OL Féminin',
    'olympique de marseille féminine': 'Olympique de Marseille Féminine',
    'fc barcelona femenino': 'FC Barcelona F',
    'fc barcelona f': 'FC Barcelona F',
    'atletico madrid women': 'Atlético de Madrid F',
    'atlético de madrid f': 'Atlético de Madrid F',
    'real madrid femenino': 'Real Madrid F',
    'real madrid f': 'Real Madrid F',
    'sevilla fc f': 'Sevilla FC F',
    'fc bayern münchen frauen': 'FC Bayern München Frauen',
    'vfl wolfsburg frauen': 'VfL Wolfsburg Frauen',
    'bayer leverkusen frauen': 'Bayer Leverkusen Frauen',
    'rb leipzig frauen': 'RB Leipzig Frauen',
    'sc freiburg frauen': 'SC Freiburg Frauen',
    'eintracht frankfurt frauen': 'Eintracht Frankfurt Frauen',
    '1. fc köln frauen': '1. FC Köln Frauen',
    '1. fc union berlin women': '1. FC Union Berlin Women',
    'werder bremen frauen': 'Werder Bremen Frauen',
    'tsg 1899 hoffenheim frauen': 'TSG 1899 Hoffenheim Frauen',
    'hamburger sv women': 'Hamburger SV Women',
    'manchester city women': 'Manchester City Women',
    'arsenal women': 'Arsenal Women',
    'chelsea women': 'Chelsea Women',
    'liverpool women': 'Liverpool Women',
    'aston villa women': 'Aston Villa Women',
    'leicester city women': 'Leicester City Women',
    'everton women': 'Everton Women',
    'brighton & hove albion women': 'Brighton Women',
    'west ham united women': 'West Ham Women',
    'tottenham hotspur women': 'Spurs Women',
    'manchester united women': 'Man Utd Women',
    'birmingham city women': 'Birmingham City Women',
    'crystal palace women': 'Crystal Palace Women',
    'charlton athletic women': 'Charlton Athletic Women',
    'juventus fc women': 'Juventus Women',
    'juventus women': 'Juventus Women',
    'roma women': 'AS Roma Women',
    'as roma women': 'AS Roma Women',
    'aj auxerre': 'AJ Auxerre',
    'rc lens': 'RC Lens',
    'as saint-étienne': 'AS Saint-Étienne',
    'stade rennais fc': 'Stade Rennais',
    'stade de reims': 'Stade de Reims',
    'montpellier hsc': 'Montpellier',
    'rc strasbourg alsace': 'RC Strasbourg',
    'toulouse fc': 'Toulouse',
    'stade brestois 29': 'Brest',
    'le havre ac': 'Le Havre',
    'fc metz': 'FC Metz',
    'dijon fco': 'Dijon',
    'grenoble foot 38': 'Grenoble',
    'pau fc': 'Pau FC',
    'rodez af': 'Rodez',
    'real sociedad femenino': 'Real Sociedad F',
    'athletic club femenino': 'Athletic Club Women',
    'ol lyonnes': 'OL Lyonnes',
    'fc rosengård': 'FC Rosengård Women',
    'bk häcken': 'BK Häcken Women',
    'malmö ff': 'Malmö FF',
    'aik': 'AIK',
    'djurgårdens if': 'Djurgårdens IF',
    'ifk göteborg': 'IFK Göteborg',
    'ifk norrköping': 'IFK Norrköping',
    'fc nordsjælland': 'FC Nordsjælland',
    'ac horsens': 'AC Horsens',
    'brøndby if': 'Brøndby IF',
    'fc midtjylland': 'FC Midtjylland',
    'fc fredericia': 'FC Fredericia',
    'silkeborg if': 'Silkeborg IF',
    'odense boldklub': 'Odense BK',
    'vejle bk': 'Vejle BK',
    'viborg ff': 'Viborg FF',
    'randers fc': 'Randers FC',
    'sønderjyske fodbold': 'Sønderjyske',
    'agf': 'AGF',
    'fk austria wien': 'Austria Wien',
    'sk rapid wien': 'Rapid Wien',
}

_DUAL_TEAM_WOMEN_MAP = {
    'Bayern München':       'FC Bayern München Frauen',
    'FC Barcelona':         'FC Barcelona F',
    'Real Madrid':          'Real Madrid F',
    'Atlético de Madrid':   'Atlético de Madrid F',
    'VfL Wolfsburg':        'VfL Wolfsburg Frauen',
    'Liverpool':            'Liverpool Women',
    'Manchester City':      'Manchester City Women',
    'Slavia Praha':         'Slavia Praha Women',
    'OL Lyonnes':           'OL Lyonnes',
}

def _load_club_managers():
	import csv as _csv
	import json as _json
	import os as _os
	result = {}
	base_dir = _os.path.dirname(_os.path.abspath(__file__))
	csv_path = _os.path.join(base_dir, 'data', 'managers.csv')
	if _os.path.exists(csv_path):
		try:
			with open(csv_path, mode='r', encoding='utf-8-sig', errors='replace') as f:
				reader = _csv.DictReader(f)
				for row in reader:
					club = (row.get('club') or row.get('team_name') or '').strip()
					name = (row.get('name') or (row.get('info.firstname', '') + ' ' + row.get('info.surname', ''))).strip()
					if club and name:
						result[club] = name
		except Exception:
			pass
	json_path = _os.path.join(base_dir, 'data', 'club_managers.json')
	if _os.path.exists(json_path):
		try:
			with open(json_path, mode='r', encoding='utf-8') as f:
				result.update(_json.load(f))
		except Exception:
			pass
	return result

CLUB_MANAGERS = _load_club_managers()

def get_club_manager(team_name):
	if not team_name:
		return 'Manager'
	clean = str(team_name).strip()
	if clean in CLUB_MANAGERS:
		return CLUB_MANAGERS[clean]
	lower = clean.lower()
	if lower in _CSV_TO_INTERNAL:
		mapped = _CSV_TO_INTERNAL[lower]
		if mapped in CLUB_MANAGERS:
			return CLUB_MANAGERS[mapped]
	norm = _strip_accents(lower)
	for k, v in CLUB_MANAGERS.items():
		if _strip_accents(k.lower()) == norm:
			return v
	for k, v in CLUB_MANAGERS.items():
		k_norm = _strip_accents(k.lower())
		if len(norm) >= 4 and (norm in k_norm or k_norm in norm):
			return v
	return '{} Manager'.format(clean)

CLUB_PHILOSOPHIES = {
	'FC Barcelona': 'tiki_taka',
	'FC Barcelona F': 'tiki_taka',
	'Manchester City': 'tiki_taka',
	'Arsenal': 'tiki_taka',
	'Leverkusen': 'tiki_taka',
	'Ajax': 'tiki_taka',
	'Sporting CP': 'tiki_taka',
	'Celtic': 'tiki_taka',
	'Real Madrid': 'direct_counter',
	'Real Madrid F': 'direct_counter',
	'Inter Milan': 'direct_counter',
	'Atlético de Madrid': 'low_block',
	'Atlético de Madrid F': 'low_block',
	'Fenerbahçe': 'low_block',
	'Atlético Nacional': 'low_block',
	'Liverpool': 'high_press',
	'FC Bayern München': 'high_press',
	'FC Bayern München Frauen': 'high_press',
	'Borussia Dortmund': 'high_press',
	'Atalanta BC': 'high_press',
	'Spurs': 'high_press',
	'Napoli': 'high_press',
	'Feyenoord': 'high_press',
	'Benfica': 'high_press',
	'FC Porto': 'high_press',
	'Brighton & Hove Albion': 'high_press',
	'Bayer Leverkusen': 'high_press',
	'RB Leipzig': 'high_press',
	'Chelsea': 'balanced',
	'Chelsea Women': 'balanced',
	'PSG': 'balanced',
	'PSG Féminine': 'balanced',
	'Man Utd': 'balanced',
	'Juventus FC': 'balanced',
	'River Plate': 'balanced',
	'Palmeiras': 'balanced',
	'Galatasaray': 'balanced',
	'Boca Juniors': 'direct_counter',
	'Real Betis': 'tiki_taka',
	'Olympique de Marseille': 'high_press',
	'OGC Nice': 'balanced',
}

class CoachAI:
	def __init__(self, team_obj, match):
		self.team = team_obj
		self.match = match
		t_name = getattr(team_obj, 'name', '') or str(team_obj)
		self.name = get_club_manager(t_name)
		self.philosophy = CLUB_PHILOSOPHIES.get(t_name, 'balanced')
		self.mentality = 'balanced'
		self.subs_made = 0
		self.max_subs = 5
		self.tactical_orders = set()

	def evaluate(self, minute, goal_diff):
		if minute >= 60 and goal_diff <= -1:
			if 'attacking_overload' not in self.tactical_orders:
				self.tactical_orders.add('attacking_overload')
				self.mentality = 'attacking_overload'
				msg = "{} are committing extra bodies forward now, with {} urging {pos} team to flood into the attacking third.".format(
					self.team.name, self.name, pos="her" if "Women" in self.team.name else "his"
				)
				self.match.logger(msg)

		elif minute >= 72 and goal_diff >= 1:
			if 'low_block' not in self.tactical_orders:
				self.tactical_orders.add('low_block')
				self.mentality = 'low_block'
				msg = "{} are managing the contest with composure now, compacting their defensive lines to protect this lead.".format(
					self.team.name
				)
				self.match.logger(msg)

		if self.subs_made < self.max_subs:
			if minute in [60, 68, 75, 82]:
				self.make_tactical_substitution(minute, goal_diff)
			elif minute >= 55:
				fatigued = [p for p in getattr(self.team, 'xi', []) if p.position != 'GK' and getattr(p, 'fitness', 1.0) < 0.52]
				cautioned = [p for p in getattr(self.team, 'xi', []) if p.position != 'GK' and len(p.inns) > 0 and p.inns[-1].yellow_cards > 0 and getattr(p, 'fitness', 1.0) < 0.65]
				if fatigued or cautioned:
					self.make_tactical_substitution(minute, goal_diff)

	def make_tactical_substitution(self, minute, goal_diff):
		used_in = [pair[0] for pair in getattr(self.team, 'subs_used', [])]
		used_out = [pair[1] for pair in getattr(self.team, 'subs_used', [])]

		if hasattr(self.team, 'bench') and self.team.bench:
			bench_pool = self.team.bench
		else:
			bench_pool = getattr(self.team, 'squad', [])

		bench = [p for p in bench_pool if p not in self.team.xi and p not in used_in and p not in used_out and p.position != 'GK']
		if not bench:
			return
		outfield = [p for p in self.team.xi if p.position != 'GK']
		if not outfield:
			return

		candidates = [p for p in outfield if p not in used_in]
		if not candidates:
			candidates = outfield

		candidates = sorted(candidates, key=lambda p: (
			getattr(p, 'fitness', 1.0) - (0.22 if (len(p.inns) > 0 and p.inns[-1].yellow_cards > 0) else 0.0)
		))
		p_out = candidates[0]

		if goal_diff <= -1 or (goal_diff == 0 and minute >= 68):
			p_in = max(bench, key=lambda p: getattr(p, 'attack', getattr(p, 'overall', 70)) * 0.5 + getattr(p, 'face_pace', 70) * 0.5)
			p_in.is_super_sub = True
			role_note = "super-sub attacking injection"
		elif goal_diff >= 1 and minute >= 74:
			def_bench = [p for p in bench if getattr(p, 'position', '') in ['CB', 'DEF', 'DMF', 'LB', 'RB']]
			p_in = max(def_bench, key=lambda p: getattr(p, 'defense', getattr(p, 'overall', 70))) if def_bench else max(bench, key=lambda p: getattr(p, 'defense', 70))
			role_note = "defensive fortress"
			if hasattr(self.team, 'formation') and '5-' not in getattr(self.team, 'formation', ''):
				self.team.formation = '5-3-2'
				self.match.logger("{} adjusts formation into a compact 5-3-2 low block to lock down the victory.".format(self.team.name))
		elif getattr(p_out, 'fitness', 1.0) < 0.55:
			p_in = max(bench, key=lambda p: getattr(p, 'overall', 70))
			role_note = "fatigue replacement"
		else:
			p_in = max(bench, key=lambda p: getattr(p, 'overall', 70))
			role_note = "fresh legs"

		idx = self.team.xi.index(p_out)
		self.team.xi[idx] = p_in
		p_in.fitness = 1.0

		if not hasattr(self.team, 'subs_used'):
			self.team.subs_used = []
		self.team.subs_used.append((p_in, p_out, minute))

		if len(p_out.inns) > 0:
			p_out.inns[-1].minutes_played = minute
			p_out.inns[-1].subbed_out = True
			p_out.inns[-1].sub_minute = minute

		if len(p_in.inns) == 0 or p_in.inns[-1].match != self.match:
			MatchPerformance(p_in, self.match)
		p_in.inns[-1].minutes_played = max(1, 90 - minute)
		p_in.inns[-1].subbed_in = True
		p_in.inns[-1].sub_minute = minute

		if p_in not in self.match.players:
			self.match.players.append(p_in)

		self.subs_made += 1
		if self.team == self.match.home:
			self.match.home_subs_made = getattr(self.match, 'home_subs_made', 0) + 1
		else:
			self.match.away_subs_made = getattr(self.match, 'away_subs_made', 0) + 1

		if hasattr(self.team, 'manager_pov') and self.team.manager_pov:
			self.team.manager_pov.record_substitution(self.team)
		out_disp = getattr(p_out, 'short_name', '') or p_out.name
		in_disp = getattr(p_in, 'short_name', '') or p_in.name
		self.match.logger("SUBSTITUTION ({}): {} replaces {} ({})".format(
			self.team.name, in_disp, out_disp, role_note
		))

class fixture:
	def __init__(self):
		self.card = []
		self.log = []
		self.players = []
		self.periods = []
		self.home = ''
		self.away = ''
		self.home_score = 0
		self.away_score = 0
		self.minute = 0
		self.win = ''
		self.draw = False
		self.loss = ''
		self.motm = ''
		self.venue = ''
		self.scorecard = 'scorecard.txt'
		self.savecard = SAVE_SCORECARD
		self.kickoff_team = ''
		self.extra_time_opt = False
		self.penalties_opt = False
		self.fullcard = True
		self.resultdesc = ''

		self.momentum = {}
		self.home_poss_ticks = 0
		self.away_poss_ticks = 0
		self.home_poss = 50.0
		self.away_poss = 50.0
		self.home_shots = 0
		self.away_shots = 0
		self.home_shots_target = 0
		self.away_shots_target = 0
		self.home_xg = 0.0
		self.away_xg = 0.0
		self.home_corners = 0
		self.away_corners = 0
		self.home_fouls = 0
		self.away_fouls = 0
		self.home_yellows = 0
		self.away_yellows = 0
		self.home_reds = 0
		self.away_reds = 0
		self.home_passes_comp = 0
		self.home_passes_att = 0
		self.away_passes_comp = 0
		self.away_passes_att = 0
		self.home_subs_made = 0
		self.away_subs_made = 0
		self.home_coach = None
		self.away_coach = None
		self.grid = PitchGrid()
		self.home_game_state = None
		self.away_game_state = None
		self.possession_engine = None
		self.home_elo = 1750
		self.away_elo = 1750

	def decay_momentum(self):
		for k in self.momentum:
			self.momentum[k] *= 0.95
		if hasattr(self.home, 'manager_pov') and self.home.manager_pov:
			self.home.manager_pov.decay_disruption(self.home)
		if hasattr(self.away, 'manager_pov') and self.away.manager_pov:
			self.away.manager_pov.decay_disruption(self.away)

	def update_possession(self):
		total = self.home_poss_ticks + self.away_poss_ticks
		if total > 0:
			self.home_poss = round((self.home_poss_ticks / float(total)) * 100.0, 1)
			self.away_poss = round(100.0 - self.home_poss, 1)

	def halftime_box(self):
		self.update_possession()
		h_name = self.home.name
		a_name = self.away.name
		h_score = self.home_score
		a_score = self.away_score
		title = "HALF TIME — {} {} - {} {}".format(h_name, h_score, a_score, a_name)

		h_acc = int((self.home_passes_comp / float(max(1, self.home_passes_att))) * 100)
		a_acc = int((self.away_passes_comp / float(max(1, self.away_passes_att))) * 100)

		self.blank()
		self.score("=" * 64)
		self.score(title.center(64))
		self.score("=" * 64)
		self.score("{:<28} {:>16} {:>16}".format("Match Stats", h_name[:16], a_name[:16]))
		self.score("-" * 64)
		self.score("{:<28} {:>15.1f}% {:>15.1f}%".format("Possession", self.home_poss, self.away_poss))
		self.score("{:<28} {:>16.2f} {:>16.2f}".format("Expected Goals (xG)", self.home_xg, self.away_xg))
		self.score("{:<28} {:>12} ({}) {:>12} ({})".format("Shots (On Target)", self.home_shots, self.home_shots_target, self.away_shots, self.away_shots_target))
		self.score("{:<28} {:>16} {:>16}".format("Corners", self.home_corners, self.away_corners))
		self.score("{:<28} {:>16} {:>16}".format("Fouls", self.home_fouls, self.away_fouls))
		self.score("{:<28} {:>16} {:>16}".format("Yellow Cards", self.home_yellows, self.away_yellows))
		self.score("{:<28} {:>15}% {:>15}%".format("Pass Accuracy", h_acc, a_acc))
		self.score("=" * 64)
		self.blank()
		self.logprint()

	def fulltime_stats(self):
		self.update_possession()
		h_name = self.home.name
		a_name = self.away.name
		h_acc = int((self.home_passes_comp / float(max(1, self.home_passes_att))) * 100)
		a_acc = int((self.away_passes_comp / float(max(1, self.away_passes_att))) * 100)

		self.blank()
		self.score("=" * 66)
		self.score("FULL TIME MATCH STATISTICS".center(66))
		self.score("=" * 66)
		self.score("{:<28} {:>17} {:>17}".format("Category", h_name[:17], a_name[:17]))
		self.score("-" * 66)
		self.score("{:<28} {:>17} {:>17}".format("Score", self.home_score, self.away_score))
		self.score("{:<28} {:>16.1f}% {:>16.1f}%".format("Possession", self.home_poss, self.away_poss))
		self.score("{:<28} {:>17.2f} {:>17.2f}".format("Expected Goals (xG)", self.home_xg, self.away_xg))
		self.score("{:<28} {:>17} {:>17}".format("Total Shots", self.home_shots, self.away_shots))
		self.score("{:<28} {:>17} {:>17}".format("Shots on Target", self.home_shots_target, self.away_shots_target))
		self.score("{:<28} {:>17} {:>17}".format("Corners", self.home_corners, self.away_corners))
		self.score("{:<28} {:>17} {:>17}".format("Fouls Committed", self.home_fouls, self.away_fouls))
		self.score("{:<28} {:>17} {:>17}".format("Yellow Cards", self.home_yellows, self.away_yellows))
		self.score("{:<28} {:>17} {:>17}".format("Red Cards", self.home_reds, self.away_reds))
		self.score("{:<28} {:>16}% {:>16}%".format("Pass Accuracy", h_acc, a_acc))
		h_passes_str = "{}/{}".format(self.home_passes_comp, self.home_passes_att)
		a_passes_str = "{}/{}".format(self.away_passes_comp, self.away_passes_att)
		self.score("{:<28} {:>17} {:>17}".format("Passes Completed", h_passes_str, a_passes_str))
		self.score("=" * 66)
		self.blank()

	def player_ratings_table(self):
		for p in self.players:
			if len(p.inns) > 0:
				p.inns[-1].calculate_rating(self)

		for t in [self.home, self.away]:
			self.blank()
			self.score("=" * 84)
			self.score("{} PLAYER RATINGS & STATS".format(t.name.upper()).center(84))
			self.score("=" * 84)
			self.score("POS  PLAYER                   OVR  G  A  SH SOT  TK INT  SV   xG   xA  MIN   RTG")
			self.score("-" * 84)

			starters = getattr(t, 'starters', t.xi[:11])
			self.score("STARTERS:")
			for p in starters:
				perf = p.inns[-1] if len(p.inns) > 0 else None
				if perf:
					pos_tag = getattr(p, 'primary_position', p.position).ljust(4)
					disp_name = (getattr(p, 'short_name', '') or p.name)[:23].ljust(23)
					min_str = "{}'".format(perf.minutes_played)
					self.score("{} {} {:>3.0f} {:>2} {:>2} {:>3} {:>3} {:>3} {:>3} {:>3} {:>5.2f} {:>4.2f} {:>4}  {:>4.1f}".format(
						pos_tag, disp_name, p.overall,
						perf.goals, perf.assists, perf.shots, perf.shots_on_target,
						perf.tackles, perf.interceptions, perf.saves, perf.xg, perf.xa, min_str, perf.rating
					))

			bench = getattr(t, 'bench', [])
			if bench:
				self.score("-" * 84)
				self.score("SUBSTITUTES:")
				for p in bench:
					perf = p.inns[-1] if (len(p.inns) > 0 and getattr(p.inns[-1], 'subbed_in', False)) else None
					pos_tag = getattr(p, 'primary_position', p.position).ljust(4)
					disp_name = (getattr(p, 'short_name', '') or p.name)[:23].ljust(23)
					if perf:
						min_str = "{}'".format(perf.minutes_played)
						self.score("{} {} {:>3.0f} {:>2} {:>2} {:>3} {:>3} {:>3} {:>3} {:>3} {:>5.2f} {:>4.2f} {:>4}  {:>4.1f}".format(
							pos_tag, disp_name, p.overall,
							perf.goals, perf.assists, perf.shots, perf.shots_on_target,
							perf.tackles, perf.interceptions, perf.saves, perf.xg, perf.xa, min_str, perf.rating
						))
					else:
						self.score("{} {} {:>3.0f}  -  -   -   -   -   -   -     -    -  {:<5}  -".format(
							pos_tag, disp_name, p.overall, 'Unused'
						))
			self.score("=" * 84)
		self.blank()

	def football(self):
		self.card = []
		self.settings()
		self.playerlog()
		if not self.home_coach and self.home != '':
			self.home_coach = CoachAI(self.home, self)
		if not self.away_coach and self.away != '':
			self.away_coach = CoachAI(self.away, self)
		self.home_manager = getattr(self.home, 'manager_pov', None) or ManagerPOV(self.home.name, formation=getattr(self.home, 'formation', None))
		self.away_manager = getattr(self.away, 'manager_pov', None) or ManagerPOV(self.away.name, formation=getattr(self.away, 'formation', None))
		self.home_manager.update_fluidity(self.home)
		self.away_manager.update_fluidity(self.away)
		self.home.manager_pov = self.home_manager
		self.away.manager_pov = self.away_manager
		self.home.formation = self.home_manager.formation
		self.away.formation = self.away_manager.formation
		self.home_formation_mod, self.away_formation_mod = get_formation_matchup(self.home.formation, self.away.formation)
		self.momentum[self.home.name] = 0.0
		self.momentum[self.away.name] = 0.0
		if (not self.venue or self.venue.endswith(' Ground')) and hasattr(self.home, 'name') and self.home.name:
			self.venue = get_stadium(self.home.name)
		if hasattr(self.home, 'name') and self.home.name and self.home_elo == 1750:
			self.home_elo = get_club_elo(self.home.name, self.home)
		if hasattr(self.away, 'name') and self.away.name and self.away_elo == 1750:
			self.away_elo = get_club_elo(self.away.name, self.away)
		self.header()
		self.kickoff()
		self.home_game_state = GameStateManager(self.home, self, is_home=True)
		self.away_game_state = GameStateManager(self.away, self, is_home=False)
		self.possession_engine = PossessionEngine(self, self.grid, self.home_game_state, self.away_game_state)

		p1 = period(self, 1)
		self.periods.append(p1)
		p1.run()
		self.blank()

		p2 = period(self, 2)
		self.periods.append(p2)
		p2.run()
		self.blank()

		if self.home_score == self.away_score and self.extra_time_opt:
			self.logger('Full time reached with scores level. Heading into extra time.')
			self.blank()
			p3 = period(self, 3)
			self.periods.append(p3)
			p3.run()
			self.blank()
			p4 = period(self, 4)
			self.periods.append(p4)
			p4.run()
			self.blank()
			if self.home_score == self.away_score and self.penalties_opt:
				self.shootout()
				self.blank()

		self.endofgame()

	def settings(self):
		settings_path = 'variables/settings.txt'
		if not os.path.exists(settings_path):
			base_dir = os.path.dirname(os.path.abspath(__file__))
			settings_path = os.path.join(base_dir, 'variables', 'settings.txt')
		if os.path.exists(settings_path):
			try:
				a = []
				with open(settings_path, 'r') as f:
					for line in f:
						line = line.strip()
						if not line or line.startswith('#'):
							continue
						x = line.split('=')
						if len(x) > 1:
							k = x[0].strip()
							v = x[1].strip()
							a.append((k, v))
				if any(k == 'active' and v.lower() == 'true' for k, v in a):
					for k, v in a:
						if v.lower() == 'default':
							continue
						if k == 'venue':
							self.venue = v
						elif k == 'extra_time':
							self.extra_time_opt = (v.lower() == 'true')
						elif k == 'penalties':
							self.penalties_opt = (v.lower() == 'true')
						elif k in ['savecard', 'save_scorecard', 'log_scorecard']:
							self.savecard = (v.lower() == 'true')
						elif k == 'kickoff':
							if v.lower() == 'home' and self.home != '':
								self.kickoff_team = self.home
							elif v.lower() == 'away' and self.away != '':
								self.kickoff_team = self.away
			except Exception:
				pass

	def playerlog(self):
		for t in [self.home, self.away]:
			if t != '':
				if not hasattr(t, 'xi') or not t.xi:
					pool = getattr(t, 'active', []) or getattr(t, 'squad', []) or getattr(t, 'players', [])
					t.xi = list(pool[:11])
				if not hasattr(t, 'starters') or not t.starters:
					t.starters = list(t.xi)
				if not hasattr(t, 'bench') or not t.bench:
					squad = getattr(t, 'squad', []) or getattr(t, 'active', []) or getattr(t, 'players', [])
					pool = [p for p in squad if p not in t.xi]
					pool.sort(key=lambda p: p.overall, reverse=True)
					t.bench = pool[:5]
				if not hasattr(t, 'subs_used'):
					t.subs_used = []

		starters_list = [*self.home.starters, *self.away.starters]
		bench_list = [*getattr(self.home, 'bench', []), *getattr(self.away, 'bench', [])]
		self.players = starters_list + bench_list
		for p in self.players:
			p.fitness = 1.0
			if len(p.inns) == 0 or p.inns[-1].match != self:
				perf = MatchPerformance(p, self)
				if p in starters_list:
					perf.minutes_played = 90
					perf.subbed_in = False
				else:
					perf.minutes_played = 0
					perf.subbed_in = False

	def logger(self, x):
		m = self.minute
		score_str = '{}-{}'.format(self.home_score, self.away_score)
		entry = [x, m, '{} {} {}'.format(self.home.name, score_str, self.away.name)]
		if x not in [a[0] for a in self.log]:
			self.log.append(entry)

	def cardkeep(self, x, end='\n'):
		if not self.savecard:
			return
		try:
			with open(self.scorecard, 'a', encoding='utf-8') as f:
				f.write(x)
				f.write(end)
		except Exception:
			pass

	def score(self, x, end='\n'):
		self.card.append(x)
		self.cardkeep(x, end)

	def logprint(self):
		for i in self.card:
			print(i)
		self.card = []

		f = None
		if self.savecard:
			try:
				f = open(self.scorecard, 'a', encoding='utf-8')
			except Exception:
				f = None

		try:
			for i in self.log:
				minute = str(i[1]).rjust(3)
				score = str(i[2]).ljust(20)
				z = "{}' {}  {}".format(minute, score, i[0])
				if i[0] == '':
					if f:
						f.write('\n')
					print()
				else:
					if f:
						f.write(z)
						f.write('\n')
					print(z)
		finally:
			if f:
				f.close()
		self.log = []

	def header(self):
		if self.savecard:
			try:
				with open(self.scorecard, 'w', encoding='utf-8') as f:
					pass
			except Exception:
				pass
		x = '{} vs. {}'.format(self.home.name, self.away.name)
		self.score(x)
		if self.venue != '':
			self.score('Venue: {}'.format(self.venue))
		self.score('Date: {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
		self.blank()
		h_mgr = "Manager: {}  |  Tactics: {}".format(self.home_coach.name, self.home_coach.philosophy.replace('_', ' ').title()) if self.home_coach else ""
		self.score('{} Starting XI:{}'.format(self.home.name, ('  [' + h_mgr + ']') if h_mgr else ''))
		h_starters = getattr(self.home, 'starters', self.home.xi)
		for p in h_starters:
			capt_str = ' (C)' if p == self.home.gamecapt else ''
			p_disp = getattr(p, 'short_name', '') or p.name
			self.score('  {} - {} [OVR:{:.0f}]{}'.format(p.primary_position.ljust(3), p_disp, p.overall, capt_str))
		if hasattr(self.home, 'bench') and self.home.bench:
			bench_names = [getattr(p, 'short_name', '') or p.name for p in self.home.bench]
			self.score('  Substitutes: {}'.format(', '.join(bench_names)))
		self.blank()
		a_mgr = "Manager: {}  |  Tactics: {}".format(self.away_coach.name, self.away_coach.philosophy.replace('_', ' ').title()) if self.away_coach else ""
		self.score('{} Starting XI:{}'.format(self.away.name, ('  [' + a_mgr + ']') if a_mgr else ''))
		a_starters = getattr(self.away, 'starters', self.away.xi)
		for p in a_starters:
			capt_str = ' (C)' if p == self.away.gamecapt else ''
			p_disp = getattr(p, 'short_name', '') or p.name
			self.score('  {} - {} [OVR:{:.0f}]{}'.format(p.primary_position.ljust(3), p_disp, p.overall, capt_str))
		if hasattr(self.away, 'bench') and self.away.bench:
			bench_names = [getattr(p, 'short_name', '') or p.name for p in self.away.bench]
			self.score('  Substitutes: {}'.format(', '.join(bench_names)))
		self.blank()

	def blank(self):
		if self.savecard:
			try:
				with open(self.scorecard, 'a', encoding='utf-8') as f:
					f.write('\n')
			except Exception:
				pass
		self.card.append('')

	def cardsave(self):
		if not self.savecard:
			return
		try:
			timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
			os.makedirs('scorecards', exist_ok=True)
			dest = 'scorecards/{}_{}_{}.txt'.format(
				self.home.name.replace(' ', '_'),
				self.away.name.replace(' ', '_'),
				timestamp
			)
			if os.path.exists(self.scorecard):
				shutil.copyfile(self.scorecard, dest)
		except Exception:
			pass

	def kickoff(self):
		if self.kickoff_team == '':
			self.kickoff_team = random.choice([self.home, self.away])
		x = '{} won the toss and will kick off.'.format(self.kickoff_team.name)
		self.score(x)
		self.blank()

	def scoreline(self):
		return '{} {} - {} {}'.format(self.home.name, self.home_score, self.away_score, self.away.name)

	def clean_sheet(self, t):
		if t == self.home.name or t == self.home:
			return self.away_score == 0
		return self.home_score == 0

	def motmpick(self):
		best_score = -1
		best_p = None
		for p in self.players:
			perf = p.inns[-1] if len(p.inns) > 0 else None
			if perf:
				rtg = perf.rating
				win_name = self.win.name if hasattr(self.win, 'name') else str(self.win)
				win_bonus = 0.4 if (p.team == win_name and not self.draw) else 0.0
				s = rtg + win_bonus + random.uniform(0, 0.2)
				if s > best_score:
					best_score = s
					best_p = p
		self.motm = best_p if best_p else (self.players[0] if self.players else '')
		return self.motm

	def shootout(self):
		self.logger('Penalty Shootout begins!')
		home_pen = 0
		away_pen = 0

		home_takers = sorted([p for p in self.home.xi if p.position != 'GK'], key=lambda p: (p.penalties * 0.7 + p.composure * 0.3), reverse=True)
		away_takers = sorted([p for p in self.away.xi if p.position != 'GK'], key=lambda p: (p.penalties * 0.7 + p.composure * 0.3), reverse=True)

		home_gk = next((p for p in self.home.xi if p.position == 'GK'), None)
		away_gk = next((p for p in self.away.xi if p.position == 'GK'), None)

		for r in range(5):
			hp = home_takers[r % len(home_takers)]
			gk_def = away_gk.gk_overall if away_gk else 70
			pen_prob = 0.75 + (hp.penalties - 70) * 0.003 - (gk_def - 70) * 0.002
			pen_prob = max(0.40, min(0.92, pen_prob))
			hp_name = getattr(hp, 'short_name', hp.name)
			if random.random() < pen_prob:
				home_pen += 1
				self.logger('Shootout: {} scored for {} ({}-{})'.format(hp_name, self.home.name, home_pen, away_pen))
			else:
				gk_name = getattr(away_gk, 'short_name', away_gk.name) if away_gk else 'the keeper'
				self.logger('Shootout: {} had their penalty saved by {}!'.format(hp_name, gk_name))

			ap = away_takers[r % len(away_takers)]
			gk_def = home_gk.gk_overall if home_gk else 70
			pen_prob = 0.75 + (ap.penalties - 70) * 0.003 - (gk_def - 70) * 0.002
			pen_prob = max(0.40, min(0.92, pen_prob))
			ap_name = getattr(ap, 'short_name', ap.name)
			if random.random() < pen_prob:
				away_pen += 1
				self.logger('Shootout: {} scored for {} ({}-{})'.format(ap_name, self.away.name, home_pen, away_pen))
			else:
				gk_name = getattr(home_gk, 'short_name', home_gk.name) if home_gk else 'the keeper'
				self.logger('Shootout: {} had their penalty saved by {}!'.format(ap_name, gk_name))

		r_round = 5
		while home_pen == away_pen:
			hp = home_takers[r_round % len(home_takers)]
			ap = away_takers[r_round % len(away_takers)]
			h_score = random.random() < 0.70
			a_score = random.random() < 0.70
			if h_score: home_pen += 1
			if a_score: away_pen += 1
			self.logger('Shootout Sudden Death: {} {} - {} {}'.format(self.home.name, home_pen, away_pen, self.away.name))
			r_round += 1

		if home_pen > away_pen:
			self.win = self.home
			self.loss = self.away
			self.draw = False
			self.resultdesc = '{} won on penalties {}-{}'.format(self.home.name, home_pen, away_pen)
		else:
			self.win = self.away
			self.loss = self.home
			self.draw = False
			self.resultdesc = '{} won on penalties {}-{}'.format(self.away.name, away_pen, home_pen)

	def endofgame(self):
		if self.resultdesc == '':
			if self.home_score > self.away_score:
				self.win = self.home
				self.loss = self.away
				self.draw = False
				self.resultdesc = '{} won {} - {}'.format(self.home.name, self.home_score, self.away_score)
			elif self.away_score > self.home_score:
				self.win = self.away
				self.loss = self.home
				self.draw = False
				self.resultdesc = '{} won {} - {}'.format(self.away.name, self.away_score, self.home_score)
			else:
				self.win = 'Draw'
				self.loss = 'Draw'
				self.draw = True
				self.resultdesc = 'the match was drawn {} - {}'.format(self.home_score, self.away_score)

		for p in self.players:
			if len(p.inns) > 0:
				p.inns[-1].stats()
			p.stats(self)

		self.fulltime_stats()
		self.player_ratings_table()
		self.motmpick()

		self.blank()
		self.score('Final Whistle: {}'.format(self.scoreline()))
		self.score('Result: {}'.format(self.resultdesc))
		if self.motm != '':
			m_disp = getattr(self.motm, 'short_name', '') or self.motm.name
			m_rtg = self.motm.inns[-1].rating if len(self.motm.inns) > 0 else 8.5
			self.score('Man of the Match: {} ({}) [Rating: {:.1f}]'.format(m_disp, self.motm.team, m_rtg))
		self.blank()
		self.matchreport()
		self.logprint()
		if self.savecard:
			self.cardsave()

	def matchreport(self):
		a = []
		a.append('Match Report:')
		if self.venue != '':
			a.append('At {}.'.format(self.venue))
		if self.kickoff_team != '':
			a.append('{} won the toss and kicked off.'.format(self.kickoff_team.name))

		total_goals = self.home_score + self.away_score
		if total_goals >= 5:
			a.append(random.choice(['It was a thrilling, high-scoring encounter.', 'Spectators were treated to an absolute goal-fest.', 'A breathless, end-to-end clash produced goals galore.']))
		elif total_goals == 0:
			a.append(random.choice(['It was a cagey, tactical battle with defenses reigning supreme.', 'Both sides cancelled each other out in a hard-fought stalemate.', 'Chances were hard to come by in a gritty, defensive contest.']))
		elif abs(self.home_score - self.away_score) >= 3:
			a.append(random.choice(['It was a completely one-sided affair.', 'The winning side delivered a dominant and commanding display.', 'A ruthlessly clinical performance sealed an emphatic victory.']))
		else:
			a.append(random.choice(['It was a closely-contested match that went right down to the wire.', 'Both teams fought tooth and nail in a competitive fixture.', 'A tense, well-matched battle kept fans on the edge of their seats.']))

		p1 = self.periods[0] if len(self.periods) > 0 else None
		if p1:
			p1_home = len([g for g in p1.goals if g[2] == self.home])
			p1_away = len([g for g in p1.goals if g[2] == self.away])
			if p1_home > p1_away:
				a.append('In the first half, {} led {}-{} at the break.'.format(self.home.name, p1_home, p1_away))
			elif p1_away > p1_home:
				a.append('In the first half, {} led {}-{} at the break.'.format(self.away.name, p1_away, p1_home))
			else:
				a.append('In the first half, the sides went into the break level at {}-{}.'.format(p1_home, p1_away))

		p2 = self.periods[1] if len(self.periods) > 1 else None
		if p2:
			p2_home = len([g for g in p2.goals if g[2] == self.home])
			p2_away = len([g for g in p2.goals if g[2] == self.away])
			p2_goals = p2_home + p2_away
			if p2_goals > 0:
				a.append('The second half saw {} more goal{} scored.'.format(p2_goals, 's' if p2_goals > 1 else ''))

		notable = []
		for p in self.players:
			if len(p.inns) > 0:
				perf = p.inns[-1]
				if perf.goals >= 1 or perf.assists >= 2 or perf.saves >= 4 or perf.rating >= 8.2:
					notable.append(perf.report(self))
		if len(notable) == 1:
			a.append('Outstanding performances included {}.'.format(notable[0]))
		elif len(notable) > 1:
			a.append('Outstanding performances included {}.'.format(listshow(notable, end='and')))

		if self.draw:
			a.append('In the end, neither side could find the winner and points were shared.')
		else:
			a.append('In the end, {} emerged victorious.'.format(self.win.name if hasattr(self.win, 'name') else str(self.win)))

		if self.motm != '':
			self.score('')
			m_disp = getattr(self.motm, 'short_name', '') or self.motm.name
			a.append('The man of the match was {} of {}.'.format(m_disp, self.motm.team))

		b = ' '.join(a)
		self.score('')
		self.score(b)

	home = ''
	away = ''
	home_score = 0
	away_score = 0
	minute = 0
	log = []
	card = []
	win = ''
	draw = False
	loss = ''
	motm = ''
	venue = ''
	scorecard = 'scorecard.txt'
	savecard = True
	kickoff_team = ''
	periods = []
	extra_time_opt = False
	penalties_opt = False
	fullcard = True
	resultdesc = ''
	players = []

class period:
	def __init__(self, match, half):
		self.match = match
		self.half = half
		other_team = match.away if match.kickoff_team == match.home else match.home
		if half in [1, 3]:
			self.att_team = match.kickoff_team
			self.def_team = other_team
		else:
			self.att_team = other_team
			self.def_team = match.kickoff_team
		self.goals = []
		self.minutes = 0
		self.active = True
		self.injury_time = random.randint(1, 3) if half == 1 else random.randint(3, 5)

	def calculate_dynamic_stoppage(self):
		if self.half == 1:
			base = 1.0
			extra = (len(self.match.card) * 0.5) + ((self.match.home_yellows + self.match.away_yellows) * 0.3)
			return max(1, min(4, round(base + extra)))
		elif self.half == 2:
			base = 2.0
			n_subs = len(getattr(self.match.home, 'subs_used', [])) + len(getattr(self.match.away, 'subs_used', []))
			n_goals = self.match.home_score + self.match.away_score
			n_cards = (self.match.home_yellows + self.match.away_yellows + self.match.home_reds + self.match.away_reds)
			stoppage = base + (0.5 * n_subs) + (0.75 * n_goals) + (0.4 * n_cards)
			return max(3, min(8, round(stoppage)))
		else:
			return random.randint(1, 3)

	def run(self):
		half_len = 15 if self.half in [3, 4] else 45
		total_mins = half_len + self.injury_time
		half_name = 'First Half' if self.half == 1 else ('Second Half' if self.half == 2 else ('Extra Time First Half' if self.half == 3 else 'Extra Time Second Half'))
		self.match.logger('Kick-off: {} begins.'.format(half_name))
		if hasattr(self.match, 'possession_engine') and self.match.possession_engine:
			self.match.possession_engine.reset_kickoff(self.att_team)
		while self.minutes < total_mins and self.active:
			if self.minutes == half_len:
				self.injury_time = self.calculate_dynamic_stoppage()
				total_mins = half_len + self.injury_time
				self.match.logger("The fourth official indicates a minimum of {} minute{} of stoppage time to be played.".format(
					self.injury_time, 's' if self.injury_time > 1 else ''
				))
			self.minute_event()
			self.match.minute += 1
			self.minutes += 1
		self.period_end()

	def period_end(self):
		half_name = 'Half Time' if self.half == 1 else ('Full Time' if self.half == 2 else 'End of Extra Time Period')
		self.match.logger('{}: {}'.format(half_name, self.match.scoreline()))
		self.match.logprint()
		if self.half == 1:
			self.match.halftime_box()

	def corner_event(self, att_team, def_team):
		if att_team == self.match.home:
			self.match.home_corners += 1
		else:
			self.match.away_corners += 1

		outfield = [p for p in att_team.xi if p.position != 'GK']
		if not outfield:
			outfield = att_team.xi

		def _taker_score(p):
			score = p.crossing * 0.65 + p.curve * 0.35
			if hasattr(p, 'has_playstyle'):
				if p.has_playstyle('whipped pass'): score += 10
				if p.has_playstyle('dead ball'): score += 10
			return score

		takers = sorted(outfield, key=_taker_score, reverse=True)
		if not takers:
			return
		taker = takers[0]

		def _aerial_score(p):
			score = p.heading * 0.45 + p.jumping * 0.35 + p.strength * 0.20
			if hasattr(p, 'has_playstyle'):
				if p.has_playstyle('aerial fortress') or p.has_playstyle('power header'): score += 12
			return score

		aerial_targets = sorted(outfield, key=_aerial_score, reverse=True)
		if not aerial_targets:
			return
		target = aerial_targets[0]

		gk = next((p for p in def_team.xi if p.position == 'GK'), None)
		gk_div = getattr(gk, 'gk_diving', 75.0) if gk else 75.0
		gk_ref = getattr(gk, 'gk_reflexes', 75.0) if gk else 75.0
		gk_han = getattr(gk, 'gk_handling', 75.0) if gk else 75.0
		gk_stat = gk_div * 0.35 + gk_ref * 0.35 + gk_han * 0.30

		def_cbs = [p for p in def_team.xi if getattr(p, 'assigned_slot', p.position) in ['CB', 'DEF', 'CDM']]
		marker = max(def_cbs, key=_aerial_score) if def_cbs else None
		marker_rating = _aerial_score(marker) if marker else 70.0

		att_mgr = getattr(att_team, 'manager_pov', None)
		set_piece_focus = att_mgr.set_piece_focus if att_mgr else 'balanced'

		t_name = getattr(target, 'short_name', '') or target.name
		k_name = getattr(taker, 'short_name', '') or taker.name
		m_disp = (getattr(marker, 'short_name', '') or marker.name) if marker else 'the defense'
		gk_disp = (getattr(gk, 'short_name', '') or gk.name) if gk else 'the keeper'

		if set_piece_focus == 'short_routine' and random.random() < 0.35:
			edge_cands = [p for p in outfield if p != taker and p != target]
			edge_p = max(edge_cands, key=lambda p: getattr(p, 'long_shots', 70) * 0.6 + getattr(p, 'shot_power', 70) * 0.4) if edge_cands else target
			e_name = getattr(edge_p, 'short_name', '') or edge_p.name
			short_xg = 0.065 * (getattr(edge_p, 'long_shots', 75) / 80.0) * getattr(edge_p, 'fitness', 1.0)
			if len(edge_p.inns) > 0:
				edge_p.inns[-1].shots += 1
				edge_p.inns[-1].xg += short_xg
			if att_team == self.match.home:
				self.match.home_shots += 1
				self.match.home_xg += short_xg
			else:
				self.match.away_shots += 1
				self.match.away_xg += short_xg

			roll = random.random()
			if roll < short_xg:
				if len(edge_p.inns) > 0:
					edge_p.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				self.log_goal(edge_p, taker, att_team, 'box')
				return
			elif roll < 0.30:
				if len(edge_p.inns) > 0:
					edge_p.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				if gk and len(gk.inns) > 0:
					gk.inns[-1].saves += 1
				self.match.logger("Short corner worked to {}, who curls a snapshot through traffic towards goal, but {} parries it cleanly away!".format(e_name, gk_disp))
				return
			else:
				self.match.logger("Short corner routine attempted by {}, but the low delivery is blocked at the near post by {}.".format(k_name, m_disp))
				return

		cross_qual = (taker.crossing * 0.65 + taker.curve * 0.35) / 80.0
		target_aer = _aerial_score(target) / 80.0
		marker_def = marker_rating / 80.0
		corner_xg = 0.034 * cross_qual * (target_aer / max(0.5, marker_def)) * getattr(target, 'fitness', 1.0)
		if target.has_playstyle('aerial fortress') or target.has_playstyle('power header'):
			corner_xg += 0.015
		if taker.has_playstyle('whipped pass'):
			corner_xg += 0.010
		if set_piece_focus == 'aerial_overload':
			corner_xg *= 1.25
		corner_xg = max(0.015, min(0.075, corner_xg))

		if len(target.inns) > 0:
			target.inns[-1].shots += 1
			target.inns[-1].xg += corner_xg
		if att_team == self.match.home:
			self.match.home_shots += 1
			self.match.home_xg += corner_xg
		else:
			self.match.away_shots += 1
			self.match.away_xg += corner_xg

		roll = random.random()
		if roll < corner_xg:
			if len(target.inns) > 0:
				target.inns[-1].shots_on_target += 1
			if att_team == self.match.home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			self.log_goal(target, taker, att_team, 'header')
		elif roll < 0.24:
			if len(target.inns) > 0:
				target.inns[-1].shots_on_target += 1
			if att_team == self.match.home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			if gk and len(gk.inns) > 0:
				gk.inns[-1].saves += 1
			self.match.logger("Corner! {} whips a dangerous cross into the box, {} connects with a thumping header, but {} makes a sensational fingertip save over the bar!".format(k_name, t_name, gk_disp))
		elif roll < 0.30:
			self.match.logger("Glancing header from {} off {}'s corner, but it rattles the outside of the post and bounces clear!".format(t_name, k_name))
		else:
			if marker and len(marker.inns) > 0:
				marker.inns[-1].aerials_won += 1
			self.match.logger("Corner swung in towards the penalty spot by {}, but {} climbs highest and thumps a commanding clearing header away.".format(k_name, m_disp))
			if set_piece_focus == 'aerial_overload' and random.random() < 0.22:
				self.match.logger("With center-backs pushed forward for the corner, {} quickly gather the loose ball and break at pace!".format(def_team.name))

	def freekick_event(self, att_team, def_team, is_indirect=None):
		outfield = [p for p in att_team.xi if p.position != 'GK']
		if not outfield:
			outfield = att_team.xi

		if is_indirect is None:
			is_indirect = (random.random() < 0.50)

		gk = next((p for p in def_team.xi if p.position == 'GK'), None)
		gk_div = getattr(gk, 'gk_diving', 75.0) if gk else 75.0
		gk_ref = getattr(gk, 'gk_reflexes', 75.0) if gk else 75.0
		gk_stat = (gk_div * 0.5 + gk_ref * 0.5) if gk else 75.0
		gk_disp = getattr(gk, 'short_name', '') or (gk.name if gk else 'the keeper')

		if not is_indirect:
			takers = sorted(outfield, key=lambda p: p.free_kick * 0.55 + p.shot_power * 0.25 + p.curve * 0.20, reverse=True)
			if not takers:
				return
			taker = takers[0]
			t_name = getattr(taker, 'short_name', '') or taker.name

			fk_xg = 0.055 * (taker.free_kick / 80.0) * (taker.curve / 80.0) * (taker.shot_power / 80.0) / (gk_stat / 75.0)
			if taker.has_playstyle('dead ball'):
				fk_xg += 0.025
			fk_xg = max(0.025, min(0.095, fk_xg))

			if len(taker.inns) > 0:
				taker.inns[-1].shots += 1
				taker.inns[-1].xg += fk_xg
			if att_team == self.match.home:
				self.match.home_shots += 1
				self.match.home_xg += fk_xg
			else:
				self.match.away_shots += 1
				self.match.away_xg += fk_xg

			roll = random.random()
			if roll < fk_xg:
				if len(taker.inns) > 0:
					taker.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				self.log_goal(taker, None, att_team, 'direct_freekick')
			elif roll < 0.34:
				if len(taker.inns) > 0:
					taker.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				if gk and len(gk.inns) > 0:
					gk.inns[-1].saves += 1
				self.match.logger("Terrific strike from the set piece! {} bends the free kick up and over the wall, but {} makes an acrobatic parry!".format(t_name, gk_disp))
				if random.random() < 0.35:
					self.corner_event(att_team, def_team)
			elif roll < 0.40:
				self.match.logger("Unbelievable strike from {}! The free kick has the keeper beaten all ends up, but crashes against the face of the crossbar!".format(t_name))
			else:
				pos_pro = 'her' if getattr(taker, 'gender', 'Male') == 'Female' else 'his'
				self.match.logger("Free Kick! {} tries {} luck from distance, but whistles the strike just wide of the target.".format(t_name, pos_pro))
		else:
			takers = sorted(outfield, key=lambda p: p.long_passing * 0.45 + p.crossing * 0.35 + p.curve * 0.20, reverse=True)
			if not takers:
				return
			taker = takers[0]
			k_name = getattr(taker, 'short_name', '') or taker.name

			aerial_targets = sorted(outfield, key=lambda p: p.heading * 0.45 + p.jumping * 0.35 + p.strength * 0.20, reverse=True)
			target = aerial_targets[0] if aerial_targets else taker
			t_name = getattr(target, 'short_name', '') or target.name

			def_cbs = [p for p in def_team.xi if getattr(p, 'assigned_slot', p.position) in ['CB', 'DEF', 'CDM']]
			marker = max(def_cbs, key=lambda p: p.heading * 0.45 + p.jumping * 0.35 + p.strength * 0.20) if def_cbs else None
			m_disp = (getattr(marker, 'short_name', '') or marker.name) if marker else 'the defense'

			def_mgr = getattr(def_team, 'manager_pov', None)
			trap_dir = def_mgr.offside_trap if def_mgr else 'balanced'
			if trap_dir != 'conservative':
				trap_risk = def_mgr.get_offside_trap_risk() if def_mgr else 0.020
				if random.random() < trap_risk:
					fluidity = getattr(def_team, 'fluidity', 1.0)
					if random.random() < (0.75 * fluidity):
						self.match.logger("The flag is up! The defensive backline stepped up in unison, catching {} half a yard offside as the delivery arrived.".format(t_name))
						return
					elif trap_dir == 'aggressive' and random.random() < 0.32:
						self.match.logger("The offside trap was disastrously mistimed! The defensive line pushed up late and {} is completely unmarked to volley home {}'s delivery!".format(t_name, k_name))
						if len(target.inns) > 0:
							target.inns[-1].shots += 1
							target.inns[-1].shots_on_target += 1
							target.inns[-1].xg += 0.38
						if att_team == self.match.home:
							self.match.home_shots += 1
							self.match.home_shots_target += 1
							self.match.home_xg += 0.38
						else:
							self.match.away_shots += 1
							self.match.away_shots_target += 1
							self.match.away_xg += 0.38
						self.log_goal(target, taker, att_team, 'box')
						return

			deliv_qual = (taker.long_passing * 0.50 + taker.crossing * 0.35 + taker.curve * 0.15) / 80.0
			target_aer = (target.heading * 0.45 + target.jumping * 0.35 + target.strength * 0.20) / 80.0
			marker_def = (marker.heading * 0.45 + marker.jumping * 0.35 + marker.strength * 0.20) / 80.0 if marker else 1.0
			ifk_xg = 0.042 * deliv_qual * (target_aer / max(0.5, marker_def)) * getattr(target, 'fitness', 1.0)
			if target.has_playstyle('aerial fortress') or target.has_playstyle('power header'):
				ifk_xg += 0.015
			ifk_xg = max(0.018, min(0.080, ifk_xg))

			if len(target.inns) > 0:
				target.inns[-1].shots += 1
				target.inns[-1].xg += ifk_xg
			if att_team == self.match.home:
				self.match.home_shots += 1
				self.match.home_xg += ifk_xg
			else:
				self.match.away_shots += 1
				self.match.away_xg += ifk_xg

			roll = random.random()
			if roll < ifk_xg:
				if len(target.inns) > 0:
					target.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				self.log_goal(target, taker, att_team, 'header')
			elif roll < 0.25:
				if len(target.inns) > 0:
					target.inns[-1].shots_on_target += 1
				if att_team == self.match.home:
					self.match.home_shots_target += 1
				else:
					self.match.away_shots_target += 1
				if gk and len(gk.inns) > 0:
					gk.inns[-1].saves += 1
				self.match.logger("{} pumps the free kick into the penalty area, {} rises to head towards the bottom corner, but {} reacts sharply to parry it away!".format(k_name, t_name, gk_disp))
			else:
				if marker and len(marker.inns) > 0:
					marker.inns[-1].aerials_won += 1
				self.match.logger("{} floats the delivery into the mixer, but {} commands the box and thumps a clearing header away.".format(k_name, m_disp))

	def penalty_event(self, att_team, def_team, fouled_player=None, fouling_player=None):
		f_name = (getattr(fouled_player, 'short_name', '') or fouled_player.name) if fouled_player else 'the attacker'
		d_name = (getattr(fouling_player, 'short_name', '') or fouling_player.name) if fouling_player else 'the defender'
		self.match.logger("Penalty! {} is brought down inside the area by {}, and the referee points straight to the spot!".format(f_name, d_name))

		outfield = [p for p in att_team.xi if p.position != 'GK']
		if not outfield:
			outfield = att_team.xi
		takers = sorted(outfield, key=lambda p: p.penalties * 0.65 + p.composure * 0.35, reverse=True)
		if not takers:
			return
		taker = takers[0]
		t_name = getattr(taker, 'short_name', '') or taker.name

		gk = next((p for p in def_team.xi if p.position == 'GK'), None)
		gk_div = getattr(gk, 'gk_diving', 75.0) if gk else 75.0
		gk_ref = getattr(gk, 'gk_reflexes', 75.0) if gk else 75.0
		gk_stat = (gk_div * 0.5 + gk_ref * 0.5) if gk else 75.0

		pen_xg = 0.78
		if len(taker.inns) > 0:
			taker.inns[-1].shots += 1
			taker.inns[-1].xg += pen_xg
		if att_team == self.match.home:
			self.match.home_shots += 1
			self.match.home_xg += pen_xg
		else:
			self.match.away_shots += 1
			self.match.away_xg += pen_xg

		conv_prob = 0.77 + (taker.penalties - 75) * 0.003 + (taker.composure - 75) * 0.002 - (gk_stat - 75) * 0.0025
		conv_prob = max(0.55, min(0.92, conv_prob))

		roll = random.random()
		if roll < conv_prob:
			if len(taker.inns) > 0:
				taker.inns[-1].shots_on_target += 1
			if att_team == self.match.home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			self.log_goal(taker, None, att_team, 'penalty')
		elif roll < conv_prob + 0.16:
			if len(taker.inns) > 0:
				taker.inns[-1].shots_on_target += 1
			if att_team == self.match.home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			if gk and len(gk.inns) > 0:
				gk.inns[-1].saves += 1
			gk_disp = getattr(gk, 'short_name', '') or (gk.name if gk else 'the keeper')
			pos_pro = 'her' if getattr(gk, 'gender', 'Male') == 'Female' else 'his'
			self.match.logger("Saved! {} guesses correctly, springs to {} left, and turns {}'s spot kick around the post!".format(gk_disp, pos_pro, t_name))
			if random.random() < 0.40:
				self.corner_event(att_team, def_team)
		else:
			self.match.logger("He's missed it! {} aims for the top corner but drills the penalty against the crossbar!".format(t_name))

	def minute_event(self):
		if hasattr(self.match, 'possession_engine') and self.match.possession_engine:
			self.match.possession_engine.simulate_minute(self, self.match.minute)
			return
		m = self.match.minute

		h_diff = self.match.home_score - self.match.away_score
		a_diff = -h_diff
		if hasattr(self.match, 'home_coach') and self.match.home_coach:
			self.match.home_coach.evaluate(m, h_diff)
		if hasattr(self.match, 'away_coach') and self.match.away_coach:
			self.match.away_coach.evaluate(m, a_diff)

		h_coach = getattr(self.match, 'home_coach', None)
		a_coach = getattr(self.match, 'away_coach', None)

		for p in (self.match.home.xi + self.match.away.xi):
			if len(p.inns) > 0:
				pos = getattr(p, 'position', 'MID')
				if pos == 'GK':
					base_decay = 0.0002
				elif pos in ['MID', 'DMF', 'AMF']:
					base_decay = 0.0022
				elif pos in ['LB', 'RB', 'LWB', 'RWB', 'LM', 'RM', 'LW', 'RW']:
					base_decay = 0.0020
				elif pos in ['ATT', 'CF', 'ST']:
					base_decay = 0.0016
				else:
					base_decay = 0.0013

				stam = getattr(p, 'stamina', 75.0)
				decay = base_decay * max(0.65, min(1.35, (115.0 - stam) / 40.0))
				if p.has_playstyle('relentless'):
					decay *= 0.70
				p.fitness = max(0.68, getattr(p, 'fitness', 1.0) - decay)

		h_mom = max(-1.5, min(1.5, self.match.momentum.get(self.match.home.name, 0.0)))
		a_mom = max(-1.5, min(1.5, self.match.momentum.get(self.match.away.name, 0.0)))

		h_mult = 1.0 + h_mom * 0.015 + 0.05
		a_mult = 1.0 + a_mom * 0.015

		if h_coach:
			if h_coach.philosophy == 'tiki_taka': h_mult *= 1.12
			elif h_coach.philosophy == 'high_press': h_mult *= 1.06
			elif h_coach.philosophy in ['direct_counter', 'low_block']: h_mult *= 0.92
			if h_coach.mentality == 'attacking_overload': h_mult *= 1.18
			elif h_coach.mentality == 'low_block': h_mult *= 0.88

		if a_coach:
			if a_coach.philosophy == 'tiki_taka': a_mult *= 1.12
			elif a_coach.philosophy == 'high_press': a_mult *= 1.06
			elif a_coach.philosophy in ['direct_counter', 'low_block']: a_mult *= 0.92
			if a_coach.mentality == 'attacking_overload': a_mult *= 1.18
			elif a_coach.mentality == 'low_block': a_mult *= 0.88

		if m >= 55:
			if h_diff >= 2:
				h_mult *= 0.88
				a_mult *= 1.22
			elif h_diff == 1:
				h_mult *= 0.94
				a_mult *= 1.12
			elif h_diff == -1:
				a_mult *= 0.94
				h_mult *= 1.12
			elif h_diff <= -2:
				a_mult *= 0.88
				h_mult *= 1.22

		h_att = att_strength(self.match.home.xi) * h_mult
		a_att = att_strength(self.match.away.xi) * a_mult
		total_ctrl = h_att + a_att
		prob_home = h_att / total_ctrl if total_ctrl > 0 else 0.50

		if random.random() < prob_home:
			self.match.home_poss_ticks += 1
			ctrl_team = self.match.home
			opp_team = self.match.away
			ctrl_coach = h_coach
			opp_coach = a_coach
		else:
			self.match.away_poss_ticks += 1
			ctrl_team = self.match.away
			opp_team = self.match.home
			ctrl_coach = a_coach
			opp_coach = h_coach

		if ctrl_coach and ctrl_coach.philosophy == 'tiki_taka':
			pass_count = random.randint(8, 14)
		elif ctrl_coach and ctrl_coach.philosophy == 'direct_counter':
			pass_count = random.randint(5, 9)
		else:
			pass_count = random.randint(6, 11)

		avg_pass_stat = sum([p.short_passing for p in ctrl_team.xi if p.position in ['MID', 'DMF', 'DEF']]) / max(1, len([p for p in ctrl_team.xi if p.position in ['MID', 'DMF', 'DEF']]))
		pass_acc_rate = min(0.92, max(0.70, (avg_pass_stat / 100.0) + 0.08))
		if ctrl_coach and ctrl_coach.philosophy == 'tiki_taka':
			pass_acc_rate = min(0.95, pass_acc_rate + 0.05)
		if opp_coach and opp_coach.philosophy == 'high_press':
			pass_acc_rate = max(0.66, pass_acc_rate - 0.05)

		completed = int(pass_count * pass_acc_rate)
		if ctrl_team == self.match.home:
			self.match.home_passes_att += pass_count
			self.match.home_passes_comp += completed
		else:
			self.match.away_passes_att += pass_count
			self.match.away_passes_comp += completed

		for p in ctrl_team.xi:
			if len(p.inns) == 0: continue
			p_role = getattr(p, 'position', 'MID')
			p_fit = getattr(p, 'fitness', 1.0)
			if p_role in ['MID', 'DMF', 'AMF']:
				if random.random() < 0.72:
					att_p = random.randint(1, 2)
					acc = min(0.95, max(0.68, (p.short_passing / 100.0) * p_fit + (0.04 if p.has_playstyle('tiki taka') else 0.0)))
					comp_p = att_p if random.random() < acc else (att_p - 1)
					p.inns[-1].passes_attempted += att_p
					p.inns[-1].passes_completed += comp_p
			elif p_role == 'DEF':
				if random.random() < 0.58:
					att_p = random.randint(1, 2)
					acc = min(0.94, max(0.68, (p.short_passing / 100.0) * p_fit))
					comp_p = att_p if random.random() < acc else (att_p - 1)
					p.inns[-1].passes_attempted += att_p
					p.inns[-1].passes_completed += comp_p
			elif p_role == 'ATT':
				if random.random() < 0.35:
					att_p = 1
					acc = min(0.90, max(0.62, (p.short_passing / 100.0) * p_fit))
					comp_p = 1 if random.random() < acc else 0
					p.inns[-1].passes_attempted += att_p
					p.inns[-1].passes_completed += comp_p
			elif p_role == 'GK':
				if random.random() < 0.18:
					att_p = 1
					acc = min(0.90, max(0.58, (getattr(p, 'gk_kicking', 70.0) / 100.0) * p_fit))
					comp_p = 1 if random.random() < acc else 0
					p.inns[-1].passes_attempted += att_p
					p.inns[-1].passes_completed += comp_p

		opp_pool = [p for p in opp_team.xi if len(p.inns) > 0]
		cdms = [p for p in opp_pool if p.position == 'DMF']
		cbs = [p for p in opp_pool if p.primary_position == 'CB' or p.position == 'DEF']
		fbs = [p for p in opp_pool if p.primary_position in ['LB', 'RB', 'LWB', 'RWB']]
		cms = [p for p in opp_pool if p.position in ['MID', 'AMF']]

		duel_mult = 1.25 if (opp_coach and opp_coach.philosophy == 'high_press') else 1.0
		if cdms and random.random() < (0.20 * duel_mult):
			cdm = random.choice(cdms)
			if random.random() < 0.58: cdm.inns[-1].tackles += 1
			else: cdm.inns[-1].interceptions += 1

		if cbs and random.random() < (0.18 * duel_mult):
			cb = random.choice(cbs)
			roll_cb = random.random()
			if roll_cb < 0.45: cb.inns[-1].tackles += 1
			elif roll_cb < 0.75: cb.inns[-1].interceptions += 1
			else: cb.inns[-1].aerials_won += 1

		if fbs and random.random() < (0.16 * duel_mult):
			fb = random.choice(fbs)
			if random.random() < 0.58: fb.inns[-1].tackles += 1
			else: fb.inns[-1].interceptions += 1

		if cms and random.random() < (0.12 * duel_mult):
			cm = random.choice(cms)
			if random.random() < 0.55: cm.inns[-1].tackles += 1
			else: cm.inns[-1].interceptions += 1

		foul_prob = 0.24
		if opp_coach and opp_coach.philosophy == 'high_press': foul_prob += 0.05
		if random.random() < foul_prob:
			fouling_team = opp_team if random.random() < 0.72 else ctrl_team
			victim_team = ctrl_team if fouling_team == opp_team else opp_team
			foul_cands = [p for p in fouling_team.xi if len(p.inns) > 0 and p.position != 'GK']
			if foul_cands:
				f_weights = []
				for fp in foul_cands:
					w = fp.aggression * 0.5 + fp.standing_tackle * 0.3
					if fp.position in ['DMF', 'DEF']: w += 20
					if fp.has_playstyle('bruiser') or fp.has_playstyle('slide tackle'): w += 15
					f_weights.append(max(1.0, w))
				fouler = random.choices(foul_cands, weights=f_weights, k=1)[0]
				fouler.inns[-1].fouls_committed += 1

				if fouling_team == self.match.home:
					self.match.home_fouls += 1
				else:
					self.match.away_fouls += 1

				victims = [p for p in victim_team.xi if p.position in ['ATT', 'AMF', 'MID']] or victim_team.xi
				victim = random.choice(victims)
				fouler_name = getattr(fouler, 'short_name', '') or fouler.name
				victim_name = getattr(victim, 'short_name', '') or victim.name

				if fouling_team == opp_team and random.random() < 0.035:
					self.penalty_event(ctrl_team, opp_team, fouled_player=victim, fouling_player=fouler)
					return

				yellow_roll = random.random()
				if yellow_roll < 0.14:
					fouler.inns[-1].yellow_cards += 1
					if fouling_team == self.match.home:
						self.match.home_yellows += 1
					else:
						self.match.away_yellows += 1

					if fouler.inns[-1].yellow_cards == 1:
						self.match.logger("Yellow card. {} is booked following a cynical foul on {}.".format(fouler_name, victim_name))
					elif fouler.inns[-1].yellow_cards >= 2:
						fouler.inns[-1].red_cards += 1
						if fouling_team == self.match.home:
							self.match.home_reds += 1
						else:
							self.match.away_reds += 1
						fouler.inns[-1].minutes_played = m
						fouler.inns[-1].out = True
						if fouler in fouling_team.xi:
							fouling_team.xi.remove(fouler)
						self.match.logger("He's off! A second yellow card for {}! The referee brandishes the red, and {} are reduced to {} men!".format(
							fouler_name, fouling_team.name, len(fouling_team.xi)
						))
						return
				elif yellow_roll < 0.1435:
					fouler.inns[-1].red_cards += 1
					if fouling_team == self.match.home:
						self.match.home_reds += 1
					else:
						self.match.away_reds += 1
					fouler.inns[-1].minutes_played = m
					fouler.inns[-1].out = True
					if fouler in fouling_team.xi:
						fouling_team.xi.remove(fouler)
					self.match.logger("Straight red card! A reckless challenge by {} on {} leaves the referee no choice! {} are down to {} men!".format(
						fouler_name, victim_name, fouling_team.name, len(fouling_team.xi)
					))
					return

		self.match.decay_momentum()

		att_split = 0.82 if (ctrl_coach and ctrl_coach.philosophy == 'tiki_taka') else 0.74
		att_team = ctrl_team if random.random() < att_split else opp_team
		def_team = opp_team if att_team == ctrl_team else ctrl_team
		att_coach = ctrl_coach if att_team == ctrl_team else opp_coach
		def_coach = opp_coach if att_team == ctrl_team else ctrl_coach

		def_cbs = [p for p in def_team.xi if p.primary_position == 'CB' or p.position == 'DEF']
		avg_def_awareness = sum([p.def_awareness for p in def_cbs]) / float(len(def_cbs)) if def_cbs else 70.0
		if random.random() < (0.014 * (avg_def_awareness / 75.0)):
			attackers = [p for p in att_team.xi if p.position in ['ATT', 'AMF']]
			if attackers:
				att_p = random.choice(attackers)
				att_name = getattr(att_p, 'short_name', '') or att_p.name
				cb = random.choice(def_cbs) if def_cbs else None
				cb_name = (getattr(cb, 'short_name', '') or cb.name) if cb else 'the defense'
				self.match.logger("Flag goes up on the far side! The backline stepped up in unison, catching {} comfortably offside.".format(att_name))
				return

		if random.random() < 0.018:
			self.freekick_event(att_team, def_team)
			return

		att = att_strength(att_team.xi)
		defe = def_strength(def_team.xi)
		if att_team == self.match.home:
			att *= 1.05
		else:
			defe *= 1.04

		if att_coach and att_coach.mentality == 'attacking_overload': att *= 1.20
		if def_coach and def_coach.mentality == 'low_block': defe *= 1.25
		if def_coach and def_coach.philosophy == 'low_block': defe *= 1.15

		ratio = att / (att + defe) if (att + defe) > 0 else 0.5
		mom_val = max(-1.5, min(1.5, self.match.momentum.get(att_team.name, 0.0)))
		momentum_bonus = mom_val * 0.008

		time_intensity = get_minute_intensity(m)
		chance_freq = (CHANCE_PER_MIN * (0.65 + ratio * 0.70) + momentum_bonus) * time_intensity
		if att_coach and att_coach.mentality == 'attacking_overload': chance_freq *= 1.20
		if def_coach and def_coach.mentality == 'low_block': chance_freq *= 0.80

		if random.random() < chance_freq:
			shooter = None
			assister = None
			shot_type = 'box'
			base_xg = 0.14

			through_ball_prob = 0.28 if (att_coach and att_coach.philosophy in ['tiki_taka', 'direct_counter']) else 0.22
			playmakers = [p for p in att_team.xi if p.position in ['AMF', 'MID'] and (p.vision >= 80 or p.has_playstyle('incisive pass') or p.has_playstyle('tiki taka'))]
			forwards = [p for p in att_team.xi if p.position in ['ATT', 'AMF']]

			if playmakers and forwards and random.random() < through_ball_prob:
				pm = max(playmakers, key=lambda p: p.vision + (12 if p.has_playstyle('incisive pass') else 0))
				striker_cands = [p for p in forwards if p != pm]
				if striker_cands:
					shooter = max(striker_cands, key=lambda p: p.positioning * 0.5 + p.pace * 0.3 + p.finishing * 0.2)
					assister = pm
					shot_type = 'big_chance'
					base_xg = 0.36
					pm_name = getattr(pm, 'short_name', '') or pm.name
					sh_name = getattr(shooter, 'short_name', '') or shooter.name
					self.match.logger("What a ball that is! {} splits the defense open with an exquisite through pass to put {} clean through on goal!".format(pm_name, sh_name))

			if shooter is None:
				wing_prob = 0.30 if (att_coach and att_coach.philosophy in ['direct_counter', 'high_press']) else 0.25
				wingers = [p for p in att_team.xi if (p.primary_position in ['LW', 'RW', 'LM', 'RM'] or (p.pace >= 85 and p.dribbling >= 82))]
				if wingers and random.random() < wing_prob:
					winger = random.choice(wingers)
					fullbacks = [p for p in def_team.xi if p.primary_position in ['LB', 'RB', 'LWB', 'RWB'] or p.position == 'DEF']
					fb = min(fullbacks, key=lambda p: p.pace) if fullbacks else None
					w_score = winger.pace * 0.5 + winger.dribbling * 0.5 + (8 if (winger.has_playstyle('quick step') or winger.has_playstyle('rapid')) else 0)
					fb_score = (fb.pace * 0.45 + fb.standing_tackle * 0.55) if fb else 70.0

					if w_score > fb_score * random.uniform(0.85, 1.15):
						box_targets = [p for p in att_team.xi if p != winger and p.position in ['ATT', 'AMF']]
						if box_targets:
							w_name = getattr(winger, 'short_name', '') or winger.name
							if random.random() < 0.60:
								shooter = random.choice(box_targets)
								assister = winger
								shot_type = 'cutback'
								base_xg = 0.22
								sh_name = getattr(shooter, 'short_name', '') or shooter.name
								self.match.logger("Electric Wing Play! {} beats {pos} marker to the byline and cuts it back across the six-yard box for {}!".format(
									w_name, sh_name, pos='her' if getattr(winger, 'gender', 'Male') == 'Female' else 'his'
								))
							else:
								shooter = max(box_targets, key=lambda p: p.heading * 0.6 + p.jumping * 0.4)
								assister = winger
								shot_type = 'header'
								base_xg = 0.09
								sh_name = getattr(shooter, 'short_name', '') or shooter.name
								self.match.logger("Gorgeous cross! {} swings an inviting delivery towards the back post where {} attacks the header!".format(w_name, sh_name))

			if shooter is None:
				shooter = self.pick_shooter(att_team.xi)
				long_bias = 0.12 if (att_coach and att_coach.philosophy == 'tiki_taka') else 0.22
				if (shooter.long_shots >= 80 or shooter.has_playstyle('power shot')) and random.random() < long_bias:
					shot_type = 'long'
					base_xg = 0.035
				elif (shooter.finishing >= 80 or shooter.curve >= 80 or shooter.has_playstyle('finesse shot')) and random.random() < 0.35:
					shot_type = 'finesse'
					base_xg = 0.10
				elif (shooter.heading >= 76 or shooter.has_playstyle('aerial fortress')) and random.random() < 0.24:
					shot_type = 'header'
					base_xg = 0.08
				else:
					shot_type = 'box'
					base_xg = 0.14
				assister = self.pick_assister(att_team.xi, shooter, shot_type)

			gk = next((p for p in def_team.xi if p.position == 'GK'), None)
			gk_div = getattr(gk, 'gk_diving', gk.overall if gk else 70.0)
			gk_han = getattr(gk, 'gk_handling', gk.overall if gk else 70.0)
			gk_kic = getattr(gk, 'gk_kicking', 70.0)
			gk_ref = getattr(gk, 'gk_reflexes', getattr(gk, 'gk_reactions', gk.overall if gk else 70.0))
			gk_spd = getattr(gk, 'gk_speed', 50.0)
			gk_pos = getattr(gk, 'gk_positioning', gk.overall if gk else 70.0)

			if shot_type == 'big_chance':
				s_score = shooter.finishing * 0.50 + shooter.composure * 0.35 + shooter.positioning * 0.15
				if shooter.has_playstyle('finesse shot') or shooter.has_playstyle('low driven'): s_score += 6
				gk_score = gk_ref * 0.40 + gk_spd * 0.35 + gk_pos * 0.25
				if gk and gk.has_playstyle('1v1 close down'): gk_score += 8
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.22, min(0.44, goal_prob))
			elif shot_type == 'cutback':
				s_score = shooter.finishing * 0.55 + shooter.positioning * 0.30 + shooter.composure * 0.15
				gk_score = gk_ref * 0.50 + gk_pos * 0.35 + gk_div * 0.15
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.12, min(0.28, goal_prob))
			elif shot_type == 'finesse':
				s_score = shooter.finishing * 0.45 + shooter.curve * 0.35 + shooter.composure * 0.20
				if shooter.has_playstyle('finesse shot'): s_score += 8
				gk_score = gk_div * 0.55 + gk_pos * 0.35 + gk_ref * 0.10
				if gk and gk.has_playstyle('far reach'): gk_score += 8
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.05, min(0.15, goal_prob))
			elif shot_type == 'header':
				s_score = shooter.heading * 0.55 + shooter.jumping * 0.25 + shooter.strength * 0.20
				if shooter.has_playstyle('precision header') or shooter.has_playstyle('aerial fortress'): s_score += 8
				gk_score = gk_pos * 0.50 + gk_han * 0.30 + gk_div * 0.20
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.04, min(0.14, goal_prob))
			elif shot_type == 'long':
				s_score = shooter.long_shots * 0.55 + shooter.shot_power * 0.35 + shooter.composure * 0.10
				if shooter.has_playstyle('power shot'): s_score += 8
				gk_score = gk_div * 0.60 + gk_pos * 0.40
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.015, min(0.055, goal_prob))
			else:
				s_score = shooter.finishing * 0.50 + shooter.shot_power * 0.25 + shooter.composure * 0.25
				if shooter.has_playstyle('first touch') or shooter.has_playstyle('low driven'): s_score += 6
				gk_score = gk_ref * 0.45 + gk_pos * 0.35 + gk_div * 0.20
				goal_prob = base_xg * (s_score / max(50.0, gk_score))
				goal_prob = max(0.08, min(0.20, goal_prob))

			if random.random() > (shooter.weak_foot / 5.0) * 0.8:
				goal_prob *= 0.92
			goal_prob *= getattr(shooter, 'fitness', 1.0)
			shot_xg = round(goal_prob, 2)

			block_prob = 0.08 if shot_type == 'big_chance' else (0.22 if shot_type == 'cutback' else 0.28)
			if def_coach and def_coach.philosophy == 'low_block': block_prob += 0.12
			def_cbs_cdms = [p for p in def_team.xi if p.position in ['DEF', 'DMF']]
			if def_cbs_cdms and random.random() < block_prob:
				defender = max(def_cbs_cdms, key=lambda p: p.standing_tackle + (15 if p.has_playstyle('block') else 0) + 10 * random.random())
				if len(defender.inns) > 0:
					defender.inns[-1].tackles += 1
				d_disp = getattr(defender, 'short_name', '') or defender.name
				if shooter and len(shooter.inns) > 0:
					shooter.inns[-1].shots += 1
					shooter.inns[-1].xg += shot_xg
				if att_team == self.match.home:
					self.match.home_shots += 1
					self.match.home_xg += shot_xg
				else:
					self.match.away_shots += 1
					self.match.away_xg += shot_xg

				self.match.logger("Heroic Defending! {} puts {pos} body on the line with an extraordinary last-ditch block!".format(
					d_disp, pos='her' if getattr(defender, 'gender', 'Male') == 'Female' else 'his'
				))
				if random.random() < 0.28:
					self.corner_event(att_team, def_team)
				return

			if shooter and len(shooter.inns) > 0:
				shooter.inns[-1].shots += 1
				shooter.inns[-1].xg += shot_xg
			if att_team == self.match.home:
				self.match.home_shots += 1
				self.match.home_xg += shot_xg
			else:
				self.match.away_shots += 1
				self.match.away_xg += shot_xg

			if assister and len(assister.inns) > 0:
				assister.inns[-1].key_passes += 1
				assister.inns[-1].xa += round(shot_xg * 0.7, 2)

			if random.random() < goal_prob:
				if shooter and len(shooter.inns) > 0: shooter.inns[-1].shots_on_target += 1
				if att_team == self.match.home: self.match.home_shots_target += 1
				else: self.match.away_shots_target += 1

				self.log_goal(shooter, assister, att_team, shot_type)
				self.match.momentum[att_team.name] = min(1.2, self.match.momentum.get(att_team.name, 0.0) + 0.45)
				self.match.momentum[def_team.name] = max(-1.2, self.match.momentum.get(def_team.name, 0.0) - 0.25)
			else:
				if random.random() < 0.65:
					if shooter and len(shooter.inns) > 0: shooter.inns[-1].shots_on_target += 1
					if att_team == self.match.home: self.match.home_shots_target += 1
					else: self.match.away_shots_target += 1
					if gk and len(gk.inns) > 0: gk.inns[-1].saves += 1
					self.match.momentum[att_team.name] = max(-1.5, self.match.momentum.get(att_team.name, 0.0) - 0.2)
					gk_disp = getattr(gk, 'short_name', '') or (gk.name if gk else 'the keeper')
					if gk_han >= 82 and random.random() < ((gk_han / 100.0) * 0.70) and shot_type != 'long':
						self.match.logger("Safe Hands: {} smothers the effort cleanly, commanding {pos} penalty area.".format(
							gk_disp, pos='her' if (gk and getattr(gk, 'gender', 'Male') == 'Female') else 'his'
						))
					else:
						if random.random() < 0.35:
							self.match.logger("Sensational Reflexes! {} makes a stunning stop and tips it around the post for a corner.".format(gk_disp))
							self.corner_event(att_team, def_team)
						else:
							self.match.logger("Terrific Stop! {} reacts rapidly to parry the strike away from danger.".format(gk_disp))
				else:
					self.match.logger(self._near_miss_commentary(att_team, shooter, shot_type))
					if random.random() < 0.12:
						self.corner_event(att_team, def_team)

	def pick_shooter(self, xi):
		outfield = [p for p in xi if getattr(p, 'position', '') != 'GK']
		if not outfield:
			return xi[0] if xi else None
		weights = []
		for p in outfield:
			fit = getattr(p, 'fitness', 1.0)
			pos = getattr(p, 'position', 'MID')
			if pos == 'ATT':
				w = 55 + getattr(p, 'positioning', 70) * 0.45 + getattr(p, 'finishing', 70) * 0.35
			elif pos == 'AMF':
				w = 35 + getattr(p, 'positioning', 70) * 0.35 + getattr(p, 'long_shots', 70) * 0.30
			elif pos == 'MID':
				w = 16 + getattr(p, 'long_shots', 70) * 0.30 + getattr(p, 'positioning', 70) * 0.20
			elif pos == 'DMF':
				w = 6 + getattr(p, 'shot_power', 70) * 0.20
			elif pos == 'DEF':
				w = 4 + getattr(p, 'heading', 70) * 0.20
			else:
				w = 0.5
			weights.append(max(0.1, w * fit))
		return random.choices(outfield, weights=weights, k=1)[0]

	def pick_assister(self, xi, scorer, shot_type='box'):
		pool = [p for p in xi if p != scorer and p.position != 'GK']
		if not pool:
			return None
		if random.random() < 0.22:
			return None

		weights = []
		for p in pool:
			fit = getattr(p, 'fitness', 1.0)
			if shot_type == 'header':
				w = p.crossing * 0.65 + p.vision * 0.35
				if p.has_playstyle('whipped pass'): w += 20
			else:
				if p.position in ['AMF', 'MID']:
					w = 40 + p.vision * 0.45 + p.short_passing * 0.35
					if p.has_playstyle('incisive pass'): w += 15
				elif p.position == 'ATT':
					w = 28 + p.vision * 0.35 + p.short_passing * 0.30
				elif p.position == 'DMF':
					w = 16 + p.long_passing * 0.40 + p.vision * 0.30
				elif p.position == 'DEF':
					w = 10 + p.crossing * 0.40 + p.long_passing * 0.30
				else:
					w = 1.0
			weights.append(max(0.1, w * fit))
		return random.choices(pool, weights=weights, k=1)[0]

	def log_goal(self, scorer, assister, team, shot_type='box'):
		if team == self.match.home:
			self.match.home_score += 1
		else:
			self.match.away_score += 1

		if scorer and len(scorer.inns) > 0:
			scorer.inns[-1].goals += 1
			scorer.match_goals += 1
		if assister and len(assister.inns) > 0:
			assister.inns[-1].assists += 1
			assister.match_assists += 1

		self.goals.append((scorer, assister, team, self.match.minute))

		if shot_type == 'big_chance':
			verbs = [
				"raced clean through on goal and slotted ice-cool past the keeper",
				"stayed composed 1-on-1, rounded the advancing goalkeeper and rolled it into the empty net",
				"latched on to the through ball and clipped a delicate finish inside the near post",
				"drilled an emphatic low drive into the bottom corner when through on goal",
				"showed world-class composure to chip the ball over the onrushing keeper"
			]
		elif shot_type == 'cutback':
			verbs = [
				"arrived on cue in the six-yard box to sidefoot home the cutback",
				"swept the low delivery first-time into the corner of the net",
				"timed the run to perfection to turn the low cross home from close range",
				"tapped into the roof of the net from point-blank range"
			]
		elif shot_type == 'long':
			verbs = [
				"unleashed an absolute thunderbolt from 30 yards",
				"smashed a ferocious long-range strike into the top corner",
				"hammered an unstoppable rocket past the helpless keeper",
				"drilled a powerful drive into the bottom corner from distance"
			]
		elif shot_type == 'finesse':
			verbs = [
				"curled a magnificent finesse shot inside the far post",
				"bent a delightful effort into the top right corner",
				"showed supreme technique to curl home from the edge of the area",
				"cut inside and guided a delicate finish beyond the keeper"
			]
		elif shot_type == 'header':
			verbs = [
				"rose highest in the box to power a commanding header home",
				"bulleted an unstoppable header into the net",
				"glanced a deft header inside the far upright",
				"arrived on cue to head emphatically into the corner"
			]
		elif shot_type == 'direct_freekick':
			verbs = [
				"curled a breathtaking direct free kick over the wall and into the top corner",
				"unleashed an exquisite free kick that dipped viciously under the crossbar",
				"hammered a sensational set piece through the wall past the stunned keeper",
				"bent a picture-perfect free kick inside the near post"
			]
		elif shot_type == 'penalty':
			verbs = [
				"dispatched the penalty coolly into the bottom corner sending the keeper the wrong way",
				"slotted home the spot kick with supreme confidence",
				"blasted the penalty emphatically into the top corner giving the goalkeeper no chance",
				"chipped a cheeky Panenka penalty down the middle as the keeper dived"
			]
		else:
			verbs = [
				"latched on to a through ball and slotted calmly past the keeper",
				"showed clinical composure to slide the ball into the bottom corner",
				"tapped home from close range after a rapid attacking move",
				"drove a low finish decisively under the advancing goalkeeper",
				"showcased brilliant footwork before finding the back of the net"
			]

		verb = random.choice(verbs)
		s_name = getattr(scorer, 'short_name', '') or (scorer.name if scorer else 'Unknown')
		if assister:
			a_name = getattr(assister, 'short_name', '') or assister.name
			text = "GOAL! {} {} (assist: {})".format(s_name, verb, a_name)
		else:
			text = "GOAL! {} {}".format(s_name, verb)

		self.match.logger(text)

	def _near_miss_commentary(self, att_team, shooter, shot_type='box'):
		pos_pro = 'her' if getattr(shooter, 'gender', 'Male') == 'Female' else 'his'
		s_name = getattr(shooter, 'short_name', '') or shooter.name
		if shot_type == 'big_chance':
			phrases = [
				"was denied by an astonishing point-blank spread save by the keeper",
				"rushed through 1-on-1 but dragged the shot agonizingly wide of the far post",
				"tried to round the keeper but had the ball plucked off {} toes by a brave dive".format(pos_pro),
				"chipped the advancing goalkeeper but saw the ball bounce back off the post"
			]
		elif shot_type == 'cutback':
			phrases = [
				"saw {} first-time strike brilliantly parried off the goal-line".format(pos_pro),
				"fired {} cutback finish inches over the crossbar from eight yards".format(pos_pro),
				"saw a point-blank effort blocked heroically by a sliding defender"
			]
		elif shot_type == 'long':
			phrases = [
				"saw {} venomous long-range drive crash against the crossbar".format(pos_pro),
				"unleashed a rocket that stung the keeper's palms and was tipped over",
				"whistled a fierce shot inches wide of the upright"
			]
		elif shot_type == 'header':
			phrases = [
				"saw {} towering header bounce agonizingly off the post".format(pos_pro),
				"directed a header just over the bar from a pinpoint delivery",
				"had a goal-bound header cleared off the line by an alert defender"
			]
		elif shot_type == 'finesse':
			phrases = [
				"saw {} curling effort tipped around the post by a flying save".format(pos_pro),
				"bent a curling shot inches wide of the top corner",
				"saw {} delicate chip clawed off the line by the keeper".format(pos_pro)
			]
		else:
			phrases = [
				"saw {} low drive brilliantly kept out by the goalkeeper's outstretched leg".format(pos_pro),
				"was denied by an astonishing point-blank reflex save",
				"blazed {} shot just over the crossbar from a dangerous position".format(pos_pro),
				"was thwarted by a superb last-ditch slide tackle inside the six-yard box"
			]
		phrase = random.choice(phrases)
		return "Chance! {} {}".format(s_name, phrase)

	match = ''
	half = 1
	att_team = ''
	def_team = ''
	goals = []
	minutes = 0
	active = True
	injury_time = 0
