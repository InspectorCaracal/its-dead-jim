from evennia.typeclasses.attributes import AttributeProperty

from core.ic.base import BaseObject
from data.software import FILE_EXTENSIONS

class DataObject(BaseObject):
	"""
	An IC-present object that represents digital data.
	"""

	_content_types = ('data',)

	size = AttributeProperty(default=1)
	appearance_template = """
{desc}
"""

	@property
	def filetype(self):
		if not (ft := self.db._filetype):
			return 'data'
		return "/".join(ft)
	
	@filetype.setter
	def filetype(self, value):
		val = str(value)
		val = tuple(val.split('/', 1))
		if len(val) != 2:
			raise ValueError(f"invalid filetype input for {type(self)}: '{value}'")
		self.db._filetype = val

	@property
	def metatype(self):
		if not (ft := self.db._filetype):
			return None
		else:
			return ft[0]
	
	@property
	def extension(self):
		if not (ft := self.db._filetype):
			return ''
		else:
			ft = ft[1].lower()
			return FILE_EXTENSIONS.get(ft, ft)

	def get_display_name(self, looker, **kwargs):
		name = self.name
		if kwargs.get('extension', True):
			name += f".{self.extension}"
		
		return name
	