import string
import time
from collections import Counter, defaultdict
from evennia import InterruptCommand
from evennia.utils import iter_to_str

from base_systems.actions.base import Action, InterruptAction
from core.ic.behaviors import NoSuchBehavior
from utils.strmanip import numbered_name, strip_extra_spaces
from utils.timing import delay

class LookAction(Action):
	move = 'look'
	dbobjs = ('actor', 'targets')

	min_req_parts = ( ('eye', 1), )
	max_used_parts = ( ('eye', 2), )


	def __init__(self, actor, targets, **kwargs):
		location = kwargs.pop('location', None)
		self.actor = actor
		self.targets = targets or [location]
		if not self.targets:
			raise InterruptAction
		self.look_in = kwargs.pop('look_in', False)
		self.glance = kwargs.pop('glance', False)
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		output = []
		outkwargs = {'target': 'look', 'action_type': 'look'}
		for obj in self.targets:
			appear = self.actor.at_look(obj, look_in=self.look_in, glance=self.glance)
			if type(appear) is tuple:
				output.append(appear[0])
				outkwargs |= appear[1]
			else:
				output.append(appear)

		output = strip_extra_spaces("\n\n".join(output))
		self.actor.msg((output, outkwargs), options=None)
		super().do(*args, **kwargs)


class MoveObjAction(Action):
	move = "move"
	dbobjs = ('actor', 'targets', 'container')
	err_msg = "You couldn't move {obnames}."

	def __init__(self, actor, targets, **kwargs):
		self.actor = actor
		self.targets = targets
		self.container = kwargs.pop('container',None)
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		moved = defaultdict(list)
		stuck = []

		quiet = len(self.targets) > 1

		for obj in self.targets:
			if res := self._move_obj(obj, quiet=quiet):
				if type(res) is tuple:
					moved[res[1]].append(res[0])
				else:
					moved[None].append(res)
			else:
				stuck.append(obj)

		if len(moved):
			# we got some stuff!
			self._msg(moved)

		elif quiet:
			# we got nothin'
			names = [obj.sdesc.get() for obj in stuck]
			namecount = Counter(names)
			namelist = [numbered_name(key, value) for key, value in namecount.items()]
			self.actor.msg(self.err_msg.format(obnames=iter_to_str(namelist, endsep=', or')))
		
		super().do(*args, **kwargs)

	def _msg(self, result):
		"""
		Emote the results
		"""
		if tail := getattr(self, 'tail_str', ''):
			tail = f",{tail}" if not tail[0] in string.punctuation else tail

		obnames = []
		# this is just the default
		message = "moves {obnames}{tail}"
		for loc, objs in result.items():
			names = [obj.sdesc.get() for obj in objs]
			namecount = Counter(names)
			namelist = [numbered_name(key, value) for key, value in namecount.items()]
			namestr = iter_to_str(namelist)
			if loc and loc != self.actor.location:
				hname = loc.get_display_name(self.actor, article=True, noid=True, contents=False)
				obnames.append( f"{namestr} from {hname}" )
			else:
				obnames.append(namestr)
		message = message.format(obnames=iter_to_str(obnames), tail=tail)
		self.actor.emote(message)

	def _move_obj(self, obj, quiet=False):
		# it doesn't work in this parent class
		return


class GetAction(MoveObjAction):
	move = "get"
	dbobjs = ('actor', 'targets')
	err_msg = "You couldn't get {obnames}."

	min_req_parts = ( ('hand', 1), )

	def __init__(self, actor, targets, **kwargs):
		kwargs.pop('container',None)
		super().__init__(actor, targets, **kwargs)

	def _msg(self, result):
		"""
		Emote the results
		"""
		if tail := getattr(self, 'tail_str', ''):
			tail = f",{tail}" if not tail[0] in string.punctuation else tail

		got_strs = []
		if (len(result.keys()) == 1) and (list(result.keys())[0] == self.actor.location):
			message = "picks up {obnames}{tail}"
			names = [ob.sdesc.get() for ob in result[self.actor.location]]
			namecount = Counter(names)
			got_strs = [numbered_name(key, value) for key, value in namecount.items()]
		else:
			message = "gets {obnames}{tail}"
			for loc, objs in result.items():
				names = [obj.sdesc.get() for obj in objs]
				namecount = Counter(names)
				namelist = [numbered_name(key, value) for key, value in namecount.items()]
				namestr = iter_to_str(namelist)
				if loc != self.actor.location:
					hname = loc.get_display_name(self.actor, article=True, noid=True, contents=False)
					got_strs.append( f"{namestr} from {hname}" )
				else:
					got_strs.append(namestr)
		message = message.format(obnames=iter_to_str(got_strs), tail=tail)
		self.actor.emote(message)

	def _move_obj(self, obj, quiet=False):
		actor = self.actor

		if actor == obj:
			if not quiet:
				actor.msg("You can't get yourself.")
			return
		if actor == obj.location:
			if not quiet:
				actor.msg("You're already carrying that.")
			return

		if not obj.access(actor, "get") or not obj.at_pre_get(actor):
			if not quiet:
				if not (err_msg := obj.db.get_err_msg):
					err_msg = "You can't get that."
				actor.msg(err_msg)
			return

		start_location = obj.location
		success = obj.move_to(actor, quiet=True, move_type='get')
		if not success:
			if not quiet:
				if not (err_msg := obj.db.get_err_msg):
					err_msg = "You can't get that."
				actor.msg(err_msg)
			return

		# calling at_get hook method
		obj.at_get(actor)
		return (obj, start_location)
	

class PutAction(MoveObjAction):
	move = "put"
	dbobjs = ('actor', 'targets', 'destination')
	err_msg = "You couldn't put down {obnames}."

	min_req_parts = ( ('hand', 1), )

	def _msg(self, results):
		if tail := getattr(self, 'tail_str', ''):
			tail = f",{tail}" if not tail[0] in string.punctuation else tail
		message = "puts {obnames}{tail}"

		onword = getattr(self, 'preposition', 'on')

		namestrs = []
		for loc, objs in results.items():
			chunk = "{names} {on} {container}"
			tname = loc.get_display_name(self.actor, article=True, noid=True, contents=False)
			namecount = Counter([obj.sdesc.get() for obj in objs])
			namelist = [numbered_name(key, value) for key, value in namecount.items()]
			namestrs.append(chunk.format(container=tname, names=iter_to_str(namelist), on=onword))

		message = message.format(obnames=iter_to_str(namestrs), on=onword, tail=tail)
		self.actor.emote(message)

	def _move_obj(self, obj, quiet=False):
		target = self.destination

		if not obj.at_pre_drop(self.actor):
			if not quiet:
				self.actor.msg("You can't put that down.")
			return False

		if obj in self.actor.holding(part=None).values():
			if not self.actor.unhold(target=obj):
				return False

		if not target.at_pre_object_receive(obj, None):
			# try to put the object into one of its parts, instead
			capacity = False
			for thing in target.parts.all():
				if thing.at_pre_object_receive(obj, None):
					target = thing
					capacity = True
					break
			if not capacity and not quiet:
				# self.actor.msg("There isn't enough room in that.")
				self.actor.msg("You can't put that there.")
				return False

		success = obj.move_to(target, quiet=True, move_type='drop')

		if not success:
			if not quiet:
				self.actor.msg("This couldn't be put down.")
			return False

		obj.at_drop(self.actor)

		return (obj, obj.location)


class DropAction(MoveObjAction):
	move = "drop"
	dbobjs = ('actor', 'targets')
	err_msg = "You couldn't put down {obnames}."

	def __init__(self, actor, targets, **kwargs):
		kwargs.pop('container',None)
		super().__init__(actor, targets, **kwargs)
	
	def _msg(self, results):
		message = "puts down {obnames}."
		# dropping is always location-less
		results = results.get(None)
		names = [obj.sdesc.get() for obj in results]
		namecount = Counter(names)
		namelist = [numbered_name(key, value) for key, value in namecount.items()]

		message = message.format(obnames=iter_to_str(namelist))
		self.actor.emote(message, msg_type='move')

	def _move_obj(self, obj, quiet=False):
		if not obj.at_pre_drop(self.actor):
			if not quiet:
				self.actor.msg("You can't put that down.")
			return False

		if obj in self.actor.holding(part=None).values():
			if not self.actor.unhold(target=obj):
				return False

		success = obj.move_to(self.actor.location, quiet=True, move_type='drop')

		if not success:
			if not quiet:
				self.actor.msg("This couldn't be put down.")
			return False

		obj.at_drop(self.actor)

		return obj
	

class GiveAction(MoveObjAction):
	move = "give"
	dbobjs = ('actor', 'targets', 'receiver')
	err_msg = "You couldn't give away {obnames}."

	def __init__(self, actor, targets, **kwargs):
		super().__init__(actor, targets, **kwargs)
	
	def _msg(self, results):
		message = "gives {obnames} to @{receiver}."

		# give results never have a location
		results = results[None]

		names = [obj.sdesc.get() for obj in results]
		namecount = Counter(names)
		namelist = [numbered_name(key, value) for key, value in namecount.items()]

		message = message.format(obnames=iter_to_str(namelist), receiver=self.receiver.sdesc.get(strip=True))
		self.actor.emote(message)

	def _move_obj(self, obj, quiet=False):
		if not obj.at_pre_give(self.actor, self.receiver):
			if not quiet:
				self.actor.msg("You can't give that away.")
			return False

		if obj in self.actor.holding(part=None).values():
			if not self.actor.unhold(target=obj):
				return False

		success = obj.move_to(self.receiver, quiet=True, move_type='give')

		if not success:
			if not quiet:
				self.actor.msg("This couldn't be given.")
			return False

		obj.at_give(self.actor, self.receiver)

		return obj


class ReadAction(Action):
	move = "read"
	dbobjs = ('actor', 'targets')

	min_req_parts = ( ('eye', 1), )
	max_used_parts = ( ('eye', 2), )


	def do(self, *args, **kwargs):
		target = self.targets[0]
		output = []
	
		if content := [t for t in target.parts.search('text', part=True) if t.get_lock(self.actor, 'view')]:
			output.append(f"You read {target.get_display_name(self.actor, article=True)}:\n")
			for text in content:
				for item in text.parts.search('detail', part=True):
					if item.get_lock(self.actor, 'read'):
						output.append(item.db.desc or '' )
					else:
						output.append('(illegible)')
					output.append('')
			self.actor.msg(("\n".join(output).rstrip(), {"type": "read", "target": "modal"}))

		else:
			self.actor.msg(f"There's nothing to read on {target.get_display_name(self.actor, article=True)}.")

		super().do(*args, **kwargs)


class EatAction(Action):
	move = "eat"
	dbobjs = ('actor', 'targets')

	min_req_parts = ( ('mouth', 1), )

	def __init__(self, **kwargs):
		self.actor = kwargs['actor']
		self.targets = kwargs['targets']
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		obj = self.targets[0]

		flavors = [ v.get('flavors',[]) for k,v in obj.materials.get("all", as_data=True) ]
		flavors += [ v.get('flavors',[]) for p in obj.parts.all() for k,v in p.materials.get("all", as_data=True) ]
		if flavors:
			flavors = dict(sorted(Counter(f for f in flavors if f).items(), key=lambda x:x[1]))
			flavor_msg = f"The {obj.get_display_name(self.actor, article=False)} tastes {iter_to_str(reversed(flavors.keys()))}."
		else:
			flavor_msg = ''

		message = f"{self.verb or self.move}s {{quant}} $gp(their) {obj.sdesc.get()}"
		uses = getattr(self, 'uses', 1)
		quant = obj.do_consume(self.actor, uses=uses)
		message = message.format(quant=quant)
		message = strip_extra_spaces(message)

		if message:
			if tail := getattr(self, 'tail_str', ''):
				if tail[0] not in string.punctuation:
					tail = f",{tail}"
			self.actor.emote(f"{message}{tail}")

		if flavor_msg:
			self.msg(flavor_msg)

		super().do(*args, **kwargs)

	def end(self, *args, **kwargs):
		super().end(*args, **kwargs)

# TODO: make eat/drink handle eating and drinking from a dish


class ToggleOpenAction(Action):
	dbobjs = ('actor', 'targets')

	def __init__(self, actor, targets, **kwargs):
		self.actor = actor
		self.targets = targets
		super().__init__(**kwargs)
		self.move = kwargs.get('toggle', 'open')

	def do(self, *args, **kwargs):
		obj = self.targets[0]
		message = f"{self.toggle}s {numbered_name(obj.sdesc.get(), 1)}."
		open = self.toggle == "open"
		if open and obj.tags.has('open', category='status'):
			self.msg("That is already open.")
			return self.fail()
		if not open and obj.tags.has('closed', category='status'):
			self.msg("That is already closed.")
			return self.fail()

		if hasattr(obj, "at_open_close"):
			message = obj.at_open_close(self.actor, open=open)

		else:
			if open:
				obj.tags.add("open", category='status')
				obj.tags.remove("closed", category='status')
			else:
				obj.tags.remove("open", category='status')
				obj.tags.add("closed", category='status')

		if message:
			self.actor.emote(message)
		
		return self.succeed()

	def succeed(self, *args, **kwargs):
		self.targets[0].react.on(self.move, self.actor)
		super().succeed(*args, **kwargs)


class ToggleLockAction(Action):
	dbobjs = ('actor', 'targets')

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.move = kwargs.get('toggle', 'lock')

	def do(self, *args, **kwargs):
		obj = self.targets[0]
		message = None
		locking = self.toggle == "lock"
		if hasattr(obj, "at_open_close"):
			message = obj.at_lock_unlock(self.actor, locking=locking)
			if message:
				self.actor.emote(message)
			else:
				self.msg(f"You need a key.")
		else:
			self.msg(f"You can't {self.toggle} that.")

		super().do(*args, **kwargs)


class GrabAction(Action):
	move = "grab"
	dbobjs = ('actor', 'targets')

	def __init__(self, actor, targets, **kwargs):
		self.actor = actor
		self.targets = targets
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		obj = self.targets[0]
		if obj.access(self.actor, "get") and obj.at_pre_get(self.actor):
			if not obj.move_to(self.actor):
				self.msg("You can't get that.")
			used_hand = self.actor.hold(obj, part=self.hand) if self.hand else self.actor.hold(obj)

		elif self.hand:
			used_hand = self.actor.hold(obj, part=self.hand)
		else:
			used_hand = self.actor.hold(obj)

		if used_hand:
			self.actor.emote(f"grabs @{obj.sdesc.get(strip_ansi=True)} with $gp(their) {used_hand.sdesc.get()}", include=[obj])
			if obj.location == self.actor.location:
				self.actor.location.posing.add(self.actor, obj, "holding")

		super().do(*args, **kwargs)

class UseAction(Action):
	move = "use"
	dbobjs = ('actor', 'targets', 'use_on')

	def __init__(self, actor, targets, **kwargs):
		self.actor = actor
		self.targets = targets
		self.use_on = kwargs.pop('use_on', None)
		super().__init__(**kwargs)

	def start(self, *args, **kwargs):
		if not len(self.targets):
			# TODO: error message
			return super().end()
		self.tool = self.targets[0]
		super().start(*args, **kwargs)

	def do(self, *args, **kwargs):
		if duration := self.tool.db.use_time:
			self._end_at = time.time() + duration
			delay(duration, self.do)
			kwargs['delay'] = True
		if self.use_on:
			self.tool.do_use(self.actor, targets=self.use_on)
		else:
			self.tool.do_use(self.actor)

		super().do(*args, **kwargs)

	def end(self, *args, **kwargs):
		if self.tool.can_consume:
			uses = getattr(self, 'uses', 1)
			self.tool.do_consume(self.actor, uses=uses)

		super().end(*args, **kwargs)


class DecorAction(Action):
	move = "use"
	dbobjs = ('actor', 'targets')

	def __init__(self, actor, targets, **kwargs):
		self.actor = actor
		self.targets = targets
		self.position = kwargs.pop('tail_str', 'here').strip()
		super().__init__(**kwargs)
		if not len(self.targets):
			# TODO: error message
			raise InterruptAction
		self.target = self.targets[0]

		if len(self.position) > 50:
			self.actor.msg("Please keep your placement description below 50 characters.")
			raise InterruptAction

	def do(self, *args, **kwargs):
		# move the object into the room first
		if self.target.location != self.actor.location:
			if not self.target.move_to(self.actor.location, quiet=True):
				self.actor.msg("That could not be placed.")
		# do the actual placement
		if not self.actor.location.decor.add(self.target, self.position):
			self.actor.msg("That could not be placed.")
		else:
			self.actor.emote(f"places {self.target.get_display_name(self.actor, noid=True, article=True)} {self.position}.", action_type="move")

		super().do(*args, **kwargs)
