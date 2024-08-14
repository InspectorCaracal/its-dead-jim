"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

		GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest, CharactersHandler
from evennia.utils.utils import is_iter, lazy_property, iter_to_str
from evennia.utils.dbserialize import pack_dbobj

from base_systems.characters.players import PlayerCharacter

from django.conf import settings
_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS
_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

from utils.funcparser_callables import FUNCPARSER_CALLABLES as LOCAL_FUNCPARSER_CALLABLES
from evennia.utils.funcparser import FuncParser
parser = FuncParser(LOCAL_FUNCPARSER_CALLABLES)


class Account(DefaultAccount):
	"""
	This class describes the actual OOC account (i.e. the user connecting
	to the MUD). It does NOT have visual appearance in the game world (that
	is handled by the character which is connected to this). Comm channels
	are attended/joined using this object.

	It can be useful e.g. for storing configuration options for your game, but
	should generally not hold any character-related info (that's best handled
	on the character level).

	Can be set using BASE_ACCOUNT_TYPECLASS.


	* available properties

	 key (string) - name of account
	 name (string)- wrapper for user.username
	 aliases (list of strings) - aliases to the object. Will be saved to database as AliasDB entries but returned as strings.
	 dbref (int, read-only) - unique #id-number. Also "id" can be used.
	 date_created (string) - time stamp of object creation
	 permissions (list of strings) - list of permission strings

	 user (User, read-only) - django User authorization object
	 obj (Object) - game object controlled by account. 'character' can also be used.
	 sessions (list of Sessions) - sessions connected to this account
	 is_superuser (bool, read-only) - if the connected user is a superuser

	* Handlers

	 locks - lock-handler: use locks.add() to add new lock strings
	 db - attribute-handler: store/retrieve database attributes on this self.db.myattr=val, val=self.db.myattr
	 ndb - non-persistent attribute handler: same as db but does not create a database entry when storing data
	 scripts - script-handler. Add new scripts to object with scripts.add()
	 cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
	 nicks - nick-handler. New nicks with nicks.add().

	* Helper methods

	 msg(text=None, **kwargs)
	 execute_cmd(raw_string, session=None)
	 search(ostring, global_search=False, attribute_name=None, use_nicks=False, location=None, ignore_errors=False, account=False)
	 is_typeclass(typeclass, exact=False)
	 swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
	 access(accessing_obj, access_type='read', default=False)
	 check_permstring(permstring)

	* Hook methods (when re-implementation, remember methods need to have self as first arg)

	 basetype_setup()
	 at_account_creation()

	 - note that the following hooks are also found on Objects and are
		 usually handled on the character level:

	 at_init()
	 at_cmdset_get(**kwargs)
	 at_first_login()
	 at_post_login(session=None)
	 at_disconnect()
	 at_message_receive()
	 at_message_send()
	 at_server_reload()
	 at_server_shutdown()

	"""
	@property
	def characters(self):
		return BetterCharacters(self)

	def at_look(self, target=None, session=None, **kwargs):
		"""
		Called when this object executes a look. It allows to customize
		just what this means.
		Args:
			target (Object or list, optional): An object or a list
				objects to inspect.
			session (Session, optional): The session doing this look.
			**kwargs (dict): Arbitrary, optional arguments for users
				overriding the call (unused by default).
		Returns:
			look_string (str): A prepared look string, ready to send
				off to any recipient (usually to ourselves)
		"""

		if target and not is_iter(target):
			# single target - just show it
			if hasattr(target, "return_appearance"):
				return target.return_appearance(self)
			else:
				return _("{target} has no in-game appearance.").format(target=target)
		else:
			if session:
				mxp = session.protocol_flags.get('MXP', True)
			else:
				mxp = True
			# list of our characters
			characters = self.characters.all()
			sessions = self.sessions.all()
			if not sessions:
				# no sessions, nothing to report
				return ""
			is_su = self.is_superuser

			# text shown when looking in the ooc area
			result = [f"Logged in as $h({self.key})\n"]

			nsess = len(sessions)
			result.append(
				nsess == 1
				and "|wConnected session:|n"
				or f"|wConnected sessions ({nsess}):|n"
			)
			for isess, sess in enumerate(sessions):
				csessid = sess.sessid
				addr = "%s (%s)" % (
					sess.protocol_key,
					isinstance(sess.address, tuple) and str(sess.address[0]) or str(sess.address),
				)
				result.append(
					" %s %s"
					% (
						session
						and session.sessid == csessid
						and "|w* %s|n" % (isess + 1)
						or "  %s" % (isess + 1),
						addr,
					)
				)
			result.append("\n |lchelp|lthelp|le - more commands")
			# result.append(" |wpublic <Text>|n - talk on public channel")

			charmax = _MAX_NR_CHARACTERS

			if session:
				screen_width = session.protocol_flags.get("SCREENWIDTH", {0: _MAX_TEXT_WIDTH})[0]
			else:
				screen_width = _MAX_TEXT_WIDTH
			result.append("-" * screen_width)
			# result.append(
			# "\n |wdelete character <name>|n - delete a character (cannot be undone!)"
			# )
			s = len(characters) > 1 and "s" or ""
			# result.append("\n |wplay <character>|n - enter the game (|wlog out|n to return here)")
			avail = f"Available character{s} ({len(characters)}/{'unlimited' if is_su else charmax}):\n"
			if charmax > 1 or is_su:
				result.append(avail)

			for char in characters:
				if char.db.chargen_step:
					result.append(f"  |lcnew character|lt|Yresume character creation|n|le")
					continue
				csessions = char.sessions.all()
				if csessions:
					for sess in csessions:
						# character is already puppeted
						sid = sess in sessions and sessions.index(sess) + 1
						if sess and sid:
							result.append(
								f"  |G{char.key}|n (being played by you in another window)"
							)
						else:
							result.append(
								f"  |R{char.key}|n (being played by someone else)"
							)
				else:
					# character is "free to puppet"
					archetype = char.archetype
					result.append(f"  |lcplay {char.key}|lt{char.key}|le ({archetype.desc if archetype else 'mundane'})")

			if not mxp:
				result.append(f"\n  |wplay <character>|n to enter the game")

			if is_su or len(characters) < charmax:
				result.append("\n  |lcnew character|ltnew character|le" + (" to create a new character" if not mxp else ""))

			#			look_string = ("-" * 68) + "\n" + "".join(result) + "\n" + ("-" * 68)
			look_string = "\n".join(result)
			return (look_string, {'target': 'location', "clear": True})

	def channel_msg(self, message, channel, senders=None, **kwargs):
		"""
		This performs the actions of receiving a message to an un-muted
		channel.

		Args:
			message (str): The message sent to the channel.
			channel (Channel): The sending channel.
			senders (list, optional): Accounts or Objects acting as senders.
				For most normal messages, there is only a single sender. If
				there are no senders, this may be a broadcasting message or
				similar.
			**kwargs: These are additional keywords originally passed into
				`Channel.msg`.

		Notes:
			Before this, `Channel.at_pre_channel_msg` will fire, which offers a way
			to customize the message for the receiver on the channel-level.

		"""
		self.msg(
			text=(message, {"from_channel": channel.key, 'target': 'channels'}),
			from_obj=senders,
			options={"from_channel": channel.key},
		)

	def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
		rest = None
		if is_iter(text):
			message, *rest = text
		else:
			message = text

		message = parser.parse(message, caller=from_obj, receiver=self)

		if rest:
			text = (message, *rest)
		else:
			text = message
		
		super().msg(text=text, from_obj=from_obj, session=session, options=options, **kwargs)


class Guest(DefaultGuest):
	"""
	This class is used for guest logins. Unlike Accounts, Guests and their
	characters are deleted after disconnection.
	"""

	pass


class BetterCharacters(CharactersHandler):
	"""blugh"""
	def __init__(self, account):
		self.account = account

	def add(self, character):
		character.db.account = self.account

	def remove(self, character):
		del character.db.account

	def all(self):
		return PlayerCharacter.objects.filter(db_attributes__db_key='account',db_attributes__db_value=pack_dbobj(self.account))
