from evennia.utils import logger
from evennia.utils.utils import class_from_module, make_iter

from utils.general import get_classpath
from utils.handlers import HandlerBase
from utils.timing import delay

class ActionQueue(HandlerBase):
	"""handle the queueing and execution of actions"""
	_tick = None
	_duration = 0
	_last_tick = 0

	def __init__(self, obj):
		super().__init__(obj, db_attr="action_queue", default_data=[])
		if self.current:
			delay(0.01, self.current.resume)
		elif self.queue:
			delay(0.01, self.next)
	
	def _load(self):
		super()._load()
		loaded = []
		for classpath, classdata, act_args in self._data:
			new_inst = class_from_module(classpath)
			loaded.append((new_inst(**classdata), act_args))

		if len(loaded):
			if not loaded[0][-1]:
				self.queue = loaded[1:]
				self._current = loaded[0][0]
			else:
				self.queue = loaded
				self._current = None
		else:
			self.queue = []
			self._current = None

	def _save(self):
		new_list = []
		if self.current:
			current = (get_classpath(self.current), {key: val for key, val in vars(self.current).items() if not key.startswith("_")}, None)
			new_list.append(current)
		for inst, args in self.queue:
			cpath = get_classpath(inst)
			data = dict(vars(inst))
			new_list.append( (cpath, data, args) )
		self._data = new_list
		super()._save()

	def override(self, action, *args, **kwargs):
		"""Adds a new action as a "priority" action, cancelling whatever is currently being done"""
		self.queue.insert(0, (action, args))
		if self.current:
			self.current.end()
		else:
			self.next()

	def add(self, action, *args, **kwargs):
		"""add a new action to the queue"""
		new_action = (action, args)
		self.queue.append(new_action)
		if self.current:
			self._save()
		else:
			self.next()
	
	def add_next(self, action, *args, **kwargs):
		"""adds a new action at the top of the queue, without affecting the current action"""
		if not self.queue:
			self.add(action, *args)
		self.queue.insert(0, (action, args))
		self._save()
	
	def next(self):
		save = False
		if self.current:
			save = True
		self._current = None
		if self.queue:
			save = True
			action, args = self.queue.pop(0)
			if self._tick:
				self._tick.cancel()
			self._tick = delay(0.01, action.start, *args)
			self.obj.prompt()
			self._current = action
		else:
			self.obj.prompt()
		if save:
			self._save()
	
	def clear(self, shutdown=False):
		self.queue = []
		if self.current:
			if hasattr(self.current, '_task'):
				self.current._task.cancel()
			try:
				self.current.end()
			except:
				logger.log_trace()
		self._current = None
		if self._tick:
			self._tick.cancel()
		self._save()
		if not shutdown:
			self.obj.prompt()

	def display(self):
		display_list = []
		if status := self.status():
			display_list.append(status)
		for i, (action, args) in enumerate(self.queue):
			index = i if i else "Next"
			display_list.append( f"{index}: {action} {' '.join(args)}" )
		if not display_list:
			return "You are not planning to do anything."
		display_list[0] = f"$h({display_list[0]})"
		return "\n".join(display_list)

	@property
	def current(self):
		return self._current
	
	def status(self):
		if self.current:
			return self.current.status()
		return ''