from evennia import create_object
from evennia.utils.dbserialize import deserialize
from evennia.utils import logger, lazy_property

from base_systems.effects.base import Effect
from base_systems.maps.building import update_object
from core.ic.behaviors import Behavior, behavior
from data.chargen import ELEMENT_OPTS
from systems.chargen.gen import set_character_feature
from systems.spells.commands import SpellCmdSet
from utils.colors import get_name_from_rgb, rgb_to_hex
from utils.strmanip import numbered_name, strip_extra_spaces

from . import commands
from .effects import ShiftedEffect
from .actions import BiteAction
from .energy import VampireLifeHandler

import switchboard

_ARCHETYPE_ATTR = "arch_data"
_ARCHETYPE_CAT = "systems"

class Archetype(Effect):
	"""
	Base class for defining functional character archetypes.
	
	This handles the basic loading and reliable access API.
	"""
	name = "archetype"
	sight = False
	heal_rate = switchboard.HEAL_RATE
	_default = {}
	cmdsets = tuple()
	behaviors = tuple()

	base_desc = "none"
	
	@property
	def desc(self):
		return self.base_desc

	def __init__(self, handler, *args, **kwargs):
		super().__init__(handler, *args, **kwargs)
		for key, val in self._default.items():
			setattr(self, key, kwargs.get(key, val))


	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		for cmdset in self.cmdsets:
			self.owner.cmdset.add(cmdset, persistent=True)
		for behave_key in self.behaviors:
			self.owner.behaviors.add(behave_key)
	
	def at_delete(self, *args, **kwargs):
		for cmdset in self.cmdsets:
			self.owner.cmdset.remove(cmdset)
		for behave_key in self.behaviors:
			self.owner.behaviors.remove(behave_key)
		super().at_delete(*args, **kwargs)

	def display(self, **kwargs):
		return ""


class WerewolfArch(Archetype):
	"""
	[lore redacted]
	"""	
	# Special abilities:
	# 	shift
	# 	track
	# """
	key = "werewolf"
	base_desc = "beast form"

	_default = {
		"current": "off",
		"forms": {
			"full": { }, # feature dict
			"partial": { }, # feature dict
			"off": None,
		},
		"shifts": {
			(None, "full"): "@Me transforms to full beast mode.",
			("off", "partial"): "@Me gets a lot hairier, sprouting fangs and claws.",
			("full", "partial"): "@Me stands back up on two legs, looking marginally more human.",
			(None, "off"): "@Me looks perfectly human again.",
		},
	}
	
	cmdsets = ( commands.WerewolfCmdSet, )
	behaviors = ( 'WereShifting', )
	heal_rate = switchboard.HEAL_RATE // 2


@behavior
class WereShifting(Behavior):
	priority = 10

	def shift(obj, form, **kwargs):
		if not (archetype := obj.archetype):
			return
		current = archetype.current
		if not form:
			# toggle
			new = None
		elif form.startswith("ful"):
			new = "full"
		elif form.startswith("part"):
			new = "partial"
		elif form.startswith("off"):
			new = "off"
		if not new:
			if current == "off":
				new = "partial"
			else:
				new = "off"
		# same as current form, so not shifting
		elif current == new:
			return

		# TRANSFORMATION TIME
		archetype.current = new
		new_features = archetype.forms.get(new, {})
		if new == "off":
			obj.effects.remove(ShiftedEffect, stacks="all")
		else:
			obj.effects.add(ShiftedEffect, features=new_features)
		# save the current status
		archetype.save()
		# get the emote string based on what you're shifting to and from
		return archetype.shifts.get( (current, new) if new == "partial" else (None, new) )


class MagicAbility(Effect):
	name = "innate magic"

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		element = kwargs.get('element')
		if element not in ELEMENT_OPTS:
			# not entirely sure this works
			self.remove(stacks="all")
			raise ValueError(f"Attempted to create magic ability with invalid element '{element}'.")

		self.element = element
		value = ELEMENT_OPTS[element]
		rgb = value[:3]
		brightness = value[-1]

		if brightness:
			self.color = rgb_to_hex(rgb)
		else:
			color = tuple((v // 2 for v in rgb))
			self.color = rgb_to_hex(color)

		if self.owner.effects.has('systems.archetypes.base.VampireArch'):
			eye_color = get_name_from_rgb(rgb, styled=True)
			
			set_character_feature(self.owner, "eye", color=eye_color)
			self.owner.update_features()

		self.owner.cmdset.add(SpellCmdSet, persistent=True)

	def at_delete(self, *args, **kwargs):
		if self.owner.effects.has('systems.archetypes.base.VampireArch'):
			# reset to a default natural color
			set_character_feature(self.owner, "eye", color="|#5E391Fdark brown|n")
			self.owner.update_features()
		self.owner.cmdset.remove(SpellCmdSet)
		super().at_delete(*args, **kwargs)


class VampireArch(Archetype):
	"""
	[lore redacted]
	"""
	key = "vampire"
	sight = True
	# vampires don't do normal healing
	heal_rate = None
	base_desc = "elemental magic"
	cmdsets = (commands.VampireCmdSet,)
	behaviors = ('VampireAbilities',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.owner._life = VampireLifeHandler(self.owner)
		
	@property
	def desc(self):
		if magic := self.owner.effects.get(name='innate magic'):
			return f"|{magic.color}{magic.element}|n magic"
		else:
			return super().desc
	
	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		# TODO: add `regenerate` trigger

@behavior
class VampireAbilities(Behavior):
	priority = 10

	def feed(obj, target, **kwargs):
		if action := BiteAction(obj, target):
			# self.obj.emote(f"bites @{target.sdesc.get(strip=True)}")
			obj.actions.override(action)
			# del self.obj.db.current_action
			# self.obj.ndb.current_action = action

	def regenerate(obj, *args, **kwargs):
		regen = 'systems.archetypes.effects.VampiricRegen'
		if not obj.effects.has(regen):
			obj.effects.add(regen)

	def get_spell(obj, *args, **kwargs):
		return obj.db.active_spell
	
	def set_spell(obj, action=None):
		if action:
			print(f'action {action}')
			obj.db.active_spell = action
			print(f'spell {obj.db.active_spell}')
		else:
			del obj.db.active_spell


class SorcererArch(Archetype):
	"""
	[lore redacted]
	"""
	key = "sorcerer"
	element = None
	cmdsets = (commands.FamiliarCmdSet,)
	behaviors = ("WitchAbilities",)

	base_desc = "elemental familiar"

	@property
	def desc(self):
		if magic := self.owner.effects.get(name='innate magic'):
			return f"|{magic.color}{magic.element}|n familiar"
		else:
			return super().desc

	@property
	def color(self):
		return self._color

	@color.setter
	def color(self, value):
		if type(value) is not tuple:
			raise ValueError("Element color must be an RGB+ tuple.")

		if self._familiar:
			self.familiar(update={'color': value})
		rgb = value[:3]
		if not value[3]:
			rgb = tuple((v // 2 for v in rgb))
		self._color = rgb_to_hex(rgb)


@behavior
class WitchAbilities(Behavior):
	priority = 10

	def get_spell(obj, *args, **kwargs):
		return obj.db.active_spell
	
	def set_spell(obj, action=None):
		obj.do_familiar(summon=False)
		if action:
			obj.db.active_spell = action
		else:
			del obj.db.active_spell
			obj.do_familiar(summon=True)

	def familiar(obj, *args, **kwargs):
		"""
		interact with the witch's familiar

		Returns:
			familiar (Character)
		"""
		fam = obj.attributes.get('familiar', category='systems')

		if obj_opts := kwargs.get("update"):
			if fam:
				if famname := obj_opts.pop('key', obj_opts.pop('name', None)):
					fam.key = obj.normalize_name(famname)
				build = fam.attributes.get('build',category="systems").deserialize()
				for key in build.keys():
					if key in obj_opts:
						build[key] = obj_opts[key]
				fam.attributes.add('build', build, category="systems")
			else:
				famname = obj_opts.pop('key', obj_opts.pop('name', 'familiar'))
				fam = create_object(
					key=obj.normalize_name(famname),
					attributes=[
						("_sdesc_list", ['{personality}', '{form}', '{persona}'], "systems"),
						('build', {
							'personality': obj_opts.get('personality',''),
							'form': obj_opts.get('form',''), 'persona': 'familiar'}, "systems"),
						('bonded', obj, "systems")],
					typeclass='base_systems.characters.npcs.Familiar',
					home=obj,
					location=None
				)
				obj.attributes.add('familiar', fam, category='systems')
			if color := obj_opts.get('color'):
				if type(color) is tuple:
					rgb = color[:3]
					brightness = color[-1]

					eye_color = get_name_from_rgb(rgb, styled=True)
					if brightness:
						body_color = get_name_from_rgb(rgb, styled=True)
					else:
						rgb = tuple((v // 2 for v in rgb))
						body_color = get_name_from_rgb(rgb, styled=True)
				fam.features.add("eyes", value=eye_color)
				# TODO: give different forms of familiars different body-feature words
				fam.features.add("hide", value=body_color)

		if not fam:
			return None

		if newname := kwargs.get("rename"):
			old = fam.key
			fam.key = obj.normalize_name(newname)
			fam.at_rename(old, newname)

		if "summon" in kwargs:
			if kwargs.get("summon"):
				if spell := obj.db.active_spell:
					spell.status()
					obj.msg("$h(dispel) it before you resummon your familiar.")
				elif fam.location != obj.location:
					fam.location = obj.location
					fam.emote("appears", action_type="move")
			else:
				if fam.location:
					fam.emote("disappears", action_type="move")
					fam.location = None

		if cmd := kwargs.get("cmd"):
			fam.execute_cmd(cmd)

		return fam


class MageArch(Archetype):
	"""
	[lore redacted]
	"""
	key = "wisper"
	sight = True
	# _cmdsets = (WisperCmdSet,)
	base_desc = "magic sense"


class FeyArch(Archetype):
	"""
	[lore redacted]
	"""
	key = "fey"
	base_desc = "glamour"


_ARCHETYPE_KEYS = {
	WerewolfArch.key: WerewolfArch,
	VampireArch.key: VampireArch,
	SorcererArch.key: SorcererArch,
	MageArch.key: MageArch,
#	"fey": FeyArch,
}


from evennia.utils import dedent
ARCHETYPE_INFO = { key: (val.base_desc, dedent(val.__doc__)) for key, val in _ARCHETYPE_KEYS.items() } | {
	# humans
	"human": ("mundane", dedent("""
		[lore redacted]
	"""))
}


def reset_archetype(obj, key=None):
	if archetype := obj.archetype:
		if not key:
			keys = [k for k,v in _ARCHETYPE_KEYS.items() if type(archetype) is v ]
			if keys:
				key = keys[0]
	if archetype:
		obj.effects.delete(archetype)
	if key == "human":
		return
	elif key not in _ARCHETYPE_KEYS:
		raise ValueError(f"Keyword argument '{key}' must be a valid archetype key.")
	obj.effects.add(_ARCHETYPE_KEYS[key])
