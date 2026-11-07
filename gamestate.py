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

		return self.mentality

	def _assign_target_man(self):
		cbs = [p for p in self.team.xi if getattr(p, 'primary_position', '') == 'CB' or getattr(p, 'position', '') == 'DEF']
		if cbs:
			self.target_man = max(cbs, key=lambda p: getattr(p, 'heading', 70) * 0.5 + getattr(p, 'jumping', 70) * 0.3 + getattr(p, 'strength', 70) * 0.2)
			tm_name = getattr(self.target_man, 'short_name', '') or self.target_man.name
			self.match.logger("HAIL MARY: {} manager pushes center-back {} up front as an emergency striker!".format(self.name, tm_name))

	def _log_mentality_shift(self, old_m, new_m, minute, goal_diff):
		order_key = "{}_{}".format(new_m, minute // 15)
		if order_key in self.tactical_orders:
			return
		self.tactical_orders.add(order_key)

		manager_name = getattr(self.team, 'manager', None) or "{} Manager".format(self.name)
		if new_m == 'park_the_bus':
			msg = "TACTICAL SHIFT: {} manager {} orders PARK THE BUS! Defending the penalty box with a deep low block.".format(self.name, manager_name)
		elif new_m == 'controlled_counter':
			msg = "TACTICAL SHIFT: {} manager {} adopts a CONTROLLED COUNTER stance, protecting the lead while hunting on the break.".format(self.name, manager_name)
		elif new_m == 'attacking_overload':
			msg = "TACTICAL SHIFT: {} manager {} calls for ATTACKING OVERLOAD! Fullbacks pressing high and committing bodies into the final third.".format(self.name, manager_name)
		elif new_m == 'desperation_hail_mary':
			msg = "TACTICAL SHIFT: {} manager {} signals ALL-OUT DESPERATION! Pumping direct aerial balls into the box!".format(self.name, manager_name)
		else:
			msg = "TACTICAL SHIFT: {} resets to a BALANCED tactical shape.".format(self.name)

		self.match.logger(msg)

	def get_press_modifier(self):
		if self.mentality == 'attacking_overload':
			return 1.25
		elif self.mentality == 'desperation_hail_mary':
			return 1.40
		elif self.mentality == 'park_the_bus':
			return 0.70
		elif self.mentality == 'controlled_counter':
			return 0.90
		return 1.0

	def get_pass_risk_modifier(self):
		if self.mentality == 'desperation_hail_mary':
			return 1.50
		elif self.mentality == 'attacking_overload':
			return 1.20
		elif self.mentality == 'park_the_bus':
			return 0.65
		elif self.mentality == 'controlled_counter':
			return 0.85
		return 1.0

	def get_backline_depth(self):
		if self.mentality == 'park_the_bus':
			return 'deep'
		elif self.mentality in ['attacking_overload', 'desperation_hail_mary']:
			return 'high'
		return 'standard'
