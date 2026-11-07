import math
import random

ZONE_NAMES = {
	1: "Own Left Wing",
	2: "Own Left Half-Space",
	3: "Own Defensive Box (Left)",
	4: "Own Defensive Box (Right)",
	5: "Own Right Half-Space",
	6: "Own Right Wing",
	7: "Middle Left Wing",
	8: "Middle Left Half-Space",
	9: "Central Midfield (Left)",
	10: "Central Midfield (Right)",
	11: "Middle Right Half-Space",
	12: "Middle Right Wing",
	13: "Attacking Left Wing",
	14: "Attacking Left Half-Space",
	15: "Opponent Penalty Box (Left)",
	16: "Opponent Penalty Box (Right)",
	17: "Attacking Right Half-Space",
	18: "Attacking Right Wing"
}

def zone_to_coord(zone_id):
	z = max(1, min(18, int(zone_id))) - 1
	return (z // 6, z % 6)

def coord_to_zone(row, col):
	r = max(0, min(2, int(row)))
	c = max(0, min(5, int(col)))
	return r * 6 + c + 1

def invert_zone(zone_id):
	r, c = zone_to_coord(zone_id)
	return coord_to_zone(2 - r, 5 - c)

def zone_distance(z1, z2):
	r1, c1 = zone_to_coord(z1)
	r2, c2 = zone_to_coord(z2)
	dr = (r1 - r2) * 1.5
	dc = (c1 - c2) * 0.7
	return math.sqrt(dr * dr + dc * dc)

def get_zones_in_path(from_zone, to_zone):
	r1, c1 = zone_to_coord(from_zone)
	r2, c2 = zone_to_coord(to_zone)
	steps = max(abs(r2 - r1), abs(c2 - c1), 1)
	path = []
	for i in range(1, steps):
		frac = i / float(steps)
		mid_r = int(round(r1 + (r2 - r1) * frac))
		mid_c = int(round(c1 + (c2 - c1) * frac))
		path.append(coord_to_zone(mid_r, mid_c))
	return list(dict.fromkeys(path))

def default_position_zones(pos_str):
	pos = str(pos_str).strip().upper()
	if pos == 'GK':
		return (3, 3)
	elif pos == 'LB':
		return (1, 7)
	elif pos == 'LWB':
		return (1, 7)
	elif pos == 'RB':
		return (6, 12)
	elif pos == 'RWB':
		return (6, 12)
	elif pos in ['CB', 'DEF']:
		return (3, 4)
	elif pos in ['CDM', 'DMF']:
		return (9, 10)
	elif pos == 'LM':
		return (7, 13)
	elif pos == 'RM':
		return (12, 18)
	elif pos in ['CM', 'MID']:
		return (9, 10)
	elif pos in ['CAM', 'AMF']:
		return (10, 15)
	elif pos == 'LW':
		return (8, 14)
	elif pos == 'RW':
		return (11, 17)
	elif pos in ['ST', 'CF', 'ATT']:
		return (10, 16)
	return (9, 10)

class PitchGrid:
	def __init__(self):
		self.player_zones = {}
		self.zone_players = {z: [] for z in range(1, 19)}

	def clear(self):
		self.player_zones.clear()
		self.zone_players = {z: [] for z in range(1, 19)}

	def update_team_positions(self, team, is_home, in_possession, mentality='balanced', def_line='mid_block'):
		cb_idx = 0
		st_idx = 0
		cm_idx = 0

		for p in team.xi:
			slot = getattr(p, 'assigned_slot', None) or getattr(p, 'primary_position', None) or getattr(p, 'position', 'MID')
			slot_upper = str(slot).strip().upper()

			def_z, att_z = default_position_zones(slot_upper)
			base_z = att_z if in_possession else def_z

			if not is_home:
				base_z = invert_zone(base_z)

			r, c = zone_to_coord(base_z)

			if slot_upper == 'CB':
				if cb_idx == 0:
					c = 1
				elif cb_idx == 1:
					c = 3
				else:
					c = 4
				cb_idx += 1
			elif slot_upper in ['ST', 'CF']:
				if st_idx == 0:
					c = 2
				else:
					c = 4
				st_idx += 1
			elif slot_upper in ['CM', 'CDM']:
				if cm_idx == 0:
					c = 2
				elif cm_idx == 1:
					c = 3
				else:
					c = 4
				cm_idx += 1

			if def_line == 'high' and slot_upper in ['CB', 'LB', 'RB', 'LWB', 'RWB', 'CDM']:
				if is_home:
					r = min(1, r + 1)
				else:
					r = max(1, r - 1)
			elif def_line == 'deep' and slot_upper in ['CB', 'LB', 'RB', 'LWB', 'RWB', 'CDM']:
				if is_home:
					r = 0
				else:
					r = 2

			if mentality == 'park_the_bus':
				if is_home:
					r = max(0, r - 1)
				else:
					r = min(2, r + 1)
			elif mentality in ['attacking_overload', 'desperation_hail_mary']:
				if is_home:
					if slot_upper in ['CB', 'DEF'] and mentality == 'desperation_hail_mary':
						r = 2
					else:
						r = min(2, r + 1)
				else:
					if slot_upper in ['CB', 'DEF'] and mentality == 'desperation_hail_mary':
						r = 0
					else:
						r = max(0, r - 1)
			elif mentality == 'controlled_counter':
				if not in_possession:
					if is_home:
						r = max(0, min(1, r))
					else:
						r = min(2, max(1, r))

			pace = getattr(p, 'pace', 70.0)
			if random.random() < (pace / 250.0):
				shift_c = random.choice([-1, 0, 1])
				c = max(0, min(5, c + shift_c))

			final_zone = coord_to_zone(r, c)
			self.player_zones[p] = final_zone
			self.zone_players[final_zone].append(p)

	def get_player_zone(self, p):
		return self.player_zones.get(p, 9)

	def get_defenders_in_lane(self, from_zone, to_zone, def_team):
		lane_zones = get_zones_in_path(from_zone, to_zone) + [to_zone]
		def_set = set(def_team.xi)
		found = []
		for z in lane_zones:
			for p in self.zone_players.get(z, []):
				if p in def_set:
					found.append((p, z))
		return found

	def calculate_pass_interception_risk(self, passer, receiver, def_team, is_home):
		p_from = self.get_player_zone(passer)
		p_to = self.get_player_zone(receiver)
		dist = zone_distance(p_from, p_to)

		lane_defs = self.get_defenders_in_lane(p_from, p_to, def_team)
		def_power = 0.0
		for d, z in lane_defs:
			d_fit = getattr(d, 'fitness', 1.0)
			def_awareness = getattr(d, 'def_awareness', 70.0)
			interceptions = getattr(d, 'interceptions', 70.0)
			standing_tackle = getattr(d, 'standing_tackle', 70.0)
			pace = getattr(d, 'pace', 70.0)
			val = (def_awareness * 0.35 + interceptions * 0.35 + standing_tackle * 0.15 + pace * 0.15) * d_fit
			if hasattr(d, 'has_playstyle'):
				if d.has_playstyle('intercept'): val += 12.0
				if d.has_playstyle('anticipate'): val += 8.0
				if d.has_playstyle('block'): val += 6.0
			def_power += val

		p_fit = getattr(passer, 'fitness', 1.0)
		short_pass = getattr(passer, 'short_passing', 70.0)
		long_pass = getattr(passer, 'long_passing', 70.0)
		vision = getattr(passer, 'vision', 70.0)
		composure = getattr(passer, 'composure', 70.0)

		pass_skill = (short_pass * 0.40 + long_pass * 0.30 + vision * 0.20 + composure * 0.10) * p_fit
		if hasattr(passer, 'has_playstyle'):
			if passer.has_playstyle('tiki taka'): pass_skill += 8.0
			if passer.has_playstyle('incisive pass'): pass_skill += 10.0
			if passer.has_playstyle('long ball pass') and dist >= 1.5: pass_skill += 12.0

		dist_penalty = max(0.0, (dist - 1.0) * 22.0)
		denom = pass_skill * 1.5 + 40.0
		numer = def_power * 0.38 + dist_penalty
		risk = numer / (numer + denom)
		return max(0.04, min(0.75, risk))
