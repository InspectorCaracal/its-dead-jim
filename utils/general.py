
class MergeDict(dict):
	def __add__(self, other):
		if not issubclass(type(other), dict):
			return NotImplemented
		return self._add_dicts(other)

	def __radd__(self, other):
		if not issubclass(type(other), dict):
			return NotImplemented
		return self._add_dicts(other)

	def __iadd__(self, other):
		new = self._add_dicts(other)
		MergeDict.update(self, new)
		return self
		
	def _add_dicts(self, other):
		""" do the actual combining """
		keys = self.keys() | other.keys()

		def get_set_value(a, b):
			return a if a is not None else b

		new = MergeDict({
			key: self[key] + other[key] if key in self and key in other else get_set_value(
				self.get(key,None), other.get(key,None)
			) for key in keys })
		return new


def get_classpath(cls):
	"""
	Returns a string representing the full path of a class object
	"""
	if not callable(cls):
		cls = cls.__class__
	return f"{cls.__module__ or ''}.{cls.__name__}"


class classproperty:
	def __init__(self, f):
		self.f = classmethod(f)
	def __get__(self, *a):
		return self.f.__get__(*a)()