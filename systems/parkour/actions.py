from time import time
from evennia.utils import iter_to_str, delay

import switchboard

from base_systems.actions.base import Action, InterruptAction
from utils.registry import FallbackRegistry
from utils.strmanip import numbered_name, strip_extra_spaces

_REQUIRED_ATTRS = ('source', 'verb', 'skill', 'dc')

class ParkourMove(Action):
	key = "base"

	@property
	def move(self):
		return self.verb
	
	def __init__(self, **kwargs):
		if not all(attr in kwargs.keys() for attr in _REQUIRED_ATTRS):
			raise InterruptAction
		if req_parts := kwargs.get('req_parts'):
			self.min_req_parts = tuple(req_parts.items())
		self.exp = kwargs.pop('exp', 1)
		self.energy = kwargs.pop('energy', 2)
		self.speed = kwargs.pop('speed', 0)
		super().__init__(**kwargs)
	
	def start(self, **kwargs):
		if not self.actor:
			return self.end()

		tagged = self.actor.tags.has(switchboard.IMMOBILE, category="status", return_list=True)
		tagged = [ pose for (pose, hasit) in zip(switchboard.IMMOBILE, tagged) if hasit ]
		if len(tagged):
			self.actor.msg(f"You're currently {iter_to_str(tagged)}.")
			return self.end(self.actor, **kwargs)

		if self.speed:
			if self.speed < self.actor.speed:
				self.actor.msg("You don't have enough momentum to clear that.")
				if kwargs.get('force'):
					return self.fail(self.actor, **kwargs)
				else:
					return self.end(self.actor, **kwargs)
		
		if self.obstacle.db.grab:
			if not self.actor.hold(self.obstacle):
				self.msg(f"You can't grab that to {self.verb} it.")
				return self.end(self.actor, **kwargs)

		return super().start(**kwargs)


	def fail(self, **kwargs):
		msg = self.obstacle.db.failure_msg or "tries in vain to {verb} the {target}"
		msg = msg.format(verb=self.verb, target=self.obstacle.sdesc.get())
		self.actor.emote(msg, action_type="move")
		if self.obstacle.location.posing.get_posed_on(self.actor) == self.obstacle:
			self.obstacle.location.posing.remove(self.actor)

		return super().fail()

	def do(self, **kwargs):
		direction = self.obstacle.db.direction
		# update moving object's momentum
		self.actor.ndb.speed_start = self.actor.ndb.speed_end
		self.actor.ndb.speed_end = time()
		self.actor.ndb.last_move_dir = direction

		# TODO: add a proper pose string when that's implemented
		self.obstacle.location.posing.set(self.actor, self.obstacle, '', pose_type='parkour')
		# TODO: add energy cost to move data
		self.actor.life.energy -= self.energy

		if fall_height := self.get_fall_height():
			self.actor.db.fall = fall_height
		else:
			del self.actor.db.fall

		if self.source.db.grab:
			# let go after moving off
			self.actor.unhold(target=self.source)
		# announcement messages
		if not kwargs.get("quiet"):
			leave_msg = self.obstacle.db.landing_msg or "{verbs} {direct} onto {exit}."
			# TODO: conjugate this properly
			leave_msg = leave_msg.format(
				verbs=self.verb + 's', direct=direction or '',
				exit=f"@{self.obstacle.sdesc.get(strip=True)}"
			)
			self.actor.emote(strip_extra_spaces(leave_msg), action_type="move")

		return super().do(exp=self.exp, **kwargs)

	def status(self):
		"""Get the status string for this action."""
		return f"You are {self.verb}ing onto {self.obstacle.get_display_name(self.actor, noid=True, article=True, link=False)}."

	def get_fall_height(self):
		return self.obstacle.db.fall


PARKOUR_MOVES = FallbackRegistry('key', default=ParkourMove)
PARKOUR_MOVES.register(ParkourMove)

@PARKOUR_MOVES.register
class TransitionalParkourMove(ParkourMove):
	"""
	A special move for things that go between other obstacles, like ladders
	"""
	key = 'transition'

	def get_fall_height(self):
		return None

@PARKOUR_MOVES.register
class TimedTransitionMove(ParkourMove):
	"""
	An EXTRA special move for things you can't actually be on.
	"""
	key = 'timed'

	def get_fall_height(self):
		return self.actor.attributes.get('fall', 0) + 1

	def do(self, **kwargs):
		kwargs['delay'] = True
		self._task = delay(self.speed, self.end, fail=True)
		self._end_at = time() + self.speed - 0.1
		super().do(**kwargs)

	def end(self, *args, **kwargs):
		if self._end_at > time():
			if self._task:
				self._task.cancel()
		else:
			# if self.obstacle.location.posing.get_posed_on(self.actor) == self.obstacle:
			self.obstacle.location.posing.remove(self.actor)
		
		super().end(**kwargs)
