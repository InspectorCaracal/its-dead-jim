_MAX_ENERGY = 200
_EXHAUSTION = 20

_HUNGER_EFFECT = "systems.archetypes.effects.HungerEffect"

class VampireLifeHandler:
	"""manage energy and hunger calculations"""
	def __init__(self, obj, **kwargs):
		self.obj = obj
		if not obj.attributes.has("life", category="systems"):
			obj.attributes.add("life", _MAX_ENERGY, category="systems")
		self.load()
	
	def load(self):
		self._energy = self.obj.attributes.get("life", category="systems")
		try:
			self._energy += 0
		except TypeError:
			self._energy = _MAX_ENERGY
			self.save()

	def save(self):
		self.obj.attributes.add("life", self._energy, category="systems")

	@property
	def status(self):
		"""return a dict of the current life-data"""
		return { 'energy': self._energy // 2, 'hunger': (_MAX_ENERGY-self._energy) // 2 }

	@property
	def energy(self):
		return self._energy
	
	@energy.setter
	def energy(self, value):
		# this is kind of a hacky way to verify it's numeric but it's fine
		value += 0
		self._energy = min(value, _MAX_ENERGY)
		self.save()
		if self._energy <= 0:
			self.obj.tags.add("dead", category="status")
			self.obj.tags.remove("sitting", category="status")
			self.obj.tags.add("lying down", category="status")
			self.obj.emote("crumples lifelessly")
			self.obj.msg("|rYour life force is depleted. Without help, you will never awaken.|n")
		elif self.obj.tags.has("dead", category='status'):
			self.obj.tags.remove("dead", category="status")
			self.obj.tags.remove("lying down", category="status")
			self.obj.tags.add("sitting", category="status")
			self.obj.emote("suddenly sits up")
			self.obj.msg("You regain a semblance of life.")
		if self._energy <= _EXHAUSTION and not self.obj.effects.has(_HUNGER_EFFECT):
			self.obj.effects.add(_HUNGER_EFFECT)
		elif self._energy > _EXHAUSTION and self.obj.effects.has(_HUNGER_EFFECT):
			self.obj.effects.remove(_HUNGER_EFFECT, stacks="all")

	@property
	def hunger(self):
		return _MAX_ENERGY - self._energy
	
	@hunger.setter
	def hunger(self, value):
		pass

	def recover(self, **kwargs):
		"""vampires can't naturally recover energy"""
		return True
