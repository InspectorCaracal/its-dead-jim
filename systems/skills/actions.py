from evennia.utils.utils import is_iter
from base_systems.actions.base import Action, InterruptAction


class SkilledAction(Action):
	"""A type of Action that requires a skill check to succeed"""
	dc = 0
	exp = 0
	
	def __init__(self, **kwargs):
		self.skill = kwargs.pop('skill', None)
		if not self.skill:
			raise InterruptAction
		super().__init__(**kwargs)


	def start(self, *args, **kwargs):
		if not hasattr(self.actor, 'skills'):
			# this actor has no skills and simply can't do this
			return self.end(*args, **kwargs)
		if self.actor.skills.use({self.skill: self.dc}):
			return super().start(*args, **kwargs)
		else:
			return self.fail(*args, **kwargs)


	def end(self, *args, **kwargs):
		if exp := kwargs.get('exp'):
			if hasattr(self.actor, 'exp'):
				self.actor.exp += exp
		super().end(*args, **kwargs)
