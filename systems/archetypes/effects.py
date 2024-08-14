import random

from evennia.utils import inherits_from

from base_systems.effects.base import Effect
from . import actions

_SHIFT_BONUS = 4

class ShiftedEffect(Effect):
	bonus = _SHIFT_BONUS

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		obj = self.handler.obj
		obj.stats.spd.mod += self.bonus
		obj.stats.str.mod += self.bonus
		if new_features := kwargs.get('features'):
			for key, value in new_features.items():
				if key == "fur":
					color = obj.features.get("hair", option="color", default="true")
					value['color'] = color
				obj.features.merge(key, **value, soft=True)

	def at_delete(self, *args, **kwargs):
		obj = self.handler.obj
		obj.stats.spd.mod -= self.bonus
		obj.stats.str.mod -= self.bonus
		obj.features.reset(match={"shifted":True})
		super().at_delete(*args, **kwargs)


_ATTACK_CAP = 20

class HungerEffect(Effect):
	duration = 5

	def at_create(self, *args, **kwargs):
		# TODO: add this as a self-viewable status
		self.handler.obj.msg("|RThe hunger is becoming overwhelming...|n")

	def at_tick(self, *args, **kwargs):
		obj = self.handler.obj
		if obj.tags.has("dead", category='status'):
			return
		if type(obj.actions.current) == actions.BiteAction:
			return
		if self.stacks >= _ATTACK_CAP:
			self._rampage()
		elif random.randint(self.stacks, _ATTACK_CAP) >= _ATTACK_CAP-1:
			self._rampage()
		else:
			self.add()
		obj.prompt()

	def _rampage(self):
		obj = self.handler.obj
		# find a viable target
		from base_systems.characters.base import Character
		from evennia.utils.dbserialize import pack_dbobj
		options = Character.objects.filter_family(db_location=obj.location)
		target = random.choice( [ob for ob in options if ob != obj] )
		obj.msg("|rYour hunger takes over!!|n")
		# this is a non-consensual bite
		from .commands import CmdBite
		CmdBite.bite(obj, target)

class VampiricRegen(Effect):
	duration = 60

	def at_tick(self, *args, **kwargs):
		"""Spend energy in order to heal"""
		spent = 0
		available = self.owner.life.energy
		base_cls = 'base_systems.effects.damage.HealableEffect'

		for obj in self.owner.parts.all():
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
		
		if spent == 0:
			# we had nothing to heal; stop regenerating
			self.remove(stacks="all")
		else:
			self.owner.life.energy -= spent
			self.owner.update_features()
			self.owner.prompt()
		