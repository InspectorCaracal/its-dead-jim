from base_systems.things.base import Thing
from core.ic.behaviors import NoSuchBehavior

from .software.apps import AppHandler

class Electronics(Thing):
	def at_object_creation(self):
		super().at_object_creation()
		self.tags.add("lightning", category="effectable")

	def at_server_start(self):
		super().at_server_start()
		if self.tags.has('cpu', category="part"):
			self.apps = AppHandler(self)

	def get_display_desc(self, looker, **kwargs):
		desc = super().get_display_desc(looker, **kwargs)
		try:
			if screen := self.do_screen_render(looker, **kwargs):
				desc += f"\n\nIt's displaying:\n{screen}"
		except NoSuchBehavior:
			pass

		return desc
		
	def at_use(self, user, *args, **kwargs):
		super().at_use(user, *args, **kwargs)
		if not args:
			if self.tags.has("powered on", category="status"):
				args = ['off']
			else:
				args = ['on']
		action = args[0]
		if action == 'on':
			if self.tags.has("powered on", category="status"):
				user.msg(f"{self.get_display_name(user, article=True)} is already on.")
			else:
				self.tags.add("powered on", category="status")
				if emote := self.db.startup_emote:
					self.emote(emote)
				else:
					user.msg(f"{self.get_display_name(user, article=True)} turns on.")
		elif action == 'off':
			if not self.tags.has("powered on", category="status"):
				user.msg(f"{self.get_display_name(user, article=True)} is already off.")
			else:
				self.tags.remove("powered on", category="status")
				if emote := self.db.shutdown_emote:
					self.emote(emote)
				else:
					user.msg(f"{self.get_display_name(user, article=True)} shuts off.")

	# def at_use(self, user, *args, **kwargs):

