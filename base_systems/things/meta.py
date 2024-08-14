from collections import Counter
from random import choices

from base_systems.things.base import Thing


class VirtualContainer(Thing):
	@property
	def size(self):
		return sum([part.size for part in self.parts.all()])
	
	# TODO: set this up to delete itself if a piece is removed and there are no contents left

	# TODO: apply effects to parts instead of itself?

	def at_object_creation(self):
		super().at_object_creation()
		# backwards compatability
		self.tags.add('virtual_container', category="systems")
	
	def at_damage(self, damage, quiet=False, **kwargs):
		"""Distribute damage to parts, by size"""
		# this object can't be damaged - damage its parts instead
		source = kwargs.get('source')
		kwargs['quiet'] = True
		parts = self.parts.all()
		weights = [ 2**p.size for p in parts ]
		damaged = Counter(choices(parts, weights=weights,k=int(damage)))
		for obj, dmg in damaged.items():
			obj.at_damage(dmg, **kwargs)

		if not quiet:
			if source and hasattr(source,'msg'):
				# TODO: add descriptors for % left
				source.msg(f"{self.get_display_name(source)} takes {damage} damage.")
			
			if self.baseobj != self:
				self.baseobj.msg(f"Your {self.sdesc.get()} takes {damage} damage.")
			self.msg(f"You take {damage} damage.")


