from core.ic.behaviors import Behavior, behavior

@behavior
class ColorBehavior(Behavior):
	priority=1

	def color(obj, target, units=1, **kwargs):
		"""Adds the pigment materials to the target's own materials"""
		if obj.stats.integrity.value < units:
			return False
		# TODO: how do i identify the usable pigment material specifically?
		for key, value in obj.materials.get("all", as_data=True).items():
			target.materials.add(key, **value)
		
		# FIXME: this only works for like chalk or crayons
		# a refillable pen is a container and wouldn't be damaged
		obj.stats.integrity.current -= units
		return True
