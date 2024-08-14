from evennia.utils.dbserialize import dbserialize, dbunserialize
from base_systems.actions.base import Action, InterruptAction
from . import effects

class SpellAction(Action):
	"""
	A generic spell action base class.
	"""
	move = "spell"
	dbobjs = ['actor', 'target']
	# defines the effect to be applied per element
	effect = None

	def __serialize_dbobjs__(self):
		# logger.log_msg(f'serializing {self}')
		if self.serialized:
			# logger.log_msg('already marked as serialized')
			return
		self.serialized = True
		for attr_name in self.dbobjs:
			if attr := getattr(self, attr_name, None):
				setattr(self, attr_name, dbserialize(attr))

	def __deserialize_dbobjs__(self):
		# logger.log_msg(f'DEserializing {self}')
		if not self.serialized:
			# logger.log_msg('already marked as deserialized')
			return
		for attr_name in self.dbobjs:
			if attr := getattr(self, attr_name, None):
				setattr(self, attr_name, dbunserialize(attr))
		self.serialized = False


	def __init__(self, actor, target, **kwargs):
		self.actor = actor
		self.target = target
		super().__init__(**kwargs)
	
	def start(self, extra_emote, **kwargs):
		if not self.effect:
			self.actor.msg("(That ability is not yet implemented.)")
			return

		if extra_emote:
			self.actor.emote(extra_emote)

		self.do(**kwargs)
		return True

	def do(self, **kwargs):
		# TODO: make the effect have more stacks if there's more of the element in the area
		self.target.effects.add(self.effect, source=self.actor)

		# TODO: the effect should probably do the energy subtraction as upkeep? hmm

	def end(self, *args, **kwargs):
		if args:
			if args[0]:
				self.actor.emote(args[0])
		if self.effect:
			self.target.effects.remove(self.effect, source=self.actor, stacks='all')
		self.actor.do_set_spell()

	def status(self):
		if self.target == self.actor:
			target_str = "yourself"
		else:
			target_str = self.target.get_display_name(self.actor, noid=True)
		if magic := self.actor.effects.get(name='innate magic'):
			color = f"|{magic.color}"
		return f"You have {color}{self.move} magic|n on {target_str}."


_ENHANCEMENT_EFFECTS = {
	'earth': effects.EarthArmor,
	'fire': effects.ShiningFinger,
	'water': '', # TODO: effects.WeatherImmunity,
	'lightning': effects.LightningArmor,
	'plant': effects.MagicPhotosynthesis,
	'light': '', # TODO: this is scrying
	'shadow': '', # TODO: this is teleporting
}

class SelfSpell(SpellAction):
	"""
	Using your innate elemental magic directly on yourself. Mostly.
	"""
	move = "enhancement"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if magic := self.actor.effects.get(name="innate magic"):
			self.effect = _ENHANCEMENT_EFFECTS[magic.element]
		else:
			raise InterruptAction


_TARGET_EFFECTS = {
	'earth': 'base_systems.effects.effect.DirtyEffect',
	'fire': 'base_systems.effects.effects.BurningEffect',
	'water': 'base_systems.effects.effects.WetEffect',
	'lightning': 'systems.electronics.effects.Overload', # multiple stacks handled by elemental strength system
	'plant': effects.EntangleEffect,
	'light': 'base_systems.effects.effects.EmitLightEffect',
	'shadow': '' # TODO: effects.ShadowyEffect
}

class TargetSpell(SpellAction):
	"""
	Using your innate elemental magic on a specific target.
	"""
	move = "targeted"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if magic := self.actor.effects.get(name="innate magic"):
			self.effect = _TARGET_EFFECTS[magic.element]
		else:
			raise InterruptAction


_AREA_EFFECTS = {
	'earth': effects.UnsteadyGroundEffect,
	'fire': '', # TODO: uhh it's hot
	'water': 'systems.weather.effects.FogEffect',
	'lightning': effects.ChargedFieldEffect,
	'plant': effects.GrowthFieldEffect,
	'light': '', # TODO: creates a room illusion, visible even in unnatural darkness
	'shadow': '', # TODO: makes it super dark
}

class AreaSpell(SpellAction):
	"""
	Using your innate magic on your entire (immediate) area.
	"""
	move = "area-effect"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if magic := self.actor.effects.get(name="innate magic"):
			self.effect = _AREA_EFFECTS[magic.element]
		else:
			raise InterruptAction
	
	def do(self, extra_emote, **kwargs):
		if not super().do(extra_emote, **kwargs):
			return
		self.actor.react.add("move", "change_target", handler='archetype', getter='get_spell')
		return True

	def end(self, *args, **kwargs):
		self.actor.react.remove("move", "change_target", handler='archetype', getter='get_spell')
		super().end(*args, **kwargs)

	def change_target(self, *args, **kwargs):
		self.target.effects.remove(self.effect, source=self.actor)
		self.target = self.actor.location
		self.target.effects.add(self.effect, source=self.actor)


# TODO: i may need these, not sure

class ScrySpell(SpellAction):
	"""
	SCRY spell move

	View a location that has enough of an elemental presence to your element, within range.

	Requires:
		a single caster
		a single target
	"""
	move = "scry"

class IllusionSpell(SpellAction):
	"""
	ILLUSION spell move

	Use a free-text emote to create a magical illusion.

	Requires:
		a single caster
		an illusionary emote string
	"""
	move = "illusion"

class ShadowstepSpell(SpellAction):
	"""
	SHADOWSTEP spell move

	Allows the caster to "teleport" to a new, sufficiently dark location.

	Requires:
		a single caster
		a single target location
	"""
	move = "shadowstep"
