from utils.general import get_classpath
from utils.handlers import HandlerBase


class CounteractQueue(HandlerBase):
	"""
	Similar to the ActionQueue but it tracks queued counteraction opportunities instead
	"""
	def __init__(self, obj):
		super().__init__(obj, db_attr="counter_queue", default_data=[])
	
	def _load(self):
		super()._load()
		queue = []
		for obj, path in self._data:
			if not (action := obj.actions.current):
				continue
			if get_classpath(action) == path:
				queue.append(action)
		self.queue = queue

	def _save(self):
		data = []
		for action in self.queue:
			data.append( (action.actor, get_classpath(action)) )
		self._data = data
		super()._save()

	def add(self, action, **kwargs):
		"""
		Adds a new action to the end of the internal queue.
		"""
		# filter out any actions from the same actor, since you can't have two up at once
		actor = action.actor
		new_queue = [ act for act in self.queue if act.actor != actor ]
		new_queue.append(action)
		self.queue = new_queue
		self._save()
		if action == self.current:
			# it's the next up, let us know
			self.prompt()
	
	def remove(self, action, **kwargs):
		"""
		Removes an action from the counteraction queue.

		If it was the current-up action, it steps to the next.
		"""
		reprompt = action == self.current
		# if action is current, then it is in the queue and this block will execute
		# so we don't need to worry about reprompting on no change
		if action in self.queue:
			self.queue.remove(action)
			self._save()
		if reprompt:
			self.prompt()
	
	@property
	def current(self):
		"""Returns the action that's next up to counter"""
		if self.queue:
			return self.queue[0]
		else:
			return None

	def prompt(self, **kwargs):
		"""
		Messages the owning object with the current action to counter
		"""
		if self.current:
			self.obj.msg(f"You have an opportunity to counteract a $h({self.current.move}) by {self.current.actor.get_display_name(self.obj)}.")
			self.obj.on_counter_opp(self.current)
