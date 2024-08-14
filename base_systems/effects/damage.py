"""Effects for damage types"""

from random import randint
from base_systems.effects.base import Effect
from utils.general import get_classpath

class HealableEffect(Effect):
	"""A parent effect class for all healable damage effects"""

class Bruised(HealableEffect):
	name = "bruised"
	percent = 0
	max_stacks = 0
	feature = "bruise"
	descs = {}
	fading = {}

	def at_create(self, *args, **kwargs):
		self.owner.tags.add("bruised", category="health")
		self.owner.react.add("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})

	def at_add(self, *args, **kwargs):
		# inherit handles stack change
		super().at_add(*args, **kwargs)

		# update visual
		percent = int(100 * (self.stacks / self.owner.stats.integrity.max))
		if percent > self.percent:
			descs = [ d for p,d in self.descs.items() if p >= percent ]
			if descs:
				desc = descs[0]
				self.owner.features.merge(self.feature, **desc)
			self.percent = percent
		
		self.max_stacks = max(self.max_stacks, self.stacks)
		
	def at_remove(self, *args, **kwargs):
		percent = int(100 * (self.max_stacks / self.stacks))

		descs = [ d for p,d in self.fading.items() if p >= percent ]
		if descs:
			desc = descs[0]
			self.owner.features.merge(self.feature, **desc)

		# inherit handles stack change
		super().at_remove(*args, **kwargs)
	
	def at_delete(self, *args, **kwargs):
		self.owner.tags.remove("bruised", category="health")
		self.owner.features.remove(self.feature)
		self.owner.react.remove("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})

	def ouch(self, *args, **kwargs):
		if randint(0,2) < self.stacks//3:
			base = self.owner.baseobj
			if hasattr(base, 'get_sdesc'):
				myname = base.get_sdesc(self.owner, article=False)
			else:
				myname = self.owner.sdesc.get()
			# TODO: randomize message a bit and/or scale with severity
			base.msg(f"You feel a twinge in your {myname}.")


class BrokenBone(HealableEffect):
	name = "broken"

	def at_create(self, *args, **kwargs):
		self.owner.tags.add('broken', category='status')
		self.owner.tags.add('broken', category='health')
		self.owner.react.add("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
	
	def at_add(self, *args, **kwargs):
		stacks = kwargs.get('stacks',1)
		kwargs['stacks'] = stacks*5
		super().at_add(*args,**kwargs)

	def at_delete(self, *args, **kwargs):
		self.owner.tags.remove('broken', category='status')
		self.owner.tags.remove('broken', category='health')
		self.owner.react.add("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})

	def ouch(self, *args, **kwargs):
		if randint(0,2) < self.stacks//3:
			base = self.owner.baseobj
			if hasattr(base, 'get_sdesc'):
				myname = base.get_sdesc(self.owner, article=False)
			else:
				myname = self.owner.sdesc.get()
			# TODO: randomize message a bit and/or scale with severity
			base.msg(f"You feel a sharp pain in your {myname}.")
			# TODO: determine math for this
			self.owner.at_damage(1, source=self.owner)

class Bleeding(HealableEffect):
	name = "bleeding"


class BurnDamage(HealableEffect):
	name = "burned"


class Sprained(HealableEffect):
	name = "sprained"

	def at_create(self, *args, **kwargs):
		self.owner.tags.add('sprained', category='health')
		self.owner.react.add("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})

	def at_delete(self, *args, **kwargs):
		self.owner.tags.remove('sprained', category='health')
		self.owner.react.add("use", "ouch", handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})

	def ouch(self, *args, **kwargs):
		if randint(0,2) < self.stacks//3+1:
			base = self.owner.baseobj
			if hasattr(base, 'get_sdesc'):
				myname = base.get_sdesc(self.owner, article=False)
			else:
				myname = self.owner.sdesc.get()
			# TODO: randomize message a bit and/or scale with severity
			base.msg(f"You feel a sharp pain in your {myname}.")
