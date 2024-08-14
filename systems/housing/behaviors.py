from core.ic.behaviors import behavior
from base_systems.characters.ai.behaviors import SocialBehavior
from utils.menus import FormatEvMenu

@behavior
class FlatsReceptionBehavior(SocialBehavior):
	"""
	special responses to being greeted
	"""
	priority = 2

	def at_social(obj, doer, social, **kwargs):
		if social == "greet":
			# TODO: implement the queueing system
			directory = obj.location.scripts.get('roomdirectory')
			if directory:
				directory = directory[0]
				FormatEvMenu(doer, 'systems.housing.flats_menu', startnode="menunode_greet",
								cmd_on_exit=None, receptionist=obj, directory=directory)
				return True

		return SocialBehavior.at_social(obj, doer, social, **kwargs)