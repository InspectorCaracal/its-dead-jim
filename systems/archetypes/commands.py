from evennia import CmdSet
from evennia.utils import iter_to_str
from core.commands import Command

# TODO: convert this to an Action
class CmdShift(Command):
	"""
	Transform to and from your werewolf forms.
	
	"shift" by itself will swap between partially shifted and unshifted.
	
	You can specify your shift with the following options:
	
	  shift full        - Transform to full quadrupedal beast form.
	  shift partial     - Transform into humanoid beast form.
	  shift off         - Transform back to human form.
	"""
	key = "shift"
	help_category = "Abilities"
	
	def func(self):
		if not self.args:
			level = None
		
		elif any( self.args.startswith(item) for item in ( "full", "part", "off" ) ):
			level = self.args
			if level.startswith("full"):
				self.msg("Full beast form hasn't been implemented yet.")
				return
		
		else:
			self.msg("That is not a valid transformation.")
			return


		if result := self.caller.do_shift(level):
			self.caller.emote(result)
		else:
			self.msg("You don't transform.")


class WerewolfCmdSet(CmdSet):
	key = "Werewolf CmdSet"
	
	def at_cmdset_creation(self):
		self.add(CmdShift)

# TODO: convert this to an Action
class CmdSummon(Command):
	"""
	Summon or dismiss your familiar

	Usage:
	  summon
	  dismiss
	"""
	key = "summon"
	aliases = ("dismiss",)

	def func(self):
		try:
			if self.cmdstring == "summon":
				self.caller.do_familiar(summon=True)
			elif self.cmdstring == 'dismiss':
				self.caller.do_familiar(summon=False)
			else:
				self.msg("Do what?")
		except:
			self.msg("You cannot do that.")

class CmdFamiliar(Command):
	"""
	Command or rename your familiar. Use "familiar commands" to see a list of all available commands.

	Usage:
		familiar name Tabby
		familiar commands
	"""
	key = "familiar"
	splitters = (' ',)

	def parse(self):
		super().parse()
		if self.argslist:
			self.command = self.argslist[0]
		if len(self.argslist) > 1:
			self.args = self.argslist[1]

	def func(self):
		if self.command == 'name' or self.command == 'rename':
			if self.args:
				if fam := self.caller.archetype.familiar(rename=self.args):
					self.msg(f"Your familiar has been renamed to {fam.key}.")
				else:
					self.msg("Could not rename your familiar.")
			else:
				self.msg("Usage: familiar name <new name>")
		elif self.command == 'commands':
			# fam.get_commands(self.caller)
			self.msg("The command listing has not yet been implemented.")
		else:
			if self.argslist:
				if not self.caller.archetype.familiar(cmd=" ".join(self.argslist)):
					self.msg("Could not command familiar.")
			else:
				self.msg("What do you want your familiar to do?")

class FamiliarCmdSet(CmdSet):
	key = "Familiar CmdSet"
	
	def at_cmdset_creation(self):
		self.add(CmdSummon)
		self.add(CmdFamiliar)

# TODO: mayyybe convert this to an Action
class CmdBite(Command):
	key = "bite"

	def func(self):
		caller = self.caller
		if caller.life.hunger <= 0:
			self.msg("You aren't hungry.")
			return
		if b := caller.holding(part="mouth"):
			self.msg(f"You are already biting {iter_to_str(b.values())}.")
			return
		target = yield from self.find_targets(self.args, location=caller.location, numbered=False)
		if not target:
			return
		
		caller.ndb.waiting_for_permission = (CmdBite.bite, caller, target, {})
		caller.msg(f"Requesting to bite {target.get_display_name(caller, article=True)}.")
		target.ask_permission(caller, "bite you")

	@classmethod
	def bite(cls, caller, target, *args):
		caller.do_feed(target)


class VampireCmdSet(CmdSet):
	key = "Vampire CmdSet"
	
	def at_cmdset_creation(self):
		self.add(CmdBite)


