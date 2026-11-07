import random
import math
from grid import PitchGrid, zone_to_coord, coord_to_zone, invert_zone, zone_distance, get_zones_in_path

class PossessionState:
	def __init__(self, team, phase='build_up', zone=3):
		self.team = team
		self.phase = phase
		self.zone = zone
		self.carrier = None
		self.chain_length = 0

class PossessionEngine:
	def __init__(self, match, grid, home_manager, away_manager):
		self.match = match
		self.grid = grid
		self.home_mgr = home_manager
		self.away_mgr = away_manager
		self.state = PossessionState(match.kickoff_team, 'build_up', 3 if match.kickoff_team == match.home else 16)
		self.transition_danger = False

	def reset_kickoff(self, restart_team):
		is_home = (restart_team == self.match.home)
		init_zone = 9 if is_home else 10
		self.state = PossessionState(restart_team, 'build_up', init_zone)
		self.transition_danger = False

	def _get_manager(self, team):
		return self.home_mgr if team == self.match.home else self.away_mgr

	def _get_opp_manager(self, team):
		return self.away_mgr if team == self.match.home else self.home_mgr

	def _get_elo_multiplier(self, is_home):
		h_elo = getattr(self.match, 'home_elo', 1750)
		a_elo = getattr(self.match, 'away_elo', 1750)
		diff = (h_elo + 10) - a_elo
		raw = 1.0 + (diff / 380.0) * 0.22 if is_home else 1.0 - (diff / 380.0) * 0.22
		return max(0.74, min(1.32, raw))

	def _decay_fitness(self, minute):
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
				if hasattr(p, 'has_playstyle') and p.has_playstyle('relentless'):
					decay *= 0.70
				p.fitness = max(0.68, getattr(p, 'fitness', 1.0) - decay)

	def simulate_minute(self, period_obj, minute):
		self._decay_fitness(minute)

		h_diff = self.match.home_score - self.match.away_score
		a_diff = -h_diff
		self.home_mgr.evaluate_mentality(minute, h_diff, len(self.match.home.xi), len(self.match.away.xi))
		self.away_mgr.evaluate_mentality(minute, a_diff, len(self.match.away.xi), len(self.match.home.xi))

		if hasattr(self.match, 'home_coach') and self.match.home_coach:
			self.match.home_coach.evaluate(minute, h_diff)
		if hasattr(self.match, 'away_coach') and self.match.away_coach:
			self.match.away_coach.evaluate(minute, a_diff)

		ticks = random.randint(2, 4)
		for _ in range(ticks):
			if not period_obj.active:
				break
			self._run_micro_tick(period_obj, minute)

	def _run_micro_tick(self, period_obj, minute):
		ctrl_team = self.state.team
		opp_team = self.match.away if ctrl_team == self.match.home else self.match.home
		is_home = (ctrl_team == self.match.home)

		ctrl_mgr = self._get_manager(ctrl_team)
		opp_mgr = self._get_opp_manager(ctrl_team)

		self.grid.clear()
		self.grid.update_team_positions(ctrl_team, is_home, True, ctrl_mgr.mentality, ctrl_mgr.get_backline_depth())
		self.grid.update_team_positions(opp_team, not is_home, False, opp_mgr.mentality, opp_mgr.get_backline_depth())

		if is_home:
			self.match.home_poss_ticks += 1
		else:
			self.match.away_poss_ticks += 1

		if self.state.phase == 'build_up':
			self._phase_build_up(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute)
		elif self.state.phase == 'progression':
			self._phase_progression(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute)
		elif self.state.phase == 'final_third':
			self._phase_final_third(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute)
		elif self.state.phase == 'transition':
			self._phase_transition(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute)
		else:
			self.state.phase = 'build_up'

	def _pick_carrier(self, team, candidate_positions):
		xi = getattr(team, 'xi', None) or getattr(team, 'squad', []) or getattr(team, 'players', [])
		pool = [p for p in xi if getattr(p, 'assigned_slot', getattr(p, 'position', 'MID')) in candidate_positions]
		if not pool:
			pool = [p for p in xi if getattr(p, 'position', 'MID') in candidate_positions]
		if not pool:
			pool = [p for p in xi if getattr(p, 'position', '') != 'GK'] or xi
		return random.choice(pool) if pool else None

	def _pick_receiver(self, team, exclude_player, target_positions):
		xi = getattr(team, 'xi', None) or getattr(team, 'squad', []) or getattr(team, 'players', [])
		pool = [p for p in xi if p != exclude_player and getattr(p, 'assigned_slot', getattr(p, 'position', 'MID')) in target_positions]
		if not pool:
			pool = [p for p in xi if p != exclude_player and getattr(p, 'position', 'MID') in target_positions]
		if not pool:
			pool = [p for p in xi if p != exclude_player] or xi
		return random.choice(pool) if pool else None

	def _record_passes(self, passer, receiver, attempted, completed, is_home):
		if is_home:
			self.match.home_passes_att += attempted
			self.match.home_passes_comp += completed
		else:
			self.match.away_passes_att += attempted
			self.match.away_passes_comp += completed

		if passer and len(passer.inns) > 0:
			passer.inns[-1].passes_attempted += attempted
			passer.inns[-1].passes_completed += completed
		if receiver and completed > 0 and len(receiver.inns) > 0:
			pass_share = max(0, completed - 1)
			receiver.inns[-1].passes_attempted += pass_share
			receiver.inns[-1].passes_completed += pass_share

	def _check_foul(self, period_obj, fouling_team, victim_team, minute, in_box=False):
		f_xi = getattr(fouling_team, 'xi', []) or getattr(fouling_team, 'players', [])
		v_xi = getattr(victim_team, 'xi', []) or getattr(victim_team, 'players', [])
		fouler_pool = [p for p in f_xi if getattr(p, 'position', '') != 'GK'] or f_xi
		victim_pool = [p for p in v_xi if getattr(p, 'position', '') != 'GK'] or v_xi
		if not fouler_pool or not victim_pool:
			return False

		f_weights = []
		for fp in fouler_pool:
			w = getattr(fp, 'aggression', 70.0) * 0.5 + getattr(fp, 'standing_tackle', 70.0) * 0.3
			if getattr(fp, 'position', '') in ['DEF', 'DMF', 'CB', 'LB', 'RB']:
				w += 20.0
			if len(fp.inns) > 0 and fp.inns[-1].yellow_cards >= 1:
				w *= 0.35
			f_weights.append(max(1.0, w))
		fouler = random.choices(fouler_pool, weights=f_weights, k=1)[0]
		victim = random.choice(victim_pool)

		if fouling_team == self.match.home:
			self.match.home_fouls += 1
		else:
			self.match.away_fouls += 1
		if len(fouler.inns) > 0:
			fouler.inns[-1].fouls_committed += 1

		fouler_name = getattr(fouler, 'short_name', '') or fouler.name
		victim_name = getattr(victim, 'short_name', '') or victim.name

		if in_box:
			period_obj.penalty_event(victim_team, fouling_team, fouled_player=victim, fouling_player=fouler)
			self.reset_kickoff(victim_team)
			return True

		card_roll = random.random()
		has_yellow = (len(fouler.inns) > 0 and fouler.inns[-1].yellow_cards >= 1)
		yellow_thresh = 0.08 if has_yellow else 0.185

		if card_roll < yellow_thresh:
			if len(fouler.inns) > 0:
				fouler.inns[-1].yellow_cards += 1
			if fouling_team == self.match.home:
				self.match.home_yellows += 1
			else:
				self.match.away_yellows += 1

			if len(fouler.inns) > 0 and fouler.inns[-1].yellow_cards >= 2:
				fouler.inns[-1].red_cards += 1
				if fouling_team == self.match.home:
					self.match.home_reds += 1
				else:
					self.match.away_reds += 1
				fouler.inns[-1].minutes_played = minute
				fouler.inns[-1].out = True
				if fouler in fouling_team.xi:
					fouling_team.xi.remove(fouler)
				self.match.logger("He's off! A second booking for {}, and the referee brandishes red! {} are down to {} men!".format(
					fouler_name, fouling_team.name, len(fouling_team.xi)
				))
			else:
				self.match.logger("Yellow Card! Cynical challenge from {}, bringing down {} and going straight into the book.".format(
					fouler_name, victim_name
				))
		elif not has_yellow and card_roll < 0.191:
			if len(fouler.inns) > 0:
				fouler.inns[-1].red_cards += 1
				fouler.inns[-1].minutes_played = minute
				fouler.inns[-1].out = True
			if fouling_team == self.match.home:
				self.match.home_reds += 1
			else:
				self.match.away_reds += 1
			if fouler in fouling_team.xi:
				fouling_team.xi.remove(fouler)
			self.match.logger("STRAIGHT RED CARD! Reckless tackle by {} on {}! The referee sends {} off!".format(
				fouler_name, victim_name, fouler_name
			))
		else:
			self.match.logger("Foul: {} catches {} with an untidy challenge. Free-kick awarded.".format(
				fouler_name, victim_name
			))

		if random.random() < 0.18:
			is_indirect = (random.random() < 0.50)
			period_obj.freekick_event(victim_team, fouling_team, is_indirect=is_indirect)

		self.state = PossessionState(victim_team, 'progression', 9 if victim_team == self.match.home else 10)
		return True

	def _phase_build_up(self, period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute):
		passer = self._pick_carrier(ctrl_team, ['GK', 'DEF', 'CB', 'LB', 'RB', 'LWB', 'RWB', 'DMF'])
		receiver = self._pick_receiver(ctrl_team, passer, ['DEF', 'CB', 'DMF', 'MID', 'LB', 'RB', 'LWB', 'RWB', 'CM'])

		att_p = random.randint(3, 5)
		risk = self.grid.calculate_pass_interception_risk(passer, receiver, opp_team, is_home)

		h_f_mod = getattr(self.match, 'home_formation_mod', 1.0)
		a_f_mod = getattr(self.match, 'away_formation_mod', 1.0)
		ctrl_f_mod = h_f_mod if is_home else a_f_mod
		ctrl_fluidity = getattr(ctrl_team, 'fluidity', 1.0)
		elo_mult = self._get_elo_multiplier(is_home)

		risk = (risk * opp_mgr.get_press_modifier() * 0.40) / ((elo_mult ** 1.1) * ctrl_f_mod * (ctrl_fluidity ** 0.5))

		if random.random() < (0.065 * opp_mgr.get_press_modifier()):
			if self._check_foul(period_obj, opp_team, ctrl_team, minute, in_box=False):
				return

		if random.random() < risk:
			comp_p = max(0, att_p - random.randint(2, 3))
			self._record_passes(passer, receiver, att_p, comp_p, is_home)

			interceptor = self._pick_carrier(opp_team, ['ATT', 'AMF', 'MID', 'LW', 'RW', 'ST'])
			if interceptor and len(interceptor.inns) > 0:
				interceptor.inns[-1].interceptions += 1

			int_name = (getattr(interceptor, 'short_name', '') or interceptor.name) if interceptor else 'the opposition'
			p_name = (getattr(passer, 'short_name', '') or passer.name) if passer else 'the defender'

			if random.random() < 0.20:
				self.match.logger("Caught in possession! {} intercepts a careless backline pass from {} deep in dangerous territory!".format(int_name, p_name))
				self.state = PossessionState(opp_team, 'final_third', 15 if opp_team == self.match.home else 4)
				self.transition_danger = True
				self._resolve_shot_chance(period_obj, opp_team, ctrl_team, not is_home, opp_mgr, ctrl_mgr, minute, is_high_press_turnover=True)
			else:
				self.match.logger("Turnover in defense: {} steps up to cut out a pass from {}.".format(int_name, p_name))
				self.state = PossessionState(opp_team, 'progression', 9 if not is_home else 10)
		else:
			comp_p = att_p if random.random() < 0.90 else max(1, att_p - 1)
			self._record_passes(passer, receiver, att_p, comp_p, is_home)
			self.state.chain_length += comp_p
			self.state.carrier = receiver
			if random.random() < 0.50:
				self.state.phase = 'progression'
				self.state.zone = 9 if is_home else 10
			else:
				self.state.phase = 'build_up'

	def _phase_progression(self, period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute):
		passer = self._pick_carrier(ctrl_team, ['DMF', 'MID', 'AMF', 'CM', 'LM', 'RM'])
		receiver = self._pick_receiver(ctrl_team, passer, ['MID', 'AMF', 'ATT', 'LW', 'RW', 'ST', 'CF'])

		opp_mgr_pov = getattr(opp_team, 'manager_pov', None)
		if opp_mgr_pov and opp_mgr_pov.offside_trap != 'conservative':
			trap_risk = opp_mgr_pov.get_offside_trap_risk()
			if random.random() < trap_risk:
				def_cbs = [p for p in opp_team.xi if getattr(p, 'primary_position', '') == 'CB' or getattr(p, 'position', '') == 'DEF']
				avg_def_awareness = sum([p.def_awareness for p in def_cbs]) / float(len(def_cbs)) if def_cbs else 70.0
				fluidity = getattr(opp_team, 'fluidity', 1.0)
				success_prob = 0.72 * (avg_def_awareness / 75.0) * fluidity

				r_name = (getattr(receiver, 'short_name', '') or receiver.name) if receiver else 'the attacker'
				if random.random() < success_prob:
					self.match.logger("The flag goes up on the far side! The backline stepped up in unison, catching {} comfortably offside.".format(r_name))
					self.state = PossessionState(opp_team, 'build_up', 3 if not is_home else 16)
					return
				elif opp_mgr_pov.offside_trap == 'aggressive' and random.random() < 0.35:
					self.match.logger("The defensive line pushed up to spring the trap but the timing was disastrous! {} is played onside and clean through on goal!".format(r_name))
					self.state.phase = 'final_third'
					self._resolve_shot_chance(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute, creator=passer, shooter=receiver, is_1on1=True)
					return

		att_p = random.randint(3, 5)
		risk = self.grid.calculate_pass_interception_risk(passer, receiver, opp_team, is_home) * 0.70

		h_f_mod = getattr(self.match, 'home_formation_mod', 1.0)
		a_f_mod = getattr(self.match, 'away_formation_mod', 1.0)
		ctrl_f_mod = h_f_mod if is_home else a_f_mod
		ctrl_fluidity = getattr(ctrl_team, 'fluidity', 1.0)
		elo_mult = self._get_elo_multiplier(is_home)

		risk = (risk * ctrl_mgr.get_pass_risk_modifier()) / ((elo_mult ** 1.2) * ctrl_f_mod * (ctrl_fluidity ** 0.5))

		if random.random() < 0.075:
			if self._check_foul(period_obj, opp_team, ctrl_team, minute, in_box=False):
				return

		if random.random() < risk:
			comp_p = max(0, att_p - random.randint(2, 3))
			self._record_passes(passer, receiver, att_p, comp_p, is_home)

			mid_opp = self._pick_carrier(opp_team, ['DMF', 'MID', 'CB', 'DEF'])
			if mid_opp and len(mid_opp.inns) > 0:
				if random.random() < 0.55:
					mid_opp.inns[-1].tackles += 1
				else:
					mid_opp.inns[-1].interceptions += 1

			if random.random() < 0.22 and opp_mgr.mentality in ['controlled_counter', 'attacking_overload']:
				self.state = PossessionState(opp_team, 'transition', 9 if not is_home else 10)
			else:
				self.state = PossessionState(opp_team, 'progression', 9 if not is_home else 10)
		else:
			comp_p = att_p if random.random() < 0.85 else max(1, att_p - 1)
			self._record_passes(passer, receiver, att_p, comp_p, is_home)
			self.state.chain_length += comp_p
			self.state.carrier = receiver

			h_s = self.match.home_score
			a_s = self.match.away_score
			lead = (h_s - a_s) if is_home else (a_s - h_s)

			advance_prob = 0.22 * ctrl_mgr.get_pass_risk_modifier() * (elo_mult ** 0.75)
			if lead >= 2:
				advance_prob *= 0.55
			if lead >= 3:
				advance_prob *= 0.35

			if random.random() < advance_prob:
				self.state.phase = 'final_third'
				self.state.zone = 15 if is_home else 4
			else:
				self.state.phase = 'progression'

	def _phase_final_third(self, period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute):
		creator = self._pick_carrier(ctrl_team, ['AMF', 'MID', 'LW', 'RW', 'CM'])
		target = self._pick_receiver(ctrl_team, creator, ['ST', 'CF', 'ATT', 'LW', 'RW', 'AMF'])
		if not creator or not target:
			self.state = PossessionState(opp_team, 'build_up', 3 if not is_home else 16)
			return

		att_p = random.randint(2, 4)
		risk = self.grid.calculate_pass_interception_risk(creator, target, opp_team, is_home)

		h_f_mod = getattr(self.match, 'home_formation_mod', 1.0)
		a_f_mod = getattr(self.match, 'away_formation_mod', 1.0)
		ctrl_f_mod = h_f_mod if is_home else a_f_mod
		ctrl_fluidity = getattr(ctrl_team, 'fluidity', 1.0)
		elo_mult = self._get_elo_multiplier(is_home)

		risk /= ((elo_mult ** 1.1) * ctrl_f_mod * (ctrl_fluidity ** 0.5))

		if random.random() < 0.080:
			if self._check_foul(period_obj, opp_team, ctrl_team, minute, in_box=(random.random() < 0.15)):
				return

		if random.random() < risk:
			comp_p = max(0, att_p - random.randint(1, 2))
			self._record_passes(creator, target, att_p, comp_p, is_home)

			def_stopper = self._pick_carrier(opp_team, ['CB', 'DEF', 'LB', 'RB', 'GK'])
			if def_stopper and len(def_stopper.inns) > 0:
				if random.random() < 0.50:
					def_stopper.inns[-1].tackles += 1
				elif random.random() < 0.85:
					def_stopper.inns[-1].interceptions += 1
				else:
					def_stopper.inns[-1].aerials_won += 1

			if random.random() < 0.52:
				period_obj.corner_event(ctrl_team, opp_team)
				self.state = PossessionState(ctrl_team, 'final_third', 15 if is_home else 4)
			else:
				self.state = PossessionState(opp_team, 'build_up', 3 if not is_home else 16)
		else:
			comp_p = att_p if random.random() < 0.78 else max(1, att_p - 1)
			self._record_passes(creator, target, att_p, comp_p, is_home)
			roll_outcome = random.random()
			if roll_outcome < 0.28:
				self._resolve_shot_chance(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute, creator=creator, shooter=target)
			elif roll_outcome < 0.44:
				period_obj.corner_event(ctrl_team, opp_team)
				self.state = PossessionState(ctrl_team, 'final_third', 15 if is_home else 4)
			else:
				if random.random() < 0.50:
					self.state.phase = 'progression'
				else:
					self.state = PossessionState(opp_team, 'build_up', 3 if not is_home else 16)

	def _phase_transition(self, period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute):
		runner = self._pick_carrier(ctrl_team, ['LW', 'RW', 'ATT', 'AMF', 'ST', 'CF'])
		passer = self._pick_carrier(ctrl_team, ['DMF', 'MID', 'CB', 'CM'])
		if not runner or not passer:
			self.state = PossessionState(ctrl_team, 'progression', 9 if is_home else 10)
			return

		r_name = getattr(runner, 'short_name', '') or runner.name
		self.match.logger("Here come the attackers on the break! {} surges into open space on a lightning counter-attack!".format(r_name))

		self._record_passes(passer, runner, 1, 1, is_home)
		self.state.phase = 'final_third'
		self._resolve_shot_chance(period_obj, ctrl_team, opp_team, is_home, ctrl_mgr, opp_mgr, minute, creator=passer, shooter=runner, is_counter=True)

	def _resolve_shot_chance(self, period_obj, att_team, def_team, is_home, att_mgr, def_mgr, minute, creator=None, shooter=None, is_high_press_turnover=False, is_counter=False, is_1on1=False):
		if shooter is None:
			pool = getattr(att_team, 'xi', []) or getattr(att_team, 'players', [])
			forwards = [p for p in pool if getattr(p, 'position', 'MID') in ['ATT', 'ST', 'CF', 'AMF']]
			shooter = random.choice(forwards) if forwards else period_obj.pick_shooter(pool)

		if shooter is None:
			return

		if creator is None and random.random() < 0.70 and not is_1on1:
			pool = getattr(att_team, 'xi', []) or getattr(att_team, 'players', [])
			cands = [p for p in pool if p != shooter]
			creator = random.choice(cands) if cands else None

		if att_mgr.mentality == 'desperation_hail_mary' and att_mgr.target_man and random.random() < 0.45:
			shooter = att_mgr.target_man

		sh_name = getattr(shooter, 'short_name', '') or shooter.name
		cr_name = (getattr(creator, 'short_name', '') or creator.name) if creator else ''

		if is_1on1:
			shot_type = 'big_chance'
			base_xg = 0.38
		elif is_high_press_turnover:
			shot_type = 'big_chance'
			base_xg = 0.28
		elif is_counter:
			shot_type = 'big_chance'
			base_xg = 0.24
		else:
			roll = random.random()
			if roll < 0.25:
				shot_type = 'cutback'
				base_xg = 0.15
			elif roll < 0.45:
				shot_type = 'header'
				base_xg = 0.09
			elif roll < 0.65:
				shot_type = 'long'
				base_xg = 0.035
			else:
				shot_type = 'box'
				base_xg = 0.125

		sh_fit = getattr(shooter, 'fitness', 1.0)
		sh_finishing = getattr(shooter, 'finishing', 70.0)
		sh_composure = getattr(shooter, 'composure', 70.0)

		gk = next((p for p in def_team.xi if getattr(p, 'position', '') == 'GK'), None)
		gk_stat = ((getattr(gk, 'gk_diving', 75) + getattr(gk, 'gk_reflexes', 75)) * 0.5) if gk else 75.0
		gk_fit = getattr(gk, 'fitness', 1.0) if gk else 1.0
		gk_disp = (getattr(gk, 'short_name', '') or gk.name) if gk else 'the goalkeeper'

		defenders = [p for p in def_team.xi if getattr(p, 'position', '') in ['CB', 'LB', 'RB', 'LWB', 'RWB', 'SW', 'DEF']]
		cb = max(defenders, key=lambda p: getattr(p, 'defending', 70)) if defenders else None
		cb_def = getattr(cb, 'defending', 70.0) if cb else 70.0
		cb_aware = getattr(cb, 'def_awareness', cb_def) if cb else 70.0
		cb_name = (getattr(cb, 'short_name', '') or cb.name) if cb else 'the defender'

		h_s = self.match.home_score
		a_s = self.match.away_score
		lead = (h_s - a_s) if is_home else (a_s - h_s)

		fin_mult = ((sh_finishing / 75.0) ** 1.30)
		comp_mult = (sh_composure / 75.0)
		separation = max(0.82, min(1.22, (sh_finishing + getattr(shooter, 'strength', 70.0)) / (cb_def + cb_aware)))
		xg_val = base_xg * fin_mult * comp_mult * sh_fit * separation

		if def_mgr.mentality in ['park_the_bus', 'low_block']:
			xg_val *= 0.70
		if lead >= 2:
			xg_val *= 0.68
		if lead >= 3:
			xg_val *= 0.45
		if lead >= 4:
			xg_val *= 0.30
		if lead <= -2 and minute >= 60:
			xg_val *= 0.85

		if hasattr(shooter, 'has_playstyle'):
			if shooter.has_playstyle('finesse shot') and shot_type in ['box', 'cutback', 'big_chance']: xg_val += 0.03
			if shooter.has_playstyle('power shot') and shot_type == 'long': xg_val += 0.02
			if shooter.has_playstyle('aerial fortress') and shot_type == 'header': xg_val += 0.03

		xg_val = max(0.015, min(0.60, xg_val))

		if len(shooter.inns) > 0:
			shooter.inns[-1].shots += 1
			shooter.inns[-1].xg += xg_val
		if creator and len(creator.inns) > 0:
			creator.inns[-1].key_passes += 1
			creator.inns[-1].xa += xg_val

		if is_home:
			self.match.home_shots += 1
			self.match.home_xg += xg_val
		else:
			self.match.away_shots += 1
			self.match.away_xg += xg_val

		block_prob = 0.12 + ((cb_def + cb_aware) / 160.0) * 0.16
		if is_1on1:
			block_prob *= 0.10
		elif is_counter:
			block_prob *= 0.28
		elif shot_type == 'long':
			block_prob *= 0.75
		elif def_mgr.mentality in ['park_the_bus', 'low_block'] or lead <= -2:
			block_prob *= 1.45
		elif lead <= -3:
			block_prob *= 1.70

		if random.random() < block_prob:
			if cb and len(cb.inns) > 0:
				cb.inns[-1].tackles += 1
			block_roll = random.random()
			if block_roll < 0.65:
				self.match.logger("Heroic Block! {} strikes goalwards, but {} deflects it behind for a corner!".format(sh_name, cb_name))
				period_obj.corner_event(att_team, def_team)
			else:
				self.match.logger("Blocked: {} throws their body in the way of {}'s shot to clear the danger.".format(cb_name, sh_name))
			self.state = PossessionState(def_team, 'build_up', 3 if not is_home else 16)
			return

		gk_factor = ((gk_stat / 75.0) ** 0.75) * (gk_fit ** 0.5)
		conv_prob = (xg_val * 1.25 * self._get_elo_multiplier(is_home)) / max(0.75, gk_factor)
		on_target_prob = min(0.65, 0.32 + (sh_finishing / 240.0))

		shot_roll = random.random()
		if shot_roll < conv_prob:
			if len(shooter.inns) > 0:
				shooter.inns[-1].shots_on_target += 1
			if is_home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			period_obj.log_goal(shooter, creator, att_team, shot_type)
			self.reset_kickoff(def_team)
		elif shot_roll < on_target_prob:
			if len(shooter.inns) > 0:
				shooter.inns[-1].shots_on_target += 1
			if is_home:
				self.match.home_shots_target += 1
			else:
				self.match.away_shots_target += 1
			if gk and len(gk.inns) > 0:
				gk.inns[-1].saves += 1

			if random.random() < 0.65:
				self.match.logger("Brilliant Save! {} fires towards goal, but {} tips it around the post for a corner!".format(sh_name, gk_disp))
				period_obj.corner_event(att_team, def_team)
			else:
				self.match.logger("Shot on Target: {} strikes firmly, but {} smothers the effort cleanly.".format(sh_name, gk_disp))
			self.state = PossessionState(def_team, 'build_up', 3 if not is_home else 16)
		else:
			period_obj._near_miss_commentary(att_team, shooter, shot_type)
			self.state = PossessionState(def_team, 'build_up', 3 if not is_home else 16)
