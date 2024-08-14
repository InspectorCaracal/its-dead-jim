from string import punctuation

from evennia.commands.cmdset import CmdSet
from evennia.utils import iter_to_str

from core.commands import Command
from core.ic.behaviors import NoSuchBehavior

from data.socials import NO_TARGET, WITH_TARGET, ALL_SOCIALS
from utils.table import EvColumn, EvTable


class CmdSocials(Command):
	"""
	Special Emotes

	Here's the help section for socials.
	"""
	key = "socials"
	aliases = ALL_SOCIALS
	locks = "cmd:all()"
	help_category = 'Roleplay'
	#	arg_regex = r"|$"
	free = True

	def get_help(self, caller, cmdset):
		social_keys = sorted(ALL_SOCIALS)
		cols_list = []
		max_len = int(len(social_keys) / 6)
		cols_list = []
		start = 0
		while start < len(social_keys):
			cols_list.append(EvColumn(*social_keys[start:start+max_len]))
			start += max_len

		table = EvTable(table = cols_list, border="none")
		helpfile = "The full list of all built-in emotes."
		helpfile += f"\n\nExample:\n  |g> laugh|n\n  {caller.name} laughs.\n\n"
		helpfile += str(table)
		return str(helpfile)
		

	def func(self):
		caller = self.caller
		target = None
		if self.cmdstring == self.key:
			self.caller.execute_cmd('help socials')
			return

		social = self.cmdstring
		target_str = ""

		allow = True

		if self.args:
			search_term = self.args.strip()
			# targetted emote
			if social in WITH_TARGET:
				emote = WITH_TARGET[social]
				result = caller.search(search_term, quiet=True)
				if len(result) == 0:
					caller.msg(f"You can't find $h({search_term}).")
					return
				elif len(result) > 1:
					caller.multimatch_msg(search_term, result)
					index = yield ("Enter a number (or $h(c) to cancel):")
					target = caller.process_multimatch(index, result)
				else:
					target = result[0]
				if not target:
					return
				# allow = target.at_pre_social(caller, social)
				target_str = target.sdesc.get(strip=True)
			elif social in NO_TARGET:
				emote = NO_TARGET[social]
			else:
				caller.msg("Nothing happens.")
				return

		else:
			# untargetted emote
			if social in NO_TARGET:
				emote = NO_TARGET[social]
			else:
				caller.msg("Nothing happens.")
				return

		emote = emote.format(target=target_str)
		caller.emote(emote)
		if target:
			target.on_socialized(caller, social)

		# i can't remember why i had this "allow" thing in here so i've removed it for now
		# if allow:
		# 	caller.emote(emote)
		# else:
		# 	self.msg(f"You cannot use $h('{social}') at $h({target_str})")


# TODO: implement this properly, along with ((think quotes))
class CmdThink(Command):
	"""
	Speak as your character

	Usage:
	  think <message>

	Talk to those in your current location.
	"""

	key = "think"
	#	aliases = ()
	locks = "cmd:all()"
	arg_regex = ""
	free = True
	help_category = "Roleplay"
	log = 'emotes'

	def func(self):
		caller = self.caller

		if not self.args:
			caller.msg("Think what?")
			return

		if self.cmdstring not in '"\'':
			verb = self.cmdstring
		else:
			verb = "say"

		# calling the speech modifying hook
		speech = caller.at_pre_say(self.args.strip(), verb=verb)

		if verb in ("yell", "shout",):
			exits = caller.location.contents_get(content_type="exit")
			for ex in exits:
				if ex.destination:
					ex.destination.msg_contents(f"Someone is {verb}ing nearby.")
		caller.emote(speech, anonymous_add=None)


class CmdSay(Command):
	"""
	Speak as your character

	Usage:
	  say <message>

	Talk to those in your current location.

	Along with the simple speech, you can preface your say with a phrase in
	parentheses to include it first, for actions.

	Example:
		say (with a bow) You've bested me again!

	Example output:
		With a bow, Monty says, "You've bested me again!"
	"""

	key = "say"
	aliases = ('"', "'", "whisper", "yell", "shout",)
	locks = "cmd:all()"
	arg_regex = ""
	free = True
	help_category = "Roleplay"
	log = 'emotes'

	def func(self):
		caller = self.caller

		if not self.args:
			caller.msg("Say what?")
			return

		if self.cmdstring not in '"\'':
			verb = self.cmdstring
		else:
			verb = "say"

		args = self.args.strip()
		if args[0] == "(" and ")" in args:
			prefix, args = args[1:].split(")", maxsplit=1)
		else:
			prefix = None

		# calling the speech modifying hook
		speech = caller.at_pre_say(args, verb=verb, prefix=prefix)

		if verb in ("yell", "shout",):
			exits = caller.location.contents_get(content_type="exit")
			for ex in exits:
				if ex.destination:
					ex.destination.msg_contents(f"Someone is {verb}ing nearby.")
		# TODO: pass in a volume here instead of the above destination check
		caller.emote(speech, anonymous_add=None)


class CmdSayto(Command):
	"""
	speak as your character

	Usage:
	  say to <player>: <message>

	Talk to those in your current location.
	"""

	key = "say to"
	aliases = ['sayto', 'say @', 'whisper to', 'whisper @']
	locks = "cmd:all()"
	arg_regex = ""
	free = True
	help_category = "Roleplay"
	log = 'emotes'

	def func(self):
		caller = self.caller

		if not self.args:
			caller.msg("Say what?")
			return

		try:
			target, speech = self.args.strip().split(':', maxsplit=1)
		except:
			caller.msg('Usage: say to <target>: <speech>')
			return

		targets = yield from self.find_targets(target)
		if not targets:
			return
		target = targets[0]

		speech = speech.strip()
		whisper = self.cmdstring.startswith("whisper")
		# calling the speech modifying hook
		emote = caller.at_pre_say(speech, target=target, whisper=whisper)

		if whisper:
			caller.emote(emote, recievers=[caller, target], anonymous_add=None)
			caller.emote(f"@Me whispers something to @{target.sdesc.get()}.", exclude=[caller, target])
		else:
			caller.emote(emote, include=[target], anonymous_add=None)
		
		target.on_spoken_to(caller, speech, whisper=whisper)


class CmdEmote(Command):
	"""
	Emote an action.

	Usage:
	  emote text

	Examples:
	  emote @Me looks around.
	  emote In a flurry of action, @me attacks @tall man with his sword.
	  emote "Hello", @me says.

	Describes an event in the world. This allows the use of @character
	markers to reference the short descs or recognized names of others in
	the room. Text in quotes such as "hello" will be recognized as speech.
	"""

	key = "emote"
	aliases = [":"]
	locks = "cmd:all()"
	arg_regex = ""
	help_category = "Roleplay"
	log = 'emotes'

	def func(self):
		"Perform the emote."
		if not self.args:
			self.caller.msg("Nothing happens.")
		else:
			emote = self.args.strip()
			tail = ''
			if emote.endswith(("'", '"')):
				tail = emote[-1]
				emote = emote[:-1]
			if not emote.endswith((".", "?", "!")):
				emote += "."
			emote += tail
			self.caller.emote(emote, anonymous_add="first", freeform=True)


class SocialCmdSet(CmdSet):
	key = "Social CmdSet"
	def at_cmdset_creation(self):
		super().at_cmdset_creation()

		self.add(CmdSay)
		self.add(CmdSayto)
		# self.add(CmdThink)
		self.add(CmdEmote)
		self.add(CmdSocials)
