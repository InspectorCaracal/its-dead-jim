import string
from collections import Counter, defaultdict

from evennia import CmdSet, InterruptCommand
from evennia.utils import iter_to_str, inherits_from, logger

from core.commands import Command
from core.ic.behaviors import NoSuchBehavior
from base_systems.actions.commands import ActionCommand
from base_systems.things import actions
#from core.exits.typeclasses import DoorExit
from utils.strmanip import numbered_name
from utils.table import EvColumn, EvTable


class ContainerableActionCommand(ActionCommand):
	"""
	an action which can target something in a container
	"""
	prefixes = ("from",)
	splitters = ','
	tail = True

	def parse(self):
		super().parse()
		self.container = ''
		if self.argsdict:
			keys = list(self.argsdict.keys())
			keys.remove(None)
			if len(keys) > 1:
				# parsing error?
				raise InterruptCommand
			elif len(keys):
				self.prefix = keys[0]
				# can only get from one container at a time
				if container := self.argsdict.get(self.prefix):
					self.container = container[0]
			# we don't use self.splitters because containers can't be split
			self.targets = [ arg.strip() for arg in self.argsdict.get(None,'') if arg.strip() ]

	def _validate_containers(self, obj_list):
		return [obj for obj in obj_list if obj.access(self.caller, 'getfrom')]

	def func(self):
		if self.container:
			if self.tail:
				holder, tail = yield from self.find_targets(self.container, filter=self._validate_containers, numbered=False, tail=True)
				self.tail_str = tail
			else:
				holder = yield from self.find_targets(self.container, filter=self._validate_containers, numbered=False)
			if not holder:
				return
			self.tail = False
			if not self.location:
				self.location = holder
		yield from super().func()

class ToolActionCommand(ActionCommand):
	"""
	an action which uses one object to do something with another
	"""
	# TODO: the "put" command should actually be this!

	def parse(self):
		super().parse()
		self.use_on = []
		if self.argsdict:
			keys = list(self.argsdict.keys())
			keys.remove(None)
			for key in keys:
				if target := self.argsdict.get(key):
					self.use_on += target
			# TODO: we SHOULD use splitters here??
			self.targets = [ arg.strip() for arg in self.argsdict.get(None,'') if arg.strip() ]

	def _validate_targets(self, targets, **kwargs):
		return targets
	
	def func(self):
		targets = []
		if use_on := self.use_on:
			if getattr(self, 'tail', None):
				target, tail = yield from self.find_targets(use_on[0], filter_cands=self._validate_targets, numbered=False, tail=True)
				if not target:
					return
				targets.append(target)
				self.tail_str = tail
				use_on = use_on[1:]
			for sterm in use_on:
				result = yield from self.find_targets(sterm, filter_cands=self._validate_targets, numbered=False)
				if result:
					targets.append(result)
			if not targets:
				return
			self.tail = False
		self.action_kwargs |= { 'use_on': targets }
		yield from super().func()



# Custom Look command expanding the look syntax to view objects contained
# within other objects.
class CmdLook(ContainerableActionCommand):
	"""
	Observes your location or objects in your vicinity.

	Usage:
	  look
	  look <obj>
		look in <obj>
		look <container>'s <obj>
		look <obj> in <container>
	"""
	key = "look"
	aliases = ("l", "look at", "glance", "gl", "glance at")
	locks = "cmd:all()"
	prefixes = ("in", "on")
	action = actions.LookAction
	err_msg = "You don't see that."
	free = True
	needs_target = False
	search_range = 3 # TODO: make -1 be full search


	def parse(self):
		super().parse()
		if not self.targets:
			return
		if not self.container:
			# handle case for looking inside of a thing
			for prefix in self.prefixes:
				prefix = prefix+' '
				if self.targets[0].startswith(prefix):
					self.targets[0] = self.targets[0][len(prefix):]
					self.action_kwargs |= {'look_in': True}
					break

	# 	self.is_part = False
	# 	# parse for possessive 's
	# 	if ("'s " in self.args):
	# 		# split at the first possessive and swap
	# 		self.container, self.target = self.args.strip().split("'s ", maxsplit=1)

	# 	elif self.args.startswith("in "):
	# 		self.container = self.args[3:]
	# 		self.target = None

	# 	elif self.argsdict.get('in'):
	# 		self.target = self.argsdict.get(None)
	# 		self.container = self.argsdict.get('in')
	# 	elif self.argsdict.get('on'):
	# 		self.target = self.argsdict.get(None)
	# 		self.container = self.argsdict.get('on')
	# 	else:
	# 		self.target = self.args
	# 		self.container = None
		
	# 	# this is so janky
	# 	if self.container and type(self.container) is not str:
	# 		if len(self.container) == 1:
	# 			self.container = self.container[0]
	# 		else:
	# 			self.msg("You can only look inside one thing at a time.")
	# 			raise InterruptCommand
	# 	if self.target and type(self.target) is not str:
	# 		self.target = self.target[0]

	def _validate_containers(self, obj_list):
		return [obj for obj in obj_list if obj.access(self.caller, 'viewcon')]

	def func(self):
		"""
		Handle the looking
		"""
		caller = self.caller
		location = caller.location

		glance = "gl" in self.cmdstring

		if not location:
			self.msg("You are in an infinite void of nothingness.")
			return
	
		self.action_kwargs |= {'glance': glance, 'location': location}

		yield from super().func()
		# if not self.args:
		# 	target = location
		# 	if not target:
		# 		caller.msg("You are in an infinite void.")
		# 		return
		# 	caller.msg(caller.at_look(target), options=None)
		# 	return

		# if self.args.lower().strip() == "doors":
		# 	if not location:
		# 		caller.msg("You are in an infinite void.")
		# 		return
		# 	caller.msg(location.get_display_doors(caller, all_doors=True))
		# 	return

		# holder = None
		# target = None
		# look_in = False

		# if self.container:
		# 	holder = yield from self.find_targets(self.container, numbered=False, locktype='view')
		# 	if not holder:
		# 		return
		# 	if not holder.access(caller, "viewcon") and not holder.access(caller, "getfrom"):
		# 		self.msg("You can't look there.")
		# 		return

		# # at this point, all needed objects have been found
		# # if "target" isn't specified, the container IS the target
		# if holder and not self.target:
		# 	look_in = True
		# 	obj_list = [holder]

		# else:
		# 	# TODO: assess if we should stack based on identical descs or just names
		# 	obj_list = yield from self.find_targets(self.target, location=holder, stack=True, locktype='view')
		# 	if not obj_list:
		# 		return


class CmdRead(ActionCommand):
	"""
	read

	Usage:
	  read <obj>

	Reads the text on something, if possible.
	"""
	key = "read"
	locks = "cmd:all()"
	action = actions.ReadAction
	err_msg = "You can't read that."
	free = True


class CmdGet(ContainerableActionCommand):
	"""
	pick up something

	Usage:
	    get <obj>
	    get <obj1>, <obj2>, ... <objX>
	    get <obj> from <obj>

	Picks up an object from your location or another object you have permission
	to get (or get from) and puts it in your inventory.

	Additional text after the command will be added as an extra emote.

	Example:
		> get key looking around suspiciously
		Monty picks up a rusty key, looking around suspiciously.
	"""

	key = "get"
	aliases = "pick up"
	locks = "cmd:all()"
	prefixes = ("from",)
	action = actions.GetAction
	err_msg = "You can't get that."


class CmdDrop(ActionCommand):
	"""
	drop something

	Usage:
		drop <obj>

	Lets you drop an object from your inventory into the
	location you are currently in.
	"""

	key = "drop"
	locks = "cmd:all()"
	action = actions.DropAction
	err_msg = "You can't put that down."
	nofound_msg = "You don't have any {sterm}."
	splitters = ','

	def parse(self):
		super().parse()
		self.location = self.caller
		self.targets = self.argslist or self.args

		if not self.targets:
			self.caller.msg(self.err_msg)
			raise InterruptCommand

		self.location = self.caller

	def _filter_targets(self, targets, **kwargs):
		return [ ob for ob in targets if ob not in self.caller.clothing.all ]


class CmdPut(ContainerableActionCommand):
	"""
	put something down

	Usage:
	    put <obj> on <obj>
	    put <obj> in <obj>

	Lets you place an object in your inventory into another object,
	or your current location
	"""

	key = "put"
	#	aliases = "place"
	locks = "cmd:all()"
	prefixes = ("in","on")
	action = actions.PutAction
	err_msg = "You can't put that down."
	nofound_msg = "You don't have any {sterm}."

	# I don't know if this will work
	def parse(self):
		super().parse()
		if not self.container:
			self.caller.msg("Put it where?")
			raise InterruptCommand
		self.location = self.caller
		prefixes = [k for k in self.argsdict.keys() if k]
		if prefixes:
			self.action_kwargs = {'preposition': prefixes[0]}

	def _filter_targets(self, targets, **kwargs):
		return [ ob for ob in targets if ob not in self.caller.clothing.all and ob not in self.action_kwargs.values() ]

	def _validate_containers(self, obj_list):
		return [obj for obj in obj_list if obj.access(self.caller, 'getfrom')]

	def func(self):
		if self.container:
			if self.tail:
				holder, tail = yield from self.find_targets(self.container, filter_cands=self._validate_containers, numbered=False, tail=True, find_none=True)
				self.tail_str = tail
			else:
				holder = yield from self.find_targets(self.container, filter_cands=self._validate_containers, numbered=False, find_none=True)
			if not holder:
				self.msg("You can't put things there.")
				return
			self.tail = False
			self.action_kwargs |= {'destination': holder}
		yield from ActionCommand.func(self)


class CmdGive(ActionCommand):
	"""
	give away something to someone

	Usage:
		give <inventory obj> to <target>

	Gives an items from your inventory to another character,
	placing it in their inventory.
	"""
	key = "give"
	locks = "cmd:all()"
	prefixes = ("to",)
	splitters = ','
	action = actions.GiveAction
	err_msg = "You can't give that away."
	nofound_msg = "You don't have any {sterm}."

	def parse(self):
		super().parse()
		self.location = self.caller
		if receivers := self.argsdict.get('to'):
			# can only give to one player
			if len(receivers) == 1:
				self.receiver = receivers[0]
				self.targets = self.argsdict.get(None)
			else:
				self.msg("You can only give things to one target at a time.")
				raise InterruptCommand

	def _filter_candidates(self, targets, **kwargs):
		return [ ob for ob in targets if ob not in self.caller.clothing.all ]

	def func(self):
		receiver = yield from self.find_targets(self.receiver, numbered=False)
		if not receiver:
			return
		self.action_kwargs = {'receiver': receiver}

		yield from super().func()

class CmdEat(ContainerableActionCommand):
	"""
	eat something

	Usage:
		eat <obj> [from <container>]

	Lets you eat something.
	"""
	# TODO: target things in your vicinity too so you can e.g. eat from a plate

	key = "eat"
	aliases = ("taste", "nibble","devour")
	locks = "cmd:all()"
	action = actions.EatAction
	err_msg = "You can't eat that."

	def parse(self):
		super().parse()
		quantity = 3
		match self.cmdstring:
			case 'taste':
				quantity = 0
			case 'nibble':
				quantity = 1
			case 'devour':
				quantity = 100
		self.action_kwargs = {'uses': quantity, 'verb': self.cmdstring}

	def _filter_candidates(self, targets, **kwargs):
		return [t for t in targets if t.can_consume]

class CmdOpenClose(ActionCommand):
	"""
	open or close something

	Usage:
		open <obj>
		close <obj>
	"""

	key = "open"
	aliases = ("close",)
	locks = "cmd:all()"
	action = actions.ToggleOpenAction
	priority = 1

	def parse(self):
		super().parse()
		self.action_kwargs = { 'toggle': self.cmdstring }

class CmdLockUnlock(ActionCommand):
	"""
	lock or unlock something

	Usage:
		open <obj>
		close <obj>
	"""

	key = "lock"
	aliases = ("unlock",)
	locks = "cmd:all()"
	action = actions.ToggleLockAction
	priority = 1

	def parse(self):
		super().parse()
		self.action_kwargs = { 'toggle': self.cmdstring }


class CmdGrab(ActionCommand):
	"""
	grab onto something

	Usage:
		grab <obj> [with <left/right> hand]
	"""

	key = "grab"
	aliases = ("hold",)
	locks = "cmd:all()"
	prefixes = ("with",)
	action = actions.GrabAction


	def parse(self):
		super().parse()
		self.targets = self.argsdict[None]
		if hand := self.argsdict.get('with'):
			if hand := self.caller.parts.search(self.hand, part=True):
				hand = hand[0]
			else:
				hand = None

		self.action_kwargs = { 'hand': hand }

# TODO: refactor as an Action
class CmdRelease(Command):
	"""
	let go of something

	Usage:
		release <obj>
		release <hand>
	"""

	key = "release"
	aliases = ("let go of",)
	locks = "cmd:all()"

	# TODO: how to make this an ActionCommand with its highly custom targetting
	def func(self):
		"""Implement command"""

		caller = self.caller
		hand = None
		obj = None

		if not (held := caller.holding(part=self.args)):
			if not self.args:
				self.msg("You aren't holding anything.")
				return
			obj = yield from self.find_targets(self.args, numbered=False)
			if not obj:
				return
			held = {None: obj}

		hands = []
		released = []
		quiet = False if len(held.keys()) == 1 else True
		for hand, obj in held.items():
			if result := caller.unhold(target=obj, part=hand, quiet=quiet):
				hands += result['parts']
				if result['obj'] not in released:
					released.append(result['obj'])
				if caller.location.posing.get(caller) == obj:
					caller.location.posing.remove(caller)

		hands = iter_to_str([ hand.sdesc.get() for hand in hands ])
		if hands:
			hands = f" with $gp(their) {hands}"
		if released:
			rstrings = [f"@{ob.sdesc.get(strip=True)}" for ob in released]
			caller.emote(f"lets go of {iter_to_str(rstrings)}{hands}", include=released)


class CmdUse(ToolActionCommand):
	"""
	use something

	Usage:
		use <obj>
		use <obj> on/with <target>

	Lets you use a particular item, for whatever its intended purpose is.
	"""

	key = "use"
	locks = "cmd:all()"
	prefixes = ("on", "with")
	action = actions.UseAction

	def _filter_candidates(self, targets, **kwargs):
		return [t for t in targets if t.can_use]

# This command is the one that is intended to be dynamically added to objects to add extra verbs to them
class CmdDynamicUse(CmdUse):
	key = "tool_use"
	auto_help = False

	def parse(self):
		super().parse()
		self.action_kwargs |= {'verb': self.cmdstring}

	def _filter_candidates(self, candidates, **kwargs):
		# TODO: figure out how to filter this by command ownership
		tools = [ obj for obj in candidates if obj.tags.has(self.cmdstring, category="verb") ]
		return list(tools)


# TODO: refactor as an Action
class CmdFlip(Command):
	"""
	Flip something over

	Usage:
		flip <obj>

	Lets you flip a multi-sided object over to another side.
	"""

	key = "flip"

	def func(self):
		"""Implement command"""

		caller = self.caller
		if not self.args:
			caller.msg("Flip what?")
			return

		# get object to use
		targets = yield from self.find_targets(self.args)
		if not targets:
			return

		if len(targets) == 1:
			obj = targets[0]
			if flip := obj.sides.turn():
				caller.msg(f"You flip the {obj.get_display_name(caller, noid=True)} to its {iter_to_str(flip)}.")
			else:
				caller.msg("You can't flip that over.")

		else:
			flipped = []
			for obj in targets:
				if obj.sides.turn():
					flipped.append(obj.get_display_name(caller, noid=True))
			if not flipped:
				caller.msg("You couldn't flip those over.")
			else:
				names = Counter(flipped)
				names = [numbered_name(*item) for item in names.items()]
				names = iter_to_str(names)
				caller.msg(f"You flip over {names}.")


class CmdInventory(Command):
	"""
	view inventory

	Usage:
		inventory

	Shows your inventory.
	"""

	# Alternate version of the inventory command which separates
	# worn and carried items.

	key = "inventory"
	aliases = ["inv", "i"]
	locks = "cmd:all()"
	help_category = "Character"
	free = True

	def func(self):
		"""check inventory"""
		caller = self.caller

		clothing = caller.clothing.all
		carried = [obj for obj in caller.contents if obj not in clothing]
		message = []
		
		def _fill_columns(obj_list):
			cols_list = []
			if len(obj_list) > 10:
				if len(obj_list) < 20:
					cols_list.append(EvColumn(*obj_list[:10]))
					cols_list.append(EvColumn(*obj_list[10:]))

				else:
					split = int(len(obj_list)/2)
					cols_list.append(EvColumn(*obj_list[:split]))
					cols_list.append(EvColumn(*obj_list[split:]))

			else:
				cols_list.append(EvColumn(*obj_list))
			
			return cols_list

		def _collapse_name_list(namelist, prefix=""):
			# TODO: make this a util function
			collapsed = []
			if namelist:
				counted = Counter(namelist)
				for key, val in counted.items():
					if key.endswith(" |x(hidden)|n"):
						named, hidden = key.rsplit(' ', maxsplit=1)
						collapsed.append( prefix + f"{numbered_name(named, val)} {hidden}" )
					else:
						collapsed.append( prefix + numbered_name(key, val) )
			return collapsed

		# build carried inventory
		message.append("$head(You are carrying:)")
		carried_names = []
		bag_names = []
		for obj in carried:
			if obj.get_lock(caller, 'viewcon') and (contents := [thing.sdesc.get(looker=caller) for thing in obj.contents]):
				bag_names.append((obj.get_display_name(caller, noid=True, link=True, article=True), _collapse_name_list(contents, prefix="|-")))
			else:
				carried_names.append(obj.get_display_name(caller, noid=True, link=True, article=False))

		carried_names = _collapse_name_list(carried_names)

		if len(carried_names) or len(bag_names):
			bag_name_list = []
			for bag, con in bag_names:
				bag_name_list.append(bag + ", containing:")
				bag_name_list += con
			carry_col_list = bag_name_list + carried_names
			carried_desc = "\n|-".join(carry_col_list)
		else:
			carried_desc = "nothing"
		message.append("|-"+carried_desc)
		message.append('')
		# build worn inventory
		message.append("$head(You are wearing:)")
		worn_names = []
		bag_names = []
		for obj in clothing:
			clothing_name = obj.get_display_name(caller, article=False, noid=True, link=True)
			if obj.tags.has('hidden', category='systems'):
				clothing_name += " |x(hidden)|n"

			containing = []
			contents = [thing.sdesc.get(looker=caller) for thing in obj.contents]
			for ob in obj.parts.all():
				contents += [thing.sdesc.get(looker=caller) for thing in ob.contents]
			if contents:
				bag_names.append((numbered_name(clothing_name, 1), _collapse_name_list(contents, prefix="|-")))
			else:
				worn_names.append(clothing_name)

		worn_names = _collapse_name_list(worn_names)
		
		if len(worn_names) or len(bag_names):
			bag_name_list = []
			for bag, con in bag_names:
				bag_name_list.append(bag + ", containing:")
				bag_name_list += con
			clothing_col_list = bag_name_list + worn_names
			clothing_desc = "\n|-".join(clothing_col_list)
		else:
			clothing_desc = "nothing"
		message.append("|-"+clothing_desc)

		# output to caller
		caller.msg(('\n'.join(message), { "target": "modal" }) )

# TODO: this should actually be wrapped into "use" - using the power button or switch
class CmdTurnOnOff(Command):
	"""
	Turn an object on or off

	Usage:
		turn on phone
		turn off lamp
	"""
	key = "power on"
	aliases = ('power off',)

	def func(self):
		caller = self.caller
		if not self.args:
			caller.msg(self.cmdstring[0].upper() + self.cmdstring[1:] + " what?")
			return

		# get object to turn on or off
		target = yield from self.find_targets(self.args, numbered=False)
		if not target:
			return
		
		if self.cmdstring.strip().endswith(' on'):
			power = True
		elif self.cmdstring.strip().endswith(' off'):
			power = False
		else:
			# this should never happen
			logger.log_err(f"power on/off called with cmdstring {self.cmdstring}")
			return
		
		try:
			toggled = target.do_power(caller, power)
		except NoSuchBehavior:
			parts = self.cmdstring.split()
			self.msg(f"That can't be {parts[0]}ed {parts[1]}.")

		if toggled is False:
			self.msg(f'That is already {"on" if power else "off"}')
		elif toggled:
			self.msg(f'You turn on {target.get_display_name(caller, article=True)}.')
		else:
			self.msg(f"That's not something you can {self.cmdstring}")


# TODO: refactor this to use the Action system
class CmdPlace(ActionCommand):
	"""
	Decorate a room with an object

	Usage:
		place <obj>[ position]

	Examples:
		place painting
		place painting hanging from the south wall
	
	Placed objects will appear as part of the room's description instead of
	its contents.
	"""

	key = "place"
	aliases = ("arrange",)
	help_category = "General"
	locks = "cmd:all()"
	action = actions.DecorAction
	tail = True
	# prefixes = ("from",)
	err_msg = "You can't place that."

	log = "content"

	def at_pre_cmd(self):
		if self.caller.location:
			if not self.caller.location.access(self.caller, "decorate"):
				self.msg("You cannot place decor here.")
				return True
		return super().at_pre_cmd()

	def _filter_targets(self, targets, **kwargs):
		return [t for t in targets if t not in self.caller.location.decor.all()]


# CmdSet for item commands

class ItemManipCmdSet(CmdSet):
	"""
	Groups the extended basic commands.
	"""
	key = "Item Manip CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdLook)
		self.add(CmdGet)
		self.add(CmdPut)
		self.add(CmdDrop)
		self.add(CmdGive)
		self.add(CmdUse)
		self.add(CmdFlip)
		self.add(CmdOpenClose)
		self.add(CmdEat)
		self.add(CmdRead)
		self.add(CmdInventory)
		self.add(CmdGrab)
		self.add(CmdPlace)
		self.add(CmdRelease)
		self.add(CmdTurnOnOff)
