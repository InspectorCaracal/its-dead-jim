

from base_systems.actions.base import Action


class SitAction(Action):
	move = 'sit'

	def __init__(self, **kwargs):
		if target := kwargs.pop('targets', None):
			target = target[0]
		self.target = target
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		statuses = self.actor.tags.get(category='status', return_list=True)
		direction = "up" if "lying down" in statuses else "down"

		# if not self.target:
		# 	if target := self.actor.location.posing.get(self.actor):
		# 		self.target = target

		# if there's a target
		if self.target:
			if not self.actor.location.posing.add(self.actor, self.target, "sitting"):
				self.actor.msg(f"You can't {self.move} on that right now.")
				return self.end()
			self.actor.emote(f"sits {direction} {self.target.db.onword or 'on'} @{self.target.sdesc.get(strip=True)}.", action_type="move")

		# various state changes
		else:
			position = self.actor.location.posing.get(self.actor)
			posed_on = position[0] if position else None
			if posed_on:
				self.actor.location.posing.set(self.actor, posed_on, 'sitting')
				self.actor.emote(f"sits {direction} {posed_on.db.onword or 'on'} @{posed_on.sdesc.get(strip=True)}.", action_type="move")
			else:
				self.actor.emote(f"sits {direction}.", action_type="move")

		if direction == "up":
			self.actor.tags.remove("lying down", category="status")
		self.actor.tags.add("sitting", category="status")
		super().do(*args, **kwargs)


class LieDownAction(Action):
	move = 'lie down'

	def __init__(self, **kwargs):
		if target := kwargs.pop('targets', None):
			target = target[0]
		self.target = target
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		statuses = self.actor.tags.get(category='status', return_list=True)
		# if there's a target
		if self.target:
			if not self.actor.location.posing.add(self.actor, self.target, "lying down"):
				self.actor.msg(f"You can't {self.move} on that right now.")
				return
			self.actor.emote(f"lies down {self.target.db.onword or 'on'} @{self.target.sdesc.get(strip=True)}.", action_type="move")

		# various state changes
		else:
			position = self.actor.location.posing.get(self.actor)
			posed_on = position[0] if position else None
			if posed_on:
				self.actor.location.posing.set(self.actor, posed_on, 'lying down')
				self.actor.emote(f"lies down {posed_on.db.onword} @{posed_on.sdesc.get(strip=True)}.", action_type="move")
			else:
				self.actor.emote("lies down.", action_type="move")

		if "sitting" in statuses:
			self.actor.tags.remove("sitting", category="status")
		self.actor.tags.add("lying down", category="status")

		super().do(*args, **kwargs)


class StandUpAction(Action):
	move = 'stand'
	min_req_parts = ( ('foot', 1), )
	max_used_parts = ( ('foot', 2), )

	def __init__(self, **kwargs):
		if target := kwargs.pop('targets', None):
			target = target[0]
		self.target = target
		super().__init__(**kwargs)

	def start(self, *args, **kwargs):
		if self.target:
			if not self.actor.location.posing.add(self.actor, self.target, "standing"):
				self.actor.msg(f"You can't {self.move} on that right now.")
				return self.end()

		return super().start(*args, **kwargs)

	def do(self, *args, **kwargs):
		statuses = self.actor.tags.get(category='status', return_list=True)
		nonstanding = [ "sitting", "lying down" ]
		standing = True

		for pose in nonstanding:
			if pose in statuses:
				self.actor.tags.remove(pose, category="status")
				standing = False

		# if there's a target
		if self.target:
			self.actor.emote(f"stands {self.target.db.onword or 'on'} @{self.target.sdesc.get(strip=True)}.", action_type="move")

		# various state changes
		else:
			position = self.actor.location.posing.get(self.actor)
			posed_on = position[0] if position else None
			if posed_on and standing:
				self.actor.emote(f"leaves @{posed_on.sdesc.get(strip=True)}.", action_type="move")
				self.actor.location.posing.remove(self.actor)
			elif posed_on:
				self.actor.emote(f"stands up {posed_on.db.onword or 'on'} @{posed_on.sdesc.get(strip=True)}.", action_type="move")
				self.actor.location.posing.set(self.actor, posed_on, 'standing')
			elif standing:
				self.actor.msg("You're already standing!")
				return self.end()
			else:
				self.actor.emote("stands up.", action_type="move")

		super().do(*args, **kwargs)


class JumpOffAction(Action):
	move = 'jump off'

	min_req_parts = ( ('foot', 1), )
	max_used_parts = ( ('foot', 2), )

	def __init__(self, actor, *args, **kwargs):
		self.actor = actor
		super().__init__(**kwargs)

	def start(self, *args, **kwargs):
		statuses = self.actor.tags.get(category='status', return_list=True)
		nonstanding = [ "sitting", "lying down" ]
		standing = True

		if [status for status in statuses if status in nonstanding]:
			self.msg("You have to stand first.")
			return self.end()

		if not self.actor.location.posing.get(self.actor):
			self.msg("You aren't on anything to jump off of.")
			return self.end()

		return super().start(*args, **kwargs)

	def do(self, *args, **kwargs):
		if not (position := self.actor.location.posing.get(self.actor)):
			return self.end()
		posed_on = position[0]
		if posed_on in self.actor.holding().values():
			self.actor.unhold(target=posed_on)
		self.actor.emote(f"jumps off of @{posed_on.sdesc.get(strip=True)}.", action_type="move")
		self.actor.location.posing.remove(self.actor)

		super().do(*args, **kwargs)

