from evennia import create_object, search_object
from base_systems.things.base import Thing
from base_systems.rooms.base import Room
from base_systems.exits.base import Exit

limbo = search_object('Limbo')[0]

if streets := search_object('street'):
	street = streets[0]
else:
	# make some rooms and stuff
	street = create_object(Room, "street")
	ex = create_object(Exit, "out", location=limbo)
	ex.destination = street

	# create some exits
	north = create_object(Room, "street")
	ex = create_object(Exit, "north", location=street)
	ex.destination = north
	ex = create_object(Exit, "south", location=north)
	ex.destination = street

# create something destructible
van = create_object(Thing, "van", location=street)
van.size = 32
for _ in range(4):
	tire = create_object(Thing,"tire")
	tire.size = 4
	van.parts.attach(tire)
for _ in range(2):
	door = create_object(Thing,"side door")
	door.size = 8
	van.parts.attach(door)

caller.msg("Done.")