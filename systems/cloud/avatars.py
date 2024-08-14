from evennia import CmdSet

from base_systems.characters.base import Character
from core.commands import Command
from core.ic.base import BaseObject
from systems.cloud.gearbook import GearHandler
from systems.cloud.software import SoftwareCmdSet

class NetCommand(Command):
	"""
	Base class for all Cloud commands.
	"""
	# the highest of priority
	priority = 201

	# TODO: set this up better
	locks = "cmd:pperm(Player)"
	
	def parse(self):
		super().parse()
		# do any additional setting up of command attributes here
		# like setting the avatar


class CmdNetLogout(NetCommand):
	key = "disconnect"
	aliases = ("dc","logout")

	def func(self):
		# TODO: implement connection/disconnection for the cloud deck
		pass

class CmdNetHome(NetCommand):
	key = "home"
	aliases = ("gohome")

	def func(self):
		player = self.caller
		character = self.obj

		if character.location != player.db.cloud_home:
			# move the character back to the account's login room
			character.location = player.db.login_room
			# and trigger the location's reception hook.
			character.location.at_object_receive(character, None) 
			character.emote("has disconnected", include=character, action_type="move")


class CmdNetJump(NetCommand):
	key = "jump"
	aliases = ("jump to")
	locks = "cmd:pperm(Player)"

	def func(self):
		if not self.args:
			self.msg("Usage: jump <location>")
			return

		# TODO: turn args into an actual destination
		destination = self.args.strip()
		jumper = self.obj
		# check here if location is a connect point before moving
		prev_location = jumper.location

		if jumper.move_to(destination, quiet=True, emit_to_obj=jumper):
			jumper.emote("has disconnected", receivers=prev_location.contents, exclude=jumper, action_type="move")
			jumper.emote("has connected", receivers=destination.contents, exclude=jumper, action_type="move")
			jumper.msg("Jumped to %s." % destination)


class AvatarCmdSet(CmdSet):
	def at_cmdset_creation(self):
		self.add(CmdNetLogout())
#		self.add(CmdNetHome())
		self.add(CmdNetJump())



class NetCharacter(Character):
	"""
	Base typeclass for online avatars.
	"""
	def at_object_creation(self):
		super().at_object_creation()
		self.cmdset.add(AvatarCmdSet, persistent=True)
		self.cmdset.add(SoftwareCmdSet, persistent=True)
		if not self.scripts.get('gearbook'):
			self.scripts.add(GearHandler)

	# TODO: make this not a puppet hook
	def at_post_puppet(self, **kwargs):
		self.msg(f"\nYou log in as |c{self.name}|n.\n")
		self.msg((self.at_look(self.location), {"type": "look"}), options=None)

		self.location.msg_contents("$You() has connected.", exclude=[self], from_obj=self)

	def at_post_unpuppet(self, account, session=None, **kwargs):
		# move the character back to the account's login room
		self.location = self.home
		self.location.at_object_receive(
			self, None
		)  # and trigger the location's reception hook.

	def get_display_name(self, looker, **kwargs):
		# TODO: add identification check and processing
		return self.sdesc.get()

	def basetype_setup(self):
		"""
		Setup character-specific security.
		"""
		BaseObject.basetype_setup(self)
		self.locks.add(
			";".join(
				[
					"get:false()",
					"teleport:perm(Admin)",
					"teleport_here:perm(Admin)",
				]
			)  # noone can pick up the character
		)  # no commands can be called on character from outside
