from django.conf import settings
from evennia import CmdSet, Command
from evennia.contrib.base_systems.unixcommand import UnixCommand
from evennia.utils.create import create_object

from core.ic.base import BaseObject

class CmdSecurityAdd(UnixCommand):
	key = "secure"
	locks = "cmd:pperm(Player)"

	new_room_lockstring = ( ## this part goes before the def func
		"control:id({id}) or perm(Admin); "
		"delete:id({id}) or perm(Admin); "
		"edit:id({id}) or perm(Admin)"
	)

	def init_parser(self):
		"Add the arguments to the parser."
		# 'self.parser' inherits `argparse.ArgumentParser`
		self.parser.add_argument("-r", "--room", help="the door name, if securing a side room")
		self.parser.add_argument("-t", "--type", help="type of security layer to add")

	def func(self):
		# 'self.opts' contains the parsed options
		room = self.opts.room
		sectype = self.opts.type

		caller = self.caller
		
		# check if caller owns the room
		# TODO: use a permission lock and a server-based auth list instead
		if self.db.creator_id != caller.id:
			caller.msg("You cannot add security to this server.")
			return

		if not room:
			target = self.obj
			connection = True

		else:
			connection = False

			# try to search locally first
			results = caller.search(room, typeclass='systems.cloud.rooms.CloudExit', quiet=True)
			if len(results) > 1:  # local results was a multimatch. Inform them to be more specific
				caller.msg("Multiple rooms match. Please try again.")
				return
			elif len(results) == 1:  # A unique local match
				target = results[0]
			else:  # No matches. Search globally
				caller.msg("No rooms match. Please try again.")
				return

#### dig/link functionality
		
		#TODO: room name should be a randomized hash

		if not room["name"]:
			caller.msg("You must supply a new room name.")
			return

		if connection:
			location = self.obj.db.front_door
		else:
			location = target.destination

		# Create the new room
		typeclass = "typeclasses.rooms.SecurityRoom"

		# create room
		new_room = create_object(
			typeclass, room["name"], report_to=caller
		)
		lockstring = self.new_room_lockstring.format(id=caller.id)
		new_room.locks.add(lockstring)
		room_string = f"Created room {new_room}({new_room.dbref}){alias_string} of type {typeclass}."

		# Create exit back from new room
		## target the current connection layer if added to the hub
		## target the exit's previous destination if added to an exit

		typeclass = settings.BASE_EXIT_TYPECLASS
		new_back_exit = create_object(
			typeclass,
			back_exit["name"], # this should also be hashed or something
			new_room,
			locks=lockstring,
			destination=location,
			report_to=caller,
		)
		alias_string = ""
		if new_back_exit.aliases.all():
			alias_string = " ({})".format(", ".join(new_back_exit.aliases.all()))

		exit_back_string = f"\nCreated Exit back from {new_room.name} to {location.name}: {new_back_exit}({new_back_exit.dbref}){alias_string}."

		# this gives builder-level data, we don't want that, this is not actually a builder command
		caller.msg("%s%s%s" % (room_string, exit_to_string, exit_back_string))

		if not connection:
			# redirect exit
			target.destination = new_room



## class CmdDig(ObjManipCommand):
class CmdRoomAdd(UnixCommand):
	key = "open"
	locks = "cmd:pperm(Player)"

	new_room_lockstring = ( ## this part goes before the def func
		"control:id({id}) or perm(Admin); "
		"delete:id({id}) or perm(Admin); "
		"edit:id({id}) or perm(Admin)"
	)

	def init_parser(self):
		"Add the arguments to the parser."
		# 'self.parser' inherits `argparse.ArgumentParser`
		self.parser.add_argument("key", help="the name of the new room")
		self.parser.add_argument("-l", "--lock", help="lock the room to an auth key")
		self.parser.add_argument("--hidden", action="store_true", help="whether the room is visible from the hub")

	def func(self):
		"func is called only if the parser succeeded."
		# 'self.opts' contains the parsed options
		key = self.opts.key
		authkey = self.opts.lock
		hidden = self.opts.hidden

		caller = self.caller
		
		# check if caller owns the room
		if self.db.creator_id != caller.id:
			caller.msg("You cannot add security to this server.")
			return

		if not room:
			target = self
			connection = True

		else:
			target = room
			connection = False

			# try to search locally first
			results = caller.search(object_name, typeclass=settings.BASE_EXIT_TYPECLASS, quiet=True)
			if len(results) > 1:  # local results was a multimatch. Inform them to be more specific
				caller.msg("Multiple rooms match. Please try again.")
				return
			elif len(results) == 1:  # A unique local match
				target = results[0]
			else:  # No matches. Search globally
				caller.msg("No rooms match. Please try again.")
				return

#### dig/link functionality
		
		## room name should be a randomized hash

		if not room["name"]:
			caller.msg("You must supply a new room name.")
			return

		if connection:
			location = self.db.front_door
		else:
			location = target.destination

		# Create the new room
		typeclass = "typeclasses.rooms.SecurityRoom"

		# create room
		new_room = create_object(
			typeclass, room["name"], report_to=caller
		)
		lockstring = self.new_room_lockstring.format(id=caller.id)
		new_room.locks.add(lockstring)
		room_string = "Created room %s(%s)%s of type %s." % (
			new_room,
			new_room.dbref,
			alias_string,
			typeclass,
		)

		# Create exit back from new room
		## target the current connection layer if added to the hub
		## target the exit's previous destination if added to an exit

		typeclass = settings.BASE_EXIT_TYPECLASS
		new_back_exit = create_object(
			typeclass,
			back_exit["name"], # this should also be hashed or something
			new_room,
			locks=lockstring,
			destination=location,
			report_to=caller,
		)
		alias_string = ""
		if new_back_exit.aliases.all():
			alias_string = " (%s)" % ", ".join(new_back_exit.aliases.all())

		exit_back_string = "\nCreated Exit back from %s to %s: %s(%s)%s."
		exit_back_string = exit_back_string % (
			new_room.name,
			location.name,
			new_back_exit,
			new_back_exit.dbref,
			alias_string,
		)

		caller.msg("%s%s%s" % (room_string, exit_to_string, exit_back_string))

		if not connection:
			# redirect exit
			target.destination = new_room



class NetroomCmdSet(CmdSet):
	pass

class HubroomCmdSet(CmdSet):
	def at_cmdset_creation(self):
		self.add(CmdSecurityAdd())


class NetRoom(BaseObject):
    def announce_move_from(self, destination, msg=None, mapping=None):
        super().announce_move_from(destination, msg="{object} leaves the room.")

    def announce_move_to(self, source_location, msg=None, mapping=None):
        super().announce_move_to(source_location, msg="{object} joins the room.")

class HubNetRoom(NetRoom):
    def at_object_creation(self):
        self.db.front_door = self
        self.cmdset.add(HubroomCmdSet, persistent=True)


class SecurityRoom(NetRoom):
    # placeholder for later
    pass