from copy import copy
from evennia.commands import cmdset
from evennia.utils import iter_to_str, lazy_property

import switchboard

from base_systems.things.base import Thing
from core.commands import Command
from systems.parkour.handler import ParkourHandler

class ObstacleCommand(Command):
	auto_help = False
	action_override = True

	def at_pre_cmd(self):
		if super().at_pre_cmd():
			return True
		
		action = self.obj.get_mover_action(self.caller, self.cmdstring)
		if not action:
			# TODO: better error messaging for position vs grab requirement
			self.msg(f"You can't {self.cmdstring} onto {self.obj.get_display_name(self.caller, article=True)} from where you are.")
			return True
		self.action = action

	def func(self):
		action = copy(self.action)
		action.actor = self.caller
		self.caller.actions.override(action)

	def at_post_cmd(self):
		self.caller.prompt()

class Obstacle(Thing):
	"""
	Obstacles are special Exits which create in-room chained movements rather than moving
	between rooms.
	"""
	exit_command = ObstacleCommand

	@lazy_property
	def moves(self):
		return ParkourHandler(self)

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
		self.locks.add('call:obstacle_check();view:obstacle_check() or is_posed_on();get:false()')

	def at_rename(self, old_name, new_name, **kwargs):
		super().at_rename(old_name, new_name, **kwargs)
		if direct := self.db.direction:
			if direct.lower() != new_name.lower():
				self.aliases.add(direct)
		self.cmdset.remove_default()

	def get_display_footer(self, looker, **kwargs):
		foot = super().get_display_footer(looker, **kwargs)
		footlist = [foot] if foot else []
		if self.locks.check_lockstring(looker, 'is_posed_on()'):
			return foot+'\n\nYou are on this.'
		source = self.location.posing.get_posed_on(looker) or looker.location
		verb = self.moves.get_verb(source)
		if not verb:
			return foot
		can = "can"
		obst = "You {can} $h({verb}) onto this"
		reqs = []
		speed = self.moves.get_speed(source)
		if speed and speed < looker.speed:
			can = "could"
			if speed <= switchboard.FAST_SPEED:
				reqs.append("were |rmoving fast|n")
			elif speed <= switchboard.MED_SPEED:
				reqs.append("had |ysome momentum|n")

		moves = self.moves.get(source)
		# TODO: find a tidy way to use the actual display name instead of the key
		failed_skills = [
			move.skill for move in moves if not looker.skills.check(**{move.skill: move.dc})
		]
		if failed_skills:
			can = "could"
			reqs.append(f"get better at {iter_to_str(failed_skills)}")
		if reqs:
			obst += f" if you {iter_to_str(reqs)}"
		obst += '.'
		# this is hacky as heck
		if can == 'can':
			verb = f'|lc{verb} {self.sdesc.get()}|lt{verb}|le'
		footlist.append(obst.format(can=can, verb=verb))

		return "\n\n".join(footlist) if footlist else ""

	def get_display_name(self, looker, link=True, **kwargs):
		name = super().get_display_name(looker, link=link, **kwargs)
		clean = self.sdesc.get(strip=True)
		if not kwargs.get('tags'):
			return name
		tags = []
		source = looker.location.posing.get_posed_on(looker) or looker.location
		if direct := self.db.direction:
			if direct.lower() != self.key.lower():
				tags.append(direct)
		if verb := self.moves.get_verb(source):
			if link:
				tags.append(f'|lc{verb} {clean}|lt{verb}|le')
			else:
				tags.append(verb)
		# TODO: include skill check
		if tags:
			return f"{name} ({', '.join(tags)})"
		else:
			return name

	def get_mover_action(self, mover, verb, **kwargs):
		"""
		Check if the mover is in a valid position.

		Returns the relevant action, or None if invalid.
		"""
		moves = self.moves.get()

		sources = [mover.location.posing.get_posed_on(mover) or mover.location]
		validated = [ m for m in moves if m.source in sources and m.verb == verb ]

		if validated:
			return validated[0]

		return None

	# TODO: (re)implement this with an `on_change_pose` reaction
	def at_poser_unpose(self, poser, **kwargs):
		"""
		Handle any necessary events when someone stops posing on this
		
		This does not trigger when the poser has re-posed to something else, only if they
		cease posing entirely.
		"""
		if falling := poser.db.fall:
			poser.effects.add('base_systems.effects.effects.FallingEffect', stacks=falling)
	
	def at_pre_posed_on(self, poser, **kwargs):
		"""Determine whether or not poser is allowed to pose on this"""
		if poser.location.posing.get_posed_on(poser) == self:
			return True
		if kwargs.get('pose_type') == 'parkour':
			return True #not sure this check is correct but i think it is
		return False


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
		for verb in exidbobj.moves.get_verbs():
			# aliases.extend( [f"{verb} {alias}" for alias in aliases] )
			# aliases.append( f"{verb} {exidbobj.db_key.strip().lower()}")
			aliases.append(verb)
		# create an exit command. We give the properties here,
		# to always trigger metaclass preparations
		cmd = self.exit_command(
			key=exidbobj.db_key.strip().lower(),
			aliases=aliases,
			locks=str(exidbobj.locks),
			auto_help=False,
			arg_regex=r"^$",
			obj=exidbobj,
		)
		# create a cmdset
		exit_cmdset = cmdset.CmdSet(exidbobj)
		exit_cmdset.key = "ObstacleCmdSet"
		exit_cmdset.priority = self.priority
		exit_cmdset.duplicates = True
		# add command to cmdset
		exit_cmdset.add(cmd)
		return exit_cmdset

	#####
	# these are reimplemented core changes because i'm not using a mixin any more
	#####

	_content_types = ("obstacle",)
	lockstring = (
		"control:id({account_id}) or perm(Admin); "
		"delete:id({account_id}) or perm(Admin); "
		"edit:id({account_id}) or perm(Admin)"
	)
	priority = 101

	def at_init(self):
		"""
		This is called when this objects is re-loaded from cache. When
		that happens, we make sure to remove any old ExitCmdSet cmdset
		(this most commonly occurs when renaming an existing exit)
		"""
		self.cmdset.remove_default()

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

		if "force_init" in kwargs or not self.cmdset.has_cmdset("ObstacleCmdSet", must_be_default=True):
			# we are resetting, or no exit-cmdset was set. Create one dynamically.
			self.cmdset.add_default(self.create_exit_cmdset(self), persistent=False)

	def get_return_exit(self, **kwargs):
		"""
		Obstacle exits do not actually traverse anything, so there is never a return exit.
		"""
		return None
