class GameStateManager:
	def __init__(self, team, match, is_home=True):
		self.team = team
		self.match = match
		self.is_home = is_home
		t_name = getattr(team, 'name', '') or str(team)
		self.name = t_name
		self.mentality = 'balanced'
		self.formation = getattr(team, 'formation', '4-3-3')
		self.urgency = 0.0
		self.target_man = None
		self.tactical_orders = set()
		self.shifts_applied = set()
		self.manager_pov = getattr(team, 'manager_pov', None)

	def calculate_urgency(self, minute, goal_diff, player_count_diff=0):
		time_left = max(1, 90 - minute)
		if goal_diff < 0:
			base_urgency = (abs(goal_diff) * 18.0) + max(0.0, (75 - time_left) * 0.8)
		elif goal_diff > 0:
			base_urgency = - (goal_diff * 14.0) - max(0.0, (75 - time_left) * 0.5)
		else:
			base_urgency = 5.0 if minute >= 75 else 0.0

		if player_count_diff < 0:
			base_urgency -= 15.0
		elif player_count_diff > 0:
			base_urgency += 12.0

		self.urgency = max(-100.0, min(100.0, base_urgency))
		return self.urgency

	def evaluate_mentality(self, minute, goal_diff, my_player_count, opp_player_count):
		player_diff = my_player_count - opp_player_count
		self.calculate_urgency(minute, goal_diff, player_diff)

		old_mentality = self.mentality

		if my_player_count < 11 and minute >= 70 and goal_diff >= 0:
			new_ment = 'park_the_bus'
		elif minute >= 82 and goal_diff <= -1:
			new_ment = 'desperation_hail_mary'
		elif minute >= 78 and goal_diff >= 1:
			new_ment = 'park_the_bus'
		elif minute >= 65 and goal_diff <= -1:
			new_ment = 'attacking_overload'
		elif 45 <= minute < 78 and goal_diff in [1, 2]:
			new_ment = 'controlled_counter'
		elif minute < 45 and goal_diff >= 3:
			new_ment = 'controlled_counter'
		else:
			new_ment = 'balanced'

		if new_ment != old_mentality:
			self.mentality = new_ment
			self._log_mentality_shift(old_mentality, new_ment, minute, goal_diff)

		if self.mentality == 'desperation_hail_mary' and self.target_man is None:
			self._assign_target_man()

		if self.manager_pov:
			if self.mentality == 'desperation_hail_mary':
				self.manager_pov.defensive_line = 'high'
				self.manager_pov.pressing_trigger = 'counterpress'
				self.manager_pov.set_piece_focus = 'aerial_overload'
			elif self.mentality == 'attacking_overload':
				self.manager_pov.defensive_line = 'high'
				self.manager_pov.pressing_trigger = 'counterpress'
			elif self.mentality == 'park_the_bus':
				self.manager_pov.defensive_line = 'deep'
				self.manager_pov.offside_trap = 'conservative'
				self.manager_pov.pressing_trigger = 'regroup'

		return self.mentality

	def _assign_target_man(self):
		cbs = [p for p in self.team.xi if getattr(p, 'primary_position', '') == 'CB' or getattr(p, 'position', '') == 'DEF']
		if cbs:
			self.target_man = max(cbs, key=lambda p: getattr(p, 'heading', 70) * 0.5 + getattr(p, 'jumping', 70) * 0.3 + getattr(p, 'strength', 70) * 0.2)
			tm_name = getattr(self.target_man, 'short_name', '') or self.target_man.name
			self.match.logger("Desperate stakes now for {} -- {} has been pushed right up into the penalty area as an emergency target man!".format(self.name, tm_name))

	def _log_mentality_shift(self, old_m, new_m, minute, goal_diff):
		order_key = "{}_{}".format(new_m, minute // 15)
		if order_key in self.tactical_orders:
			return
		self.tactical_orders.add(order_key)

		if new_m == 'park_the_bus':
			msg = "{} are digging in now, retreating ten men behind the ball and defending the edge of their box.".format(self.name)
		elif new_m == 'controlled_counter':
			msg = "{} look happy to absorb a bit of pressure now, keeping their shape and waiting to strike on the counter.".format(self.name)
		elif new_m == 'attacking_overload':
			msg = "Urgency creeping in for {} now -- fullbacks are bombing forward and bodies are flooding into the final third.".format(self.name)
		elif new_m == 'desperation_hail_mary':
			msg = "It's all hands on deck for {} -- throwing caution to the wind and pumping direct aerial balls into the box!".format(self.name)
		else:
			msg = "{} look to settle back into their standard rhythm and shape.".format(self.name)

		self.match.logger(msg)

	def get_press_modifier(self):
		base = 1.0
		if self.mentality == 'attacking_overload':
			base = 1.25
		elif self.mentality == 'desperation_hail_mary':
			base = 1.40
		elif self.mentality == 'park_the_bus':
			base = 0.70
		elif self.mentality == 'controlled_counter':
			base = 0.90

		if self.manager_pov:
			base *= self.manager_pov.get_pressing_modifier()

		return base

	def get_pass_risk_modifier(self):
		if self.mentality == 'desperation_hail_mary':
			base = 1.50
		elif self.mentality == 'attacking_overload':
			base = 1.20
		elif self.mentality == 'park_the_bus':
			base = 0.65
		elif self.mentality == 'controlled_counter':
			base = 0.85
		else:
			base = 1.0

		if self.manager_pov:
			base /= max(0.5, self.manager_pov.get_build_up_modifier())

		return base

	def get_backline_depth(self):
		if self.mentality == 'park_the_bus':
			return 'deep'
		elif self.mentality in ['attacking_overload', 'desperation_hail_mary']:
			return 'high'
		if self.manager_pov:
			return self.manager_pov.defensive_line
		return 'mid_block'
