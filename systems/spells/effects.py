from random import shuffle
from evennia.utils import logger, inherits_from
from base_systems.effects.effects import ImmobileEffect
from base_systems.effects.base import Effect, AreaEffect, StatBuffEffect
from switchboard import NOT_STANDING
from utils.general import get_classpath

# TODO: WRITE TESTS FOR THESE!!!

class SpellFieldEffect(AreaEffect):
	start_msg = ''
	end_msg = ''
	desc = ''
	
	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		if self.start_msg:
			self.handler.obj.emote(self.start_msg, from_obj=self.handler.obj.location, anonymous_add=False)
		if self.desc:
			self.handler.obj.descs.add(self.name, self.desc, temp=True)

	def at_delete(self, *args, **kwargs):
		if text := self.end_msg:
			self.handler.obj.emote(text, from_obj=self.handler.obj.location, anonymous_add=False)
		if self.desc:
			self.handler.obj.descs.remove(self.name, temp=True)
		super().at_delete(*args, **kwargs)

class ChargedFieldEffect(SpellFieldEffect):
	name = "charged field"
	pulse = "systems.electronics.effects.Overload"
	start_msg = "A prickle of electricity fills the air."
	end_msg = "The static-like charge in the air fades away."
	desc = "The air here feels charged with electricity."

class UnsteadyGroundEffect(SpellFieldEffect):
	name = "unsteady ground"
	pulse = "base_systems.effects.effects.OffBalanceEffect"
	start_msg = "The ground rumbles and begins to shake."
	end_msg = "The vibrations through the ground fade away."
	desc = "The ground here shifts and vibrates beneath your feet."
	block = (NOT_STANDING, "status")

# TODO: this should probably NOT be a pulsing effect field but rather
# a ticking effect that directly modifies target contents
class GrowthFieldEffect(SpellFieldEffect):
	pulse = "systems.spells.effects.Growth"


class EntangleEffect(Effect):
	# TODO: emote on adding stacks
	def at_create(self, *args, source=None, **kwargs):
		super().at_create(*args, source=source, **kwargs)
		self.handler.obj.descs.add("immobile", "held tightly by unnatural vines")
		text = f"Vines erupt from the ground, grabbing hold of @{self.handler.obj.name}"
		self.handler.add(ImmobileEffect)
		self.handler.obj.emote(text, anonymous_add=False)

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		text = f"The vines wrapped around @{self.handler.obj.name} wither and fall away."
		self.handler.obj.descs.remove("immobile")
		self.handler.remove(ImmobileEffect)
		self.handler.obj.emote(text, anonymous_add=False)

class MagicPhotosynthesis(Effect):
	duration = 60
	recovery = 1

	def at_tick(self):
		# TODO: how do i check if we are in sunlight or sun-equivalent light?
		base_cls = 'base_systems.effects.damage.HealableEffect'
		owner = self.handler.obj
		available = self.recovery

		for obj in shuffle(owner.parts.all()):
			spendme = 0
			if spent >= available:
				break
			if obj.stats.integrity.current < obj.stats.integrity.max:
				obj.stats.integrity.current += 1
				spendme = 1
			# for now, we'll do 1 energy = 1 damage recovery on 1 part
			# the more parts that need to heal, the more energy it costs per tick
			for effect in obj.effects.all():
				if inherits_from(effect, base_cls):
					effect.remove()
					spendme = 1

			spent += spendme
		
		if spent > 0:
			owner.update_features()
			owner.prompt()


class BarrierEffect(Effect):
	"""
	This effect can only be used on exits.
	"""
	mods = {}

	@property
	def mod(self):
		if self.mods:
			return max(self.mods.values())
		return 0

	def at_create(self, *args, source=None, name=None, **kwargs):
		super().at_create(*args, source=source, **kwargs)
		logger.log_msg(f"created new barrier with {self.sources}")

		self.mods = {}
		obj = self.handler.obj
		self.backup_verb = obj.db.verb
		obj.db.verb = "climb"
		self.backup_error = obj.db.err_traverse
		obj.db.err_traverse = "That's too difficult to climb."
		self.backup_skill = obj.db.skill_req
		obj.db.skill_req = "athletics"
		self.backup_name = obj.key
		if name:
			obj.key = name
			obj.at_rename(self.backup_name, name)

	def at_add(self, *args, **kwargs):
		super().at_add(*args, **kwargs)
		logger.log_msg(f"added barrier with {self.sources}")
		obj = self.handler.obj
		# remove previous mod
		obj.stats.skill.mod -= self.mod

		source = kwargs.get('source', None)
		mod = kwargs.get('mod', 1)
		if source in self.mods:
			self.mods[source] = max(self.mods[source], mod)
		else:
			self.mods[source] = mod
		# add new mod
		obj.stats.skill.mod += self.mod

	def at_remove(self, *args, **kwargs):
		obj = self.handler.obj
		# remove previous mod
		obj.stats.skill.mod -= self.mod
		source = kwargs.get('source',None)
		if source not in self.sources:
			if source in self.mods:
				del self.mods[source]
		# add new mod
		obj.stats.skill.mod += self.mod
		super().at_remove(*args, **kwargs)

	def at_delete(self, *args, **kwargs):
		obj = self.handler.obj
		if self.backup_verb:
			obj.db.verb = self.backup_verb
		else:
			del obj.db.verb
		if self.backup_error:
			obj.db.err_traverse = self.backup_error
		else:
			del obj.db.err_traverse
		if self.backup_skill:
			obj.db.skill_req = self.backup_skill
		else:
			del obj.db.skill_req

		obj.stats.skill.mod -= self.mod
		name = obj.key
		obj.key = self.backup_name
		obj.at_rename(name, self.backup_name)
		super().at_delete(*args, **kwargs)

class LightningArmor(StatBuffEffect):
	name = "lightning armor"
	bonus = 2
	stat = 'spd'

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		# TODO: add special messaging/description
		self.handler.obj.emote(self.start_msg)
		self.handler.obj.descs.add(self.name, self.desc, temp=True)

	def at_delete(self, *args, **kwargs):
		# TODO: remove special messaging/description
		super().at_delete(*args, **kwargs)

# TODO: make these self-enhancement spells share a parent class that handles messaging/descs
class EarthArmor(Effect):
	name = "earth armor"
	bonus = 2
	start_msg = "(rocky armor start)"
	end_msg = "(rocky armor end)"
	desc = "(rocky armor description)"

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.react.add('on_defense', 'modify_damage', handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		self.handler.obj.emote(self.start_msg)
		self.handler.obj.descs.add(self.name, self.desc, temp=True)

	def at_delete(self, *args, **kwargs):
		self.handler.obj.react.remove('on_defense', 'modify_damage', handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		self.handler.obj.emote(self.end_msg)
		self.handler.obj.descs.remove(self.name, temp=True)
		super().at_delete(*args, **kwargs)

	def modify_damage(self, damaged_obj, damage, **kwargs):
		"""Modify the incoming damage dict"""
		# TODO: take this out once i change damage to a dict
		if type(damage) is int:
			return
		defense_per_type = (self.bonus * self.stacks) / len(damage.keys())
		for dmg_type, dmg in damage.items():
			damage[dmg_type] = dmg - defense_per_type


class ShiningFinger(Effect):
	name = "fire armor"
	bonus = 2
	desc = "$Gp(it) $pconj(looks) like $gp(it)'s on fire!"

	# TODO: redo this to use a StatBuffEffect on the hands instead

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.react.add('on_hit', 'apply_heat', handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		self.handler.obj.emote(self.start_msg)
		for obj in self.handler.obj.parts('hand', part=True):
			obj.descs.add(self.name, self.desc, temp=True)
			obj.stats.dmg.mod += self.bonus
		# TODO: how do we handle removing the effect from a hand that gets removed

	def at_delete(self, *args, **kwargs):
		self.handler.obj.react.remove('on_hit', 'apply_heat', handler='effects', handler_args=(get_classpath(self),), handler_kwargs={'name': self.name})
		for obj in self.handler.obj.parts('hand', part=True):
			obj.descs.remove(self.name, temp=True)
			obj.stats.dmg.mod -= self.bonus
		super().at_delete(*args, **kwargs)

	def apply_heat(self, obj, target, damage, **kwargs):
		"""Apply heat to the target"""
		# TODO: this will change the damage type
		# defense_per_type = self.bonus / len(damage.keys())
		# for dmg_type, dmg in damage.items():
		# 	damage[dmg_type] = dmg - defense_per_type