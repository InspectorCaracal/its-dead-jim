from random import choice
from evennia import search_tag
from core.scripts import Script


class FlatsDirectory(Script):
	"""
	A storage script that records which rooms belong to who and what their
	door lock objects are.
	
	Intended to be added to the lobby room for the building.
	"""
	
	def at_object_creation(self):
		self.key = "roomdirectory"
		if not self.db.residents:
			self.db.residents = {}
	
	def get_room_number(self, chara, **kwargs):
		return self.db.residents.get(chara) if self.db.residents else None
	
	def claim_free_room(self, chara, **kwargs):
		zone = self.obj.tags.get(category='zone')
		free_doors = search_tag(zone, category='free_room')
		if not free_doors:
			return None

		room_entrance = choice(free_doors)
		room_entrance.tags.remove(zone, category="free_room")

		room_door = room_entrance.db.door
		for lock in room_door.parts.search('lock', part=True):
			lock.db.owner = chara
		
		if not self.db.residents:
			self.db.residents = {chara: room_entrance}
		else:
			self.db.residents[chara] = room_entrance
		
		return room_entrance


def create_new_flats(lobby, floors=2, rooms=9):
	"""
	Creates the entire rest of the apartment building starting from a single `lobby` room
	"""
	if not (zone := lobby.tags.get(category='zone')):
		print(f"{lobby} must be set as a zone before creating an apartment building")
		return
	if lobby.scripts.has('roomdirectory'):
		print(f"{lobby} is already part of an apartment building.")
		return

	from evennia import create_object, create_script
	from evennia.utils.utils import int2str

	lobby.scripts.add(FlatsDirectory)

	panel = create_object(key='panel', typeclass='systems.machines.elevators.ElevatorPanel', attributes=[('desc','A slightly battered black and silver panel.')], location=elevator, tags=[(zone, 'zone')])

	elevator_door_data = {
		'key': 'elevator door',
		'attributes': [('desc', 'A smooth silver sliding door.')],
		'tags': [(zone, 'zone'), 'closed']
	}
	elevator_lock_data = {
		'key': 'lock',
		'tags': [('hidden', 'systems'), ('lock', 'part'), 'locked', (zone, 'zone')]
	}
	elevator_button_data = {
		'key': 'call button',
		'typeclass': 'systems.machines.elevators.ElevatorCallButton',
		'attributes': [('desc','A circular button is set into the wall.')],
		'tags': [(zone, 'zone')]
	}
	stops = []
	elevator = create_object(key="An elevator", typeclass='base_systems.rooms.base.Room', attributes=[('desc', 'A very boring elevator.')], tags=[(zone, 'zone')])
	elevator_door = create_object(**elevator_door_data)
	inner_exit = create_object(key='elevator door', aliases=('leave','out'), typeclass='base_systems.exits.doors.DoorExit', location=elevator, destination=lobby, tags=[(zone, 'zone')], attributes=[('door', elevator_door)])
	panel.link = inner_exit
	lock = create_object(attributes=[('owner',panel)], **elevator_lock_data)
	lock.partof = elevator_door
	elevator_door.db.sides = (inner_exit,)

	def connect_elevator(room):
		door = create_object(**elevator_door_data)
		ex = create_object(key='elevator door', typeclass='base_systems.exits.doors.DoorExit', location=room, destination=elevator, tags=[(zone, 'zone')], attributes=[('door', door)])
		door.db.sides = (ex,)
		lock = create_object(attributes=[('owner',panel)], **elevator_lock_data)
		lock.partof = door
		create_object(location=room, **elevator_button_data).link = panel
		stops.append(room)
	
	connect_elevator(lobby)

	def create_flat(hall, num):
		flat = create_object(key="Studio apartment", typeclass='base_systems.rooms.base.Room', tags=[(zone, 'zone')])
		door = create_object(key='heavy wooden door', attributes=[('desc','A well-worn, heavily weighted wooden door, painted white.')], tags=[(zone, 'zone'), 'closed'])
		lock = create_object(key='lock', tags=[('hidden', 'systems'), ('lock', 'part'), 'locked', (zone, 'zone')])
		lock.partof = door
		inner = create_object(key="front door", aliases=('out','leave'), destination=hall, typeclass='base_systems.exits.doors.DoorExit', tags=[(zone, 'zone')], location=flat, attributes=[('door',door)])
		outer = create_object(key=f"room {num}", aliases=(str(num),), destination=flat, typeclass='base_systems.exits.doors.DoorExit', tags=[(zone, 'zone'), (zone, 'free_room')], location=hall, attributes=[('door',door)])
		door.db.sides = (inner, outer)

	for i in range(floors):
		ref = i+1
		key = int2str(ref, adjective=True) + " floor hallway"
		hallway = create_object(key=key, typeclass='base_systems.rooms.base.Room', tags=[(zone, 'zone')])
		connect_elevator(hallway)
		# we create the actual flats here
		baseroom = ref*100
		for n in range(baseroom, baseroom+rooms):
			create_flat(hallway, n+1)

	# this goes at the end so that all the floors can be added in one write
	panel.db.stops = stops

	npc = create_object(key="Edith", typeclass='base_systems.characters.npcs.BaseNPC', location=lobby)
	npc.behaviors.add('FlatsReceptionBehavior')
	print(f"Created apartment building from {lobby}")