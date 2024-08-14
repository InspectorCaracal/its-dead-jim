from copy import copy
from evennia.utils import logger

from utils.general import get_classpath


BEHAVIOR_REGISTRY = {}

# decorator for behavior classes
def behavior(cls):
	key = cls.__name__
	if key in BEHAVIOR_REGISTRY:
		if BEHAVIOR_REGISTRY[key] != cls:
			logger.log_warn(f"Conflicting behavior key '{key}' is overwriting.")
	# instead of having to inherit from Behavior, we'll just require a priority
	if hasattr(cls, 'priority'):
		BEHAVIOR_REGISTRY[key] = cls
	else:
		logger.log_err(f"Invalid behavior class! {get_classpath(cls)}")
	return cls

class NoSuchBehavior(Exception):
	pass

def _get_methods(cls):
	"""
	Retrieves a list of behavior methods on the class.
	"""
	return list([ item for item in dir(cls) if not item.startswith("_") and callable(getattr(cls, item)) ])

class BehaviorSet:
	"""
	Manage all of the current mechanics behaviors accessible to this object
	"""
	def __init__(self, obj):
		self.obj = obj
		if not obj.attributes.get("behaviors", category="systems", default=None):
			obj.attributes.add("behaviors", set(), category="systems")
		self.load()
	
	def all(self):
		"""returns all available behavior methods"""
		return {key: val[0] for key, val in sorted(self.behaviors.items(), key=lambda x: x[0])}
	
	def loaded(self):
		"""returns the registry keys for all behavior classes loaded onto this"""
		return copy(self._behave_set)
	
	def _add_methods(self, cls, default=False, **kwargs):
		new_tuple = (cls, kwargs)
		for method in _get_methods(cls):
			if method in self.behaviors:
				if new_tuple not in self.behaviors[method]:
					self.behaviors[method].append(new_tuple)
					self.behaviors[method].sort(key=lambda x: x[0].priority, reverse=True)
			else:
				self.behaviors[method] = [new_tuple]
			# NOTE: with this new 'list of methods' implementation, is _default obsolete?
			if default:
				if method in self._default:
					if new_tuple not in self._default[method]:
						self._default[method].append(new_tuple)
						self._default[method].sort(key=lambda x: x[0].priority, reverse=True)
				else:
					self._default[method] = [new_tuple]

	def _del_methods(self, cls, default=False, **kwargs):
		for method in _get_methods(cls):
			if not (behaves := self.behaviors.get(method)):
				continue
			if behaves := [item for item in behaves if item != (cls, kwargs)]:
				self.behaviors[method] = behaves
			else:
				del self.behaviors[method]
			# NOTE: is the default system obsolete?
			if not (behaves := self._default.get(method)):
				continue
			if behaves := [item for item in behaves if item != (cls, kwargs)]:
				self._default[method] = behaves
			else:
				del self._default[method]

	def load(self):
		self.behaviors = {}
		self._default = {}
		self._behave_set = self.obj.attributes.get("behaviors", category="systems").deserialize()
		for registry_key in self._behave_set:
			if cls := BEHAVIOR_REGISTRY.get(registry_key):
				self._add_methods(cls, default=True)
			else:
				logger.log_err(f"Behavior '{registry_key}' not found in registry")
				continue
		for obj in self.obj.parts.all():
			self.merge(obj)
	
	def save(self):
		self.obj.attributes.add("behaviors", self._behave_set, category="systems")
	
	def add(self, registry_key, **kwargs):
		"""
		Add a new behavior to the object

		Optional: save=False for merge behavior
		"""
		cls = BEHAVIOR_REGISTRY[registry_key]
		self._behave_set.add(registry_key)
		save = kwargs.pop("save", True)
		self._add_methods(cls, default=save, **kwargs)
		if save:
			self.save()
			if self.obj.baseobj != self.obj:
				self.obj.baseobj.behaviors.merge(self.obj)

	def remove(self, registry_key, **kwargs):
		"""
		save=False for unmerge behavior
		"""
		if registry_key not in self._behave_set:
			# can't remove what we don't have!
			return
		cls = BEHAVIOR_REGISTRY[registry_key]
		self._behave_set.remove(registry_key)
		save = kwargs.pop("save", True)
		self._del_methods(cls, default=save, **kwargs)
		if save:
			self.save()
			if self.obj.baseobj != self.obj:
				self.obj.baseobj.behaviors.unmerge(self.obj)

	def merge(self, obj, **kwargs):
		"""
		merge behaviors from one object temporarily into the owner object
		"""
		for registry_key in obj.behaviors._behave_set:
			self.add(registry_key, save=False, behavior_source=obj)

	def unmerge(self, obj, **kwargs):
		"""
		remove behaviors from the owner object that were merged from this object
		"""
		# FIXME: this will sometimes remove behaviors that were gained from multiple parts
		for registry_key in obj.behaviors._behave_set:
			self.remove(registry_key, save=False, behavior_source=obj)

	def can_do(self, method):
		return method in self.behaviors

	def do(self, method, *args, **kwargs):
		if not (behave := self.behaviors.get(method)):
			raise NoSuchBehavior(f"'{type(self).__name__}' has no attribute 'do_{method}'")
		clsobj, cls_kwargs = behave[0]
		func = getattr(clsobj, method)
		return func(*args, **(cls_kwargs | kwargs))


class Behavior:
	priority = -1

