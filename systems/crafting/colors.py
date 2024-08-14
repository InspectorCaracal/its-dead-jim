from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import iter_to_str

from base_systems.things.base import Thing
from utils.colors import add_colors, blend_colors

class BaseColorObject(Thing):
	"""
	implements a usable, consumable item that changed the colors of other things
	"""
	pigment = AttributeProperty(default='|=nGrey|n')
	overlay = AttributeProperty(default=True)
	
	def at_pre_use(self, user):
		if not self.db.valid_base_tags:
			user.msg("You can't use this to color anything.")
			return False
		return True

	def use(self, user, targets, **kwargs):
		valid_tags = self.attributes.get("valid_base_tags")
		names = []
		# size validation will go in this loop too
		for obj in targets:
			if any(obj.tags.has(valid_tags, category="design_base", return_list=True)):
				# it's a valid material for this object
				names.append(obj.get_display_name(obj))
				obj.materials.reset() # prevents coloring soft-merge mats, need a better workaround
				for mat in obj.materials.all:
					if self.overlay:
						# user.msg(f"setting {mat} color to {self.pigment}")
						# replace the old color
						obj.materials.set(mat, color=self.pigment)
					else:
						# have to combine with the old color
						old = obj.materials.get(mat, as_dict=True)
						old = old.get("color") if old else None
						if not old:
							# there is no color, just use ours
							obj.materials.set(mat, color=self.pigment)
						else:
							# TODO: implement blend vs add
							new = add_colors(old, self.pigment) or self.pigment
							obj.materials.set(mat, color=new.lower())
				obj.update_desc() # TODO: update for new features system

			self.size -= 1
		
		if not len(names):
			user.msg("You couldn't color any of those things.")
			return
		
		message = "colors {names} with {pigment}"
		if self.size <= 0:
			message += ", using it up"
		message = message.format( names = iter_to_str(names), pigment = self.get_display_name(self) )
		user.emote(message)
		if self.size <= 0:
			self.delete()