from evennia.utils import logger

from base_systems.effects.base import Effect

class Overload(Effect):
	"""
	This is a special effect that only works on electronics and electrical objects.
	"""
	threshold = 0
	duration = 10

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		# TODO: get threshold from object stats here
		self.threshold = 3

	def at_add(self, *args, **kwargs):
		obj = self.handler.obj
		if not obj.tags.has("lightning", category="effectable"):
			return
		super().at_add(*args, **kwargs)
		if self.stacks > self.threshold and not obj.tags.has('overloaded', category='status'):
			obj.tags.add("shorted out", category="status")
			obj.tags.add("disabled")
			obj.emote("abruptly arcs with electricity then goes dark, trickling smoke", volume=3)

	def at_tick(self, source, *args, **kwargs):
		self.remove(source=source)
