import random

REFEREE_ROSTER = [
	("Szymon Marciniak", "balanced", 1.00, 0.25, 0.08),
	("Michael Oliver", "disciplinarian", 1.28, 0.18, 0.10),
	("Clement Turpin", "lenient", 0.78, 0.32, 0.06),
	("Anthony Taylor", "disciplinarian", 1.22, 0.20, 0.11),
	("Daniele Orsato", "balanced", 1.02, 0.24, 0.07),
	("Felix Zwayer", "disciplinarian", 1.25, 0.19, 0.09),
	("Slavko Vincic", "balanced", 0.98, 0.26, 0.07),
	("Danny Makkelie", "lenient", 0.82, 0.30, 0.05),
	("Francois Letexier", "balanced", 1.05, 0.23, 0.08),
	("Istvan Kovacs", "disciplinarian", 1.30, 0.17, 0.12)
]

WEATHER_CONDITIONS = [
	("Clear", 1.00, 1.00, 1.00, 1.00),
	("Clear", 1.00, 1.00, 1.00, 1.00),
	("Wet / Heavy Rain", 1.12, 1.30, 1.05, 1.18),
	("Wet / Heavy Rain", 1.12, 1.30, 1.05, 1.18),
	("Extreme Heat", 0.96, 1.00, 1.20, 1.00),
	("Freezing / Snow", 0.88, 1.15, 1.05, 1.15)
]

class Referee:
	def __init__(self, name=None, profile="balanced", strictness=1.00, card_thresh=0.25, crowd_bias=0.08):
		self.name = name or "Match Referee"
		self.profile = profile
		self.strictness = strictness
		self.card_thresh = card_thresh
		self.crowd_bias = crowd_bias

	@classmethod
	def generate_random(cls):
		choice = random.choice(REFEREE_ROSTER)
		return cls(choice[0], choice[1], choice[2], choice[3], choice[4])

	def should_call_foul(self, base_prob, is_home=False, venue_attendance=45000):
		mult = self.strictness
		if venue_attendance > 50000:
			atten_scale = min(1.3, venue_attendance / 50000.0)
			if is_home:
				mult *= (1.0 - self.crowd_bias * 0.5 * atten_scale)
			else:
				mult *= (1.0 + self.crowd_bias * 0.5 * atten_scale)
		return random.random() < min(0.92, base_prob * mult)

	def evaluate_card(self, severity_score, is_home=False, has_yellow=False):
		thresh = self.card_thresh
		if has_yellow:
			thresh *= 1.35
		if self.profile == "disciplinarian":
			thresh *= 0.82
		elif self.profile == "lenient":
			thresh *= 1.25
		if severity_score > (thresh * 2.8):
			return "red"
		elif severity_score > thresh:
			return "yellow"
		return "none"

class Weather:
	def __init__(self, condition="Clear", pass_mult=1.0, spill_mult=1.0, stamina_mult=1.0, foul_mult=1.0):
		self.condition = condition
		self.pass_mult = pass_mult
		self.spill_mult = spill_mult
		self.stamina_mult = stamina_mult
		self.foul_mult = foul_mult

	@classmethod
	def generate_random(cls):
		w = random.choice(WEATHER_CONDITIONS)
		return cls(w[0], w[1], w[2], w[3], w[4])

class VAREngine:
	def __init__(self, overturn_rate=0.40):
		self.overturn_rate = overturn_rate

	def check_candidate_goal(self, match, scorer_name, assister_name=None, shot_type="box"):
		if shot_type in ["penalty", "direct_freekick"]:
			return False, None, []
		var_trigger_prob = 0.048
		if shot_type in ["cutback", "big_chance"]:
			var_trigger_prob = 0.065
		if random.random() >= var_trigger_prob:
			return False, None, []
		
		reasons = ["marginal offside in the build-up", "a possible handball in the lead-up", "a foul in the attacking phase"]
		chosen_reason = random.choice(reasons)
		lines = []
		lines.append(f"Hold on, the referee has paused play with a hand to the earpiece. VAR is reviewing {chosen_reason}!")
		
		is_overturned = random.random() < self.overturn_rate
		if is_overturned:
			lines.append(f"DECISION OVERTURNED: Following VAR consultation, the goal by {scorer_name} is disallowed for {chosen_reason}!")
			if hasattr(match, 'stoppage_delays'):
				match.stoppage_delays += 1.8
			else:
				match.stoppage_delays = 1.8
		else:
			lines.append(f"DECISION CONFIRMED: The VAR check is complete and the on-field decision stands. Goal awarded to {scorer_name}!")
			if hasattr(match, 'stoppage_delays'):
				match.stoppage_delays += 1.2
			else:
				match.stoppage_delays = 1.2
		return is_overturned, chosen_reason, lines

	def check_penalty_appeal(self, match, att_name, def_name):
		lines = [f"Penalty appeal! {att_name} goes down under pressure from {def_name}. The referee signals for a VAR review!"]
		is_pen = random.random() < 0.52
		if is_pen:
			lines.append("DECISION CONFIRMED: The referee points to the spot after reviewing the monitor! Penalty awarded!")
		else:
			lines.append("DECISION OVERRULED: No penalty given. The contact was deemed minimal and play resumes.")
		if hasattr(match, 'stoppage_delays'):
			match.stoppage_delays += 1.5
		return is_pen, lines

class SetPieceChoreography:
	ROUTINES = ["near_post_flick", "far_post_overload", "goalkeeper_screen", "short_cutback"]

	@classmethod
	def select_routine(cls, team_philosophy="balanced", taker=None, targets=None):
		if team_philosophy in ["high_press", "direct_counter"]:
			weights = [0.35, 0.35, 0.20, 0.10]
		elif team_philosophy == "tiki_taka":
			weights = [0.15, 0.15, 0.20, 0.50]
		elif team_philosophy == "low_block":
			weights = [0.40, 0.40, 0.15, 0.05]
		else:
			weights = [0.30, 0.30, 0.20, 0.20]
		return random.choices(cls.ROUTINES, weights=weights, k=1)[0]

	@classmethod
	def generate_commentary(cls, routine, taker_name, target_name, gk_name, is_goal=False, is_save=False):
		if routine == "near_post_flick":
			if is_goal:
				return f"Sensational set-piece choreography! {target_name} makes an explosive near-post dart to meet {taker_name}'s whip and glances a deft flick inside the far upright!"
			elif is_save:
				return f"{target_name} attacks the near post off {taker_name}'s corner and flicks it goalwards, but {gk_name} makes an instinctive reaction stop!"
			else:
				return f"{taker_name} drills the corner low towards the near post, but the flick is mistimed and cleared away."
		elif routine == "far_post_overload":
			if is_goal:
				return f"Choreographed corner routine executed to perfection! Delivered deep by {taker_name}, an aerial overload at the back post leaves {target_name} unmarked to power a towering header past {gk_name}!"
			elif is_save:
				return f"Deep inswinger from {taker_name} finds {target_name} towering at the back post, but {gk_name} scrambles across the goal line to claw it away!"
			else:
				return f"{taker_name} floats a deep ball towards the far post, but it drifts out of reach for a goal kick."
		elif routine == "goalkeeper_screen":
			if is_goal:
				return f"Clever dead-ball tactics! As {taker_name} whips the delivery in, attackers crowd the six-yard box to screen {gk_name}, and {target_name} rises highest to nod into the unguarded corner!"
			elif is_save:
				return f"{taker_name}'s corner causes chaos in the crowded six-yard box, but {gk_name} punches through traffic with supreme authority!"
			else:
				return f"Crowded goalmouth as {taker_name} swings it in, but the referee blows for a defensive free kick due to an off-the-ball push."
		else:
			if is_goal:
				return f"Brilliant short corner routine! {taker_name} works it quickly into the half-space before {target_name} arrows an unstoppable strike through the crowd into the bottom corner!"
			elif is_save:
				return f"Short corner variation opens up space for {target_name} to strike from the edge of the area, but {gk_name} dives full length to push it behind!"
			else:
				return f"Short corner worked out wide, but the low cross is cut out cleanly at the front post."

