from systems.parkour.actions import PARKOUR_MOVES
from utils.handlers import HandlerBase

class ParkourHandler(HandlerBase):
	def __init__(self, obj):
		super().__init__(obj, "freerunning", "systems", default_data=list())
	
	def _load(self):
		super()._load()
		self.data = list([ PARKOUR_MOVES.get(key, **kwargs) for key, kwargs in self._data ])

	def _save(self):
		self._data = [ (move.key, vars(move)) for move in self.data ]
		super()._save()

	def set(self, source, registry_key="base", **kwargs):
		if not (extant := self.get(source=source)):
			return self.add(source, registry_key=registry_key, **kwargs)
		for r in extant:
			if not self.remove(r, save=False):
				return False
		new_move = PARKOUR_MOVES.get(registry_key, source=source, obstacle=self.obj, **kwargs)
		if new_move in self.data:
			return False
		else:
			self.data.append(new_move)
			self._save()
		return True

	def add(self, source, registry_key="base", **kwargs):
		if self.get(source=source):
			# we already have one
			return False
		new_move = PARKOUR_MOVES.get(registry_key, source=source, obstacle=self.obj, **kwargs)
		if new_move in self.data:
			return False
		else:
			self.data.append(new_move)
			self._save()
		return True

	def remove(self, item_or_index, save=True):
		if type(item_or_index) is int:
			del self.data[item_or_index]
		elif item_or_index in self.data:
			self.data.remove(item_or_index)
		else:
			return False
		if save:
			self._save()
		return True

	def get(self, source=None):
		"""Get the associated moves for a source location. If source is None, return all"""
		if not source:
			return list(self.data)
		else:
			return [ m for m in self.data if m.source == source ]
	
	def get_sources(self):
		"""Return a list of all sources the object can be reached from"""
		return list( {m.source for m in self.data} )

	def get_verbs(self):
		"""Get all verbs associated with this obstacle"""
		return list({ m.verb for m in self.data if m.verb })
	
	def get_verb(self, source):
		"""Get the verb specific to a source"""
		verbs = [ m.verb for m in self.data if m.source == source and m.verb ]
		if not verbs:
			return None
		elif len(verbs) > 1:
			# better error handling?
			raise KeyError(f"{self.obj} (#{self.obj.id}) has multiple verbs for {source}")
		else:
			return verbs[0]
	
	def get_speed(self, source):
		"""Get the minimum speed value (i.e. time passed) required to move to self.obj from source"""
		if speeds := [ m.speed for m in self.data if m.source == source ]:
			return min( speeds )
		else:
			return 0

