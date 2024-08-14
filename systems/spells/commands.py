from evennia import CmdSet

from core.commands import Command
from systems.spells import actions

class CmdSpell(Command):
	"""
	Use your innate elemental magic. Innate magic abilities can be used on yourself, your location, or a specific object.

	Usage:
		cast [<target>] [<optional addition to the emote>]

	Examples:
		cast here
		cast north
		cast box stretches an arm out towards @box and clenches her hand into a fist
	"""
	key = "cast"
	help_category = "Magic"

	def func(self):
		caller = self.caller

		if current := caller.do_get_spell():
			if self.args:
				# can't cast two spells at once
				self.msg("You cannot have two active targets at once; $h(dispel) your current magic first.")
			else:
				# return current spell info
				current.status()
			return

		if not self.args:
			self.msg("Use your magic on what?")
			return

		target, tail = yield from self.find_targets(self.args, tail=True, find_none=True)
		if not target:
			return
		
		# FIXME: am I supposed to have to do this? I can't remember
		target = target[0]
		
		if target == caller:
			spell_cls = actions.SelfSpell
		elif target == caller.location:
			spell_cls = actions.AreaSpell
		else:
			spell_cls = actions.TargetSpell
			
		action = spell_cls(caller, target)
		if action.start(tail):
			caller.do_set_spell(action)

		# else:
		# 	logger.log_msg(f"failed. spell class: {action} move: {self.move}")
		# 	self.msg("That isn't a valid spell type.")
		# 	return


class CmdDispel(Command):
	"""
	Remove your magic effects from your current target.

	Usage:
		dispel
	"""
	key = "dispel"
	aliases = ('dispell',)
	help_category = "Magic"

	def func(self):
		caller = self.caller
		if not (current := caller.do_get_spell()):
			caller.msg("You have no active magic to dispel.")
			return

		current.end(self.args)
		# caller.archetype.set_spell()
		caller.msg("Your magic dissipates.")

class SpellCmdSet(CmdSet):
	key = "Spell CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdSpell)
		self.add(CmdDispel)

