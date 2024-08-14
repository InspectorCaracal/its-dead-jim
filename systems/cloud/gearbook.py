from evennia import DefaultScript, Command, CmdSet, InterruptCommand
from evennia.contrib.base_systems.unixcommand import UnixCommand

from .software import CmdRun

class GearCommand(Command):
	"""
	Runs gear scripts. I need a real help file here.
	"""
	key = "!"
	aliases = ()
	locks = "cmd:pperm(Player)"
	arg_regex = r".+"

	def func(self):
		args = self.args.strip().split()

		gearbook = self.caller.scripts.get("gearbook")
		if not gearbook:
			self.caller.msg("!! ERROR !!")
			return
		
		scrname = args[0]
		
		if script_data := gearbook.db.cmds.get(scrname,None):
			target = " ".join(args[1:]) if len(args) > 1 else None
			if target:
				searching = self.caller.search(target, quiet=True)
				if searching:
					target = searching

			self.target = target
			# parse the script attr
			lines = list([ line.strip().lower() for line in script_data['script'].splitlines() ])

			# TODO: rewrite this to use crafted animations
			on_use = script_data['on_use']
			self.caller.location.msg_contents(on_use)

			err = self.eval_script(lines)
			if not err:
				self.caller.msg("empty script")
			elif err < 0:
				# handle error
				self.caller.msg("error")
			else:
				# on success
				self.caller.msg("success")

		else:
			self.caller.msg("ERROR: %s not found" % scrname)

	def do_comp(self, a, b, comp, **mapping):
		"""
		valid comparisons:
		self (parses as the caller)
		target (parses as the target of the script)
		here (parses as the location of the caller)
		<string> (can only be compared to keywords)
		<string>,<string>,...,<string> (can only be used after "in")
		when keywords are used after "in", references a list of the object's contents
		"""
		target = self.target
		caller = self.caller
		
		mapping |= { "SELF": caller, "TARGET": target, "HERE": caller.location }
		
		if comp == "IN":
			if b in mapping:
				# TODO: revise to handle mapped variables
				b = mapping[b].contents
				if a in mapping:
					return mapping[a] in b
				else:
					return caller.search(a, candidates=b, quiet=True) > 0
			else:
				return any( [self.do_comp(a, item.strip(), "IS") for item in b.split(",")] )

		a = mapping.get(a, a)
		b = mapping.get(b, b)
		tf = comp == "IS"

		if type(a) is type(b):
			return (a == b) == tf
		
		# TODO: handle a or b being numbers

		aname = a if type(a) is str else a.name #a.get_display_name(caller)
		bname = b if type(b) is str else b.name #b.get_display_name(caller)
		return (aname == bname) == tf
		
	def eval_script(self, lines, **kwargs):
		if not lines: # received empty script
			return 0

		target = self.target
		caller = self.caller

		mapping = { "SELF": caller, "TARGET": target, "HERE": caller.location }

		i = 0
		while i < len(lines):
			line = lines[i].strip()
			i += 1
			match line.split():
				case ['IF', *args]:
					i = self.parse_block(args, lines, i, **kwargs)
					if i == -1:
						break # do error parsing here
				case ['RUN', *args]:
					caller.execute_cmd(" ".join(args))
				case ['ECHO', *args]:
					args = " ".join(args)
					args = mapping.get(args, kwargs.get(args, args))
					caller.msg(args)
				case ['SHOW', *args]:
					# TODO: redo this so that it's displaying crafted animations instead of free text
					args = " ".join(args)
					args = mapping.get(args, kwargs.get(args, args))
					caller.location.msg_contents(args)
				case ['SET', varname, 'TO', *args]:
					# TODO: allow you to save the results of a RUN command
					args = " ".join(args)
					try:
						args = float(args)
					except ValueError:
						args = mapping.get(args, args)
					kwargs[varname] = args
				case _:
					continue

		if i >= len(lines):
			return 1 # 1 means no error
		else:
			return -1 # -1 means error

	def parse_block(self, args, lines, start, **kwargs):
		target = self.target
		caller = self.caller
		
		endif = lines[start:].index("ENDIF")
		if endif < 0:
			return -1
		else:
			endif += start

		elsepos = lines[start:endif].index("ELSE")
		if elsepos > 0:
			elsepos += start
			do_then = lines[start+1:elsepos]
			do_else = lines[elsepos+1:endif]
		else:
			do_then = lines[start+1:endif]
			do_else = []

		match args:
			case ["RUN", *cmd]:
				result = self.run_cmd(" ".join(cmd))
			case [a, comp, b] if comp in ("IS", "NOT", "IN"):
				# equality check
				result = self.do_comp(a, b, comp, target, caller, **kwargs)
			case _:
				# invalid conditional
				return -1
		
		if result:
			err = self.eval_script(do_then, **kwargs)
		else:
			err = self.eval_script(do_else, **kwargs)
		
		if err < 0:
			return err
		else:
			return endif

	def run_cmd(self, cmdargs, **mapping):
		cmdobj = CmdRun()
		cmdobj.args = cmdargs
		try:
			cmdobj.parse()
		except InterruptCommand:
			return False
		
		modstring = cmdobj.opts.module
		tgt_string = cmdobj.opts.target
		if not modstring:
			return False

		# TODO: need a new way to check deck contents
		available = self.caller.db.deck.contents
		modules = caller.search(modstring, candidates=available, quiet=True)
		if len(modules) != 1:
			return False
		module = modules[0]

		target = self.target
		caller = self.caller

		mapping |= { "SELF": caller, "TARGET": target, "HERE": caller.location }

		if not tgt_string:
			run_target = None
		elif not (run_target := mapping.get(tgt_string)):
			run_target = caller.search(tgt_string, quiet=True)
			if len(run_target) != 1:
				return False
			run_target = run_target[0]
		
		result = module.at_use(self.caller, run_target)
		# TODO: handle returning the actual result
		return True if result else False
			

class GearCmdHandler(CmdSet):
	def at_cmdset_creation(self):
		self.add(GearCommand())

class GearHandler(DefaultScript):
	"""
	Storage Script for tracking personal gear scripts.

	"""

	def at_script_creation(self):
		self.key = "gearbook"
		self.desc = "gear scripts attached to this avatar"
		self.persistent = True  # will survive reload
		self.db.cmds = {}
		self.cmdset.add_default(GearCmdHandler)

	def add_script(caller, self, key, script, on_use):
		if key in self.db.cmds:
			caller.msg("%s already exists" % key)
			return
		


# creating/editing scripts

# helpers
def _load_script(caller):
	key = caller.ndb._gearscript_key
	if key:
		gearbook = caller.scripts.get("gearbook")
		if gearbook:
			if key in gearbook.db.cmds:
				return gearbook.db.cmds[key]["script"]


def _save_script(caller, buffer):
	key = caller.ndb._gearscript_key
	if key:
		gearbook = caller.scripts.get("gearbook")
		if gearbook:
			if key in gearbook.db.cmds:
				gearbook.db.cmds[key]["script"] = buffer
				caller.msg("saved")
				return True
			else:
				caller.msg("%s not found, save failed" % key)
				return False
		else:
			caller.msg("!! ERROR !!")
			return False
	else:
		caller.msg("!! ERROR !!")
		return False


# commands

class EditGearCmd(UnixCommand):
	key = "edit"
	aliases = ()
	locks = "cmd:pperm(Player)"

	def init_parser(self):
		"Add the arguments to the parser."
		self.parser.add_argument("script",
				help="the gear script to edit")
		self.parser.add_argument("-a", "--action",
				help="the action displayed to the room on script execution")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		script = self.opts.script
		action = self.opts.action
		caller = self.caller
		
		gearscript = caller.scripts.get("gearbook")
		if not gearscript:
			caller.msg("ERROR")
			return

		if target in gearscript.db.cmds:
			if action:
				gearscript.db.cmds[target]['on_use'] = action
				caller.msg("action updated for %s" % target)
			else:
				from evennia.utils.eveditor import EvEditor
				caller.ndb._gearscript_key = target
				editor_key = "editing %s" % target
				EvEditor(caller, loadfunc=_load_script, savefunc=_save_script, key=editor_key, persistent=False)
		
		else:
			caller.msg("ERROR: %s not found" % target)


class CreateGearCmd(UnixCommand):
	key = "make"
	aliases = ()
	locks = "cmd:pperm(Player)"

	def init_parser(self):
		"Add the arguments to the parser."
		self.parser.add_argument("script",
				help="the gear script to create")
		self.parser.add_argument("-a", "--action",
				help="the action displayed to the room on script execution")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		script = self.opts.script
		action = self.opts.action
		caller = self.caller
		
		gearscript = caller.scripts.get("gearbook")
		if not gearscript:
			caller.msg("ERROR")
			return

		if script in gearscript.db.cmds:
			caller.msg("ERROR: %s already exists" % script)

		else:
			if action:
				gearscript.db.cmds[script]['on_use'] = action
			# do the stuff
			from evennia.utils.eveditor import EvEditor
			caller.ndb._gearscript_key = script
			editor_key = "editing %s" % script
			EvEditor(caller, loadfunc=_load_script, savefunc=_save_script, key=editor_key, persistent=False)


class DeleteGearCmd(UnixCommand):
	key = "del"
	aliases = ()
	locks = "cmd:pperm(Player)"

	def init_parser(self):
		"Add the arguments to the parser."
		# 'self.parser' inherits `argparse.ArgumentParser`
		self.parser.add_argument("script",
				help="the gear script to delete")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		script = self.opts.script
		caller = self.caller
		
		gearscript = caller.scripts.get("gearbook")
		if not gearscript:
			caller.msg("ERROR")
			return

		if script in gearscript.db.cmds:
			# confirm deletion with a y/n input yield
			pass

		
class CopyGearCmd(UnixCommand):
	key = "copy"
	aliases = ()
	locks = "cmd:pperm(Player)"

	def init_parser(self):
		"Add the arguments to the parser."
		# 'self.parser' inherits `argparse.ArgumentParser`
		self.parser.add_argument("script",
				help="the software script to copy")
		self.parser.add_argument("-t", "--target",
				help="the avatar to copy the script to")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		script = self.opts.script
		tgt_string = self.opts.target
		caller = self.caller
		
		gearscript = caller.scripts.get("gearbook")
		if not gearscript:
			caller.msg("ERROR")
			return


class GearCmdSet(CmdSet):
	def at_cmdset_creation(self):
		self.add(CreateGearCmd())
		self.add(EditGearCmd())
		self.add(CopyGearCmd())
		self.add(DeleteGearCmd())
