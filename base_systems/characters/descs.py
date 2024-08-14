from core.ic.descs import DescsHandler
import switchboard


class CharacterDescsHander(DescsHandler):
	"""overridden subclass for custom character-specific handling of descs"""

	def _get_status_descs(self, looker, **kwargs):
		desc_list = []
		if damage := self.obj.damage_status(third=looker!=self.obj):
			desc_list.append(damage)

		if state_descs := super()._get_status_descs(looker, **kwargs):
			desc_list.append(state_descs)

		return "  ".join(desc_list)

	def _get_base_desc(self, looker, **kwargs):
		"""get the base description for this object"""

		desc_str = "$Pron(you) $pconj(are) {build}{pose}."
		pose_str = self.obj.get_pose(fallback=False, looker=looker)
		pose_str = f", {pose_str}" if pose_str else ""
		build_str = switchboard.INFLECT.an(self.obj.build) if self.obj.build else "someone"

		desc_str = desc_str.format(build=build_str, pose=pose_str)

		return desc_str

	def get(self, looker, **kwargs):
		desc_str = super().get(looker, **kwargs)

		if self.obj.archetype:
			if arch_str := self.obj.archetype.display():
				arch_str = " "+arch_str[0].upper()+arch_str[1:]
				desc_str += arch_str

		return desc_str

