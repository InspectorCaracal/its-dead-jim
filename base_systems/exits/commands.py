from time import time
from evennia import CmdSet
from evennia.utils import logger

from evennia.commands.default.muxcommand import MuxCommand
from core.commands import Command

from base_systems.maps.pathing import relative_to_cardinal, dir_to_abbrev, compass_words

class CmdGo(Command):
	"""
	Move to a new location.
	
	Usage:
	  go <exit or direction>
	  
	You can optionally set your movement type by using an alias.

	Examples:
		go north
		saunter out
	"""
	key = "go"
	aliases = ("walk", "run", "stroll", "stride", "hop", "jog", "skip", "saunter")
	locks = "cmd:all()"
	help_category = "Movement"

	def func(self):
		if self.cmdstring != "go":
			self.caller.movement = self.cmdstring + "s"

		direction = relative_to_cardinal(self.caller.ndb.last_move_dir, self.args.lower().strip())
		if direction:
			self.execute_cmd(direction)
		else:
			self.execute_cmd(self.args)


class CmdTurn(Command):
	"""
	turn to face a different direction.

	Usage:
		turn <direction>
	
	Examples:
		turn right
		turn around
	"""
	key = "turn"
	aliases = ("face",)
	locks = "cmd:all()"
	help_category = "Movement"

	def func(self):
		if not (moving := self.caller.ndb.last_move_dir):
			self.msg("You aren't facing a direction to turn from.")
			return
		facing = self.args.lower().strip()
		if direction := relative_to_cardinal(self.caller.ndb.last_move_dir, facing):
			words = compass_words.get(direction)
		elif abbrev := dir_to_abbrev(facing):
			words = compass_words.get(abbrev)
		else:
			self.msg("That isn't a valid direction.")
			return

		self.caller.ndb.last_move_dir = direction
		self.caller.msg(f"You are now facing {words}.")

class CmdNoDirection(Command):
	"""
	fail to move in a direction
	"""
	auto_help=False
	key = "__no_movement"

	def func(self):
		self.msg("You cannot go that way.")

class CmdNorth(CmdNoDirection):
	key = "north"
	aliases = ("n",)
class CmdSouth(CmdNoDirection):
	key = "south"
	aliases = ("s",)
class CmdEast(CmdNoDirection):
	key = "east"
	aliases = ("e",)
class CmdWest(CmdNoDirection):
	key = "west"
	aliases = ("w",)
class CmdNW(CmdNoDirection):
	key = "northwest"
	aliases = ("nw",)
class CmdNE(CmdNoDirection):
	key = "northeast"
	aliases = ("ne",)
class CmdSW(CmdNoDirection):
	key = "southwest"
	aliases = ("sw",)
class CmdSE(CmdNoDirection):
	key = "southeast"
	aliases = ("se",)

class DirectionCmdSet(CmdSet):
	key = "Direction CmdSet"
	priority = -1

	def at_cmdset_creation(self):
		self.add(CmdNorth)
		self.add(CmdSouth)
		self.add(CmdEast)
		self.add(CmdWest)
		self.add(CmdNW)
		self.add(CmdNE)
		self.add(CmdSW)
		self.add(CmdSE)

class NavCmdSet(CmdSet):
	key = "Nav CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdGo)
		self.add(CmdTurn)
		self.add(DirectionCmdSet)
