from evennia.utils.utils import class_from_module, make_iter

from utils.general import get_classpath
from utils.handlers import HandlerBase

_EFFECT_ATTR = "effects"
_EFFECT_CAT = "systems"

class EffectsHandler(HandlerBase):
	def __init__(self, obj):
		"""
		Initialize the handler.
		"""
		super().__init__(obj, _EFFECT_ATTR, _EFFECT_CAT, default_data=[])

	def _load(self):
		super()._load()
		loaded = []
		for classpath, classdata in self._data:
			new_inst = class_from_module(classpath)
			loaded.append(new_inst(self, **classdata))

		self.effects = loaded

	def _save(self, **kwargs):
		self.save(**kwargs)

	def save(self, to_save=None):
		if to_save:
			cpath = get_classpath(to_save)
			data = dict(vars(to_save))
			data.pop('handler', None)
			if to_save in self.effects:
				i = self.effects.index(to_save)
				self._data[i] = (cpath, data)
			else:
				self.effects.append(to_save)
				self._data.append( (cpath, data) )
		else:
			new_list = []
			for inst in self.effects:
				cpath = get_classpath(inst)
				data = dict(vars(inst))
				data.pop('handler',None)
				new_list.append( (cpath, data) )
			self._data = new_list
		super()._save()

	def _find_effect(self, effect, name):
		effect_obj = None
		if effect:
			effect_str = effect if type(effect) is str else get_classpath(effect) 
			for obj in self.effects:
				if get_classpath(obj) == effect_str:
					if not name:
						effect_obj = obj
						break
					elif name == obj.name:
						effect_obj = obj
						break
		elif name:
			for obj in self.effects:
				if name == obj.name:
					effect_obj = obj
					break

		return effect_obj

	def has(self, effect=None, name=None, **kwargs):
		return True if self._find_effect(effect, name) else False
	
	def get(self, effect=None, name=None, **kwargs):
		return self._find_effect(effect, name)

	def all(self):
		"""Returns all Effect objects on this object"""
		return tuple(self._data)

	def add(self, effect, *args, **kwargs):
		"""
		Add an effect to the handler.
		"""
		name = kwargs.get("name")
		if type(effect) is str:
			effect = class_from_module(effect, defaultpaths="base_systems.effects")

		if not (effect_obj := self._find_effect(effect, name)):
			effect_obj = effect(self, *args, **kwargs)
		
		# handle effect cancelling
		if negation := getattr(effect_obj, "negate", None):
			stacks = kwargs.get('stacks',1)
			for path in make_iter(negation):
				if negated := self._find_effect(path):
					negated_stacks = negated.stacks
					negated.remove(source='all', stacks=stacks)
					stacks -= negated_stacks
					if stacks <= 0:
						return
			kwargs['stacks'] = stacks

		if effect_obj not in self.effects:
			# this will append the new effect both internally and to the data attr
			self._save(to_save=effect_obj)
			effect_obj.at_create(*args, **kwargs)
		effect_obj.add(*args, **kwargs)

	def remove(self, effect, *args, **kwargs):
		name = kwargs.get("name")
		if type(effect) is str:
			effect = class_from_module(effect)

		if effect_obj := self._find_effect(effect, name):
			effect_obj.remove(*args, **kwargs)

	def delete(self, classobj, *args, **kwargs):
		if classobj in self.effects:
			classobj.duration = 0 # makes sure the ticker stops
			classobj.at_delete(*args, **kwargs)
			self.effects.remove(classobj)
			self._save()

	def clear(self):
		"""
		Completely removes all effects without triggering any of their hooks.
		"""
		# timers cause class objects to be preserved, so flag them all off first
		for cob in self.effects:
			if hasattr(cob, 'duration'):
				cob.duration = 0
		self.effects = []
		self._save()
		self._load()
