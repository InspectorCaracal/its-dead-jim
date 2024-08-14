from utils.handlers import HandlerBase


class PoseHandler(HandlerBase):
	"""
	Manages the posed states of a room or object's contents
	"""

	def __init__(self, obj):
		"""
		Initialize the handler.
		"""
		super().__init__(obj, 'poses', 'systems')

	def add(self, poser, target, pose, **kwargs):
		if loc := self._data.get(poser):
			return loc == target
		return self.set(poser, target, pose, **kwargs)
		
	def set(self, poser, target, pose, **kwargs):
		# TODO: actually use the `pose` string someday
		cand = self.obj.contents
		if not (poser in cand and target in cand):
			return False
		
		if not target.at_pre_posed_on(poser, **kwargs):
			return False
		
		self._data[poser] = target
		self._save()
		return True

	def remove(self, poser, **kwargs):
		if poser not in self._data:
			return
		ex_posee = self._data.pop(poser)
		if hasattr(ex_posee, 'at_poser_unpose'):
			ex_posee.at_poser_unpose(poser)
		self._save()
	
	def get(self, target, **kwargs):
		"""
		Get the current pose status for an object.
		
		Returns a tuple of (obj target is posed on, obj posing on target) or None if there is no pose data.
		Values of tuple are `None` if no object is valid
		"""
		# check posers
		posed_on = self._data.get(target)

		# check posees
		objs = [ obj for obj, val in self._data.items() if val == target ]
		posing_on = objs
		
		if not (posed_on or posing_on):
			return None
		
		return (posed_on, posing_on)
	
	def get_posed_on(self, target, **kwargs):
		"""Get the current object target is posed on"""
		return self._data.get(target)
	
	def get_being_posed(self, target, **kwargs):
		"""Get any objects that are posing on target"""
		return [ obj for obj, val in self._data.items() if val == target ]