"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""
from time import time

from evennia.commands import cmdset
from evennia.objects.objects import ObjectDB
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import iter_to_str, lazy_property
from base_systems.actions.base import Action, InterruptAction
from base_systems.maps import pathing
from switchboard import IMMOBILE

from core.ic.base import BaseObject
from core.commands import Command
import switchboard

_FAST_SPEED = 15
_MED_SPEED = 30

class ExitAction(Action):
	min_req_parts = (('foot', 2),) # not 100% convinced but it's fine
	max_used_parts = (('foot', 2),)

	def __init__(self, **kwargs):
		self.actor = kwargs.get('actor')
		super().__init__(**kwargs)
		if not hasattr(self, 'exit_obj'):
			raise InterruptAction

	def status(self, **kwargs):
		if self.exit_obj.db.direction:
			return f"You are going {self.exit_obj.get_display_name(looker=self.actor)}."
		else:
			# TODO: should this be grabbed from the exit msg db attributes?
			return f"You are going to {self.exit_obj.get_display_name(looker=self.actor)}."

	def start(self, **kwargs):
		if not self.exit_obj.destination:
			self.actor.msg("That doesn't go anywhere.")
			return self.end(**kwargs)
		
		tagged = self.actor.tags.has(switchboard.IMMOBILE, category="status", return_list=True)
		tagged = [ pose for (pose, hasit) in zip(switchboard.IMMOBILE, tagged) if hasit ]
		if len(tagged):
			self.actor.msg(f"You're currently {iter_to_str(tagged)}.")
			return self.end(**kwargs)

		if hasattr(self, 'skills'):
			# NOTE: this might be kind of spammy in practice
			while counter := self.actor.counteract.current:
				# TODO: assess if this skill is the right one
				if self.actor.skills.use(evasion=counter.counter_dc):
					self.actor.counteract.remove(self.counter)
					self.counter.fail()
				else:
					self.actor.emote(f"tries in vain to get away")
					return self.fail(**kwargs)
		return super().start(**kwargs)

	def do(self, **kwargs):
		if skill_req := self.exit_obj.db.skill_req:
			if self.energy:
				self.actor.life.energy -= self.energy
			success = self.actor.skills.use(**{self.exit_obj.stats.skill:skill_req})
			if not (verb := self.exit_obj.db.verb):
				verb = skill_req
			if not success:
				self.actor.emote(f"tries in vain to {verb} the {self.exit_obj.sdesc.get()}")
				return self.fail(**kwargs)

		source_location = self.actor.location
		target_location = self.exit_obj.destination
		# TODO: figure out or create flag to suppress auto-look in move_to
		if not self.actor.move_to(target_location, quiet=True, skip=True):
			self.fail(**kwargs)

		if self.actor.speed < 5:
			# we're running!
			max_nrg = self.exit_obj.db.energy_cost or 3
			nrg_mod = self.actor.skills.running.value // 10
			self.actor.skills.use(running=0)
			self.actor.life.energy -= max(max_nrg-nrg_mod, 0)

		leave_msg = self.exit_obj.db.leave_traverse or "{verbs} {exit}."
		verb = self.exit_obj.db.verb or self.actor.movement
		leave_msg = leave_msg.format(verbs=f"$conj({verb})" or "leave", exit=self.exit_obj.key)
		leave_msg = f"You {leave_msg}"
		self.actor.msg(leave_msg)

		# update moving object's momentum
		self.actor.ndb.speed_start = self.actor.ndb.speed_end
		self.actor.ndb.speed_end = time()
		self.actor.ndb.last_move_dir = self.exit_obj.db.direction

		# announcement messages
		if not kwargs.get("quiet"):
			announce_leave = [obj for obj in source_location.contents if obj != self.actor]
			announce_arrive = [obj for obj in target_location.contents if obj != self.actor]
			# TODO: set a linked exit attribute and check that first
			dest_exit = self.exit_obj.get_return_exit()
			# dest_exit = dest_exit[0] if len(dest_exit) else None
			if leave_msg := self.exit_obj.db.leave_traverse:
				disappear_msg = leave_msg
			else:
				leave_msg = "{verbs} {exit}."
				disappear_msg = "{verbs} {exit} out of view"

			if dest_exit:
				if arrive_msg := dest_exit.db.arrive_traverse:
					appear_msg = arrive_msg
				else:
					arrive_msg = "{verbs} from {exit}."
					appear_msg = "{verbs} into view from {exit}"
				in_name = dest_exit.key
			else:
				arrive_msg = "{verbs} in."
				appear_msg = "{verbs} into view"
				in_name = ""

			leave_msg = leave_msg.format(verbs=f"$conj({verb})" or "leaves", exit=self.exit_obj.key)
			disappear_msg = disappear_msg.format(verbs=f"$conj({verb})" or "leaves", exit=self.exit_obj.key)
			arrive_msg = arrive_msg.format(verbs=f"$conj({verb})" or "arrives", exit=in_name)
			appear_msg = appear_msg.format(verbs=f"$conj({verb})" or "arrives", exit=in_name)

			# this is a hacky fix for the "gruff voice walks east" problem
			self.actor.nattributes.add("prev_location", self.exit_obj.location)
			self.actor.emote(leave_msg, receivers=announce_leave, action_type="move")
			self.actor.emote(arrive_msg, receivers=announce_arrive, action_type="move")

			# i'm not sure this will work...
			old_area = set()
			for _, rooms in pathing.visible_area(source_location, self.actor, source_location.db.visibility or 1).items():
				old_area.update([r for r, _ in rooms])
			new_area = set()
			for _, rooms in pathing.visible_area(target_location, self.actor, target_location.db.visibility or 1).items():
				new_area.update([r for r, _ in rooms])
			ignore = set([source_location, target_location])
			disappear = (old_area - new_area) - ignore
			appear = (new_area - old_area) - ignore
			receivers = []
			for room in disappear:
				receivers.extend(room.contents)
			if receivers:
				self.actor.emote(disappear_msg, receivers=receivers, action_type="move")
			receivers = []
			for room in appear:
				receivers.extend(room.contents)
			if receivers:
				self.actor.emote(appear_msg, receivers=receivers, action_type="move")

			# and end uncertainty

			self.actor.nattributes.remove("prev_location")

		super().do(**kwargs)
	
	def fail(self, **kwargs):
		err_msg = self.exit_obj.db.err_traverse or "You cannot go that way."
		self.actor.msg(err_msg)
		super().fail(**kwargs)

	def succeed(self, **kwargs):
		self.actor.at_post_move(self.exit_obj.location, **kwargs)

		for obj in self.exit_obj.location.contents:
			if hasattr(obj, "follow_check"):
				obj.follow_check(self.actor, self)
		
		super().succeed(**kwargs)

class ExitCommand(Command):
	def at_pre_cmd(self):
		try:
			action = ExitAction(actor=self.caller, exit_obj=self.obj)
		except InterruptAction:
			return True
		self.action = action

	def func(self):
		if self.obj.access(self.caller, "traverse"):
			# we may traverse the exit.
			self.caller.actions.add(self.action)
		else:
			# exit is locked
			self.msg(self.obj.db.err_traverse or "You cannot go that way.")

class Exit(BaseObject):
	"""
	Exits are connectors between rooms. Exits are normal Objects except
	they defines the `destination` property. It also does work in the
	following methods:

	 basetype_setup() - sets default exit locks (to change, use `at_object_creation` instead).
	 at_cmdset_get(**kwargs) - this is called when the cmdset is accessed and should
							  rebuild the Exit cmdset along with a command matching the name
							  of the Exit object. Conventionally, a kwarg `force_init`
							  should force a rebuild of the cmdset, this is triggered
							  by the `@alias` command when aliases are changed.
	 at_failed_traverse() - gives a default error message ("You cannot
							go there") if exit traversal fails and an
							attribute `err_traverse` is not defined.

	Relevant hooks to overload (compared to other types of Objects):
		at_traverse(traveller, target_loc) - called to do the actual traversal and calling of the other hooks.
											If overloading this, consider using super() to use the default
											movement implementation (and hook-calling).
		at_post_traverse(traveller, source_loc) - called by at_traverse just after traversing.
		at_failed_traverse(traveller) - called by at_traverse if traversal failed for some reason. Will
										not be called if the attribute `err_traverse` is
										defined, in which case that will simply be echoed.
	"""

	exit_command = ExitCommand
	
	@property
	def weights(self):
		# do this properly later
		return {}

	@property
	def visibility(self):
		if vis := self.ndb.visibility:
			return vis
		return self.db.visibility
	
	@property
	def direction(self):
		if not self.ndb._direction:
			self.ndb._direction = self.db.direction
		return self.ndb._direction
	
	@direction.setter
	def direction(self, value):
		self.db.direction = self.ndb._direction = value

	def at_object_creation(self):
		super().at_object_creation()
		self.stats.add("speed", "Momentum DC", trait_type="static", base=0)
		self.stats.add("skill", "Skill DC", trait_type="static", base=0)

	def at_rename(self, old_name, new_name, **kwargs):
		super().at_rename(old_name, new_name, **kwargs)
		if direct := self.db.direction:
			if direct.lower() != new_name.lower():
				self.aliases.add(direct)
		self.cmdset.remove_default()

	def get_display_desc(self, looker, **kwargs):
		desc = super().get_display_desc(looker, **kwargs)
		descs = [desc] if desc and desc.strip() != "You see nothing special." else []
		if verb := self.db.verb:
			obst = f"\nYou can $h({verb}) this"
			speed = self.stats.speed.value
			if speed:
				if speed <= _FAST_SPEED:
					obst += " if you're |rmoving fast|n"
				elif speed <= _MED_SPEED:
					obst += " if you have |ysome momentum|n"
			obst += "."
			descs.append(obst)

		if "visibility" not in kwargs:
			kwargs['visibility'] = self.visibility

		# only look through if you can see and you aren't glancing
		if kwargs['visibility']:
			kwargs['look_in'] = not kwargs.get('glance')
		
		if kwargs.get('look_in'):
			look_through = self.destination.return_appearance(looker, **kwargs)
			if type(look_through) is tuple:
				look_through = look_through[0]
			if prefix := self.db.look_through:
				look_through = f"{prefix}{look_through}"
			else:
				look_through = f"On the other side, you see:\n  {look_through}"

			descs.append(look_through)

		return "\n\n".join(descs) if descs else "You see nothing special."

	def get_display_name(self, looker, link=True, **kwargs):
		name = super().get_display_name(looker, **kwargs)
		tags = []
		if direct := self.db.direction:
			if direct.lower() != self.key.lower():
				tags.append(direct)
		if verb := self.db.verb:
			if link:
				tags.append(f'|lc{verb}|lt{verb}|le')
			else:
				tags.append(verb)
		if link:
			name = f'|lc{self.key}|lt{name}|le'
		if tags:
			return f"{name} ({', '.join(tags)})"
		else:
			return name

	def at_pre_traverse(self, mover, target_location, **kwargs):
		return
		success = True
		if skill_req := self.db.skill_req:
			success = mover.skill_check(skill_req, self.stats.skill)
			if not (verb := self.db.verb):
				verb = skill_req
			if not success:
				mover.emote(f"tries in vain to {verb} the {self.sdesc.get()}")
		return success

	def at_traverse(self, mover, target_location, **kwargs):
		return
		source_location = mover.location
		# TODO: figure out or create flag to suppress auto-look in move_to
		if mover.move_to(target_location, quiet=True):
			leave_msg = self.db.leave_traverse or "{verbs} {exit}."
			verb = self.db.verb or mover.movement
			leave_msg = leave_msg.format(verbs=f"$conj({verb})" or "leave", exit=self.key)
			leave_msg = f"You {leave_msg}"
			mover.msg(leave_msg)
			self.at_post_traverse(mover, source_location)
		else:
			self.at_failed_traverse(mover)

	def at_post_traverse(self, mover, leaving, **kwargs):
		pass

	def at_failed_traverse(self, mover, **kwargs):
		return
		err_msg = self.db.err_traverse or "You cannot go that way."
		mover.msg(err_msg)


	def create_exit_cmdset(self, exidbobj):
		"""
		Helper function for creating an exit command set + command.

		The command of this cmdset has the same name as the Exit
		object and allows the exit to react when the account enter the
		exit's name, triggering the movement between rooms.

		Args:
			exidbobj (Object): The DefaultExit object to base the command on.

		"""
		aliases = exidbobj.aliases.all()
		if verb := exidbobj.db.verb:
#			aliases.extend( [f"{verb} {alias}" for alias in aliases] )
#			aliases.append( f"{verb} {exidbobj.db_key.strip().lower()}")
			aliases.append(verb)
		# create an exit command. We give the properties here,
		# to always trigger metaclass preparations
		cmd = self.exit_command(
			key=exidbobj.db_key.strip().lower(),
			aliases=aliases,
			locks=str(exidbobj.locks),
			auto_help=False,
			destination=exidbobj.db_destination,
			arg_regex=r"^$",
			is_exit=True,
			obj=exidbobj,
		)
		# create a cmdset
		exit_cmdset = cmdset.CmdSet(None)
		exit_cmdset.key = "ExitCmdSet"
		exit_cmdset.priority = self.priority
		exit_cmdset.duplicates = True
		# add command to cmdset
		exit_cmdset.add(cmd)
		return exit_cmdset

	#####
	# these are reimplemented core changes because i'm not using a mixin any more
	#####

	_content_types = ("exit",)
	lockstring = (
		"control:id({account_id}) or perm(Admin); "
		"delete:id({account_id}) or perm(Admin); "
		"edit:id({account_id}) or perm(Admin)"
	)
	priority = 101

	def basetype_setup(self):
		"""
		Setup exit-security

		You should normally not need to overload this - if you do make
		sure you include all the functionality in this method.

		"""
		super().basetype_setup()

		# setting default locks (overload these in at_object_creation()
		self.locks.add(
			";".join(
				[
					"puppet:false()",  # would be weird to puppet an exit ...
					"traverse:all()",  # who can pass through exit by default
					"get:false()",  # noone can pick up the exit
					"teleport:false()",
					"teleport_here:false()",
				]
			)
		)

		# an exit should have a destination - try to make sure it does
		if self.location and not self.destination:
			self.destination = self.location

	def at_cmdset_get(self, **kwargs):
		"""
		Called just before cmdsets on this object are requested by the
		command handler. If changes need to be done on the fly to the
		cmdset before passing them on to the cmdhandler, this is the
		place to do it. This is called also if the object currently
		has no cmdsets.

		Keyword Args:
		  force_init (bool): If `True`, force a re-build of the cmdset
			(for example to update aliases).

		"""

		if "force_init" in kwargs or not self.cmdset.has_cmdset("ExitCmdSet", must_be_default=True):
			# we are resetting, or no exit-cmdset was set. Create one dynamically.
			self.cmdset.add_default(self.create_exit_cmdset(self), persistent=False)


	def at_init(self):
		"""
		This is called when this objects is re-loaded from cache. When
		that happens, we make sure to remove any old ExitCmdSet cmdset
		(this most commonly occurs when renaming an existing exit)
		"""
		self.cmdset.remove_default()

	def get_return_exit(self, return_all=False):
		"""
		Get the exits that pair with this one in its destination room
		(i.e. returns to its location)

		Args:
			return_all (bool): Whether to return available results as a
							   list or single matching exit.

		Returns:
			queryset or exit (Exit): The matching exit(s).
		"""
		query = ObjectDB.objects.filter(db_location=self.destination, db_destination=self.location)
		if return_all:
			return query
		return query.first()
