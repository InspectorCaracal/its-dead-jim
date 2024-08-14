from evennia.utils import iter_to_str, make_iter
from utils.handlers import HandlerBase
from utils.strmanip import strip_extra_spaces

_DEFAULT_DESC = "You see nothing special."

_DEFAULT_STATUS_DESCS = {
	'charred': 'charred and blackened',
	'wet': 'soaking wet',
	'dirty': 'covered with dirt',
}

class DescsHandler(HandlerBase):
	"""Handle the correct rendering of displayable attributes"""
	def __init__(self, obj):
		super().__init__(obj, 'descs', 'systems')
	
	def _get_status_descs(self, looker, **kwargs):
		"""get description strings for the status flags on this object"""
		status_descs = _DEFAULT_STATUS_DESCS | self._data
		states = self.obj.tags.get(category="status",return_list=True)

		desc_list = []
		for state in sorted(states):
			if desc := status_descs.get(state):
				desc_list.append(desc)
			else:
				desc_list.append(state)
		
		if desc_list:
			return f"$Pron(You) $pconj(are) {iter_to_str(desc_list)}."

	def _get_part_descs(self, looker, **kwargs):
		"""get description strings for all externally-visible parts"""
		if not (outside_parts := self.obj.parts.external):
			return []
		
		desc_list = []
		for part in outside_parts:
			if desc := part.get_display_desc(looker, **kwargs):
				desc_list.append(desc)
		
		return desc_list

	def _get_base_desc(self, looker, **kwargs):
		"""get the base description for this object"""
		return self.obj.db.desc

	def get(self, looker, **kwargs):
		if not self.obj.get_lock(looker, 'view'):
			return ''

		descs_list = []

		glance = kwargs.get("glance", False)

		if base_desc := self._get_base_desc(looker, **kwargs):
			descs_list.append(base_desc)

		# if sides := self._get_side_desc(looker, **kwargs):
		# 	descs_list.append(sides)

		if kwargs.get('status', True) and (states := self._get_status_descs(looker, **kwargs)):
			descs_list.append(states)

		if kwargs.get('temp', not glance) and (temp_descs := self._data.get('temp')):
			descs_list.append('  '.join(temp_descs.values()))

		if kwargs.get('features',not glance) and (features := self.obj.features.view):
			descs_list.append(f"$Pron(You) $pconj(have) {features}.")
		
		if kwargs.get('parts',not glance) and (part_descs := self._get_part_descs(looker, **(kwargs | { 'parts': False, 'fallback': False}))):
			descs_list.append('  '.join(part_descs))

		desc_str = strip_extra_spaces("\n\n".join(descs_list))

		if not desc_str and kwargs.get('fallback', True):
			return _DEFAULT_DESC
		else:
			return desc_str
	
	def add(self, key, desc_str, temp=False):
		base_dict = self._data.get('temp', {}) if temp else self._data

		old = base_dict.get(key)
		base_dict[key] = desc_str

		if temp:
			self._data['temp'] = base_dict

		text = f"Description for '{key}' has been set to:\n{desc_str}"
		if old:
			text += f"\n...replacing the previous description of:\n{old}"
		
		self._save()

		return text
	
	def remove(self, key, temp=False):
		if temp:
			if 'temp' not in self._data:
				return
			old = self._data['temp'].pop(key, None)
		else:
			old = self._data.pop(key, None)
		
		if old:
			self._save()
	
		return old
	