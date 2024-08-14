from evennia import CmdSet, Command, default_cmds
from evennia.utils import logger
from django.conf import settings
from typeclasses.characters import NetCharacter

class CmdNetConnect(Command):
	key = "uplink"
	aliases = ("login","logon")
	locks = "cmd:pperm(Player)"

	def func(self):
		account = self.caller.account
		sessions = self.caller.sessions.get()
		session = sessions[len(sessions)-1]
		avatar = self.args.strip()
		old_char = account.db.offline_char
		account.db._last_puppet = old_char
		new_character = None
		character_candidates = []

		if not self.args:
			self.msg("Usage: logon <avatar>")
			return
		else:
			# argument given
			if account.db._playable_characters:
				character_candidates = [ obj for obj in account.db._playable_characters if avatar in obj.key]

		# handle possible candidates
		if not character_candidates:
			self.msg("%s is not a valid avatar choice." % avatar)
			if account.db._playable_characters:
				self.msg(
					"Available avatars:\n %s"
					% ", ".join("%s" % obj.key for obj in account.db._playable_characters if obj != self.caller)
				)
			return
		if len(character_candidates) > 1:
			self.msg(
				"Multiple avatars match the input name:\n %s"
				% ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in character_candidates)
			)
			return
		else:
			new_character = character_candidates[0]

			try:
				account.unpuppet_object(session)

			except RuntimeError as exc:
				self.msg("|rCould not log in from |c%s|n: %s" % (old_char, exc))

			# do the puppet puppet
			try:
				account.puppet_object(session, new_character)
				account.db._last_puppet = new_character
				logger.log_sec(
					"Puppet Success: (Caller: %s, Target: %s, IP: %s)."
					% (account, new_character, self.session.address)
				)
			except RuntimeError as exc:
				self.msg("|rYou cannot log in to |C%s|n: %s" % (new_character.name, exc))
				logger.log_sec(
					"Puppet Failed: %s (Caller: %s, Target: %s, IP: %s)."
					% (exc, account, new_character, self.session.address)
				)

class CmdAvatarList(Command):
	key = "list avatars"
	aliases = ("avatars","list avs","avs",)
	locks = "cmd:pperm(Player)"

	def func(self):
		account = self.caller.account
		character_candidates = account.db._playable_characters

		if len(character_candidates) > 1:
			self.msg(
				"Available avatars:\n %s"
				% ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in character_candidates if obj != self.caller)
			)
			return
		else:
			self.msg("No avatars available. Please create one with |Cnewavatar <charname>|n")


# this should use the unix command contrib i think
class CmdAvatarCreate(default_cmds.MuxCommand):
	"""
	create a new net avatar
	Usage:
	  newavatar <charname> [= desc]

	Create a new character, optionally giving it a description. You
	may use upper-case letters in the name - you will nevertheless
	always be able to access your character using lower-case letters
	if you want.
	"""

	key = "newavatar"
	locks = "cmd:pperm(Player)"
	help_category = "General"

	def func(self):
		account = self.caller.account

		"""create the new character"""
		if not self.args:
			self.msg("Usage: newavatar <av_name> [= description]")
			return
		key = self.lhs
		desc = self.rhs

		charmax = settings.MAX_NR_CHARACTERS

		if not account.is_superuser and (
			account.db._playable_characters and len(account.db._playable_characters) >= charmax
		):
			plural = "" if charmax == 1 else "s"
			self.msg(f"You may only create a maximum of {charmax} character{plural}.")
			return

		from evennia.objects.models import ObjectDB
		typeclass = "typeclasses.characters.NetCharacter"

		if ObjectDB.objects.filter(db_typeclass_path=typeclass, db_key__iexact=key):
			# check if this Character already exists. Note that we are only
			# searching the base character typeclass here, not any child
			# classes.
			self.msg("|rAn avatar named '|w%s|r' already exists.|n" % key)
			return

		# create the character
		from evennia.utils.create import create_object
		default_home = account.db.login_room
		permissions = settings.PERMISSION_ACCOUNT_DEFAULT
		new_character = create_object(
			typeclass, key=key, location=default_home, home=default_home, permissions=permissions
		)
		# only allow creator (and developers) to puppet this char
		new_character.locks.add(
			"puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer);delete:id(%i) or perm(Admin)"
			% (new_character.id, account.id, account.id)
		)
		account.db._playable_characters.append(new_character)
		if desc:
			new_character.db.desc = desc
		elif not new_character.db.desc:
			new_character.db.desc = "This is the default virtual avatar."
		self.msg(
			"Created new avatar %s. You can now |wlogon %s|n to enter the net with this avatar."
			% (new_character.key, new_character.key)
		)
		logger.log_sec(
			"Character Created: %s (Caller: %s, IP: %s)."
			% (new_character, account, self.session.address)
		)


class DeckCmdSet(CmdSet):
	def at_cmdset_creation(self):
		self.add(CmdNetConnect())
		self.add(CmdAvatarCreate())
		self.add(CmdAvatarList())



class DeckObject(Object):
	"""
	The object typeclass that allows you to enter VR and load/program software.
	"""
	def at_object_creation(self):
		super().at_object_creation()
		self.cmdset.add_default(DeckCmdSet)
		self.cmdset.add(GearCmdSet, persistent=True)
