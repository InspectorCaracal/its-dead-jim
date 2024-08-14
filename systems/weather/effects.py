from base_systems.effects.base import AreaEffect


class FogEffect(AreaEffect):
	name = 'fog'
	pulse = "base_systems.effects.effects.Wet"
	duration = 60
	block = ("water", "protect_against")

	# TODO: change local visibility with stacks

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.emote("The area slowly fills with fog.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")
		self.handler.obj.descs.add("precip", "It's foggy here.", temp=True)
	
	def at_add(self, *args, **kwargs):
		if self.stacks:
			# prevent this message from happening on initial start
			self.handler.obj.emote("The fog thickens.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")
		super().at_add(*args, **kwargs)

	def at_remove(self, *args, **kwargs):
		super().at_remove(*args, **kwargs)
		if self.stacks:
			# prevent this message from happening on removal
			self.handler.obj.emote("The fog seems thinner.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.emote("The fog lifts.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")
		self.handler.obj.descs.remove("precip", temp=True)

	def at_tick(self, *args, **kwargs):
		if self.stacks > 3:
			super().at_tick(*args, **kwargs)


class RainEffect(AreaEffect):
	name = 'rain'
	pulse = "base_systems.effects.effects.Wet"
	block = ("water", "protect_against")
	duration = 60

	# TODO: add weather desc

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.handler.obj.emote("It begins to rain.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")
		# TODO: update the descs based on number of stacks
		self.handler.obj.descs.add("precip", "It's raining.", temp=True)

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.descs.remove("precip", temp=True)
		self.handler.obj.emote("The rain stops.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")

	# TODO: change duration based on stacks so you get more wet faster if it's raining harder

	def at_remove(self, *args, **kwargs):
		super().at_remove(*args, **kwargs)
		if self.stacks:
			# prevent this message from happening on deletion
			self.handler.obj.emote("The rain lightens.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")

	def at_add(self, *args, **kwargs):
		if self.stacks:
			# prevent this message from happening on creation
			self.handler.obj.emote("The rain gets heavier.", receivers=self.handler.obj.contents, anonymous_add=False, action_type="weather")
		super().at_add(*args, **kwargs)
