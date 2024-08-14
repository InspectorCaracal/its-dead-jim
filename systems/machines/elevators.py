from evennia.utils import lazy_property, iter_to_str, delay, logger
from evennia import CmdSet
from evennia.typeclasses.attributes import AttributeProperty
from base_systems.exits.doors import DoorExit

from core.commands import Command
from base_systems.things.base import Thing
from utils.strmanip import strip_extra_spaces

## Objects

# TODO: all of these things need to be reworked to be powered systems etc. eventually

class ElevatorPanel(Thing):
	"""An object to go inside of an elevator room to control it"""
	link = AttributeProperty(None)

	def at_object_creation(self):
		super().at_object_creation()
		# saves the ordered list of "floors" or "stops"
		# each item in the list is a `destination` room
		self.locks.add('get:false()')
		self.db.stops = []
		# how long it takes for each floor
		self.db.interval = 5
		self.db.wait = 30
		self.db.depart_msg = "The doors close and the room begins to move."
		self.db.arrival_msg = "The room slows to a stop, arriving at |lcout|lt{dest}|le."
		# self.db.outer_arrive = "The |lcelevator|ltelevator|le doors open."
		# self.db.outer_depart = "The |lcelevator|ltelevator|le doors close."
		self.cmdset.add(ElevatorCmdSet, persistent=True)

	def get_display_desc(self, looker, **kwargs):
		if not looker:
			return ""
		
		desc = super().get_display_desc(looker, **kwargs)
		buttons = [ "|lcpush {num}|lt{num}|le: {name}".format(num=i+1, name=obj.get_display_name(self)) for i, obj in reversed(list(enumerate(self.db.stops))) ]
		buttons = "\n".join(buttons)

		if desc:
			desc += "\n\n" + buttons if buttons else ""
		else:
			desc = buttons

		return desc

	def get_display_footer(self, looker, **kwargs):
		lit = ""
		if call_list := self.ndb.call_list:
			if len(call_list) > 1:
				lit = "The numbers {} are lit."
			else:
				lit = "The number {} is lit."
			lit = lit.format(iter_to_str([i+1 for i in call_list]))
		foot = super().get_display_footer(looker,**kwargs)

		if foot and lit:
			return lit + '\n\n' + foot
		else:
			return lit + foot

	def move_next(self):
		"""
		Step to the next destination in the list.
		"""
		self.ndb.waiting = False
		if door := self.link:
			floor = door.destination
			if not floor:
				# already moving
				return
		else:
			return
		
		# get the door for the other side
		outer_door = door.get_return_exit()

		try:
			current = self.db.stops.index(floor)
		except ValueError:
			# current destination isn't in stops list
			current = 0

		direction = self.ndb.direction or "up"
		called = self.ndb.call_list or []

		if not len(called):
			return

		# get stops "higher" than here
		up = [i for i in called if i > current]
		# get stops "lower" than here
		down = [i for i in called if i < current]

		if not len(up) and not len(down):
			# we're already there
			door.destination = self.db.stops[current]
			self.ndb.call_list = []
			return

		if not len(up):
			direction = "down"
		elif not len(down):
			direction = "up"

		if direction == "up":
			next = up[0]
		elif direction == "down":
			next = down[0]

		door.at_open_close(self, open=False, anonymous=True)
		if outer_door:
			outer_door.at_open_close(self, open=False, anonymous=True)

		self.ndb.direction = direction
		interval = abs(current-next) * self.db.interval
		message = self.db.depart_msg
		self.emote(self.db.depart_msg, anonymous_add=None)
		# self.emote(self.db.outer_depart, receivers=floor.contents, anonymous_add=None)
		delay(interval, self._set_destination, next, persistent=True)
		self.link.destination = None

	def _set_destination(self, dest_index):
		try:
			destination = self.db.stops[dest_index]
		except IndexError:
			# assigned index doesn't point to an existing stop
			destination = self.db.stops[0]

		door = self.link
		door.destination = destination
		message = self.db.arrival_msg
		message = message.format(dest=destination.get_display_name(self))
		self.emote(message, anonymous_add=None)
		door.at_open_close(self, open=True, anonymous=True)
		if outer_door := door.get_return_exit():
			outer_door.at_open_close(self, open=True, anonymous=True)
		# self.emote(self.db.outer_arrive, receivers=destination.contents, anonymous_add=None)
		self.ndb.waiting = True

		if self.ndb.call_list:
			self.ndb.call_list = [i for i in self.ndb.call_list if i != dest_index]
		delay(self.db.wait, self.move_next)


class ElevatorCallButton(Thing):
	link = AttributeProperty(None)

	def at_object_creation(self, **kwargs):
		super().at_object_creation()
		self.locks.add('get:false()')
		self.cmdset.add(ElevatorCallCmdSet, persistent=True)

	def get_display_name(self, looker, **kwargs):
		name = super().get_display_name(looker, **kwargs)
		if panel := self.link:
			stops = panel.db.stops
			call_list = panel.nattributes.get("call_list",[])
			if self.location in stops:
				if stops.index(self.location) in call_list:
					name = f"{name}, lit," if kwargs.get("article",False) else f"lit {name}"

		return name

	def get_display_footer(self, looker, **kwargs):
		message = super().get_display_footer(looker, **kwargs)
		if panel := self.link:
			stops = panel.db.stops
			call_list = panel.nattributes.get("call_list",[])
			if self.location in stops:
				if stops.index(self.location) in call_list:
					message += "\nThe light is on."
		return message

## Commands

# TODO: this should probably just be an object use
class CmdElevatorCall(Command):
	"""
	Call an elevator to come to this floor.

	Usage:
		call elevator
	"""
	key = "call elevator"
	aliases = ("push",)
	locks="cmd:perm(Player)"
	help_category = "here"

	def func(self):

		caller = self.caller

		panel = self.obj.link
		if not panel:
			caller.msg("There is no elevator to call.")
			return

		stoplist = panel.db.stops
		if not stoplist:
			caller.msg("This elevator is out of order.")
			return
		if caller.location not in stoplist:
			caller.msg("Something seems to be wrong with this elevator...")
			return

		num = stoplist.index(caller.location)
		call_list = panel.ndb.call_list or []
		if num in call_list:
			caller.msg("The elevator is already on its way.")
		else:
			call_list.append(num)
			panel.ndb.call_list = sorted(call_list)
			caller.emote(f"The {self.sdesc.get(strip=True)} lights up, showing the elevator is on its way.", anonymous_add=None)
		if not panel.ndb.waiting:
			panel.move_next()

# TODO: this should probably just be an object use
class CmdElevatorPush(Command):
	"""
	Send the elevator to a different floor.

	Usage:
		push <number>
	"""
	key = "push"
	locks = "cmd:perm(Player)"
	help_category = "here"
	
	def func(self):
		caller = self.caller
		obj = self.obj
		stoplist = obj.db.stops
		
		if not self.args:
			caller.msg("Push what?")
			return
		if not stoplist:
			caller.msg("There are no stops available.")
			return

		value = self.args.strip()
		
		try:
			num = int(value)
		except ValueError:
			floor = str(value)
			floors = [i for i, stop in enumerate(stoplist) if floor in stop.get_display_name(obj)]
			if not len(floors):
				caller.msg(f"{value} is not a valid option.")
				return
			num = floors[0]

		max = len(stoplist)
		if num > max:
			caller.msg(f"There is no {num} button.")
			return
		
		num -= 1
		call_list = obj.nattributes.get("call_list", [])
		if num in call_list:
			caller.msg(f"The {num+1} button is already lit.")
		else:
			call_list.append(num)
			obj.ndb.call_list = sorted(call_list)
			obj.emote(f"The {num+1} button lights up.", anonymous_add=None)
		if not obj.ndb.waiting:
			obj.move_next()
	
	
class ElevatorCmdSet(CmdSet):
	key = "ElevatorCmdSet"
	priority = 2
	
	def at_cmdset_creation(self):
		self.add(CmdElevatorPush())

class ElevatorCallCmdSet(CmdSet):
	key = "ElevatorCallCmdSet"
	
	def at_cmdset_creation(self):
		self.add(CmdElevatorCall())
