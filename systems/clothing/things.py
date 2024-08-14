from utils.strmanip import numbered_name
from evennia.utils import list_to_string

from base_systems.things.base import Thing

class ClothingObject(Thing):
	def get_worn_desc(self, plural=False):
		if plural_desc := self.db.plural_desc:
			description = plural_desc if plural else self.db.desc
		else:
			description = self.db.desc
		description = description[0].lower() + description[1:] if len(description) > 1 else description.lower()
		if description[-1] in [".","!","?"]:
			description = description[:-1]
		# append worn style
		if wearstyle := self.db.worn:
			description = f"{description}, {wearstyle}" if ',' in description else f"{description} {wearstyle}"
		return description

	def crafted_effect(self, inputs=None, skill=None, **kwargs):
		if not inputs or not skill:
			return

		try:
			# skill is expected to be a tuple with the skill name and level
			skill_name, skill_lvl = skill
		except ValueError:
			return

		textures = []
		for obj in inputs:
			texture = obj.attributes.get("texture",None)
			if texture and (texture not in textures):
				textures.append(texture)

		self.db.texture = list_to_string(textures)

	def get_extra_info(self, looker, **kwargs):
		if self.location == looker:
			if self in looker.clothing.all:
				return " (worn)"
			return " (carried)"
		return super().get_extra_info(looker, **kwargs)

	def at_get(self, getter):
		"""
		Clear the "worn" and "covered" status, in case they were somehow set.
		"""
		self.db.worn = None
		self.db.covered_by = None

	def at_give(self, giver, getter, **kwargs):
		"""
		Be sure to remove clothing before giving it
		"""
		if self in giver.clothing.all:
			giver.clothing.remove(self, quiet=True)

	def at_drop(self, dropper, **kwargs):
		"""
		Be sure to remove clothing before dropping it
		"""
		if self in dropper.clothing.all:
			dropper.clothing.remove(self, quiet=True)

	def at_pre_give(self, giver, getter, **kwargs):
		if self.db.covered_by:
			giver.msg("You can't give that away because it's covered by %s." % numbered_name(self.db.covered_by.sdesc.get(),1))
			return False
		return True

	def at_pre_drop(self, dropper, **kwargs):
		if self.db.covered_by:
			dropper.msg("You can't drop that because it's covered by %s." % numbered_name(self.db.covered_by.sdesc.get()))
			return False
		return True