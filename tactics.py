import json
import os
import random

FORMATIONS = {
	'4-3-3': ['GK', 'LB', 'CB', 'CB', 'RB', 'CDM', 'CM', 'CM', 'LW', 'ST', 'RW'],
	'4-2-3-1': ['GK', 'LB', 'CB', 'CB', 'RB', 'CDM', 'CDM', 'CAM', 'LM', 'RM', 'ST'],
	'4-4-2': ['GK', 'LB', 'CB', 'CB', 'RB', 'LM', 'CM', 'CM', 'RM', 'ST', 'ST'],
	'3-5-2': ['GK', 'CB', 'CB', 'CB', 'LWB', 'RWB', 'CDM', 'CM', 'CAM', 'ST', 'ST'],
	'3-4-3': ['GK', 'CB', 'CB', 'CB', 'LWB', 'RWB', 'CM', 'CM', 'LW', 'ST', 'RW'],
	'5-3-2': ['GK', 'CB', 'CB', 'CB', 'LWB', 'RWB', 'CM', 'CM', 'CM', 'ST', 'ST'],
	'5-4-1': ['GK', 'CB', 'CB', 'CB', 'LWB', 'RWB', 'CM', 'CM', 'LM', 'RM', 'ST'],
	'4-1-2-1-2': ['GK', 'LB', 'CB', 'CB', 'RB', 'CDM', 'CM', 'CM', 'CAM', 'ST', 'ST']
}

_CACHED_TACTICS = None

def _load_all_tactics():
	global _CACHED_TACTICS
	if _CACHED_TACTICS is not None:
		return _CACHED_TACTICS

	base_dir = os.path.dirname(os.path.abspath(__file__))
	path = os.path.join(base_dir, 'data', 'tactics.json')
	if not os.path.exists(path):
		path = 'data/tactics.json'

	if os.path.exists(path):
		try:
			with open(path, 'r', encoding='utf-8') as f:
				_CACHED_TACTICS = json.load(f)
				return _CACHED_TACTICS
		except Exception:
			pass

	_CACHED_TACTICS = {}
	return _CACHED_TACTICS

def load_club_tactics(club_name):
	all_t = _load_all_tactics()
	name = str(club_name).strip()
	if name in all_t:
		return dict(all_t[name])

	for k, v in all_t.items():
		if k.lower() == name.lower():
			return dict(v)

	for k, v in all_t.items():
		if k.lower() in name.lower() or name.lower() in k.lower():
			return dict(v)

	return {
		'formation': '4-3-3',
		'defensive_line': 'mid_block',
		'pressing_trigger': 'press_on_touch',
		'build_up_style': 'short_patient',
		'set_piece_focus': 'balanced',
		'offside_trap': 'balanced',
		'games_together': 28,
		'win_streak': 1
	}

def calculate_player_familiarity(p, target_slot):
	target = target_slot.upper()
	p_prim = getattr(p, 'primary_position', '').upper()
	p_gen = getattr(p, 'position', '').upper()

	if target == 'GK':
		return 1.0 if (p_prim == 'GK' or p_gen == 'GK') else 0.15

	if p_prim == 'GK' or p_gen == 'GK':
		return 0.15

	if p_prim == target:
		return 1.0

	compat_map = {
		'CB': {'CDM': 0.88, 'LB': 0.75, 'RB': 0.75, 'LWB': 0.70, 'RWB': 0.70},
		'LB': {'LWB': 0.92, 'LM': 0.82, 'CB': 0.75, 'RB': 0.75},
		'RB': {'RWB': 0.92, 'RM': 0.82, 'CB': 0.75, 'LB': 0.75},
		'LWB': {'LB': 0.92, 'LM': 0.88, 'LW': 0.78, 'RWB': 0.75},
		'RWB': {'RB': 0.92, 'RM': 0.88, 'RW': 0.78, 'LWB': 0.75},
		'CDM': {'CM': 0.88, 'CB': 0.85, 'CAM': 0.72},
		'CM': {'CDM': 0.88, 'CAM': 0.88, 'LM': 0.78, 'RM': 0.78},
		'CAM': {'CM': 0.88, 'CF': 0.85, 'ST': 0.80, 'LW': 0.78, 'RW': 0.78, 'LM': 0.75, 'RM': 0.75},
		'LM': {'LW': 0.90, 'LWB': 0.85, 'RM': 0.80, 'CM': 0.75, 'CAM': 0.75},
		'RM': {'RW': 0.90, 'RWB': 0.85, 'LM': 0.80, 'CM': 0.75, 'CAM': 0.75},
		'LW': {'LM': 0.88, 'RW': 0.85, 'ST': 0.80, 'CF': 0.80, 'LWB': 0.72},
		'RW': {'RM': 0.88, 'LW': 0.85, 'ST': 0.80, 'CF': 0.80, 'RWB': 0.72},
		'ST': {'CF': 0.95, 'LW': 0.80, 'RW': 0.80, 'CAM': 0.78}
	}

	slot_compat = compat_map.get(target, {})
	if p_prim in slot_compat:
		return slot_compat[p_prim]

	if target in ['CB', 'LB', 'RB', 'LWB', 'RWB'] and p_gen == 'DEF':
		return 0.74
	if target in ['CDM', 'CM', 'CAM', 'LM', 'RM'] and (p_gen in ['MID', 'DMF', 'AMF']):
		return 0.74
	if target in ['ST', 'LW', 'RW'] and (p_gen in ['ATT', 'AMF']):
		return 0.74

	return 0.58

def calculate_team_fluidity(team_obj, win_streak=2, games_together=30, subs_disruption=0.0):
	xi = getattr(team_obj, 'xi', None) or getattr(team_obj, 'players', [])
	if not xi:
		return 1.0

	fam_scores = [getattr(p, 'position_familiarity', 1.0) for p in xi]
	avg_fam = sum(fam_scores) / float(len(fam_scores))

	games_bonus = min(0.08, max(-0.04, (games_together - 20) * 0.002))
	streak_bonus = min(0.06, max(-0.04, win_streak * 0.015))
	penalty = subs_disruption

	score = avg_fam + games_bonus + streak_bonus - penalty
	return max(0.65, min(1.25, score))

def get_formation_matchup(home_form, away_form):
	h = str(home_form).strip()
	a = str(away_form).strip()
	h_mod = 1.0
	a_mod = 1.0

	cm_count = {
		'4-3-3': 3,
		'4-2-3-1': 3,
		'4-4-2': 2,
		'3-5-2': 4,
		'3-4-3': 2,
		'5-3-2': 3,
		'5-4-1': 2,
		'4-1-2-1-2': 4
	}

	h_cm = cm_count.get(h, 3)
	a_cm = cm_count.get(a, 3)

	if h_cm > a_cm:
		diff = h_cm - a_cm
		h_mod += 0.03 * diff
		a_mod -= 0.015 * diff
	elif a_cm > h_cm:
		diff = a_cm - h_cm
		a_mod += 0.03 * diff
		h_mod -= 0.015 * diff

	if h == '4-2-3-1' and a in ['4-1-2-1-2', '4-3-3']:
		h_mod += 0.04
		a_mod -= 0.02
	elif a == '4-2-3-1' and h in ['4-1-2-1-2', '4-3-3']:
		a_mod += 0.04
		h_mod -= 0.02

	if h in ['3-5-2', '3-4-3'] and a in ['5-3-2', '5-4-1']:
		h_mod += 0.05
	elif a in ['3-5-2', '3-4-3'] and h in ['5-3-2', '5-4-1']:
		a_mod += 0.05

	if h in ['4-3-3', '3-4-3'] and a in ['3-5-2', '5-3-2']:
		h_mod += 0.04
	elif a in ['4-3-3', '3-4-3'] and h in ['3-5-2', '5-3-2']:
		a_mod += 0.04

	if (h == '5-4-1' and a in ['4-3-3', '4-2-3-1']):
		h_mod += 0.04
		a_mod -= 0.04
	elif (a == '5-4-1' and h in ['4-3-3', '4-2-3-1']):
		a_mod += 0.04
		h_mod -= 0.04

	return round(h_mod, 3), round(a_mod, 3)

class ManagerPOV:
	def __init__(self, club_name, formation=None, defensive_line=None, pressing_trigger=None,
				 build_up_style=None, set_piece_focus=None, offside_trap=None,
				 games_together=None, win_streak=None):
		cfg = load_club_tactics(club_name)

		self.club_name = club_name
		self.formation = formation or cfg.get('formation', '4-3-3')
		self.defensive_line = defensive_line or cfg.get('defensive_line', 'mid_block')
		self.pressing_trigger = pressing_trigger or cfg.get('pressing_trigger', 'press_on_touch')
		self.build_up_style = build_up_style or cfg.get('build_up_style', 'short_patient')
		self.set_piece_focus = set_piece_focus or cfg.get('set_piece_focus', 'balanced')
		self.offside_trap = offside_trap or cfg.get('offside_trap', 'balanced')
		self.games_together = games_together if games_together is not None else cfg.get('games_together', 28)
		self.win_streak = win_streak if win_streak is not None else cfg.get('win_streak', 1)
		self.subs_disruption = 0.0
		self.fluidity = 1.0

	def update_fluidity(self, team_obj):
		self.fluidity = calculate_team_fluidity(
			team_obj,
			win_streak=self.win_streak,
			games_together=self.games_together,
			subs_disruption=self.subs_disruption
		)
		return self.fluidity

	def record_substitution(self, team_obj):
		self.subs_disruption += 0.025
		self.update_fluidity(team_obj)

	def decay_disruption(self, team_obj):
		if self.subs_disruption > 0.0:
			self.subs_disruption = max(0.0, self.subs_disruption - 0.005)
			self.update_fluidity(team_obj)

	def get_pressing_modifier(self):
		base = 1.0
		if self.pressing_trigger == 'counterpress':
			base *= 1.22
		elif self.pressing_trigger == 'press_on_touch':
			base *= 1.08
		elif self.pressing_trigger == 'regroup':
			base *= 0.85

		if self.defensive_line == 'high':
			base *= 1.15
		elif self.defensive_line == 'deep':
			base *= 0.88

		return base * (self.fluidity ** 0.5)

	def get_build_up_modifier(self):
		base = 1.0
		if self.build_up_style == 'short_patient':
			base *= 1.12
		elif self.build_up_style == 'direct_vertical':
			base *= 0.92
		elif self.build_up_style == 'wing_focus':
			base *= 1.04
		return base * self.fluidity

	def get_offside_trap_risk(self):
		base_chance = 0.015
		if self.offside_trap == 'aggressive':
			base_chance = 0.038
		elif self.offside_trap == 'conservative':
			base_chance = 0.004

		if self.defensive_line == 'high':
			base_chance *= 1.35
		elif self.defensive_line == 'deep':
			base_chance *= 0.50

		return base_chance * (self.fluidity ** 0.8)

	def get_set_piece_modifier(self):
		if self.set_piece_focus == 'aerial_overload':
			return 1.25
		elif self.set_piece_focus == 'short_routine':
			return 0.90
		return 1.0

