from base_systems.effects.base import Effect
from utils.general import get_classpath


class SealedEffect(Effect):
	name = 'sealed'

	def at_create(self, *args, **kwargs):
		self.owner.react.add("open", "unseal", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		self.handler.obj.descs.add("sealed", "$Gp(it) $pconj(has) never been opened.", temp=True)

	def at_delete(self, *args, **kwargs):
		self.owner.react.remove("open", "unseal", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		self.handler.obj.descs.remove("sealed", temp=True)

	def unseal(self, *args, **kwargs):
		self.owner.effects.remove(self, stacks='all')