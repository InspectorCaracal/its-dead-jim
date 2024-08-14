"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
# base imports
import time
from collections import Counter, defaultdict
from random import choices 

# core evennia imports
from django.conf import settings
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import logger, lazy_property, iter_to_str, inherits_from
from evennia.utils.dbserialize import deserialize
from evennia.utils.utils import latinify

# core project imports
import switchboard
from core.ic.base import BaseObject

# other project imports
from base_systems.actions.queue import ActionQueue
from base_systems.actions.counterqueue import CounteractQueue
from systems.chargen.gen import init_bodyparts, init_stats
from systems.clothing.handler import ClothingHandler
from systems.crafting.recipe_book import RecipeHandler
from systems.skills.handler import SkillsHandler
from systems.skills.skills import init_skills
from utils.timing import delay_iter
from utils.colors import strip_ansi
from utils.strmanip import get_band, strip_extra_spaces

# local system imports
from .descs import CharacterDescsHander
from .energy import LifeHandler
from .timestamps import TimestampHandler


# funcparser
from evennia.utils.funcparser import FuncParser, ACTOR_STANCE_CALLABLES
from utils.funcparser_callables import FUNCPARSER_CALLABLES as LOCAL_FUNCPARSER_CALLABLES
PARSER = FuncParser(ACTOR_STANCE_CALLABLES | LOCAL_FUNCPARSER_CALLABLES)


class Character(BaseObject):

	gender = AttributeProperty(default="plural")
	size = AttributeProperty(default=8)

	@property
	def archetype(self):
		return self.effects.get(name='archetype')

	### Movement ###
	@property
	def movement(self):
		verb = ''
		if self.tags.has("off-balance", category="status"):
			verb = "stumbles"
		elif self.speed < 5:
			verb = "runs"
		if not verb:
			verb = self.db.movement or "walks"
		return verb

	@movement.setter
	def movement(self, value):
		# make work right later
		self.db.movement = value

	@property
	def speed(self):
		# if start := self.ndb.speed_start:
		# 	if end := self.ndb.speed_end:
		# 		return end - start
		# i take it back
		if end := self.ndb.speed_end:
			return time.time() - end
		return 10000
	
	def at_pre_move(self, *args, **kwargs):
		# well this is a janky stairway
		for key, val in self.holding(part=None).items():
			if val.baseobj.location == self.location:
				if not self.unhold(hand=key):
					return False
		return super().at_pre_move(*args, **kwargs)

	def at_pre_craft(self, user, *args, **kwargs):
		# you cannot craft with an actual character, only parts of one
		return False

	### Stats and Skills ###
	@lazy_property
	def skills(self):
		return SkillsHandler(self)

	@lazy_property
	def recipes(self):
		return RecipeHandler(self)

	### Combat and Moves ###
	@property
	def wielded(self):
		# TODO: ability to actually equip weapons and check for that here
		# sort these by handedness later
		return self.parts.search("hand")

	def at_damage(self, damage, **kwargs):
		"""Distribute damage to parts, by size"""
		# TODO: make incoming damage arg be a dictionary of damage types
		self.on_defense(damage, source=kwargs.get('source'))
		parts = self.parts.all()
		weights = [ 3**p.size for p in parts ]
		damaged = Counter(choices(parts, weights=weights,k=int(damage)))
		if not kwargs.get('quiet') and len(damaged.keys()) > 3:
			# TODO: use a scaled percent-of-total word here instead
			self.msg(f"You take damage all over.")
			kwargs['quiet'] = True
		for obj, dmg in damaged.items():
			obj.at_damage(dmg, notify=False, **kwargs)
		self.on_damaged(damage, source=kwargs.get('source'))
		# TODO: change this down here to have archetypes add their own reaction
		# if callme := getattr(self.archetype, "at_damage", None):
		# 	callme(damage, **kwargs)
		self.update_features()
		self.prompt()
	
	def at_part_damaged(self, damage, **kwargs):
		self.on_damaged(damage, source=kwargs.get('source'))
		# TODO: change this down here to have archetypes add their own reaction
		# if callme := getattr(self.archetype, "at_damage", None):
		# 	callme(damage, **kwargs)

	def heal(self, timediff):
		"""Called by the timestamp handler"""
		heal_rate = switchboard.HEAL_RATE
		if archetype := self.archetype:
			heal_rate = archetype.heal_rate
		
		if heal_rate is None:
			# some characters don't have natural healing
			return False

		# FIXME: integer division without capturing remainder means healing time can potentially be lost
		days = timediff // heal_rate
		if not days:
			return False

		healable_effects = []
		base_cls = 'base_systems.effects.damage.HealableEffect'
		for obj in self.parts.all():
			if obj.stats.integrity.current < obj.stats.integrity.max:
				obj.stats.integrity.current += days
			healable_effects += [ effect for effect in obj.effects.all() if inherits_from(effect, base_cls)]

		for effect in healable_effects:
			effect.remove(stacks=days)

		return True

	@property
	def life(self):
#		self.archetype
		if not hasattr(self, '_life'):
			self._life = LifeHandler(self)
		return self._life

	@lazy_property
	def actions(self):
		return ActionQueue(self)

	@lazy_property
	def counteract(self):
		return CounteractQueue(self)

	### Description ###
	@lazy_property
	def descs(self):
		return CharacterDescsHander(self)

	def prompt(self,**kwargs):
		# TODO: add in prompt account toggle
		msg = self.get_status()
		if msg != self.ndb.last_prompt:
			self.msg(prompt=msg)
			self.ndb.last_prompt = msg

	@property
	def build(self):
		return self.features.get('build', force=True).rsplit(' ', maxsplit=1)[0]

	def get_display_name(self, looker, strip=True, article=True, **kwargs):
		return super().get_display_name(looker, strip=True, article=True, **kwargs)
	
	# TODO: filter out items you're holding from the `carried` section of your desc

	def get_pose(self, **kwargs):
		looker = kwargs.get("looker")
		# add held things to pose
		held_dict = defaultdict(list)
		# collect all held objects together
		for hand, obj in self.holding(part=None).items():
			held_dict[obj].append(hand)
		holding_list = []
		pron = "your" if looker == self else "$gp(their)"
		for obj, hands in held_dict.items():
			holding_list.append( f"{obj.get_display_name(looker=looker, article=True, noid=True)} with {pron} {iter_to_str( [hand.sdesc.get() for hand in hands] )}" )

		if holding_list:
			held_str = f"holding {iter_to_str(holding_list)}"
			return super().get_pose(extras=[held_str], **kwargs)
		else:
			return super().get_pose(**kwargs)

	def _filter_things(self, thing_list, **kwargs):
		"""customize what things to exclude from the thing list"""
		exclude = self.decor.all() + self.clothing.all
		return [thing for thing in thing_list if thing not in exclude]

	def _format_display_things(self, things_str, **kwargs):
		return f"$Pron(you) $pconj(are) carrying:\n {things_str}."
		
	@lazy_property
	def clothing(self):
		return ClothingHandler(self)


	def get_display_decor(self, looker, **kwargs):
		if outfit := self.clothing.get_outfit(looker=looker):
			return "\n$Pron(you) $pconj(are) wearing:\n  " + "\n  ".join(outfit)

	### General ###
	@lazy_property
	def timestamps(self):
		return TimestampHandler(self)

	@property
	def can_see(self):
		if not self.location:
			return True
		return not self.tags.has("blinded") and self.location.lighting > 0

	@property
	def can_speak(self):
		mouths = self.parts.search('mouth')
		if not mouths:
			return False
		return any( [ not (obj.db.holding or obj.tags.has("disabled", category="status")) for obj in mouths ] )

	def get_status(self, third=False, **kwargs):
		msg = []
		status_dict = self.life.status
		energy_msg = get_band("energy", status_dict['energy'])
		hunger_msg = get_band("hunger", status_dict['hunger'], invert=True)
		values = [energy_msg]
		if len(hunger_msg):
			values.append(hunger_msg)
		if pose := self.get_pose(fallback=False):
			values.append(pose)
		if third:
			prefix = "$Gp(they) $pconj(is)"
			prefix = PARSER.parse(prefix, caller=self)
		else:
			# do the actual xp display here
			prefix = "You are"
		msg.append("{} {}.".format(prefix, iter_to_str(values)))

		if text := self.damage_status(third=third):
			msg.append(text)

		if not third and self.can_get_spell:
			if spell := self.do_get_spell():
				msg.append(spell.status())
		if active := self.actions.status():
			msg.append(active)


		return "\n".join(msg)
	
	def damage_status(self, third=False, **kwargs):
		"""Return an assessment of the total health status"""
		tags = set()
		current = 0
		max_hp = 0
		severe = {}

		for part in self.parts.all():
			max_hp += part.stats.integrity.max
			current += part.stats.integrity.value
			part_tags = part.tags.get(category="health", return_list=True)
			if any( t in part_tags for t in switchboard.SEVERE_TAGS ):
				severe[part] = part_tags
			else:
				tags.update(part_tags)


		pct = 100*(current/max_hp) if max_hp else 0
		if pct < 98:
			overall_msg = get_band("health", pct)
		else:
			overall_msg = "overall in great shape"

		if third:
			prefix = "$Gp(they) $pconj(are)"
			prefix = PARSER.parse(prefix, caller=self)
			parts_template = "$Gp(their) {part} is {status}."
		else:
			prefix = "You are"
			parts_template = "Your {part} is {status}."
		
		# time to render!
		part_str = " ".join( parts_template.format(part=key.sdesc.get(), status=iter_to_str(val)) for key, val in severe.items() )
		part_str = PARSER.parse(part_str, caller=self)
		message = [f"{prefix} {overall_msg}."]
		if tags:
			message.append(f"{prefix} feeling {iter_to_str(tags)}.")
		if part_str:
			message.append(part_str)
		
		return strip_extra_spaces(" ".join(message))

	def at_object_creation(self):
		"""
		Called once when the object is created.
		"""
		super().at_object_creation()
		self.db.onword = "on"

	# 	self.tags.add("generating")
	# 	self.attributes.add('build', { "persona": "nobody" }, category="systems")
	# 	self.sdesc.add(["persona"])
	# 	self.vdesc.add("voice", "voice")
	# 	self.db.onword = "on"

	# 	# initialize the timestamps
	# 	stamps = ('heal',)
	# 	self.timestamps.stamp(*stamps)

	# 	if self.id == 1:
	# 		return
	# 	init_stats(self)
	# 	init_skills(self)
	# 	gener = init_bodyparts(self)
	# 	delay_iter(gener, 0.2)

	def at_server_reload(self):
		super().at_server_reload()
		if self.archetype:
			self.archetype.save()
		if current := self.actions.current:
			if hasattr(current, '_task'):
				current._task.cancel()
				del current._task
		self.actions._save()


	def at_server_start(self):
		super().at_server_start()
#		self.archetype = load_archetype(self, self.archetype_key)
		self.actions

	def at_look(self, target, **kwargs):
		# if self.location and not self.location.nattributes.get("lit", True):
			# return "It's too dark to see anything."
		if not kwargs.get('visibility') and self.location:
			kwargs['visibility'] = self.location.visibility
		description = super().at_look(target, **kwargs)
		if isinstance(description, tuple):
			description = (PARSER.parse(description[0], caller=target, receiver=self), *description[1:])
		elif isinstance(description, str):
			description = PARSER.parse(description, caller=target, receiver=self)
		return description

	def at_post_puppet(self, **kwargs):
		self.msg(f"You become {self.get_display_name(self)}. $h(quit) to return to character selection.")
		if self.location.get_lock(self, "view"):
			message = self.at_look(self.location)
			if isinstance(message,tuple):
				message = ( message[0], message[1] | {"target": "location", "clear": True} )
			else:
				message = (message, {"target": "location", "clear": True})
			self.msg(message)

	def get_all_contents(self):
		"""Returns a list of all objects carried by this character or contained in their clothing"""
		contents = self.contents
		for obj in self.clothing.all:
			contents += obj.get_all_contents()
		
		return contents

	def at_pre_unpuppet(self, account=None, session=None, **kwargs):
		if spell := self.db.active_spell:
			spell.end()
			del self.db.active_spell
		super().at_pre_unpuppet(**kwargs)

	def at_pre_say(self, message, **kwargs):
		"""
		Called before the object says or whispers anything, return modified message.

		Args:
			message (str): The suggested say/whisper text spoken by self.
		Keyword Args:
			whisper (bool): If True, this is a whisper rather than a say.

		"""
		if target := kwargs.get("target", ''):
			target = f" to @{strip_ansi(target.sdesc.get())}"
		if kwargs.get("whisper"):
			return f'@Me whispers{target}, "{message}"'
		return f'@Me says{target}, "{message}"'

	def process_language(self, text, speaker, language, **kwargs):
		"""
		Allows to process the spoken text, for example
		by obfuscating language based on your and the
		speaker's language skills. Also a good place to
		put coloring.

		Args:
			text (str): The text to process.
			speaker (Object): The object delivering the text.
			language (str): An identifier string for the language.

		Return:
			text (str): The optionally processed text.

		Notes:
			This is designed to work together with a string obfuscator
			such as the `obfuscate_language` or `obfuscate_whisper` in
			the evennia.contrib.rpg.rplanguage module.

		"""
		return "{label}|w{text}|n".format(
			label=f"|W({language})" if language else "",
			text=text
			)

	### Object Interactions
	def holding(self, part="hand"):
		held = {}
		if not part:
			# oh boy we gotta return all of the things
			held = { obj: obj.db.holding for obj in self.parts.all() if obj.db.holding }
		elif type(part) is str:
			for obj in self.parts.search(part):
				if held_obj := obj.db.holding:
					held[obj] = held_obj
		else:
			if held_obj := part.db.holding:
				held[part] = held_obj

		return held

	def hold(self, target, part="hand", **kwargs):
		"""
		Hold onto a target with a free body part.

		Args:
			target (Object): the object that is going to be grabbed
		Returns:
			the hand object which is holding target, or False if the hold failed
		"""
		# TODO: implement handedness
		if type(part) is str:
			free = [h for h in self.parts.search(part, part=True) if not h.db.holding]
			if not free:
				self.msg(f"You have no {part} free.")
				return False
			obj = free[0]
		else:
			obj = part
		if target == self.holding(part=part).get(obj):
			self.msg(f"You are already holding {target.get_display_name(self, article=True)} with your {obj.sdesc.get()}.")
			return False
		obj.db.holding = target
		return obj

	def unhold(self, part=None, target=None, **kwargs):
		"""
		Release one's grip on an object.

		Keyword args:
			hand (Object or None): the hand that is letting go
			target (Object or None): the target object that is being released
		
		Returns:
			False if the release failed, otherwise a dict representing the hands/object
		"""
		if not part and not target:
			return False
		
		if part and target:
			if self.holding(part=part).get(part) != target:
				if not kwargs.get('quiet'):
					self.msg(f"Your {part.sdesc.get()} is not holding {target.get_display_name(self)}.")
				return False
			else:
				del part.db.holding
				return {'parts': [part], 'obj': target}
		elif part:
			if obj := part.db.holding:
				del part.db.holding
			return {'parts': [part], 'obj': obj}
		elif target:
			hands = []
			for hand, obj in self.holding(part=None).items():
				if obj == target:
					hands.append(hand)
					del hand.db.holding
			
			if hands and target:
				return {'parts': hands, 'obj': target}
			else:
				if not kwargs.get('quiet'):
					self.msg("You aren't holding onto that.")
				return False


	# TODO: how am I going to deal with things moving when being held?
	def at_pre_object_receive(self, obj, source_location, **kwargs):
		my_size = self.size
		obj_size = obj.size
		max_capacity = switchboard.CHARACTER_CARRY_CAPACITY * len( [hand for hand in self.parts.search("hand") if not hand.db.holding] )
		if obj_size >= min(my_size,max_capacity):
			self.msg(f"You can't carry {obj.get_display_name(self, article=True)}.")
			return False
		clothing = self.clothing.all
		carried = [obj.size for obj in self.contents if obj not in clothing]
		if len(carried):
			# already carrying some things
			if obj_size >= switchboard.CHARACTER_CARRY_CAPACITY:
				self.msg("Your arms are too full to take something that size.")
				return False
		remaining = max_capacity * switchboard.CAPACITY_RATIO - sum(carried)
		if obj_size >= remaining:
			self.msg(f"Your arms are too full to take {obj.get_display_name(self, article=True)}.")
			return False

		# passed all the checks, it's A-OK
		return super().at_pre_object_receive(obj, source_location, **kwargs)

	#####
	# these are reimplemented core changes because i'm not using a mixin any more
	#####

	_content_types = ("character",)
	# lockstring of newly created rooms, for easy overloading.
	# Will be formatted with the appropriate attributes.
	lockstring = (
		"puppet:pid({account_id}) or perm(Developer) or pperm(Developer);"
		"delete:pid({account_id}) or perm(Admin);"
		"edit:pid({account_id}) or perm(Admin)"
	)
	
	@classmethod
	def create(cls, key, account=None, **kwargs):
		"""
		Creates a basic Character with default parameters, unless otherwise
		specified or extended.

		Provides a friendlier interface to the utils.create_character() function.

		Args:
			key (str): Name of the new Character.
			account (obj, optional): Account to associate this Character with.
				If unset supplying None-- it will
				change the default lockset and skip creator attribution.

		Keyword Args:
			description (str): Brief description for this object.
			ip (str): IP address of creator (for object auditing).
			All other kwargs will be passed into the create_object call.

		Returns:
			tuple: `(new_character, errors)`. On error, the `new_character` is `None` and
			`errors` is a `list` of error strings (an empty list otherwise).

		"""
		errors = []
		obj = None
		ip = kwargs.pop("ip", "")

		# Normalize to latin characters and validate, if necessary, the supplied key
		key = cls.normalize_name(key)

		if not cls.validate_name(key):
			errors.append(_("Invalid character name."))
			return obj, errors


		# Check to make sure account does not have too many chars
		if account:
			if len(account.characters) >= settings.MAX_NR_CHARACTERS:
				errors.append(_("There are too many characters associated with this account."))
				return obj, errors

		# Get permissions
		kwargs["permissions"] = kwargs.get("permissions", settings.PERMISSION_ACCOUNT_DEFAULT)
		
		obj, errors = super().create(key, account=account, **kwargs)
		
		if not errors:
			# Record creator id and creation IP
			if ip:
				obj.db.creator_ip = ip
			# add to playable characters list
			if account:
				if obj not in account.characters:
					account.db._playable_characters.append(obj)

		return obj, errors

	@classmethod
	def normalize_name(cls, name):
		"""
		Normalize the character name prior to creating. Note that this should be refactored to
		support i18n for non-latin scripts, but as we (currently) have no bug reports requesting
		better support of non-latin character sets, requiring character names to be latinified is an
		acceptable option.

		Args:
			name (str) : The name of the character

		Returns:
			latin_name (str) : A valid name.
		"""
		latin_name = latinify(name, default="X")
		return latin_name

	@classmethod
	def validate_name(cls, name):
		"""Validate the character name prior to creating.

		Args:
			name (str) : The name of the character
		Returns:
			valid (bool) : True if character creation should continue; False if it should fail

		"""

		return True  # Default validator does not perform any operations

	@property
	def idle_time(self):
		"""
		Returns the idle time of the least idle session in seconds. If
		no sessions are connected it returns nothing.

		"""
		idle = [session.cmd_last_visible for session in self.sessions.all()]
		if idle:
			return time.time() - float(max(idle))
		return None

	@property
	def connection_time(self):
		"""
		Returns the maximum connection time of all connected sessions
		in seconds. Returns nothing if there are no sessions.

		"""
		conn = [session.conn_time for session in self.sessions.all()]
		if conn:
			return time.time() - float(min(conn))
		return None

	def basetype_setup(self):
		"""
		Setup character-specific security.
		"""
		super().basetype_setup()
		self.locks.add(
			";".join(
				[
					"get:false()",
					"viewcon:true()",
					"getfrom:false()",
					"call:false()",
					"teleport:perm(Admin)",
					"teleport_here:perm(Admin)",
				]
			)  # noone can pick up the character
		)  # no commands can be called on character from outside
		# add the default cmdset
		self.cmdset.add_default(settings.CMDSET_CHARACTER, persistent=True)


	def ask_permission(caller, requester, message, **kwargs):
		"""
		Generic method to get confirmation for an action.
		"""
		requester.grant_permission(True)

	def grant_permission(self, permission, **kwargs):
		"""
		Point of contact for being given permission to do a pending action
		"""
		if permission:
			self.msg("Your request was accepted.")
			if waiting := self.ndb.waiting_for_permission:
				action, *args = waiting
				if callable(action):
					action(*args)
		else:
			self.msg("Your request was denied.")

		del self.ndb.waiting_for_permission