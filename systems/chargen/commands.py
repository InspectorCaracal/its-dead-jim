import string
from random import choices

from django.conf import settings

from evennia import default_cmds
from evennia.utils import create, logger, search
from evennia.objects.models import ObjectDB

#from evennia.utils.evmenu import EvMenu
from utils.menus import FormatEvMenu

from core.commands import Command

_CHARACTER_TYPECLASS = getattr(settings, "PLAYER_CHARACTER_TYPECLASS", settings.BASE_CHARACTER_TYPECLASS)
_CHARGEN_MENU = getattr(settings, "CHARGEN_MENU", None)


class CmdIC(Command):
	"""
	control an object you have permission to puppet

	Usage:
		play <character>

	Go in-character as a given Character.

	This will attempt to "become" a different object assuming you have
	the right to do so. Note that it's the ACCOUNT that puppets
	characters/objects and which needs to have the correct permission!
	"""
	key = "play"
	locks = "cmd:is_ooc()"
	aliases = ["puppet", "ic"]
	help_category = "General"

	def func(self):
		"""Don't allow puppeting unless the chargen_step attribute has been cleared."""
		caller = self.caller
		account = self.account
		session = self.session
		characters = list(account.characters)

		if not self.args:
			if len(characters) == 1:
				new_character = characters[0]
			else:
				caller.msg("Play who?")
				return

		else:
			if not (charlist := search.object_search(self.args, candidates=characters)):
				if account.locks.check_lockstring(account, "perm(Admin)"):
					charlist = [
							char
							for char in search.object_search(self.args)
							if char.access(account, "puppet")
						]

			# handle possible candidates
			if not charlist:
				self.msg("That is not a valid character choice.")
				return
			if len(charlist) > 1:
				self.multimatch_msg(self.args, charlist)
				index = yield ("Enter a number (or $h(c) to cancel):")
				new_character = self.process_multimatch(index, charlist)
				if not new_character:
					return
			else:
				new_character = charlist[0]

		if new_character.db.chargen_step:
			self.session.execute_cmd(f'new character')
		else:
			try:
				account.puppet_object(session, new_character)
				account.db._last_puppet = new_character
				logger.log_sec(
					f"Puppet Success: (Caller: {account}, Target: {new_character}, IP:"
					f" {self.session.address})."
				)
			except RuntimeError as exc:
				self.msg(f"|rYou cannot become |C{new_character.name}|n: {exc}")
				logger.log_sec(
					f"Puppet Failed: %s (Caller: {account}, Target: {new_character}, IP:"
					f" {self.session.address})."
				)


class CmdCharCreate(Command):
	"""
	Create a new character

	Begin creating a new character, or resume character creation for
	an existing in-progress character.

	You can stop character creation at any time and resume where
	you left off later.
	"""

	key = "new character"
	aliases = ("charcreate",)
	locks = "cmd:pperm(Player) and is_ooc()"
	help_category = "General"
	
	account_caller = True

	def func(self):
		"create the new character"
		if not _CHARGEN_MENU:
			self.msg("Character creation is not available yet, sorry!")
			return

		account = self.account
		session = self.session

		characters = account.characters
		# only one character should be in progress at a time, so we check for WIPs first
		in_progress = [chara for chara in characters if chara.db.chargen_step]

		if len(in_progress):
			# we're continuing chargen for a WIP character
			new_character = in_progress[0]
		else:
			# we're making a new character
			charmax = settings.MAX_NR_CHARACTERS

			if not account.is_superuser and (len(characters) >= charmax):
				plural = "" if charmax == 1 else "s"
				self.msg(f"You may only create a maximum of {charmax} character{plural}.")
				return

			# create the new character object, with default settings
			# start_location = ObjectDB.objects.get_id(settings.START_LOCATION)
			# TODO: define this to an in-game UID and use get_by_id
			default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
			permissions = settings.PERMISSION_ACCOUNT_DEFAULT
			# generate a randomized key so the player can choose a character name later
			key = "".join(choices(string.ascii_letters + string.digits, k=10))
			new_character = create.create_object(
				_CHARACTER_TYPECLASS,
				key=key,
				location=None,
				home=default_home,
				permissions=permissions,
			)
			# only allow creator (and developers) to puppet this char
			new_character.locks.add(
				f"puppet:pid({account.id}) or perm(Developer) or"
				f" pperm(Developer);delete:id({account.id}) or perm(Admin)"
			)
			# initalize the new character to the beginning of the chargen menu
			new_character.db.chargen_step = "menunode_welcome"
			new_character.db.account = account

		# set the menu node to start at to the character's last saved step
		startnode = new_character.db.chargen_step
		# attach the character to the session, so the chargen menu can access it
		session.new_char = new_character

		# this gets called every time the player exits the chargen menu
		def finish_char_callback(session, menu):
			char = session.new_char
			if char.db.chargen_step:
				# we've exited in the middle
				session.msg("Exited character creation.")
				account.execute_cmd('look', session=session)
			else:
				# this means character creation was completed - start playing!
				# execute the ic command to start puppeting the character
				account.execute_cmd("ic {}".format(char.key), session=session)
		
		FormatEvMenu(session, _CHARGEN_MENU, startnode=startnode, cmd_on_exit=finish_char_callback)
