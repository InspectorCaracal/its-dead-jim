from evennia import CmdSet, Command
from evennia.contrib.base_systems.unixcommand import UnixCommand

from core.ic.base import BaseObject

class CmdRun(UnixCommand):
	"""
	run
	
	Usage:
	  run <module> [flags]

	Run a software module that's been installed into your deck.
	
	For more information on available flags:
	  run -h
	  run --help
	"""

	key = "run"
	locks = "cmd:pperm(Player)"

	def init_parser(self):
		"Add the arguments to the parser."
		# 'self.parser' inherits `argparse.ArgumentParser`
		self.parser.add_argument("module",
				help="the software module to be run")
		self.parser.add_argument("-t", "--target",
				help="a target to run the module on")
		self.parser.add_argument("-q", "--quiet", action="store_true",
				help="suppress the printed output from the command")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		modstring = self.opts.module
		tgt_string = self.opts.target
		quiet = self.opts.quiet
		caller = self.caller
		
		# check that module is a valid installed software object
		module = caller.search(modstring, candidates=caller.db.deck.contents)

		if not module:
			caller.msg(f"ERROR: {modstring} not found") # format for code
			return None

		if not module.is_typeclass(SoftwareObject, exact=False):
			caller.msg(f"ERROR: {module.key} is invalid module")
			return None
		
		# parse target
		if tgt_string:
			if tgt_string == "here":
				target = caller.location
			else:
				target = caller.search(tgt_string, candidates=caller.location.contents + caller.contents)

			if not target:
				caller.msg(f"ERROR: {tgt_string} not found") # format for code
				return None

		else:
			target = None

		result = module.at_use(target=target, quiet=quiet)
		
		return result
		

class SoftwareCmdSet(CmdSet):
	def at_cmdset_creation(self):
		self.add(CmdRun())



class SoftwareObject(BaseObject):
	def at_object_creation(self):
		super().at_object_creation()
		self.cmdset.add_default(SoftwareCmdSet)
		self.db.level = 0
		self.db.size = 0

	def at_use(self, caller, **kwargs):
		pass

class DecryptionObject(SoftwareObject):
	'''
	The Object class for decryption software modules.
	Each module has a specific algorithm it can decrypt,
	and a maximum encryption level it can crack.
	'''
	def at_object_creation(self):
		super().at_object_creation()
		self.db.algo = None

	def at_use(self, caller, target, quiet=False, **kwargs):
		if target is None:
			if not quiet:
				caller.msg("ERROR: target required")
			return None

		try:
			# this should return either a number representing the new encryption level, or False if it's the wrong algorithm
			result = target.decrypt(self,quiet)
		except AttributeError as e:
			if not quiet:
				caller.msg("ERROR: unencryptable")
			return None
		
		return result


class EncryptionObject(SoftwareObject):
	'''
	The Object class for decryption software modules.
	Each module has a specific algorithm it uses to encrypt,
	and an encryption complexity level.
	'''

	def at_object_creation(self):
		super().at_object_creation()
		self.db.algo = None

	def at_use(self, caller, target, quiet=False, **kwargs):
		if target is None:
			if not quiet:
				caller.msg("ERROR: target required")
			return None
		
		try:
			# should return True on successful encryption, or False if failed e.g. no write permissions
			result = target.encrypt(self,quiet)
		except AttributeError as e:
			if not quiet:
				caller.msg("ERROR: unencryptable")
			return None
		
		return result
		
class ObfuscationObject(SoftwareObject):

	def at_object_creation(self):
		super().at_object_creation()

	def at_use(self, caller, **kwargs):
		pass

class DefuscationObject(SoftwareObject):

	def at_object_creation(self):
		super().at_object_creation()

	def at_use(self, caller, **kwargs):
		pass



