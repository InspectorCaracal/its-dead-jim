
# System Info
				
from django.conf import settings
from evennia.commands import cmdhandler
from evennia.commands.cmdset import CmdSet
from evennia.commands.default.system import CmdAbout as CoreCmdAbout
from evennia.utils import iter_to_str, get_evennia_version
from core.accounts import Account
from core.commands import Command


def _generate_evennia_version_info():
	string = f"""\
 |cEvennia|n MU* development system

 |wEvennia version|n: {get_evennia_version()}
 |wHomepage|n:        https://evennia.com
 |wCode|n:            https://github.com/evennia/evennia
 |wGame listings|n:   https://games.evennia.com

 |wDiscord|n:    https://discord.gg/AJJpcRUhtF
 |wForum|n:      https://github.com/evennia/evennia/discussions
 |wLicence|n:    https://opensource.org/licenses/BSD-3-Clause
 |wMaintainer|n (2010-):   Griatch (griatch AT gmail DOT com)
 |wMaintainer|n (2006-10): Greg Taylor

""".rstrip()
	return string

from switchboard import GAME_VERSION

_EVENNIA_VERSION = _generate_evennia_version_info()


class CmdAboutEvennia(CoreCmdAbout):
	"""
	show Evennia info

	Usage:
	  about evennia

	View info about the underlying Evennia game engine.
	"""

	key = "@about evennia"
	aliases = ("@version evennia", "@evennia")

	def func(self):
		self.execute_cmd(f'help {self.key}')

	def get_help(self, *args):
		return _EVENNIA_VERSION
	
class CmdAbout(Command):
	"""
	show game version info

	Usage:
	  about

	View info about the current game version.
	"""

	key = "@about"
	aliases = ("@version",)
	locks = "cmd:all()"
	help_category = "System"

	def func(self):
		self.execute_cmd(f'help {self.key}')
	
	def get_help(self, caller, *args):
		string = """\
  $head({game_name}) v{version}

  $h(Website): {url}
  $h(Discord): {discord}
  $h(Forum):   {forum}
  $h(Devs):    {dev_team}
  $h(Staff):   {staff_team}
		""".rstrip()
		
		fkeys = {
			'game_name': settings.SERVERNAME,
			'version': GAME_VERSION,
			'url': "https://"+settings.SERVER_HOSTNAME,
			'discord': "N/A",
			'forum': "N/A",
			'dev_team': iter_to_str(self._get_devs(caller)) or "N/A",
			'staff_team': iter_to_str(self._get_staff(caller)) or "N/A",
		}
		
		string = string.format(**fkeys)
		return string
	
	def _get_devs(self, caller):
		devs = [acct.get_display_name(caller) for acct in Account.objects.all() if 'developer' in acct.permissions.all()]
		return list(devs)
	
	def _get_staff(self, caller):
		staff = [acct.get_display_name(caller) for acct in Account.objects.all() if 'admin' in acct.permissions.all()]
		return list(staff)


class CmdMultimatch(Command):
	key = cmdhandler.CMD_MULTIMATCH
	locks = "cmd:all()"
	auto_help = False

	def func(self):
		caller = self.caller

		match_opts = self.matches
		match_opts.sort(key=lambda y: y[0])
		match_cmds = []
		match_objects = [(mat[2], mat[0]) for mat in match_opts]
		self.multimatch_msg("command", match_objects, match_cmd=True)
		index = yield ("Enter a number or command (or $h(c) to cancel).")
		cmd = self.process_multimatch(index, match_opts, free_text=True)

		if cmd:
			if type(cmd) is str:
				self.execute_cmd(cmd)
			else:
				# cmd is (cmdstring, args, cmd object, etc.)
				self.execute_cmd(cmd[1], cmdobj=cmd[2], cmdobj_key=cmd[0])

from django.core.management import call_command
class CmdCollectStatic(Command):
	"""Update the cached web files, e.g. CSS"""
	key = "collectstatic"

	def func(self):
		self.msg("Running collecstatic...")
		call_command("collectstatic", interactive=False)
		self.msg("Done")

class SystemCmdSet(CmdSet):
	key = "System Commands"

	def at_cmdset_creation(self):
		self.add(CmdAbout)
		self.add(CmdAboutEvennia)
		self.add(CmdMultimatch)
		self.add(CmdCollectStatic)