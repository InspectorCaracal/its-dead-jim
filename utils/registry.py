from shutil import RegistryError
import typing
from class_registry import ClassRegistry

class FallbackRegistry(ClassRegistry):
	def __init__(
		self,
		attr_name: typing.Optional[str] = None,
		unique: bool = False,
		default: typing.Any = None,
	) -> None:
		super().__doc__
		super().__init__(attr_name, unique=unique)
		self.default = default

	def __missing__(self, key: typing.Hashable):
		super().__doc__
		if self.default:
			return self.default
		else:
			return super().__missing__(key)
