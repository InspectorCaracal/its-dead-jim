"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""
from evennia import ObjectDB
from evennia.utils import logger
from base_systems.maps.pathing import build_graph

def at_server_init():
	"""
	This is called first as the server is starting up, regardless of how.
	"""
	# i hate this solution so much so much so much
	from base_systems.characters.ai import behaviors
	from base_systems.prototypes import behaviors
	from base_systems.things import behaviors
	from systems.crafting import behaviors
	from systems.electronics import behaviors
	from systems.housing import behaviors
	from systems.recordings import behaviors
	from systems.money import behaviors
	from systems.money.shopping import behaviors

def at_server_start():
	"""
	This is called every time the server starts up, regardless of
	how it was shut down.
	"""
#	logger.log_msg(ObjectDB.objects.all())
	for obj in ObjectDB.objects.all():
		if hasattr(obj, "at_server_start"):
			obj.at_server_start()
	build_graph()


def at_server_stop():
	"""
	This is called just before the server is shut down, regardless
	of it is for a reload, reset or shutdown.
	"""
	for obj in ObjectDB.objects.all():
		if hasattr(obj, "effects"):
			obj.effects.save()


def at_server_reload_start():
	"""
	This is called only when server starts back up after a reload.
	"""
	pass


def at_server_reload_stop():
	"""
	This is called only time the server stops before a reload.
	"""
	pass


def at_server_cold_start():
	"""
	This is called only when the server starts "cold", i.e. after a
	shutdown or a reset.
	"""
	pass


def at_server_cold_stop():
	"""
	This is called only when the server goes down due to a shutdown or
	reset.
	"""
	# Clear all queued actions
	from base_systems.characters.base import Character
	for obj in Character.objects.all_family():
		obj.actions.clear(shutdown=True)

