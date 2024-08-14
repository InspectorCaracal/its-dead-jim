from collections import defaultdict
import networkx
from evennia import search_object
from evennia.utils import logger

from base_systems.exits.base import Exit

WorldGraph = networkx.DiGraph()
compass_rose = [ 'n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw' ]
compass_words = { 'n': 'north', 'ne': 'northeast', 'e': 'east', 'se': 'southeast', 's': 'south', 'sw': 'southwest', 'w': 'west', 'nw': 'northwest',  }

def build_graph():
	WorldGraph.clear()
	exits = Exit.objects.all_family()
	for ex in exits:
		if ex.location and ex.destination:
			weightings = { f"view_{d}": None for d in compass_words.values()}
			weightings |= { d: None for d in compass_words.values()}
			weightings |= ex.weights
			if direction := ex.direction:
				weightings |= { f"view_{direction}": 1, direction: 1 }
				dir_key = [ key for key, val in compass_words.items() if val == direction ]
				if dir_key:
					dir_key = dir_key[0]
					i = compass_rose.index(dir_key)
					if i == 7:
						i = -1
					fan = (compass_words[compass_rose[i-1]], compass_words[compass_rose[i+1]])
					weightings |= { f"view_{fan[0]}": 2, f"view_{fan[1]}": 2 }
			WorldGraph.add_edge(ex.location.id, ex.destination.id, dbref=f"#{ex.id}", **weightings) #weighting categories will be added as keywords

def visible_area(room, looker, vis, directions=None):
	"""
	Finds all rooms visible from a location.

	Args:
		room (Room): the location that's being looked from
		vis (int): the visibility range
	
	Returns:
		dict: a dictionary of lists of rooms sorted by directional key and distance
	"""
	data = defaultdict(list)
	if not directions:
		directions = [
				ex.direction
				for ex in room.contents_get(content_type='exit')
				if ex.get_lock(looker, "view") and ex.direction
			]
	if area_dict := room.ndb.area:
		# we cache a list of rooms in the fov and just validate that they're still visible
		for d in directions:
			for r in area_dict.get(d,[]):
				try:
					path = networkx.dijkstra_path(WorldGraph, room.id, r.id, weight=f"view_{d}")
					data[d].append( (r, len(path)-1) )
				except networkx.NetworkXNoPath:
					continue
	else:
		fov = networkx.DiGraph()
		room.ndb.area = defaultdict(list)
		for d in directions:
			cone = networkx.ego_graph(WorldGraph, room.id, radius=vis, center=False, distance=f"view_{d}")
			fov = networkx.compose(fov,cone)
		for n in fov.nodes:
			if not (n_room := looker.search(f"#{n}", use_dbref=True, exact=True)):
				logger.log_warn("Node {n} in graph has no matching dbobj id")
				continue
			if ret := _compass_avg(room, n_room):
				data[ret[0]].append((n_room, ret[1]))
				room.ndb.area[ret[0]].append(n_room)
	for key, val in data.items():
		if key in directions:
			data[key] = sorted(val, key=lambda x:x[1])

	return data

def _compass_avg(room, target):
	"""
	Averages the shortest path from room to target to the nearest compass rose direction.

	Args:
		room (Room): the starting location
		target (Room): the ending location
	
	Returns:
		tuple or None: a (str, int) describing the average compass rose direction, or None if path includes non-compass directions
	"""
	path = networkx.dijkstra_path(WorldGraph, room.id, target.id)
	dirs = []
	for i, r in enumerate(path):
		if i == 0:
			continue
		u = path[i-1]
		v = r
		exid = WorldGraph[u][v]['dbref']
		if not (ex := search_object(exid, exact=True, use_dbref=True)):
			logger.log_warn("Edge {u},{v} had invalid dbref {exid}")
			return None
		ex = ex[0]
		dir_key = dir_to_abbrev(ex.direction)
		if dir_key not in compass_rose:
			return None
		ind = compass_rose.index(dir_key)
		# this is hacky but whatever
		if ind == 7:
			ind = -1
		dirs.append(ind)
	if not dirs:
		return None
	avg = round(sum(dirs)/len(dirs))
	return compass_words[compass_rose[avg]], len(dirs)


def path_to_target(start, end, weight='static'):
	try:
		path = networkx.dijkstra_path(WorldGraph, start, end, weight=weight)
	except networkx.NetworkXNoPath:
		return None
	return path

def step_to_target(obj, target, weight='static'):
	if type(target) is int:
		target_id = target
		target_obj = obj.search(f"#{target}", exact=True, global_search=True)
	else:
		target_id = target.id
		target_obj = target

	if obj.location == target_obj:
		return True
	if not (path := obj.ndb.route):
		path = path_to_target(obj.location.id, target_id, weight=weight)
	if not path:
		# TODO: better error message
		return False
	next_room = path[0]
	obj.ndb.route = path[1:]
	ex = get_exit_for_path(obj.location.id, next_room)
	if not ex:
		return False
	if ex.at_traverse(obj, ex.destination):
		ex.at_post_traverse(obj, ex.location)
		return True
	else:
		ex.at_failed_traverse(obj)
		return True

def get_room_and_dir(obj):
	if location := obj.location:
		if location.location:
			return get_room_and_dir(location)
	return (location, obj.ndb.last_move_dir)

def get_exit_for_path(node_a, node_b):
	"""
	Returns the exit object associated with an edge between two nodes

	Args:
		node_a (Room): node to start
		node_b (Room): connected node destination

	Returns:
		Exit or None: the Exit leading from node_a to node_b or None if no object is found
	"""
	edge_data = WorldGraph.get_edge_data(node_a, node_b, default={})
	return edge_data.get('obj')

def get_path_in_direction(start, moving, steps):
	if type(start) is not int:
		start = start.id
	# TODO: catch/prevent missing directions (i don't remember what i meant here)
	compass_index = compass_rose.index(dir_to_abbrev(moving))
	G = networkx.ego_graph(WorldGraph, start, radius=steps, center=True, distance=moving)
	routes = networkx.shortest_path(G, source=start, weight=moving)
	if not routes:
		return None
	routes = sorted(routes.items(), key=lambda e: len(e[1]))
	destination, route = routes[-1]
	if len(route) < steps:
		new_steps = steps-len(route)
		veer_a = get_path_in_direction(destination, compass_words[compass_rose[compass_index-1]], new_steps)
		veer_b = get_path_in_direction(destination, compass_words[compass_rose[compass_index+1]], new_steps)
		if not (veer_a or veer_b) or (veer_a and veer_b):
			return (destination, route, True)
		destination, append = veer_a or veer_b
		route += append
	
	return (destination, route, False)

def dir_to_abbrev(direction):
	final = ''
	if "north" in direction:
		final = 'n'
	elif "south" in direction:
		final = 's'
	if 'east' in direction:
		final += 'e'
	elif "west" in direction:
		final += 'w'
	return final

_relative_minus = ( "straight", "slight left", "left", "sharp left", "back", "sharp right", "right", "slight right"  )
_relative_mappings = {
	"around": "back", "u-turn": "back", "hard left": "sharp left", "hard right": "sharp right", "forward": "straight"
}

def relative_to_cardinal(moving, turn):
	"""
	Identifies the new cardinal direction when turning a relative direction.

	Args:
		moving (str): The direction the entity is currently moving
		turn (str): The relative direction of the turn.

	Returns:
		str or None: The new cardinal direction, or None if inputs are invalid
	"""
	if not moving or not turn:
		return None

	if len(moving) > 2:
		# convert from words to abbreviations
		moving = dir_to_abbrev(moving)
	if turn in _relative_mappings:
		turn = _relative_mappings.get(turn)

	if not moving or turn not in _relative_minus:
		return None
	
	mi = compass_rose.index(moving)
	ti = _relative_minus.index(turn)
	return compass_rose[mi-ti]


def cardinal_to_relative(moving, turn):
	"""
	Identifies the relative direction to turn when changing cardinal direction.

	Args:
		moving (str): The direction the entity is currently moving
		turn (str): The direction the entity wants to be moving next

	Returns:
		str or None: The relative direction word(s), or None if inputs are invalid
	"""
	if not moving or not turn:
		return None

	if len(moving) > 2:
		# convert from words to abbreviations
		moving = dir_to_abbrev(moving)
	if len(turn) > 2:
		turn = dir_to_abbrev(turn)
	
	if not moving or not turn:
		# check again in case they were invalid
		return None
	
	mi = compass_rose.index(moving)
	ti = compass_rose.index(turn)

	if mi == ti:
		return "straight"

	diff = abs(mi-ti)
	if diff == 4:
		return "u-turn"

	mult = 1 if mi>ti else -1
	if diff > 4:
		diff = 8-diff
		mult *= -1
	diff *= mult
	if diff == -3:
		return "sharp right"
	if diff < 0:
		return "right"
	if diff == 3:
		return "sharp left"
	if diff > 0:
		return "left"
	return None
