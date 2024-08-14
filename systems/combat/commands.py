from random import choice
from evennia import CmdSet
from evennia.utils import is_iter
from base_systems.actions.commands import ActionCommand
from core.commands import Command
from systems.combat.utils import get_hit_location
from systems.combat import actions

class CmdAttack(ActionCommand):
	"""
	Hit a target with something.

	Usage:
	  hit <target>
	  hit <target> with <obj>
	"""
	key = "hit"
	aliases = ('kick',)
	prefixes = ("with",)
	action = actions.HitAction
	err_msg = "You can't attack that."

	def parse(self):
		super().parse()
		self.weapon = None
		if self.argsdict:
			weapon = self.argsdict.get('with')
			if weapon:
				self.weapon = weapon[0]
			self.targets = self.argsdict.get(None)

	def func(self):
		caller = self.caller

		if self.cmdstring == 'kick':
			# ignore weapons and use your feet
			feet = self.caller.parts.search('foot', part=True)
			if not feet:
				self.msg('You have no feet to kick with....')
				return
			# allows you to specify which foot to kick with
			if self.weapon:
				weapon = yield from self.find_targets(self.weapon, candidates=feet, numbered=False)
				if not weapon:
					return
			else:
				weapon = feet[0]

		else:
			if self.weapon:
				weapon = yield from self.find_targets(self.weapon, location=caller, numbered=False)
			else:
				weapon = caller.wielded
			if not weapon:
				self.msg("You have nothing to attack with.")
				return
			if is_iter(weapon):
				weapon = weapon[0]

		self.action_kwargs |= { 'weapon': weapon, 'verb': self.cmdstring }

		yield from super().func()


class CmdEvade(ActionCommand):
	"""
	Avoid being targeted by something.

	Usage:
		dodge [emote string]
	
	Example:
		dodge lunging to the left in an evasive roll
	Result:
		Monty dodges a short stout citizen, lunging to the left in an evasive roll.
	
	Evaded actions have a chance of targeting something else instead. (NOT YET IMPLEMENTED)
	"""
	key = "dodge"
	aliases = ("evade","avoid",)
	action = actions.EvadeAction
	err_msg = "You couldn't dodge."
	needs_target = False

	def func(self):
		self.tail_str = self.args
		self.targets = ''
		yield from super().func()


class CmdThrow(ActionCommand):
	"""
	throw something or someone

	Usage:
		throw <obj> [at <target>]
	"""

	key = "throw"
	aliases = ('toss',)
	locks = "cmd:all()"
	prefixes = ("at",)
	action = actions.ThrowAction
	err_msg = "You can't throw that."
	nofound_msg = "You don't have anything like {sterm} to throw."

	def parse(self):
		super().parse()
		self.target = None
		if self.argsdict:
			to_throw = self.argsdict.get(None)
			if to_throw:
				self.targets = to_throw
			target = self.argsdict.get('at')
			if target:
				self.target = target[0]

	def _filter_targets(self, targets, **kwargs):
		if held := getattr(self, 'held_obj', None):
			return list([obj for obj in targets if obj in held])
		else:
			return targets

	def func(self):
		caller = self.caller

		if not self.args:
			self.msg("Throw what?")
			return

		cands = []
		if holding := caller.holding(part=None):
			# check if we're holding the thing to throw, first
			cands = list(holding.values()) + [ ob.baseobj for ob in holding.values() ]
			self.held_objs = cands

		if cands:
			self.search_kwargs = { 'candidates': list(set(cands + caller.contents)) }
		else:
			self.location = caller
		
		if self.target:
			# find what we're throwing things at
			# TODO: add a distance=-1 to do "full distance"
			target = yield from self.find_targets(self.target, numbered=False, distance=3)
			if not target:
				return
			self.action_kwargs |= {'throw_at': target}
		yield from super().func()


class CombatCmdSet(CmdSet):
	key = "Combat CmdSet"

	def at_cmdset_creation(self):
		super().at_cmdset_creation()
		self.add(CmdAttack)
		self.add(CmdEvade)
		self.add(CmdThrow)


