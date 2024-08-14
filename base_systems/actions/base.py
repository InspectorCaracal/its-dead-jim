import time
from evennia.utils.dbserialize import dbserialize, dbunserialize
from evennia.utils import iter_to_str, is_iter, logger

from switchboard import INFLECT
from utils.strmanip import numbered_name

from utils.timing import delay

class InterruptAction(Exception):
	"""Fail to initialize an action"""
	pass

class Action:
	move = "action"
	dbobjs = ['actor'] # deprecated
	actor = None

	min_req_parts = tuple()
	max_used_parts = tuple()

	energy = 0
	exp = 0

	def __str__(self):
		return self.move

	def __init__(self, *args, **kwargs):
		self.serialized = False
		for key, val in kwargs.items():
			if callable(getattr(self, key, None)):
				continue
			setattr(self, key, val)

	# def __serialize_dbobjs__(self):
	# 	logger.log_msg(f'serializing {self}')
	# 	if self.serialized:
	# 		logger.log_msg('already marked as serialized')
	# 		return
	# 	self.serialized = True
	# 	for attr_name in self.dbobjs:
	# 		if attr := getattr(self, attr_name, None):
	# 			setattr(self, attr_name, dbserialize(attr))

	# def __deserialize_dbobjs__(self):
	# 	logger.log_msg(f'DEserializing {self}')
	# 	if not self.serialized:
	# 		logger.log_msg('already marked as deserialized')
	# 		return
	# 	for attr_name in self.dbobjs:
	# 		if attr := getattr(self, attr_name, None):
	# 			setattr(self, attr_name, dbunserialize(attr))
	# 	self.serialized = False

	def delay(self, interval, *args, end=False):
		"""so i don't need to keep remembering to set the right attributes"""
		now = time.time()
		if end:
			self._end_at = now+interval
			func = self.end
		else:
			self._next_step = now+interval
			self.do_args = args
			func = self.do
		self._task = delay(interval, func, *args)

	def resume(self):
		if next_step := getattr(self, '_next_step', None):
			delay(max(0, next_step - time.time()), self.do, *getattr(self, 'do_args', []))
		elif end_at := getattr(self, '_end_at', None):
			delay(max(0, end_at - time.time()), self.end)
		else:
			self.start()

	def start(self, *args, **kwargs):
		"""
		Begin an action.

		This method is where you do any initialization and pre-action validation.
		"""
		can_use = {}
		if self.actor:
			# check for available parts
			for item in self.min_req_parts:
				part, mincount = item
				partlist = self.actor.parts.search(part, part=True)
				if len(partlist) >= mincount:
					partlist = [ p for p in partlist if p.is_usable() ]
				if len(partlist) < mincount:
					# TODO: better error messaging
					self.msg(f"You need to use {numbered_name(part, mincount)} for that.")
					return self.end(*args, **kwargs)
				can_use[part] = partlist
			# check against the skill if it's 
			if hasattr(self, 'skill'):
				if not hasattr(self.actor, 'skills'):
					# this actor has no skills and simply can't do this
					return self.end(*args, **kwargs)
				if not self.actor.skills.use(**{self.skill: getattr(self, 'dc', 0)}):
					return self.fail(*args, **kwargs)
				self.counter_dc = self.actor.skills.get(self.skill).value

		self.parts_to_use = can_use

		do_args = args
		if hasattr(self, 'do_args'):
			do_args = self.do_args

		self.do(*do_args, **kwargs)
		return True

	def do(self, *args, **kwargs):
		"""
		Do an action.

		This method contains the bulk of the actual effects of the action.
		"""
		if getattr(self, 'parts_to_use', None):
			max_used = self.max_used_parts or self.min_req_parts
			for item in max_used:
				part, usecount = item
				self.parts_to_use[part] = self.parts_to_use[part][:usecount]

		if kwargs.get('delay'):
			self.actor.prompt()
		else:
			return self.succeed(*args, **kwargs)
			

	def succeed(self, *args, **kwargs):
		"""
		Succeed at an action.

		Any code specific to a success case goes in here.
		"""
		return self.end(*args, **kwargs)

	def fail(self, *args, **kwargs):
		"""
		Fail an action.

		Any code specific to a failure case goes in here.
		"""
		return self.end(*args, **kwargs)

	def end(self, *args, **kwargs):
		"""
		End an action.

		This method should contain any final cleanup that happens regardless of success status.
		It also informs the actor's action queue that it's been completed and triggers any reactions.
		"""
		if exp := kwargs.get('exp'):
			if hasattr(self.actor, 'exp'):
				self.actor.exp += exp

		if hasattr(self, '_task'):
			if self._task:
				self._task.cancel()
		if actor := self.actor:
			reaction = f"on_{self.move}"
			func = getattr(actor, reaction)
			# TODO: needs a better way of passing info into this
			func(*args, **kwargs)

			used_parts = getattr(self, 'parts_to_use', {})
			affected = set()
			for partlist in used_parts.values():
				for p in partlist:
					affected.update(p.get_affected_parts())
			for part in affected:
				part.on_use(actor, self.move)

			if hasattr(actor, "actions"):
				actor.actions.next()

	def status(self):
		"""Return the status string for this action."""
		return f"You are doing {INFLECT.an(self.move)}."

	def msg(self, *args, **kwargs):
		"""Sends a message to the actor doing this."""
		if actor := self.actor:
			actor.msg(*args, **kwargs)