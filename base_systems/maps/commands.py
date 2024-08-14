from collections import defaultdict
from django.conf import settings
from evennia import CmdSet, create_object, InterruptCommand
from evennia.commands.default.building import CmdExamine as BaseCmdExamine
from evennia.commands.default.batchprocess import CmdBatchCode
from evennia.utils import delay, iter_to_str, is_iter, logger, search, display_len, dbref

from core.commands import Command
from core.ic.behaviors import BEHAVIOR_REGISTRY
from core.scripts import Script

from base_systems.exits.base import Exit
from base_systems.rooms.base import Room
from base_systems.characters.base import Character
from base_systems.things.base import Thing
from base_systems.meta.base import MetaThing

from .building import get_obj_family, gen_zone_ids, write_object_creation, write_script_creation
from .pathing import compass_rose, compass_words, dir_to_abbrev

class BuilderCommand(Command):
	"""
	A base command class with shared functionality for area-building tools.
	"""
	splitters = (',', '=')
	all_splitters = True
	help_category = "Building"
	locks = "cmd:perm(dig) or perm(Builder)"

	# lockstring of newly created rooms, for easy overloading.
	# Will be formatted with the {id} of the creating object.
	new_room_lockstring = (
		"control:id({id}) or perm(Admin); "
		"delete:id({id}) or perm(Admin); "
		"edit:id({id}) or perm(Admin)"
	)

	new_obj_lockstring = "control:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"

	def create_exit(self, location, destination, name, aliases=None, typeclass=None, direction=None, tags=None):
		"""
		Helper function to avoid code duplication.
		At this point we know destination is a valid location

		"""
		caller = self.caller
		string = ""
		if aliases and not direction:
			for alias in aliases:
				# TODO: implement in/out up/down
				if alias in compass_rose:
					direction = compass_words[alias]
					break
				elif direct := dir_to_abbrev(alias):
					direction = compass_words[direct]
					break

		# check if this exit object already exists at the location.
		# we need to ignore errors (so no automatic feedback)since we
		# have to know the result of the search to decide what to do.
		exit_obj = caller.search(name, location=location, quiet=True, exact=True)
		if len(exit_obj) > 1:
			# give error message and return 
			caller.search(name, location=location, exact=True)
			return None
		if exit_obj:
			exit_obj = exit_obj[0]
			if not exit_obj.destination:
				# we are trying to link a non-exit
				caller.msg(
					f"'{name}' already exists and is not an exit!\nIf you want to convert it "
					"to an exit, you must assign an object to the 'destination' property first."
				)
				return None
			# we are re-linking an old exit.
			old_destination = exit_obj.destination
			if old_destination:
				string = f"Exit {name} already exists."
				if old_destination.id != destination.id:
					# reroute the old exit.
					exit_obj.destination = destination
					if direction:
						exit_obj.db.direction = direction
					if aliases:
						[exit_obj.aliases.add(alias) for alias in aliases]
					string += (
						f" Rerouted its old destination '{old_destination.name}' to"
						f" '{destination.name}' and changed aliases."
					)
				else:
					string += " It already points to the correct place."

		else:
			# exit does not exist before. Create a new one.
			lockstring = self.new_obj_lockstring.format(id=caller.id)
			if not typeclass:
				typeclass = settings.BASE_EXIT_TYPECLASS
			exit_obj = create_object(
				typeclass,
				key=name,
				location=location,
				aliases=aliases,
				tags=tags,
				locks=lockstring,
				report_to=caller,
			)
			if exit_obj:
				# storing a destination is what makes it an exit!
				exit_obj.destination = destination
				if direction:
					exit_obj.db.direction = direction
				string = (
					""
					if not aliases
					else " (aliases: %s)" % ", ".join([str(e) for e in aliases])
				)
				string = (
					f"Created new Exit '{name}' ({exit_obj.dbref}) from {location.name} ({location.dbref}) to"
					f" {destination.name} ({destination.dbref}){string}."
				)
			else:
				string = f"Error: Exit '{name}' not created."
		# emit results
		caller.msg(string)
		return exit_obj
	
	def parse(self):
		super().parse()
		# separate out aliases/typeclasses
		def split_out_data(arg):
			if not arg:
				return {}
			data = {}
			name, *typeclass = arg.split(':')
			if typeclass:
				data['typeclass'] = typeclass[0]
			name, *aliases = name.split(';')
			data['name'] = name
			data['aliases'] = aliases
			return data

		# THIS IS TERRIBLE
		room = self.argslist[0][0]
		exit_to = exit_from = ''
		if len(self.argslist) > 1:
			exits = self.argslist[1]
			exit_to = exits[0]
			if len(exits) > 1:
				exit_from = exits[1]

		self.room = split_out_data(room)
		self.exit_to = split_out_data(exit_to)
		self.exit_from = split_out_data(exit_from)
		if self.exit_to and not self.exit_from:
			name = self.exit_to['name']
			# TODO: add support for in/out up/down
			if name in compass_rose:
				dirkey = name
				self.exit_to['aliases'].append(name)
				self.exit_to['name'] = compass_words[name]
			else:
				dirkey = dir_to_abbrev(name)
			if dirkey:
				self.exit_to['direction'] = compass_words[dirkey]
				if dirkey not in self.exit_to['aliases']:
					self.exit_to['aliases'].append(dirkey)
				back_key = compass_rose[ compass_rose.index(dirkey)-4 ]
				self.exit_from['direction'] = compass_words[back_key]
				if tclass := self.exit_to.get('typeclass'):
					self.exit_from['typeclass'] = tclass
				self.exit_from['aliases'] = back_key
				self.exit_from['name'] = compass_words[back_key]


class CmdDig(BuilderCommand):
	"""
	build new rooms and connect them to the current location

	Usage:
	  dig <roomname>[;alias;alias...][:typeclass]
			[, <exit_to_there>[;alias][:typeclass]]
			   [= <exit_to_here>[;alias][:typeclass]]

	Examples:
	   dig kitchen, north;n=south;s
	   dig house:myrooms.MyHouseTypeclass
	   dig sheer cliff;cliff;sheer, climb up=climb down

	This command is a convenient way to build rooms quickly; it creates the
	new room and you can optionally set up exits back and forth between your
	current room and the new one. You can add as many aliases as you
	like to the name of the room and the exits in question; an example
	would be 'north;no;n'.

	Notes:
		If a single directional exit is given leading to the new room, a matching
		return exit will be created automatically.

		If your current location is within a zone, the new room and any exits will
		be created with the same zone.
	"""

	key = "@dig"
	locks = "cmd:perm(dig) or perm(Builder)"

	def func(self):
		caller = self.caller

		if not self.room or not self.room['name']:
			self.msg("You must at least specify a room name. $h(help dig) for more detail.")
			return

		location = caller.location
		zones = location.tags.get(category="zone", return_list=True)
		tags = [(key, "zone") for key in zones]

		# Create the new room
		typeclass = self.room.get("typeclass")
		if not typeclass:
			typeclass = settings.BASE_ROOM_TYPECLASS

		# create room
		new_room = create_object(
			typeclass=typeclass, key=self.room["name"], aliases=self.room["aliases"], tags=tags, report_to=caller
		)
		lockstring = self.new_room_lockstring.format(id=caller.id)
		new_room.locks.add(lockstring)
		alias_string = ""
		if new_room.aliases.all():
			alias_string = " (%s)" % ", ".join(new_room.aliases.all())
		self.msg(
			f"Created room {new_room}({new_room.dbref}){alias_string} of type {typeclass}."
		)

		# create exit to room
		if not location and (self.exit_to or self.exit_from):
			self.msg("You cannot create exits to or from nowhere.")
		else:
			if self.exit_to:
				if not self.exit_to["name"]:
					self.msg("No exit created to new room; a name is required.")
				else:
					# Build the exit to the new room from the current one
					new_to_exit = self.create_exit(location, new_room, tags=tags, **self.exit_to)

			if self.exit_from:
				if not self.exit_from["name"]:
					self.msg("No exit created from new room; a name is required.")
				else:
					# Build the exit back from the new room to the current one
					new_from_exit = self.create_exit(new_room, location, tags=tags, **self.exit_from)

class CmdOpen(BuilderCommand):
	"""
	open a new exit from the current room

	Usage:
	  open <destination>, <exit_to_there>[;alias][:typeclass][= <exit_to_here>[;alias][:typeclass]]

	Examples:
	   open kitchen, north;n=south;s
	   open #25, suspicious door;sus;door:exits.HiddenExit

	Handles the creation of exits. If a destination is given, the exit
	will point there. The <return exit> argument sets up an exit at the
	destination leading back to the current room. Destination name
	can be given both as a #dbref and a name, if that name is globally
	unique.

	"""

	key = "@open"
	aliases = ('@open to',)

	def parse(self):
		super().parse()
		self.location = self.caller.location
		if not self.room or not self.exit_to:
			self.caller.msg(
				"Usage: open <destination>, <exit_to_there>[;alias][:typeclass][= <exit_to_here>[;alias][:typeclass]]"
			)
			raise InterruptCommand
		if not self.location:
			self.caller.msg("You cannot create an exit from nowhere.")
			raise InterruptCommand
		self.destination = self.caller.search(self.room['name'], global_search=True)
		if not self.destination:
			raise InterruptCommand

	def func(self):
		"""
		This is where the processing starts.
		Uses the ObjManipCommand.parser() for pre-processing
		as well as the self.create_exit() method.
		"""
		# Create exit
		ok = self.create_exit(self.location, self.destination, **self.exit_to)
		if not ok:
			# an error; the exit was not created, so we quit.
			return
		# Create back exit, if any
		if self.exit_from:
			self.create_exit(self.destination, self.location, **self.exit_from)

class CmdDestroy(Command):
	"""
	permanently delete objects

	Usage:
	   destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]

	Examples:
	   destroy house, roof, door, 44-78
	   destroy 5-10, flower, 45

	Destroys one or many objects. If dbrefs are used, a range to delete can be
	given, e.g. 4-10. Also the end points will be deleted. This command
	displays a confirmation before destroying, to make sure of your choice.
	"""

	key = "@destroy"
	aliases = ["@delete", "@del"]
	locks = "cmd:perm(destroy) or perm(Builder)"
	help_category = "Building"
	splitters = (",",)

	confirm = True  # set to False to always bypass confirmation
	default_confirm = "yes"  # what to assume if just pressing enter (yes/no)

	def func(self):
		"""Implements the command."""

		caller = self.caller

		if not self.argslist:
			caller.msg("Usage: destroy[/switches] [obj, obj2, obj3, [dbref-dbref],...]")
			return

		def delobj(obj):
			# helper function for deleting a single object
			string = ""
			if not obj.pk:
				string = f"\nObject {obj.db_key} was already deleted."
			else:
				objname = obj.name
				if not (obj.access(caller, "control") or obj.access(caller, "delete")):
					return f"\nYou don't have permission to delete {objname}."
				if obj.account and "override" not in self.switches:
					return (
						f"\nObject {objname} is controlled by an active account. Use /override to"
						" delete anyway."
					)
				if obj.dbid == int(settings.DEFAULT_HOME.lstrip("#")):
					return (
						f"\nYou are trying to delete |c{objname}|n, which is set as DEFAULT_HOME. "
						"Re-point settings.DEFAULT_HOME to another "
						"object before continuing."
					)

				# do the deletion
				okay = obj.delete(full=True)
				if not okay:
					string += (
						f"\nERROR: {objname} not deleted - delete() returned False."
					)
				else:
					string += f"\n{objname} was destroyed. All parts and any exits to or from {objname} were destroyed as well."
			return string

		objs = set()
		for objname in self.argslist:
			if "-" in objname:
				# might be a range of dbrefs
				dmin, dmax = [dbref(part, reqhash=False) for part in objname.split("-", 1)]
				if dmin and dmax:
					for dbref in range(int(dmin), int(dmax + 1)):
						obj = caller.search("#" + str(dbref), quiet=True)
						if obj:
							objs.append(obj)
					continue
				else:
					obj = yield from self.find_targets(objname)
			else:
				obj = yield from self.find_targets(objname)

			if not obj:
				self.msg(
					" (Objects to destroy must either be local or specified with a unique #dbref.)"
				)
				return
			elif is_iter(obj):
				objs.update(obj)
			else:
				objs.add(obj)

		if objs:
			confirm = "Are you sure you want to destroy "
			if len(objs) < 5:
				confirm += ", ".join([obj.get_display_name(caller) for obj in objs])
			else:
				confirm += ", ".join(["#{}".format(obj.id) for obj in objs])
			confirm += " [yes]/no?" if self.default_confirm == "yes" else " yes/[no]"
			answer = yield(confirm)
			answer = answer or self.default_confirm

			if answer not in ("yes", "y", "no", "n"):
				self.msg(
					"Canceled: Either accept the default by pressing return or specify yes/no."
				)
				return
			elif answer.strip().lower() in ("n", "no"):
				self.msg("Canceled: No object was destroyed.")
				return

		results = []
		for obj in objs:
			results.append(delobj(obj))

		if results:
			caller.msg("".join(results).strip())

class CmdGenIDs(Command):
	"""
	generate unique IDs for zoned objects

	Usage:
		generate ids
	
	Checks all zoned objects and, if they don't already have an ID, creates one.
	"""
	key = "generate ids"
	help_category = "Building"
	locks = "cmd:perm(gen_id) or perm(Builder)"

	def func(self):
		from evennia.typeclasses.tags import Tag

		zone_list = set(t.db_key for t in Tag.objects.filter(db_category="zone"))
		# prevent locking up the game too badly by delaying each zone
		self.msg(f"Generating IDs for the following zones: {iter_to_str(zone_list)}")
		# TODO: make this use delay_iter
		for i, zone_tag in enumerate(zone_list):
			delay(i, gen_zone_ids, zone_tag, self.session)


class CmdBuildWrite(Command):
	"""
	generate a build script for the current UID'd game world

	Usage:
		generate build
	
	!! WARNING !!
	This will cause the game to hang if there are many rooms. Do NOT run on Production!
	"""
	key = "generate build"
	help_category = "Building"
	locks = "cmd:pperm(Developer)"

	def func(self):
		from time import time

		filename = f"world/builds/{int(time())}.py"
		self.msg(f"Writing rebuild script to {filename}....")
		with open(filename, "w+") as file:
			file.write("from base_systems.maps.building import update_or_create_object, update_or_create_script, deref_uids\n")
			file.write("affected = []\n")
			self.msg("Writing out Room recreations....")
			for obj in Room.objects.all_family():
				if obj.uid:
					write_object_creation(obj, file)
					file.write("affected.append(obj)\n")
			self.msg("Writing out Exit recreations....")
			for obj in Exit.objects.all_family():
				if obj.uid:
					write_object_creation(obj, file)
					file.write("affected.append(obj)\n")
			self.msg("Writing out Object recreations....")
			for obj in Thing.objects.all_family():
				if obj.uid:
					write_object_creation(obj, file)
					file.write("affected.append(obj)\n")
			self.msg("Writing out Character recreations....")
			for obj in Character.objects.all_family():
				if obj.uid:
					write_object_creation(obj, file)
					file.write("affected.append(obj)\n")
			for obj in MetaThing.objects.all_family():
				if obj.uid:
					write_object_creation(obj, file)
					file.write("affected.append(obj)\n")
			self.msg("Writing out Script recreations....")
			for obj in Script.objects.all_family():
				if obj.uid:
					write_script_creation(obj, file)
					file.write("affected.append(obj)\n")
			# ensure all object references in attributes are dereferenced
			file.write("for obj in affected:\n")
			file.write("  unpacked = [ (attr.key, deref_uids(attr.value), attr.category) for attr in obj.attributes.all()]\n")
			file.write("  obj.attributes.batch_add(*unpacked)\n")

		self.msg("Rebuild script complete.")

class CmdZone(Command):
	"""
	assign the zone for an object or location

	Usage:
		zone <obj>=<zone>
	
	Examples:
		zone table=kitchen
		zone here=mystic forest
	"""
	key = "zone"
	splitters = "="
	locks = "cmd:perm(Builder)"

	def func(self):
		if len(self.argslist) == 1:
			target = self.argslist[0]
			zone = None
		elif len(self.argslist) != 2:
			self.msg("Usage: zone <obj>=<zone>")
			return
		else:
			target, zone = self.argslist

		targets = yield from self.find_targets(target)
		if not targets:
			return
		
		if zone:
			for t in targets:
				message = ""
				if zones := t.tags.get(category='zone', return_list=True):
					if zone in zones:
						self.msg(f"{t.get_display_name(self.caller)} is already in zone $h({zone}); no change made.")
						continue
					message = f"removed zone $h({iter_to_str(zones)}) and "
				t.tags.remove(category='zone')
				t.tags.add(zone, category='zone')
				for p in t.parts.all():
					p.tags.remove(category='zone')
					p.tags.add(zone, category='zone')
				for s in t.scripts.all():
					s.tags.remove(category='zone')
					s.tags.add(zone, category='zone')
				message += f"assigned zone $h({zone}) to {t.get_display_name(self.caller)}."
				message = message[0].upper() + message[1:]
				self.msg(message)
		else:
			for t in targets:
				if zones := t.tags.get(category='zone', return_list=True):
					self.msg(f"{t} (#{t.id}) is zoned as $h({iter_to_str(zones)}).")
				else:
					self.msg(f"{t} (#{t.id}) is not zoned.")


class CmdBuildLatest(CmdBatchCode):
	key = "build latest"
	aliases = []
	locks = 'cmd:pperm(Developer)'

	def parse(self):
		super().parse()
		self.switches = []
		import os
		files = []
		with os.scandir(os.path.abspath('./world/builds/')) as builds:
			for item in builds:
				if item.name.endswith('.py'):
					files.append('builds/'+item.name[:-3])
		if files:
			files.sort()
			self.args = files[-1]

	def at_post_cmd(self):
		super().at_post_cmd()
		if self.args:
			self.msg("Make sure to $h(reload) to update the pathfinding.")


class CmdExamine(BaseCmdExamine):
	object_type = "object"

	detail_color = "|c"
	header_color = "|w"
	quell_color = "|r"
	separator = "-"

	# def msg(self, text):
	# 	"""
	# 	Central point for sending messages to the caller. This tags
	# 	the message as 'examine' for eventual custom markup in the client.

	# 	Attributes:
	# 		text (str): The text to send.

	# 	"""
	# 	super().msg(text=(text, {"type": "examine"}))


	def format_typeclass(self, obj):
		if hasattr(obj, "typeclass_path"):
			return f"{obj.typename} ({obj.typeclass_path})"

	def format_sessions(self, obj):
		if hasattr(obj, "sessions"):
			sessions = obj.sessions.all()
			if sessions:
				return ", ".join(f"#{sess.sessid}" for sess in obj.sessions.all())

	def format_email(self, obj):
		if hasattr(obj, "email") and obj.email:
			return f"{self.detail_color}{obj.email}|n"


	def format_last_login(self, obj):
		if hasattr(obj, "last_login") and obj.last_login:
			return f"{self.detail_color}{obj.last_login}|n"


	def format_account_key(self, account):
		return f"{self.detail_color}{account.name}|n ({account.dbref})"


	def format_account_typeclass(self, account):
		return f"{account.typename} ({account.typeclass_path})"


	# def format_account_permissions(self, account):
	# 	perms = account.permissions.all()
	# 	if account.is_superuser:
	# 		perms = ["<Superuser>"]
	# 	elif not perms:
	# 		perms = ["<None>"]
	# 	perms = ", ".join(perms)
	# 	if account.attributes.has("_quell"):
	# 		perms += f" {self.quell_color}(quelled)|n"
	# 	return perms


	# def format_location(self, obj):
	# 	if hasattr(obj, "location") and obj.location:
	# 		return f"{obj.location.key} (#{obj.location.id})"


	# def format_home(self, obj):
	# 	if hasattr(obj, "home") and obj.home:
	# 		return f"{obj.home.key} (#{obj.home.id})"


	# def format_destination(self, obj):
	# 	if hasattr(obj, "destination") and obj.destination:
	# 		return f"{obj.destination.key} (#{obj.destination.id})"


	# def format_permissions(self, obj):
	# 	perms = obj.permissions.all()
	# 	if perms:
	# 		perms_string = ", ".join(perms)
	# 		if obj.is_superuser:
	# 			perms_string += " <Superuser>"
	# 		return perms_string


	def format_locks(self, obj):
		locks = str(obj.locks)
		if locks:
			return "; ".join([lock for lock in locks.split(";")])
		return "Default"


	# def format_scripts(self, obj):
	# 	if hasattr(obj, "scripts") and hasattr(obj.scripts, "all") and obj.scripts.all():
	# 		return f"{obj.scripts}"


	def format_single_tag(self, tag):
		if tag.db_category:
			return f"{tag.db_key}[{tag.db_category}]"
		else:
			return f"{tag.db_key}"


	def format_tags(self, obj):
		if hasattr(obj, "tags"):
			tags = sorted(obj.tags.all(return_objs=True))
			if tags:
				formatted_tags = [self.format_single_tag(tag) for tag in tags]
				return ", ".join(formatted_tags)


	# def format_single_cmdset_options(self, cmdset):
	# 	def _truefalse(string, value):
	# 		if value is None:
	# 			return ""
	# 		if value:
	# 			return f"{string}: T"
	# 		return f"{string}: F"

	# 	txt = ", ".join(
	# 		_truefalse(opt, getattr(cmdset, opt))
	# 		for opt in ("no_exits", "no_objs", "no_channels", "duplicates")
	# 		if getattr(cmdset, opt) is not None
	# 	)
	# 	return ", " + txt if txt else ""


	# def format_single_cmdset(self, cmdset):
	# 	options = self.format_single_cmdset_options(cmdset)
	# 	return f"{cmdset.path} [{cmdset.key}] ({cmdset.mergetype}, prio {cmdset.priority}{options})"


	# def format_stored_cmdsets(self, obj):
	# 	if hasattr(obj, "cmdset"):
	# 		stored_cmdset_strings = []
	# 		stored_cmdsets = sorted(obj.cmdset.all(), key=lambda x: x.priority, reverse=True)
	# 		for cmdset in stored_cmdsets:
	# 			if cmdset.key != "_EMPTY_CMDSET":
	# 				stored_cmdset_strings.append(self.format_single_cmdset(cmdset))
	# 		return "\n  " + "\n  ".join(stored_cmdset_strings)


	# def format_merged_cmdsets(self, obj, current_cmdset):
	# 	if not hasattr(obj, "cmdset"):
	# 		return None

	# 	all_cmdsets = [(cmdset.key, cmdset) for cmdset in current_cmdset.merged_from]
	# 	# we always at least try to add account- and session sets since these are ignored
	# 	# if we merge on the object level.
	# 	if inherits_from(obj, evennia.DefaultObject) and obj.account:
	# 		# get Attribute-cmdsets if they exist
	# 		all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.account.cmdset.all()])
	# 		if obj.sessions.count():
	# 			# if there are more sessions than one on objects it's because of multisession mode
	# 			# we only show the first session's cmdset here (it is -in principle- possible
	# 			# that different sessions have different cmdsets but for admins who want such
	# 			# madness it is better that they overload with their own CmdExamine to handle it).
	# 			all_cmdsets.extend(
	# 				[(cmdset.key, cmdset) for cmdset in obj.account.sessions.all()[0].cmdset.all()]
	# 			)
	# 	else:
	# 		try:
	# 			# we have to protect this since many objects don't have sessions.
	# 			all_cmdsets.extend(
	# 				[
	# 					(cmdset.key, cmdset)
	# 					for cmdset in obj.get_session(obj.sessions.get()).cmdset.all()
	# 				]
	# 			)
	# 		except (TypeError, AttributeError):
	# 			# an error means we are merging an object without a session
	# 			pass
	# 	all_cmdsets = [cmdset for cmdset in dict(all_cmdsets).values()]
	# 	all_cmdsets.sort(key=lambda x: x.priority, reverse=True)

	# 	merged_cmdset_strings = []
	# 	for cmdset in all_cmdsets:
	# 		if cmdset.key != "_EMPTY_CMDSET":
	# 			merged_cmdset_strings.append(self.format_single_cmdset(cmdset))
	# 	return "\n  " + "\n  ".join(merged_cmdset_strings)


	# def format_current_cmds(self, obj, current_cmdset):
	# 	current_commands = sorted([cmd.key for cmd in current_cmdset if cmd.access(obj, "cmd")])
	# 	return "\n" + utils.fill(", ".join(current_commands), indent=2)


	# def format_single_attribute_detail(self, obj, attr):
	# 	global _FUNCPARSER
	# 	if not _FUNCPARSER:
	# 		_FUNCPARSER = funcparser.FuncParser(settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES)

	# 	key, category, value = attr.db_key, attr.db_category, attr.value
	# 	typ = self._get_attribute_value_type(value)
	# 	typ = f" |B[type: {typ}]|n" if typ else ""
	# 	value = utils.to_str(value)
	# 	value = _FUNCPARSER.parse(ansi_raw(value), escape=True)
	# 	return (
	# 		f"Attribute {obj.name}/$h({key}) "
	# 		f"[category={category}]{typ}:\n\n{value}"
	# 	)


	# def format_single_attribute(self, attr):
	# 	global _FUNCPARSER
	# 	if not _FUNCPARSER:
	# 		_FUNCPARSER = funcparser.FuncParser(settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES)

	# 	key, category, value = attr.db_key, attr.db_category, attr.value
	# 	typ = self._get_attribute_value_type(value)
	# 	typ = f" |B[type: {typ}]|n" if typ else ""
	# 	value = utils.to_str(value)
	# 	value = _FUNCPARSER.parse(ansi_raw(value), escape=True)
	# 	value = utils.crop(value)
	# 	if category:
	# 		return f"{self.header_color}{key}|n[{category}]={value}{typ}"
	# 	else:
	# 		return f"{self.header_color}{key}|n={value}{typ}"


	def format_attributes(self, obj):
		output = "\n  " + "\n  ".join(
			sorted(self.format_single_attribute(attr) for attr in obj.db_attributes.all() if attr.category not in ('systems', 'traits'))
		)
		if output.strip():
			# we don't want just an empty line
			return output


	# def format_nattributes(self, obj):
	# 	try:
	# 		ndb_attr = obj.nattributes.all()
	# 	except Exception:
	# 		return

	# 	if ndb_attr and ndb_attr[0]:
	# 		return "\n  " + "\n  ".join(
	# 			sorted(self.format_single_attribute(attr) for attr in ndb_attr)
	# 		)

	# def format_exits(self, obj):
	# 	if hasattr(obj, "exits"):
	# 		exits = ", ".join(f"{exit.name}({exit.dbref})" for exit in obj.exits)
	# 		return exits if exits else None


	# def format_chars(self, obj):
	# 	if hasattr(obj, "contents"):
	# 		chars = ", ".join(f"{o.name}({o.dbref})" for o in obj.contents if 'character' in o.content_types)
	# 		return chars if chars else None


	# def format_things(self, obj):
	# 	if hasattr(obj, "contents"):
	# 		things = ", ".join(
	# 			f"{obj.name}({obj.dbref})"
	# 			for obj in obj.contents
	# 			if not obj.account and not obj.destination
	# 		)
	# 		return things if things else None

	def format_parts(self, obj):
		if hasattr(obj, "parts"):
			things = ", ".join(
				f"{obj.name}({obj.dbref})"
				for obj in obj.parts.all()
			)
			return things if things else None


	# def format_script_desc(self, obj):
	# 	if hasattr(obj, "db_desc") and obj.db_desc:
	# 		return crop(obj.db_desc, 20)


	# def format_script_is_persistent(self, obj):
	# 	if hasattr(obj, "db_persistent"):
	# 		return "T" if obj.db_persistent else "F"


	# def format_script_timer_data(self, obj):
	# 	if hasattr(obj, "db_interval") and obj.db_interval > 0:
	# 		start_delay = "T" if obj.db_start_delay else "F"
	# 		next_repeat = obj.time_until_next_repeat()
	# 		active = "|grunning|n" if obj.db_is_active and next_repeat else "|rinactive|n"
	# 		interval = obj.db_interval
	# 		next_repeat = "N/A" if next_repeat is None else f"{next_repeat}s"
	# 		repeats = ""
	# 		if obj.db_repeats:
	# 			remaining_repeats = obj.remaining_repeats()
	# 			remaining_repeats = 0 if remaining_repeats is None else remaining_repeats
	# 			repeats = f" - {remaining_repeats}/{obj.db_repeats} remain"
	# 		return (
	# 			f"{active} - interval: {interval}s "
	# 			f"(next: {next_repeat}{repeats}, start_delay: {start_delay})"
	# 		)


	# def format_channel_sub_totals(self, obj):
	# 	if hasattr(obj, "db_account_subscriptions"):
	# 		account_subs = obj.db_account_subscriptions.all()
	# 		object_subs = obj.db_object_subscriptions.all()
	# 		online = len(obj.subscriptions.online())
	# 		ntotal = account_subs.count() + object_subs.count()
	# 		return f"{ntotal} ({online} online)"

	# def format_channel_account_subs(self, obj):
	# 	if hasattr(obj, "db_account_subscriptions"):
	# 		account_subs = obj.db_account_subscriptions.all()
	# 		if account_subs:
	# 			return "\n  " + "\n  ".join(
	# 				format_grid([sub.key for sub in account_subs], sep=" ", width=_DEFAULT_WIDTH)
	# 			)

	# def format_channel_object_subs(self, obj):
	# 	if hasattr(obj, "db_object_subscriptions"):
	# 		object_subs = obj.db_object_subscriptions.all()
	# 		if object_subs:
	# 			return "\n  " + "\n  ".join(
	# 				format_grid([sub.key for sub in object_subs], sep=" ", width=_DEFAULT_WIDTH)
	# 			)


	def get_formatted_obj_data(self, obj, current_cmdset):
		"""
		Calls all other `format_*` methods.

		"""
		objdata = {}
		objdata["Name/key"] = self.format_key(obj)
		objdata["Aliases"] = self.format_aliases(obj)
		objdata["Typeclass"] = self.format_typeclass(obj)
		objdata["Sessions"] = self.format_sessions(obj)
		objdata["Email"] = self.format_email(obj)
		objdata["Last Login"] = self.format_last_login(obj)
		if getattr(obj, 'has_account', None):
			objdata["Account"] = self.format_account_key(obj.account)
			objdata["  Account Typeclass"] = self.format_account_typeclass(obj.account)
			objdata["  Account Permissions"] = self.format_account_permissions(obj.account)
		objdata["Location"] = self.format_location(obj)
		objdata["Home"] = self.format_home(obj)
		objdata["Destination"] = self.format_destination(obj)
		objdata["Permissions"] = self.format_permissions(obj)
		objdata["Locks"] = self.format_locks(obj)
		if current_cmdset and not (
			len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "_EMPTY_CMDSET"
		):
			objdata["Stored Cmdset(s)"] = self.format_stored_cmdsets(obj)
			objdata["Merged Cmdset(s)"] = self.format_merged_cmdsets(obj, current_cmdset)
			objdata[
				f"Commands available to {obj.key} (result of Merged Cmdset(s))"
			] = self.format_current_cmds(obj, current_cmdset)
		if self.object_type == "script":
			objdata["Description"] = self.format_script_desc(obj)
			objdata["Persistent"] = self.format_script_is_persistent(obj)
			objdata["Script Repeat"] = self.format_script_timer_data(obj)
		objdata["Scripts"] = self.format_scripts(obj)
		objdata["Tags"] = self.format_tags(obj)
		objdata["Persistent Attributes"] = self.format_attributes(obj)
		objdata["Non-Persistent Attributes"] = self.format_nattributes(obj)
		objdata["Exits"] = self.format_exits(obj)
		objdata["Characters"] = self.format_chars(obj)
		objdata["Contents"] = self.format_things(obj)
		objdata["Parts"] = self.format_parts(obj)
		if self.object_type == "channel":
			objdata["Subscription Totals"] = self.format_channel_sub_totals(obj)
			objdata["Account Subscriptions"] = self.format_channel_account_subs(obj)
			objdata["Object Subscriptions"] = self.format_channel_object_subs(obj)

		return objdata

	def format_output(self, obj, current_cmdset):
		"""
		Formats the full examine page return.

		"""
		objdata = self.get_formatted_obj_data(obj, current_cmdset)

		# format output
		main_str = []
		max_width = -1
		for header, block in objdata.items():
			if block is not None:
				blockstr = f"{self.header_color}{header}|n: {block}"
				max_width = max(max_width, max(display_len(line) for line in blockstr.split("\n")))
				main_str.append(blockstr)
		main_str = "\n".join(main_str)

		max_width = max(0, min(self.client_width(), max_width))
		sep = self.separator * max_width

		return f"{sep}\n{main_str}\n{sep}"


# 	def func(self):
# 		"""Process command"""
# 		for obj, obj_attrs in self.examine_objs:
# 			# these are parsed out in .parse already

# 			if not obj.access(self.caller, "examine"):
# 				# If we don't have special info access, just look
# 				# at the object instead.
# 				self.msg(self.caller.at_look(obj))
# 				continue

# 			if obj_attrs:
# 				# we are only interested in specific attributes
# 				attrs = [attr for attr in obj.db_attributes.all() if attr.db_key in obj_attrs]
# 				if not attrs:
# 					self.msg(f"No attributes found on {obj.name}.")
# 				else:
# 					out_strings = []
# 					for attr in attrs:
# 						out_strings.append(self.format_single_attribute_detail(obj, attr))
# 					out_str = "\n".join(out_strings)
# #					max_width = max(display_len(line) for line in out_strings)
# 					max_width = max(0, min(max_width, self.client_width()))
# 					sep = self.separator * max_width
# 					self.msg(f"{sep}\n{out_str}")
# 				return

# 			# examine the obj itself

# 			if self.object_type in ("object", "account"):
# 				# for objects and accounts we need to set up an asynchronous
# 				# fetch of the cmdset and not proceed with the examine display
# 				# until the fetch is complete
# 				session = None
# 				if obj.sessions.count():
# 					mergemode = "session"
# 					session = obj.sessions.get()[0]
# 				elif self.object_type == "account":
# 					mergemode = "account"
# 				else:
# 					mergemode = "object"

# 				account = None
# 				objct = None
# 				if self.object_type == "account":
# 					account = obj
# 				else:
# 					account = obj.account
# 					objct = obj

# 				# this is usually handled when a command runs, but when we examine
# 				# we may have leftover inherited cmdsets directly after a move etc.
# 				obj.cmdset.update()
# 				# using callback to print results whenever function returns.

# 				def _get_cmdset_callback(current_cmdset):
# 					self.msg(self.format_output(obj, current_cmdset).strip())

# 				(
# 					command_objects,
# 					command_objects_list,
# 					command_objects_list_error,
# 					caller,
# 					error_to,
# 				) = generate_cmdset_providers(obj, session=session)

# 				get_and_merge_cmdsets(
# 					obj, command_objects_list, mergemode, self.raw_string, error_to
# 				).addCallback(_get_cmdset_callback)

# 			else:
# 				# for objects without cmdsets we can proceed to examine immediately
# 				self.msg(self.format_output(obj, None).strip())



class CmdAddRemBehavior(Command):
	"""
	manage behaviors on an object

	Usage:
		behaviors - list all classes
		behaviors [on] <obj> - show behaviors on object
		behavior add <behavior class> to <object>
		behavior remove/rem/del <behavior class> from <obj>
	"""
	key = "behaviors"
	locks = "cmd:perm(Builder)"
	aliases = ('behavior',)
	prefixes = ('to', 'from')

	def func(self):
		if self.cmdstring == 'behaviors':
			# we list them
			if search_term := self.args:
				if search_term.startswith('on '):
					search_term = search_term[3:]
				target = yield from self.find_targets(search_term, numbered=False)
				if not target:
					return
				self.msg(f"$head(Behaviors available to {target.get_display_name(self.caller)}):")
				display = []
				for key, val in target.behaviors.all().items():
					cls, clskwargs = val
					info = val[0].__name__
					if source := clskwargs.get('behavior_source'):
						if source != target:
							info += f" via {source.get_display_name(self.caller)}"

					display.append(f"  $h({key}) ({info})")
				if display:
					self.msg("\n".join(display))
					self.msg(f"All behavior classes added: "+", ".join(target.behaviors.loaded()))
				else:
					self.msg("  None")
			else:
				# list all of the registered behaviors
				self.msg("$head(Available behavior classes):")
				self.msg(", ".join(BEHAVIOR_REGISTRY.keys()))
		elif not self.args:
			self.execute_cmd('help behaviors')
			return

		else:
			if not (baseargs := self.argsdict.get(None)):
				self.msg("Usage: behavior <add/remove> <behavior> to <object>")
				return
			addremove, *key = baseargs[0].split(' ', maxsplit=1)
			if not key:
				self.msg("Usage: behavior <add/remove> <behavior> to <object>")
				return
			key = key[0]
			addremove = addremove.lower()
			if addremove not in ('add', 'rem', 'del', 'remove'):
				self.msg("Usage: behavior <add/remove> <behavior> to <object>")
				return
			if not (search_term := self.argsdict.get('to')):
				if not (search_term := self.argsdict.get('from')):
					self.msg("Usage: behavior <add/remove> <behavior> to <object>")
					return
			search_term = search_term[0]
			target = yield from self.find_targets(search_term, numbered=False)
			if not target:
				return

			if addremove == 'add':
				target.behaviors.add(key)
				self.msg(f"Added behavior '{key}' to {target.get_display_name(self.caller)}")
			else:
				target.behaviors.remove(key)
				self.msg(f"Removed behavior '{key}' from {target.get_display_name(self.caller)}")


class BuilderCmdSet(CmdSet):
	key="Builder CmdSet"

	def at_cmdset_creation(self):
		super().at_cmdset_creation()

		self.add(CmdDig)
		self.add(CmdOpen)
		self.add(CmdGenIDs)
		self.add(CmdBuildWrite)
		self.add(CmdBuildLatest)
		self.add(CmdZone)
		self.add(CmdExamine)
		self.add(CmdAddRemBehavior)
