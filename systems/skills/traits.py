from evennia.contrib.rpg.traits import StaticTrait, TraitException


class DescTrait(StaticTrait):
	trait_type = "desc_trait"

	default_keys = {
		"base": 0,
		"mod": 0,
		"mult": 1.0,
		"descs": None,
	}

	@staticmethod
	def validate_input(cls, trait_data):
		"""Add extra validation for descs"""
		trait_data = super().validate_input(cls, trait_data)
		# validate descs
		descs = trait_data["descs"]
		if isinstance(descs, dict):
			if any(
				not (isinstance(key, (int, float)) and isinstance(value, str))
				for key, value in descs.items()
			):
				raise TraitException(
					f"Trait descs must be defined on the form {{number:str}} (instead found {descs})."
				)
			if sorted(descs.keys()) != list(descs.keys()):
				raise TraitException(
					f"Trait descs must be defined in ascending order (instead given {descs.keys()})."
				)
		return trait_data

	@property
	def desc(self):
		"""
		Retrieve descriptions of the current value, if available.
		Returns:
			str: The description describing the `value` value.
				If not found, returns the empty string.
		"""
		if not (descs := self._data["descs"]):
			return ""
		value = self.base + self.mod
		filtered = [ txt for bound, txt in descs.items() if bound >= value ]
		if not filtered:
			# somehow above the defined descs: grab the highest known desc
			return list(descs.values())[-1]
		# we want the lowest item that passed
		return filtered[0]

	def levels_to_desc(self, desc):
		"""
		Returns the number of levels required to get to the listed desc.

		If the desc is invalid or already passed, returns 0.
		"""
		if not (descs := self._data["descs"]):
			# this has no descs
			return 0
		desc = desc.lower().strip()
		value = self.base + self.mod
		current_desc = self.desc
		if desc == 'next':
			# desc keys are caps, so we can find the current desc's key and add 1
			level = [ key for key, val in descs.items() if val.lower() == current_desc ]
			if not level:
				# who knows how this would happen
				return 0
			level = level[0] + 1
		else:
			# desc keys are caps, so we want to get the highest key below desc and add 1
			levels = []
			for key, val in descs.items():
				if val.lower() == desc:
					break
				levels.append(key)
			if not level:
				# it's the lowest tier, we can't raise to it
				return 0
			# use the highest filtered key
			level = level[-1] + 1

		# get the difference
		if level > value:
			return level - value
		else:
			return 0

