import time
from evennia.utils.utils import delay

from switchboard import COUNTER_WINDOW
from base_systems.actions.base import Action, InterruptAction
from systems.combat.utils import get_hit_location


class AttackAction(Action):
	def __init__(self, **kwargs):
		# self.actor = actor
		# self.target = target
		self.weapon = kwargs.pop('weapon', None)
		self.skill = kwargs.pop('skill', 'martial')
		self.exp = kwargs.pop('exp',1)
		super().__init__(**kwargs)
		target = get_hit_location(self.targets[0])
		if not target:
			raise InterruptAction
		self.target = target
	
	def start(self, *args, **kwargs):
		if not self.weapon:
			if not (wielded := self.wielded):
				self.actor.msg("You have nothing to attack with.")
				return self.end()
			# by default, weapon will be your first wielded weapon
			self.weapon = wielded[0]
			# TODO: pull skill and DC from this fallback weapon
		if self.weapon.baseobj != self.actor:
			# make sure we can or are holding the object
			if self.weapon not in self.actor.holding().values():
				if not self.actor.hold(self.weapon):
					self.msg(f"You cannot hold that right now.")
					return self.end()
		# do a skill check on the weapon's dependent skill
		return super().start(*args, **kwargs)
		
	def do(self, *args, **kwargs):
		# TODO: this is kind of janky, figure out a better way
		if 'succeed' in args:
			return self.succeed(*args, **kwargs)

		# marks the parts that will be used for this action
		super().do(*args, **kwargs | { 'delay': True })

		if hasattr(self.target.baseobj, 'counteract'):
			self.actor.emote(f"{self.verb}s at @{self.target.sdesc.get(strip=True, article=False)} with $gp(their) {self.weapon.sdesc.get(article=False)}", include=[self.target])
			dur = getattr(self, 'duration', COUNTER_WINDOW)
			self._next_step = time.time() + dur
			self._task = delay(dur, self.succeed)
			self.do_args = ['succeed']
			self.target.baseobj.counteract.add(self)
		else:
			self.actor.emote(f"{self.verb}s @{self.target.sdesc.get(strip=True, article=False)} with $gp(their) {self.weapon.sdesc.get(article=False)}", include=[self.target])
			self.succeed()

	def succeed(self, *args, **kwargs):
		damage = self.weapon.stats.dmg.value
		damage_type = getattr(self.weapon.stats.dmg, 'dtype', '')
	
		# TODO: refactor damage code to include the type
		self.target.at_damage(damage, source=self.actor)
		if self.exp:
			kwargs['exp'] = self.exp
		return super().succeed(*args, **kwargs)

	def fail(self, *args, **kwargs):
		# if not kwargs.get('quiet'):
		# 	# TODO: should we implement accidentally hitting something else?
		# 	self.actor.emote(f"tries to {self.verb} @{self.target.sdesc.get(strip=True, article=False)} with $gp(their) {self.weapon.sdesc.get(article=False)}, but misses.", include=[self.target])
		
		return super().fail(*args, **kwargs)


class HitAction(AttackAction):
	"""A melee-range attack"""
	move = "strike"


class ThrowAction(Action):
	"""Throw something! Or someone!"""
	move = "throw"

	def __init__(self, **kwargs):
		target = kwargs.pop('targets',[])
		if not len(target):
			raise InterruptAction
		self.thrown = target[0]
		self.target = kwargs.pop('throw_at', None)
		self.exp = kwargs.pop('exp',1)
		super().__init__(**kwargs)

	def start(self, *args, **kwargs):
		# first we have to see if the thing is being held already
		cands = []
		if holding := self.actor.holding(part=None):
			# check if we're holding the thing to throw, first
			cands = list(holding.values()) + [ ob.baseobj for ob in holding.values() ]

		if self.thrown not in cands:
			# we aren't holding it, try to hold it
			if not self.actor.hold(self.thrown):
				return super().end()

		if 'character' in self.thrown.baseobj._content_types:
			self.skill = "wrestling"
		else:
			self.skill = "aim"
		
		# TODO: figure out the DC to check

		return super().start(*args, **kwargs)
	
	def do(self, *args, **kwargs):
		# you should always drop something when you try to throw it
		if not self.actor.unhold(target=self.thrown):
			return super().end()

		base = self.thrown.baseobj

		target_base = None
		if self.target:
			if self.target.baseobj and self.target.baseobj.location == base.location:
				target_base = self.target.baseobj
			else:
				self.target = None

		# TODO: do a strength check to determine if it can go that far
		if self.target and base.location == self.actor:
			target_loc = target_base.location
		else:
			target_loc = self.actor.location
		# handling throwing something versus a wrestling move
		if base.location == self.actor:
			if not base.at_pre_drop(self.actor):
				self.actor.msg("You can't throw that.")
				return super().end()
			# TODO: travel "through" rooms on the way
			succeed = base.move_to(target_loc, quiet=True)
			if not succeed:
				self.actor.msg("You can't throw that.")
				return super().end()

			base.at_drop(self.actor)
		# TODO: you should be able to try to throw a character into something else
		# ....and if that something else is a character, they should be able to counteract as well
		if hasattr(base, 'counteract'):
			kwargs['delay'] = True
			emote_base = f"attempts to throw @{base.sdesc.get(strip=True)}"
			self.actor.emote(f"attempts to throw @{base.sdesc.get(strip=True)}")
			base.counteract.add(self)
		elif hasattr(target_base, 'counteract'):
			kwargs['delay'] = True
			self.actor.emote(f"throws @{base.sdesc.get(strip=True)} at @{target_base.sdesc.get(strip=True)}")
			target_base.counteract.add(self)

		return super().do(*args, **kwargs)

	def succeed(self, *args, **kwargs):
		self.actor.location.posing.remove(self.thrown)

		# damage calculations
		# TODO: define better damage calculations
		base = self.thrown.baseobj
		strength = self.actor.stats.str.value
		size_ratio = self.actor.size / base.size
		# TODO: range calculation from str and size
		damage = (strength*size_ratio)*10 # this is so arbitrary
		self.actor.emote(f"throws @{base.sdesc.get(strip=True)}!")
		base.at_damage(damage, source=self.actor, damage_type='impact')

		if self.target:
			# it should be harder to hit smaller things
			# self.msg("|YThrowing at targets is not yet implemented.|n")
			# TODO: better damage calculations,,,
			self.target.at_damage(damage, source=self.actor, damage_type='impact')


		return super().succeed(*args, **(kwargs | {'exp': self.exp}))
	
	def fail(self, *args, **kwargs):
		self.actor.emote(f"drops @{self.thrown.baseobj.sdesc.get(strip=True)}.")
		super().fail(*args, **kwargs)



class EvadeAction(Action):
	move = "dodge"

	def __init__(self, **kwargs):
		print("initializing evasion action")
		self.skill = kwargs.pop('skill', 'evasion')
		super().__init__(**kwargs)
	
	def start(self, *args, **kwargs):
		if self.actor.counteract.current:
			self.counter = self.actor.counteract.current
			self.dc = self.counter.counter_dc
		return super().start(*args, **kwargs)

	
	def succeed(self, *args, **kwargs):
		if not hasattr(self, 'counter'):
			self.actor.emote(getattr(self, 'tail_str', "does a fancy dodge move"))
		
		else:
			emote_str = f"dodges @{self.counter.actor.sdesc.get(strip=True)}"
			if tail_str := getattr(self, 'tail_str', ''):
				emote_str += f", {tail_str}"
			self.actor.emote(emote_str)
			self.actor.counteract.remove(self.counter)
			self.counter.fail()
		
		return super().succeed(*args, **kwargs | {'exp': getattr(self, 'exp', 0)})

	def fail(self, *args, **kwargs):
		emote_str = f"tries to avoid @{self.counter.actor.sdesc.get(strip=True)}"
		if tail_str := getattr(self, 'tail_str', ''):
			emote_str += f", {tail_str}"
		self.actor.emote(emote_str)
		self.actor.counteract.remove(self.counter)
		return super().fail(*args, **kwargs)
