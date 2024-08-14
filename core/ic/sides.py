from random import choice
from utils.handlers import HandlerBase


class SidesHandler(HandlerBase):
	"""look it's such a small handler idk"""
	def __init__(self, obj):
		super().__init__(obj, 'sides', default_data=set())

	def all(self):
		return tuple(self._data)

	def add(self, side):
		if side in self._data:
			return
		self._data.add(side)
		self._save()
		return

	def remove(self, side):
		if side not in self._data:
			return
		self._data.remove(side)
		self._save()
		return

	def reveal(self, *sides):
		"""
		make one or more sides visible

		returns True if all sides were revealed, otherwise False

		Note: a single argument of "all" will reveal all sides
		"""
		sides = set(sides)
		if not sides.issubset(self._data):
			return False

		for side in sides:
			self.obj.tags.add(side, category="side_up")
		return True

	def hide(self, *sides):
		"""
		hide one or more sides

		returns True if all given sides were obscured, otherwise False

		Note: a single argument of "all" will obscure all sides
		"""
		sides = set(sides)
		if not sides.issubset(self._data):
			return False

		for side in sides:
			self.obj.tags.remove(side, category="side_up")
		return True

	def turn(self):
		"""
		change the current side to another side

		for objects with multiple visible sides, it just removes one and adds one randomly

		returns the current list of now-visible sides
		"""
		# TODO: dice ;-;
		current = self.current()
		options = self._data - set(current)
		if not options:
			return current

		if current:
			to_remove = choice(current)
			self.obj.tags.remove(to_remove, category="side_up")

		to_add = choice(list(options))
		self.obj.tags.add(to_add, category="side_up")
		
		return self.current()

	def current(self):
		"""return all the current sides"""
		return self.obj.tags.get(category='side_up', return_list=True)