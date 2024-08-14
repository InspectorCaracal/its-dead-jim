from utils.handlers import HandlerBase


_MAX_ENERGY = 100
_EXHAUSTION = 10

_RESTING_EFFECT = "base_systems.effects.effects.RestingEffect"

class LifeHandler(HandlerBase):
	"""manage energy and hunger calculations"""
	def __init__(self, obj, **kwargs):
		super().__init__(obj, "life", "systems", default_data={"hunger":0,"energy":_MAX_ENERGY})

	@property
	def status(self):
		"""return a dict of the current life-data"""
		return dict(self._data)

	@property
	def energy(self):
		return self._data.get('energy')
	
	@energy.setter
	def energy(self, value):
		# this is kind of a hacky way to verify it's numeric but it's fine
		value += 0
		energy = max(0,min(value, _MAX_ENERGY))
		self._data['energy'] = energy
		self._save()
		if self._data['energy'] < _MAX_ENERGY and not self.obj.effects.has(_RESTING_EFFECT):
			self.obj.effects.add(_RESTING_EFFECT)

		if energy < _EXHAUSTION and not self.obj.tags.has("unconscious", category="status"):
			# time to collapse
			self.obj.msg("You've pushed yourself to exhaustion.")
			self.obj.emote("collapses, unconscious.")
			self.obj.actions.clear()
			self.obj.tags.remove(category="status")
			self.obj.tags.add("unconscious", category="status")
			self.obj.tags.add("lying down", category="status")
			self.prompt() # NOTE: may not want this here


	@property
	def hunger(self):
		return self._data.get('hunger')

	@hunger.setter
	def hunger(self, value):
		# this is kind of a hacky way to verify it's numeric but it's fine
		value += 0
		if hgr := self._data.get('hunger'):
			self._data['hunger'] = max(0,min(value, _MAX_ENERGY))
		else:
			self._data['hunger'] = value
		self._save()

	def recover(self, quiet=False):
		"""
		recover energy

		returns True if fully rested, False otherwise
		"""
		obj = self.obj
		energy = self._data['energy']
		hunger = self._data['hunger']
		message = ""
		prompt = False
		if energy < _MAX_ENERGY:
			diff = _MAX_ENERGY - energy
			regain = 0
			# if lying down, get a bonus +2
			if obj.tags.has("lying down", category="status"):
				regain += 2
				prompt = True
			# otherwise, if sitting, get a bonus +1
			elif obj.tags.has("sitting", category="status"):
				regain += 1
				prompt = True
			# use hunger if below threshold
			if energy < _MAX_ENERGY-hunger:
				hunger += 1
				regain += 1
				prompt = True
			energy += min(diff, regain)
			self._data = { "energy": energy, "hunger": hunger }
			self._save()
			if energy >= _MAX_ENERGY:
				message = "You feel fully rested."
		if obj.tags.has("unconscious", category="status") and energy > _EXHAUSTION:
			message = "You regain consciousness."
			obj.tags.remove("unconscious", category="status")
			prompt = True

		# TODO: only send prompt if the words change
		if not quiet:
			if message:
				obj.msg( (message, {"type": "status"}) )
			if prompt:
				obj.prompt()
		
		return self.energy == _MAX_ENERGY
		
