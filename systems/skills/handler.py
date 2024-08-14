from evennia.utils import string_partial_matching, string_suggestions

from utils.handlers import HandlerBase
from .skills import Skill

class SkillsHandler(HandlerBase):
	def __init__(self, obj):
		super().__init__(obj, "skills")
	
	def _load(self):
		super()._load()
		loaded_data = {}
		for key, data in self._data.items():
			loaded_data[key] = Skill(handler=self, **data)
		
		self.data = loaded_data

	def __getattr__(self, attr):
		if skill := self.get(attr):
			return skill
		raise AttributeError(f"'{self.__name__}' object has no attribute '{attr}'")
	
	def _save(self, key=None):
		if key and key in self.data.keys():
			data = { k:v for k, v in vars(self.data[key]).items() if k != 'handler' }
			self._data[key] = data
		else:
			flattened = {}
			for key, clsobj in self.data.items():
				data = vars(clsobj)
				del data['handler']
				flattened[key] = data
			self._data = flattened
		super()._save()
	

	def add(self, skill_key, display_name, **kwargs):
		"""
		Add a new skill.

		Returns:
			True if skill was added, else False
		"""
		if skill_key in self.data.keys():
			return False
		try:
			new_skill = Skill(handler=self, name=display_name, key=skill_key, **kwargs)
		except:
			return False
		self.data[skill_key] = new_skill
		self._save(key=skill_key)
		return True


	def remove(self, skill_key, **kwargs):
		"""
		Remove an existing skill
		
		Returns:
			True if a skill was removed, else False
		"""
		if skill_key not in self.data:
			return False
		del self.data[skill_key]
		self._save()
		return True


	def get(self, skill_key):
		"""
		Returns a reference to the class representing the skill for the given key.

		If no key is found, returns None
		"""
		return self.data.get(skill_key, None)
	
	def all(self, keys=True):
		"""
		Returns a list of all the skill keys if keys is True.
		Otherwise, returns a list of all the skill objects.
		"""
		if keys:
			return list(self.data.keys())
		else:
			return list(self.data.values())


	def check(self, return_list=False, **kwargs):
		"""
		Checks the skillkey:dc pairs in kwargs and compares against the internal values for each key.

		By default, returns True if all items pass, else False

		If return_list is True, returns a list booleans representing whether each individual check passes or not.
		"""
		if not kwargs:
			return [] if return_list else True
		
		results = []
		for key, dc in kwargs.items():
			if skill := self.data.get(key):
				results.append(skill.value >= dc)
			else:
				results.append(False)
		
		if return_list:
			return results
		else:
			return all(results)


	def use(self, individual=False, **kwargs):
		"""
		Checks the skillkey:dc pairs in kwargs and if they pass, marks a practice point for each.

		If individual is set to True, it checks and marks each skill individually rather than together.

		Returns either a single boolean, or a list of booleans if individual is True.
		"""
		result = self.check(return_list=individual, **kwargs)
		practice_list = []
		if individual:
			practice_list = [ key for key, practice in zip(kwargs.keys(), result) if practice ]
		elif result:
			# all of the checks passed, we should increment all of them
			practice_list = list(kwargs.keys())

		for key in practice_list:
			self.data[key].practice += 1
		
		return result


	def search(self, search_term, **kwargs):
		"""Find a skill in the handler by key or display name"""
		if skill := self.data.get(search_term):
			return [skill]
		
		skill_list = list(self.data.values())
		matches = string_partial_matching([skill.name for skill in skill_list], search_term, ret_index=True)
		if matches:
			return [skill_list[i] for i in matches]
		
		matches = string_partial_matching(self.data.keys(), search_term, ret_index=False)
		if matches:
			return [self.data[key] for key in matches]
		
		suggested_names = string_suggestions(search_term, [skill.name for skill in skill_list])
		return [skill for skill in skill_list if skill.name in suggested_names]
	