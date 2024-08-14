"""
Behavior classes for NPCs
"""
from evennia.utils import delay
from core.ic.behaviors import Behavior, behavior

@behavior
class SocialBehavior(Behavior):
	"""
	Defines basic reactions to being the target of socials.
	"""
	def at_social(obj, doer, social, **kwargs):
		"""
		The primary hook behavior called by the socials command
		"""
		if not hasattr(obj, 'ai'):
			# we have no intelligence, do nothing
			return
		
		# TODO: influence this with personality once it's a thing
		delay(1, obj.execute_cmd, f"{social} {doer.get_display_name(obj)}")
		return True