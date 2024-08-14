from evennia.utils import logger
from random import choice, randrange
from base_systems.effects.base import Effect

class RestingEffect(Effect):
	name = 'resting'
	duration = 10

	def at_tick(self, *args, **kwargs):
		"""
		Code to be executed when the effect "ticks", i.e. the internal timer loops.
		"""
		super().at_tick(*args, **kwargs)
		obj = self.handler.obj
		if obj.life.recover():
			self.remove(stacks="all")


class ImmobileEffect(Effect):
	name = 'immobile'

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.tags.add("immobile", category="status")
		self.handler.obj.msg("You have been immobilized.")

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.tags.remove("immobile", category="status")
		self.handler.obj.msg("You are no longer immobilized.")


class BurningEffect(Effect):
	name = 'burning'
	duration = 10
	block = ("fire", "protect_against")
	negate = "base_systems.effects.effects.WetEffect"
	# TODO: data entry, add more emotes
	strings = (
		"Flames crackle ominously around @{sdesc}.",
		"Tongues of fire lick at @{sdesc}."
		)

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.emote("bursts into flames")

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.emote("The fire on @me goes out.")

	def at_add(self, *args, **kwargs):
		obj = self.handler.obj
		if obj.tags.has("fire", category="protect_against"):
			self.handler.remove(self)
			return
		super().at_add(*args, **kwargs)

	def at_tick(self, *args, **kwargs):
		"""
		Code to be executed when the effect "ticks", i.e. the internal timer loops.
		"""
		super().at_tick(*args, **kwargs)
		stacks = self.stacks
		obj = self.handler.obj
		obj.at_damage(stacks)
		obj.tags.add("charred", category="status")
		spread = []
		base = obj.baseobj
		spread.extend(base.parts.all())
		if base != obj:
			spread.append(base)
		spread.extend(obj.contents)
		if obj.location:
			spread.append(obj.location)
		spread = [ob for ob in spread if hasattr(ob, 'at_damage')]
		if type(self.block) is tuple:
			tagname, tagcat = self.block
		else:
			tagname = self.block
			tagcat = None
		for item in spread:
			if tagname:
				if obj.tags.has(tagname, category=tagcat):
					continue
			if randrange(50) < stacks:
				item.effects.add(BurningEffect)

		# randomized emote
		if not randrange(4):
			obj.emote(choice(self.strings).format(sdesc=obj.sdesc.get(strip=True)), anonymous_add=False)


class WetEffect(Effect):
	name = 'wet'
	block = ("water", "protect_against")
	negate = "base_systems.effects.effects.BurningEffect"

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.tags.add("wet", category="status")

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.tags.remove("wet", category="status")

	# TODO: make wetness do damage to vulnerable objects like fire

	# TODO: make wetness potentially spread on contact


class DirtyEffect(Effect):
	# TODO: add tiered descs for this, similar to bruising features
	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.descs.add("dirty", "$Gp(it) $pconj(is) covered in dirt.", temp=True)

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.descs.remove("dirty", temp=True)


class OffBalanceEffect(Effect):
	name = 'offbalance'
	duration = 1
	block = None

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.tags.add("off-balance", category="status")

	def at_delete(self, *args, **kwargs):
		self.handler.obj.tags.remove("off-balance", category="status")
		super().at_delete(*args, **kwargs)

	def at_tick(self, *args, **kwargs):
		"""
		Check whether or not we fall over or recover some balance
		"""
		stacks = self.stacks
		obj = self.handler.obj
		# if we're already falling, clear
		if obj.effects.has(FallingEffect):
			self.remove(stacks="all")
			return

		super().at_tick(*args, **kwargs)
	
		check = 0
		# get the max of the relevant stats
		if stat := obj.stats.get('pos'):
			check = max(check,stat.value)
		if stat := obj.stats.get('spd'):
			check = max(check,stat.value)
		if stat := obj.stats.get('stab'):
			check = max(check,stat.value)
		if stacks > check:
			# we fall down!
			obj.effects.add(FallingEffect, stacks=1, duration=1)
			self.remove(stacks="all")
		else:
			# we successfully remove one stack
			self.remove(stacks=1)


class FallingEffect(Effect):
	name = 'falling'
	duration = 5
	block = None
	ticks = 0

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.emote("falls!")

	def at_delete(self, *args, **kwargs):
		self.handler.obj.at_damage(2**self.ticks, damage_type='impact')
		super().at_delete(*args, **kwargs)

	def at_tick(self, *args, **kwargs):
		"""
		Code to be executed when the effect "ticks", i.e. the internal timer loops.
		"""
		super().at_tick(*args, **kwargs)
		stacks = self.stacks
		obj = self.handler.obj
		if self.stacks <= self.ticks:
			# time to hit the floor
			obj.emote("hits the ground!")
			obj.tags.add('lying down', category='status')
			self.remove(stacks="all")
		elif self.ticks:
			obj.emote(f"continues falling")
		self.ticks += 1

class EmitLightEffect(Effect):
	name = 'emit-light'

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		if not self.handler.obj.stats.get('light'):
			self.handler.obj.stats.add('light', trait_type='static', base=0, min=0)

	def at_add(self, *args, **kwargs):
		super().at_add(*args, **kwargs)
		# add stacks to brightness
		# TODO: rework lit-ness to use stats
		self.handler.obj.stats.light.mod += kwargs.get('stacks', 1)

	def at_remove(self, *args, **kwargs):
		super().at_remove(*args, **kwargs)
		# remove stacks from brightness
		# TODO: rework lit-ness to use stats
		self.handler.obj.stats.light.mod -= kwargs.get('stacks', 1)


class CoveredEffect(Effect):
	name = "covered"

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.tags.add('hidden', category='systems')
	
	def at_delete(self, *args, **kwargs):
		self.handler.obj.tags.remove('hidden', category='systems')
		super().at_delete(*args, **kwargs)
		