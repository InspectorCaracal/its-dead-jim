"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""
from evennia import default_cmds
from evennia.commands.default.admin import CmdPerm
from evennia.contrib.utils.git_integration.git_integration import CmdGit

from core.scripts import CmdScripts
from core.system_cmds import SystemCmdSet

from base_systems.characters.assess import CmdHealth
from base_systems.help.commands import CmdHelp
from base_systems.prototypes.spawning import CmdSpawn

from base_systems.actions.commands import ActionCmdSet
from base_systems.characters import social, movement
from base_systems.exits.commands import NavCmdSet
from base_systems.maps.commands import BuilderCmdSet
from base_systems.things.commands import ItemManipCmdSet
from base_systems.community.commands import CommunityCmdSet

from systems.chargen.commands import CmdCharCreate, CmdIC
from systems.combat.commands import CombatCmdSet
from systems.clothing.commands import ClothedCharacterCmdSet
from systems.machines.driving import DrivingCmdSet
from systems.parkour.building import ObstacleBuilderCmdSet
from systems.skills.commands import SkillCmdSet
from systems.crafting.commands import CraftingCmdSet
from utils.CmdWiki import CmdWiki

class CharacterCmdSet(default_cmds.CharacterCmdSet):
	key = "DefaultCharacter"

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
		# get rid of some stuff we don't want
		self.remove("@tunnel")
		self.remove("setdesc")

		# add our commands
		self.add(social.SocialCmdSet)
		self.add(ItemManipCmdSet)
		self.add(CombatCmdSet)
		self.add(movement.MovementCmdSet)
		self.add(ObstacleBuilderCmdSet)
		self.add(CraftingCmdSet)
		self.add(NavCmdSet)
		self.add(BuilderCmdSet)
		# self.add(DrivingCmdSet)
		self.add(CommunityCmdSet)
		self.add(ActionCmdSet)
		self.add(SkillCmdSet)
		self.add(ClothedCharacterCmdSet)
		self.add(CmdSpawn)
		self.add(CmdHelp)
		self.add(CmdHealth)
		self.remove('@about')

		# ugh
		self.add(CmdScripts)

class AccountCmdSet(default_cmds.AccountCmdSet):
	key = "DefaultAccount"

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
		self.add(CmdPerm)
		self.add(CmdCharCreate)
		self.add(CmdIC)
		self.add(CmdHelp)
		self.add(CmdGit)
		# TODO: add in my own versions with friend lists etc.
		self.remove("who")
		self.remove('@about')

		self.add(CmdWiki)

		# ugh
		self.add(CmdScripts)

class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
	"""
	Command set available to the Session before being logged in.  This
	holds commands like creating a new account, logging in, etc.
	"""

	key = "DefaultUnloggedin"

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
		#
		# any commands you add below will overload the default ones.
		#
		self.add(SystemCmdSet)


class SessionCmdSet(default_cmds.SessionCmdSet):
	"""
	This cmdset is made available on Session level once logged in. It
	is empty by default.
	"""

	key = "DefaultSession"

	def at_cmdset_creation(self):
		"""
		This is the only method defined in a cmdset, called during
		its creation. It should populate the set with command instances.

		As and example we just add the empty base `Command` object.
		It prints some info.
		"""
		super().at_cmdset_creation()
		#
		# any commands you add below will overload the default ones.
		#
		self.add(SystemCmdSet)
