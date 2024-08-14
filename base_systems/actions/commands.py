from evennia import CmdSet
from base_systems.actions.base import InterruptAction
from core.commands import Command

class CmdStop(Command):
	"""
	Stop whatever you're doing.

	Usage:
		stop [all]
	
	Using "stop" by itself will end your current action, moving on to any next-in-queue action.

	Using "stop all" will end your current action and cancel any queued actions.
	"""

	key = "stop"
	aliases = ('stop all',)
	help_category = "Character"
	free = True

	def func(self):
		if self.cmdstring == 'stop all':
			self.caller.actions.clear()
			self.caller.prompt()
		elif action := self.caller.actions.current:
			action.end()
		elif self.caller.actions.queue:
			self.caller.actions.next()
		else:
			self.msg("You aren't doing anything.")

class CmdStatus(Command):
	"""
	View the current status of yourself or another object.

	Usage:
		status [<obj>]
	"""
	key = "status"
	help_category = "Character"
	free = True

	def func(self):
		if self.args:
			target = yield from self.find_targets(self.args, numbered=False)
			if not target:
				return
		else:
			target = self.caller

		self.msg(target.get_status(third=(target != self.caller)))

class CmdViewQueue(Command):
	"""
	View your current action and any queued actions.

	Usage:
		queue
	"""
	key = "queue"
	help_category = "Character"
	free = True

	def func(self):
		self.msg(self.caller.actions.display())

class ActionCmdSet(CmdSet):
	key = "Action CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdStop)
		self.add(CmdStatus)
		self.add(CmdViewQueue)


class ActionCommand(Command):
	"""
	A base command class intended for commands which use Actions for their primary logic.

	This should be most in-character commands.
	"""
	# the action class to be used
	action=None
	location=None
	candidates=None
	# whether the action requires target permission
	permission=False
	err_msg = "Something went wrong."
	needs_target = True

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.action_kwargs = {}
		self.search_kwargs = {}

	def parse(self):
		super().parse()
		self.targets = self.argslist
		if not self.targets:
			self.targets = [self.args]

	def at_pre_cmd(self):
		if not self.action:
			self.msg(self.err_msg)
			return True
		return super().at_pre_cmd()

	def func(self):
		if not self.targets and self.needs_target:
			self.msg(f"You can't {self.key} nothing.")
			return

		caller = self.caller
		act_kwargs = {} | self.action_kwargs
		# target stuff
		location = self.location
		target_list = []
		
		tail = getattr(self, 'tail_str', '')

		if targets := self.targets:
			targets = self.targets
			if not tail and getattr(self, 'tail', False):
				obj_list, tail = yield from self.find_targets(targets[-1], location=location, tail=True, find_none=self.needs_target, **self.search_kwargs)
				if obj_list:
					target_list += obj_list
				targets = targets[:-1]
			for sterm in targets:
				obj_list = yield from self.find_targets(sterm, location=location, **self.search_kwargs)
				if obj_list:
					target_list += obj_list

			if not target_list and self.needs_target:
				return

		if tail:
			act_kwargs['tail_str'] = tail
		
		try:
			action = self.action(actor=caller, targets=target_list, **act_kwargs)
		except InterruptAction:
			caller.msg(self.err_msg)
			return
		
		queue_up = caller.actions.add
		if getattr(self, 'action_override', False):
			queue_up = caller.actions.override

		if self.permission and len(target_list) == 1 and hasattr(target_list[0], 'ask_permission'):
			target = target_list[0]
			caller.ndb.waiting_for_permission = (queue_up, action)
			caller.msg(f"Requesting permission to {self.cmdstring} from {target.get_display_name(caller, article=True)}.")
			target.ask_permission(caller, f"{self.cmdstring} you")
		else:
			queue_up(action)

	# def at_post_cmd(self):
	# 	self.caller.prompt()