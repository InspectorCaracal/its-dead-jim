def menunode_greet(caller, raw_string, **kwargs):
	"""begin talking to the receptionist"""
	speaker = caller.ndb._evmenu.receptionist
	greeting = f'{speaker.get_display_name(caller, article=True, ref="t")} smiles at {caller.get_display_name(caller, article=True)}. "Hello! What can I help you with today?"'

	directory = caller.ndb._evmenu.directory
	if directory.get_room_number(caller):
		options = [
			{'desc': 'Ask for a duplicate key', 'goto': _get_new_key},
			{'desc': 'Check your room number', 'goto': "menunode_room_number"},
			]
	else:
		options = [{'desc': 'Rent a room', 'goto': _get_new_room}]

	options.append({"desc": "Never mind", 'goto': 'menunode_end'})
	options.append({"key": "_default", 'goto': _parse_input})

	return greeting, options


def _parse_input(caller, raw_string, **kwargs):
	text = raw_string.strip().lower()
	if any( keyword in text for keyword in ('duplicate', 'key') ):
		return _get_new_key(caller, raw_string, **kwargs)
	if any( keyword in text for keyword in ('number', 'forgot') ):
		return "menunode_room_number"
	if any( keyword in text for keyword in ('rent',) ):
		return _get_new_room(caller, raw_string, **kwargs)
	
	# we didn't understand it
	return "menunode_confused"


def menunode_confused(caller, raw_string, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	text = f'{speaker.get_display_name(caller, article=True, ref="t")} waits expectantly for you to say something relevant.'
	if caller.attributes.get('house', category='systems'):
		options = [
			{'desc': 'Ask for a duplicate key', 'goto': _get_new_key},
			{'desc': 'Check your room number', 'goto': "menunode_room_number"},
			]
	else:
		options = [{'desc': 'Rent a room', 'goto': _get_new_room}]
	options.append({"desc": "Never mind", 'goto': 'menunode_end'})
	options.append({"key": "_default", 'goto': _parse_input})

	return text, options


def _get_new_key(caller, raw_string, **kwargs):
	"""create a key object keyed to the character's room"""
	directory = caller.ndb._evmenu.directory
	if not (room := directory.get_room_number(caller)):
		return "menunode_no_house"

	directory = caller.ndb._evmenu.directory
	room = directory.get_room_number(caller)
	return ("menunode_room_number", {'room': room})


def _get_new_room(caller, raw_string, **kwargs):
	"""assign a room to the character"""
	directory = caller.ndb._evmenu.directory
	# first we check if the caller already has a room here
	if room := directory.get_room_number(caller):
		return ("menunode_room_number", {'room': room})

	if not (newroom := directory.claim_free_room(caller)):
		return "menunode_no_rooms"
	
	return ("menunode_new_room", {'room': newroom })

def menunode_new_room(caller, raw_string, room, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	text = f'{speaker.get_display_name(caller, article=True, ref="t")} nods to {caller.get_display_name(caller)}. "Your new room is {room.name}. As a special service to our earliest residents, your rent has been waived."'

	options = [{'desc': 'Ask for a duplicate key', 'goto': _get_new_key}]
	options.append({"desc": "Leave", 'goto': 'menunode_end'})
	options.append({"key": "_default", 'goto': _parse_input})

	return text, options

def menunode_room_number(caller, raw_string, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	if not (room := kwargs.get('room')):
		directory = caller.ndb._evmenu.directory
		room = directory.get_room_number(caller)

	text = f'{speaker.get_display_name(caller, article=True, ref="t")} consults the directory, then says to {caller.get_display_name(caller)}, "Your current room is {room.key}. Is there anything else I can help you with?"'

	options = [{'desc': 'Ask for a duplicate key', 'goto': _get_new_key}]
	options.append({"desc": "No thanks", 'goto': 'menunode_end'})
	options.append({"key": "_default", 'goto': _parse_input})

	return text, options

def menunode_no_rooms(caller, raw_string, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	text = f'{speaker.get_display_name(caller, article=True, ref="t")} frowns at the directory. "Unfortunately, we don\'t have any rooms available right now."'
	options = [{"desc": "Oh well", 'goto': 'menunode_end'},
					{"key": "_default", 'goto': _parse_input}]

	return text, options

def menunode_no_house(caller, raw_string, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	text = f'{speaker.get_display_name(caller, article=True, ref="t")} frowns at the directory. "I\'m sorry, but you don\'t seem to have a room here."'
	
	options = [{'desc': 'Rent a room', 'goto': _get_new_room}]
	options.append({"desc": "Never mind", 'goto': 'menunode_end'})
	options.append({"key": "_default", 'goto': _parse_input})

	return text, options

def menunode_end(caller, raw_string, **kwargs):
	speaker = caller.ndb._evmenu.receptionist
	text = f'{speaker.get_display_name(caller, article=True, ref="t")} smiles at {caller.get_display_name(caller)}. "Have a lovely day!"'

	return text