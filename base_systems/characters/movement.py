from evennia import CmdSet
from base_systems.actions.commands import ActionCommand

from base_systems.characters import actions

# TODO: refactor these to use Actions
class CmdSit(ActionCommand):
	"""
	Sit down, possibly on something.
	
	Usage:
	  sit
		sit on <target>
	"""
	key = "sit"
	aliases = ("sit on", "sit down",)
	locks = "cmd:all()"
	help_category = "Movement"
	permission = True
	action = actions.SitAction
	needs_target = False

	def at_pre_cmd(self):
		statuses = self.caller.tags.get(category="status", return_list=True)
		if "sitting" in statuses:
			self.msg(f"You are already sitting.")
			return True


class CmdLieDown(ActionCommand):
	"""
	Lie down, possibly on something.
	
	Usage:
	  lie down
		lie on <target>
	"""
	key = "lie down"
	aliases = ("lie on", "lie down on",)
	locks = "cmd:all()"
	help_category = "Movement"
	permission = True
	action = actions.LieDownAction
	needs_target = False

	def at_pre_cmd(self):
		statuses = self.caller.tags.get(category="status", return_list=True)
		if "lying down" in statuses:
			self.msg(f"You are already lying down.")
			return True


class CmdStand(ActionCommand):
	"""
	Stand up.
	
	Usage:
	  stand
	"""
	key = "stand"
	aliases = ("stand on","stand up",)
	locks = "cmd:all()"
	help_category = "Movement"
	permission = True
	action = actions.StandUpAction
	needs_target = False


class CmdJumpOff(ActionCommand):
	"""
	Jump off of something.
	
	Usage:
	  jump off
	"""
	key = "jump off"
#	aliases = ("stand on","stand up",)
	locks = "cmd:all()"
	help_category = "Movement"
	permission = True
	action = actions.JumpOffAction
	needs_target = False


class MovementCmdSet(CmdSet):
	key = "Movement CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdSit)
		self.add(CmdLieDown)
		self.add(CmdStand)
		self.add(CmdJumpOff)
