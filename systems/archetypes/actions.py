from evennia.utils import delay

from base_systems.actions.base import Action, InterruptAction
import time

class BiteAction(Action):
	move = "bite"
	dbobjs = ['actor', 'target']

	def __init__(self, actor, target, **kwargs):
		if b := actor.holding(part="mouth"):
			if target not in b.values():
				raise InterruptAction
		self.actor = actor
		self.target = target
		super().__init__(**kwargs)

	# def __serialize_dbobjs__(self):
	# 	del self._tick
	# 	super().__serialize_dbobjs__()

	# def resume(self):
	# 	if hasattr(self, "_next_tick"):
	# 		d = int(self._next_tick - time.time())
	# 		self._tick = delay(max(d,0), self.do)
	# 	else:
	# 		super().resume()


	def start(self, *args, **kwargs):
		# add in the grab here
		if not self.actor.hold(self.target, part="mouth"):
			super().end()
		self.actor.emote(f"bites @{self.target.sdesc.get(strip=True)}")
		super().start(*args, **kwargs)

	def do(self, *args, **kwargs):
		if self.target.tags.has("unconscious", category='status') or self.target.life.energy < 10:
			self.end()
		elif self.actor.life.hunger <= 0:
			self.end()
		else:
			self.target.life.energy -= 10
			self.actor.life.energy += 10
			self.actor.prompt()
			self._next_step = time.time()+10
			self._tick = delay(10, self.do)

	def end(self, *args, **kwargs):
		self.actor.emote(f"releases @{self.target.sdesc.get(strip=True)}")
		self.actor.unhold(target=self.target)
		self.actor.prompt()

		try:
			self._tick.cancel()
		except AttributeError:
			pass
		super().end()

	def status(self):
		if (actor := self.actor) and (target := self.target):
			actor.msg(f"You are feeding on {target.get_display_name(actor)}.")
