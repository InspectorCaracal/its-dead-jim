import inspect
from evennia.utils import logger
from evennia.utils.utils import class_from_module, make_iter, variable_from_module
from evennia.utils.dbserialize import deserialize

from core.ic.behaviors import NoSuchBehavior
from utils.general import get_classpath
from utils.handlers import HandlerBase
from utils.timing import delay

_REACT_ATTR = "reactions"
_REACT_CAT = "systems"

class ReactionHandler(HandlerBase):
	def __init__(self, obj):
		"""
		Initialize the handler.
		"""
		super().__init__(obj, _REACT_ATTR, _REACT_CAT, default_data={})

	def add(self, trigger, func, handler=None, handler_args=None, handler_kwargs=None, getter='get'):
		"""
		adds a reaction to `trigger` of `func`

		func can be a function on a handler-contained object, a flat module function, or a method on ourself
		"""
		if trigger.startswith('on_'):
			trigger = trigger[3:]

		if trigger not in self._data:
			self._data[trigger] = []
		
		reaction = None

		if handler:
			# we will need to be able to retrieve the object from a handler
			if not isinstance(func, str):
				func = func.__name__
			reaction = (func, handler, handler_args or [], handler_kwargs or {}, getter)
		else:
			if isinstance(func, str):
				reaction = tuple(reversed(func.rsplit('.',maxsplit=1)))
			elif inspect.ismethod(func):
				# TODO: validate that it's actually on ourself
				reaction = tuple(func.__name__, 'self')
			else:
				reaction = (func.__name__, func.__module__ or '')
		
		if reaction not in self._data[trigger]:
			self._data[trigger].append(reaction)
			self._save()

	def remove(self, trigger, func, handler=None, handler_args=None, handler_kwargs=None, getter="get"):
		if trigger.startswith('on_'):
			trigger = trigger[3:]

		if trigger not in self._data:
			return
		
		reaction = None

		if handler:
			# we will need to be able to retrieve the object from a handler
			if not isinstance(func, str):
				func = func.__name__
			reaction = (func, handler, handler_args or [], handler_kwargs or {}, getter)
		else:
			if isinstance(func, str):
				reaction = tuple(reversed(func.rsplit('.',maxsplit=1)))
			elif isinstance(func, inspect.method):
				# TODO: validate that it's actually on ourself
				reaction = tuple(func.__name__, 'self')
			else:
				reaction = (func.__name__, func.__module__ or '')

		if reaction in self._data[trigger]:
			self._data[trigger].remove(reaction)
			self._save()
	

	def on(self, trigger, *args, **kwargs):
		"""
		!! IMPORTANT: ALL reactions to a specific trigger MUST match arguments or have catchers, or they will error!
		"""
		# TODO: assess "reaction time"
		# TODO: figure out how to not lose triggers on reloads, maybe?
		delay(0.1, _run_trigger, self.obj, trigger, self._data.get(trigger, []), *args, **kwargs)

def _run_trigger(obj, trigger, reactions, *args, **kwargs):
	"""does the actual function execution"""
	del_me = []
	for reaction in reactions:
		func, *extra = reaction
		if len(extra) == 4:
			handler_attr, handler_args, handler_kwargs, handler_getter = extra
			try:
				handler = getattr(obj, handler_attr)
				getter = getattr(handler, handler_getter)
				reacting_obj = getter(*handler_args, **handler_kwargs)
				func = getattr(reacting_obj, func)
			except AttributeError:
				del_me.append(reaction)
				continue
		else:
			path = extra[0]
			if path == "self":
				try:
					func = getattr(obj, func)
				except (AttributeError, NoSuchBehavior):
					del_me.append(reaction)
					continue
			else:
				func = variable_from_module(path, func)
		func(*args, **kwargs)
		
	if del_me:
		print(f"Removing triggers:\n {del_me}")
		for reaction in del_me:
			obj.react._data[trigger].remove(reaction)
		
		obj.react._save()

