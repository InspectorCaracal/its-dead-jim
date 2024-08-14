import types
from django.test import TestCase
import evennia
from django.conf import settings
from mock import MagicMock, Mock, patch
from evennia.commands.command import InterruptCommand
from evennia.accounts.models import AccountDB
from evennia.utils.idmapper.models import flush_cache
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest, _RE_STRIP_EVMENU

from server.conf.serversession import ServerSession
from utils.colors import strip_ansi

#oh yikes
from server.conf.at_server_startstop import at_server_init
at_server_init()

def undelay(time, func, *args, **kwargs):
	func(*args, **kwargs)
	


class NexusTest(EvenniaTest):
	player_typeclass = settings.PLAYER_CHARACTER_TYPECLASS

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
	
	def assertInteractiveResult(self, generator_func, expected):
		"""
		Assert that the result of interactive function `func` is the expected value
		"""
		with self.assertRaises(StopIteration) as context:
			while generator_func:
				next(generator_func)
		self.assertEquals(context.exception.value, expected)		

	def validate_msg(self, message, wanted):
		"""
		Verify that the received message matches the wanted message

		This handles str vs tuples and also stripping of markup for ease of comparison and readability
		"""
		if type(message) is str:
			message = strip_ansi(message)
		else:
			message = strip_ansi(message[0])
		
		return message.startswith(wanted)

	@patch('utils.timing.delay', new=undelay)
	def create_player(self, key="Player"):
		"""creates a new player character object"""
		player = create.create_object(typeclass=self.player_typeclass, key=key)
		player.features.set('build', persona='person')
		player.permissions.add('player')
		return player

	def create_character(self, key="Char"):
		"""creates a new generic character object"""
		chara = create.create_object(typeclass=self.character_typeclass, key=key)
		chara.features.add('build', format="{persona}", persona='person')
		chara.sdesc.add(['build persona'])
		chara.permissions.add('player')
		return chara

	def create_object(self, key="something"):
		"""creates a new Thing object"""
		return create.create_object(typeclass=self.object_typeclass, key=key)

	def create_account(self, key="TestAccount", permissions=None):
		acct_num = AccountDB.objects.all().count()
		account = create.create_account(
			key + str(acct_num),
			email="test@test.com",
			password="testpassword",
			typeclass=self.account_typeclass,
		)

		permissions = permissions if permissions else ['player']
		for permission in permissions:
			account.permissions.add(permission)
		return account
	
	def create_room(self, key="A room"):
		return create.create_object(typeclass=self.room_typeclass, key=key)

	def setup_session(self, account):
		dummysession = ServerSession()
		dummysession.init_session("telnet", ("localhost", "testmode"), evennia.SESSION_HANDLER)
		dummysession.sessid = 1
		evennia.SESSION_HANDLER.portal_connect(
			dummysession.get_sync_data()
		)  # note that this creates a new Session!
		session = evennia.SESSION_HANDLER.session_from_sessid(1)  # the real session
		evennia.SESSION_HANDLER.login(session, account, testmode=True)
		self.session = session

	def setUp(self):
		"""
		we do NOT want to use the upstream setUp!
		"""
		pass

	def player_setup(self, puppet=False):
		self.backups = (
			evennia.SESSION_HANDLER.data_out,
			evennia.SESSION_HANDLER.disconnect,
		)
		evennia.SESSION_HANDLER.data_out = Mock()
		evennia.SESSION_HANDLER.disconnect = Mock()
		self.account = self.create_account()
		self.setup_session(self.account)
		if puppet:
			if room := getattr(self, 'room', None):
				puppet.location = room
			session = self.session
			puppet.sessions.add(session)
			puppet.account = self.account
			session.puid = puppet.id
			session.puppet = puppet

	def tearDown(self):
		if hasattr(self, 'backups'):
			flush_cache()
			try:
				evennia.SESSION_HANDLER.data_out = self.backups[0]
				evennia.SESSION_HANDLER.disconnect = self.backups[1]
			except AttributeError as err:
				raise AttributeError(
					f"{err}: Teardown error. If you overrode the `setUp()` method "
					"in your test, make sure you also added `super().setUp()`!"
				)

			del evennia.SESSION_HANDLER[self.session.sessid]
			if hasattr(self, "account"):
				self.account.delete()
			TestCase.tearDown(self)

@patch("evennia.server.portal.portal.LoopingCall", new=MagicMock())
class NexusCommandTest(NexusTest):
	"""
	Mixin to add to a test in order to provide the `.call` helper for
	testing the execution and returns of a command.

	Tests a Command by running it and comparing what messages it sends with
	expected values. This tests without actually spinning up the cmdhandler
	for every test, which is more controlled.

	Example:
	::

		from commands.echo import CmdEcho

		class MyCommandTest(EvenniaTest, CommandTestMixin):

			def test_echo(self):
				'''
				Test that the echo command really returns
				what you pass into it.
				'''
				self.call(MyCommand(), "hello world!",
						  "You hear your echo: 'Hello world!'")

	"""

	OOC = False

	# formatting for .call's error message
	_ERROR_FORMAT = """
=========================== Wanted message ===================================
{expected_msg}
=========================== Returned message =================================
{returned_msg}
==============================================================================
""".rstrip()

	def setUp(self):
		"""A command test always requires a PlayerCharacter caller in a location"""
		# self.player_setup()
		if not self.OOC:
			self.room = self.create_room()
			self.caller = self.create_player(key="Caller")
			self.player_setup(self.caller)
		else:
			self.player_setup()
			self.caller = self.account

	def call(
		self,
		cmdobj,
		input_args,
		msg=None,
		cmdset=None,
		noansi=True,
		caller=None,
		receiver=None,
		cmdstring=None,
		obj=None,
		inputs=None,
		raw_string=None,
	):
		"""
		Test a command by assigning all the needed properties to a cmdobj and
		running the sequence. The resulting `.msg` calls will be mocked and
		the text= calls to them compared to a expected output.

		Args:
			cmdobj (Command): The command object to use.
			input_args (str): This should be the full input the Command should
				see, such as 'look here'. This will become `.args` for the Command
				instance to parse.
			msg (str or dict, optional): This is the expected return value(s)
				returned through `caller.msg(text=...)` calls in the command. If a string, the
				receiver is controlled with the `receiver` kwarg (defaults to `caller`).
				If this is a `dict`, it is a mapping
				`{receiver1: "expected1", receiver2: "expected2",...}` and `receiver` is
				ignored. The message(s) are compared with the actual messages returned
				to the receiver(s) as the Command runs. Each check uses `.startswith`,
				so you can choose to only include the first part of the
				returned message if that's enough to verify a correct result. EvMenu
				decorations (like borders) are stripped and should not be included. This
				should also not include color tags unless `noansi=False`.
				If the command returns texts in multiple separate `.msg`-
				calls to a receiver, separate these with `|` if `noansi=True`
				(default) and `||` if `noansi=False`. If no `msg` is given (`None`),
				then no automatic comparison will be done.
			cmdset (str, optional): If given, make `.cmdset` available on the Command
				instance as it runs. While `.cmdset` is normally available on the
				Command instance by default, this is usually only used by
				commands that explicitly operates/displays cmdsets, like
				`examine`.
			noansi (str, optional): By default the color tags of the `msg` is
				ignored, this makes them significant. If unset, `msg` must contain
				the same color tags as the actual return message.
			caller (Object or Account, optional): By default `self.char1` is used as the
				command-caller (the `.caller` property on the Command). This allows to
				execute with another caller, most commonly an Account.
			receiver (Object or Account, optional): This is the object to receive the
				return messages we want to test. By default this is the same as `caller`
				(which in turn defaults to is `self.char1`). Note that if `msg` is
				a `dict`, this is ignored since the receiver is already specified there.
			cmdstring (str, optional): Normally this is the Command's `key`.
				This allows for tweaking the `.cmdname` property of the
				Command`.  This isb used for commands with multiple aliases,
				where the command explicitly checs which alias was used to
				determine its functionality.
			obj (str, optional): This sets the `.obj` property of the Command - the
				object on which the Command 'sits'. By default this is the same as `caller`.
				This can be used for testing on-object Command interactions.
			inputs (list, optional): A list of strings to pass to functions that pause to
				take input from the user (normally using `@interactive` and
				`ret = yield(question)` or `evmenu.get_input`). Each  element of the
				list will be passed into the command as if the user answered each prompt
				in that order.
			raw_string (str, optional): Normally the `.raw_string` property  is set as
				a combination of your `key/cmdname` and `input_args`. This allows
				direct control of what this is, for example for testing edge cases
				or malformed inputs.

		Returns:
			str or dict: The message sent to `receiver`, or a dict of
				`{receiver: "msg", ...}` if multiple are given. This is usually
				only used with `msg=None` to do the validation externally.

		Raises:
			AssertionError: If the returns of `.msg` calls (tested with `.startswith`) does not
				match `expected_input`.

		Notes:
			As part of the tests, all methods of the Command will be called in
			the proper order:

			- cmdobj.at_pre_cmd()
			- cmdobj.parse()
			- cmdobj.func()
			- cmdobj.at_post_cmd()

		"""
		# The `self.char1` is created in the `EvenniaTest` base along with
		# other helper objects like self.room and self.obj
		caller = caller if caller else self.caller
		cmdobj.caller = caller
		cmdobj.cmdname = cmdstring if cmdstring else cmdobj.key
		cmdobj.raw_cmdname = cmdobj.cmdname
		cmdobj.cmdstring = cmdobj.cmdname  # deprecated
		cmdobj.args = input_args
		cmdobj.cmdset = cmdset
		cmdobj.session = evennia.SESSION_HANDLER.session_from_sessid(1)
		cmdobj.account = self.account
		cmdobj.raw_string = raw_string if raw_string is not None else cmdobj.key + " " + input_args
		cmdobj.obj = obj or (caller if caller else self.char1)
		inputs = inputs or []

		# set up receivers
		receiver_mapping = {}
		if isinstance(msg, dict):
			# a mapping {receiver: msg, ...}
			receiver_mapping = {
				recv: str(msg).strip() if msg else None for recv, msg in msg.items()
			}
		else:
			# a single expected string and thus a single receiver (defaults to caller)
			receiver = receiver if receiver else caller
			receiver_mapping[receiver] = str(msg).strip() if msg is not None else None

		unmocked_msg_methods = {}
		for receiver in receiver_mapping:
			# save the old .msg method so we can get it back
			# cleanly  after the test
			unmocked_msg_methods[receiver] = receiver.msg
			# replace normal `.msg` with a mock
			receiver.msg = Mock()

		# Run the methods of the Command. This mimics what happens in the
		# cmdhandler. This will have the mocked .msg be called as part of the
		# execution. Mocks remembers what was sent to them so we will be able
		# to retrieve what was sent later.
		try:
			with patch('base_systems.actions.queue.delay') as mock_delay:
				if cmdobj.at_pre_cmd():
					return
				cmdobj.parse()
				ret = cmdobj.func()

				# handle func's with yield in them (making them generators)
				if isinstance(ret, types.GeneratorType):
					while True:
						try:
							inp = inputs.pop() if inputs else None
							if inp:
								try:
									# this mimics a user's reply to a prompt
									ret.send(inp)
								except TypeError:
									next(ret)
									ret = ret.send(inp)
							else:
								# non-input yield, like yield(10). We don't pause
								# but fire it immediately.
								next(ret)
						except StopIteration:
							break

				cmdobj.at_post_cmd()

				for call_args in mock_delay.call_args_list:
					undelay(*call_args[0], **call_args[1])

		except StopIteration:
			pass
		except InterruptCommand:
			pass

			for inp in inputs:
				# if there are any inputs left, we may have a non-generator
				# input to handle (get_input/ask_yes_no that uses a separate
				# cmdset rather than a yield
				caller.execute_cmd(inp)

		# At this point the mocked .msg methods on each receiver will have
		# stored all calls made to them (that's a basic function of the Mock
		# class). We will not extract them and compare to what we expected to
		# go to each receiver.

		returned_msgs = {}
		for receiver, expected_msg in receiver_mapping.items():
			# get the stored messages from the Mock with Mock.mock_calls.
			stored_msg = []
			for name, args, kwargs in receiver.msg.mock_calls:
				if args and args[0]:
					stored_msg.append(args[0])
				elif text := kwargs.get('text'):
					stored_msg.append(text)
			# we can return this now, we are done using the mock
			receiver.msg = unmocked_msg_methods[receiver]

			# Get the first element of a tuple if msg received a tuple instead of a string
			stored_msg = [
				str(smsg[0]) if isinstance(smsg, tuple) else str(smsg) for smsg in stored_msg
			]
			if expected_msg is None:
				# no expected_msg; just build the returned_msgs dict

				returned_msg = "\n".join(str(msg) for msg in stored_msg)
				returned_msgs[receiver] = strip_ansi(returned_msg).strip()
			else:
				# compare messages to expected

				# set our separator for returned messages based on parsing ansi or not
				msg_sep = "|" if noansi else "||"

				# We remove Evmenu decorations since that just makes it harder
				# to write the comparison string. We also strip ansi before this
				# comparison since otherwise it would mess with the regex.
				returned_msg = msg_sep.join(
					_RE_STRIP_EVMENU.sub("", strip_ansi(mess))
					for mess in stored_msg
				).strip()

				# this is the actual test
				if expected_msg == "" and returned_msg or not returned_msg.startswith(expected_msg):
					# failed the test
					raise AssertionError(
						self._ERROR_FORMAT.format(
							expected_msg=expected_msg, returned_msg=returned_msg
						)
					)
				# passed!
				returned_msgs[receiver] = returned_msg

		if len(returned_msgs) == 1:
			return list(returned_msgs.values())[0]
		return returned_msgs

