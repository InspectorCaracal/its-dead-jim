from evennia import CmdSet, create_object, InterruptCommand
from evennia.utils import logger, iter_to_str

from core.commands import Command
from data.skills import ALL_SKILLS
import switchboard
from utils.general import get_classpath
from utils.menus import FormatEvMenu, MenuTree
from utils.strmanip import numbered_name

from .actions import PARKOUR_MOVES

# These are the attributes which are required by all ParkourMoves
_REQUIRED_KEYS = ( 'verb', 'skill', 'dc' )
_ALL_KEYS =  ('verb', 'skill', 'dc', 'direction', 'speed', 'move', 'req_parts')

class CmdObstacle(Command):
	"""
	Creates a new obstacle in the current room

	Usage:
	  obstacle <name>[;aliases], <verb>[:direction] from <location>, skill=dc

	Examples:
	   obstacle fire escape;ladder, jump from balcony, acrobatics=10

	Allows the creation of obstacles. Obstacles are special objects which reposition the
	caller to themselves, and which can have restricted access based on the caller's
	current positioning.

	Using the keyword "here" as the location will use either the room, or the object you're
	posed on.

	"""

	key = "@obstacle"
	free = True
	help_category = "Building"
	locks = "cmd:perm(obstacle) or perm(Builder)"
	splitters = (';',)
	maxsplits = -1

	def create_obstacle(self, key, aliases, **kwargs):
		ob = create_object(
			typeclass='systems.parkour.obstacles.Obstacle',
			key = key,
			location = self.caller.location,
			aliases = aliases,
		)
		return ob
	
	def func(self):
		if not self.argslist:
			self.msg("Usage: obstacle <key>[;alias;alias]")
			return
		
		obj_key, *aliases = self.argslist

		result = yield from self.find_targets(obj_key, numbered=False, find_none=True)
		if result == False:
			return
		if not result or result == "create":
			obj = self.create_obstacle(obj_key, aliases)
		else:
			ans = yield(f"Found existing obstacle $h({result}) (#{result.id}). Do you want to modify it? YES/No")
			if 'n' in ans.lower():
				obj = self.create_obstacle(obj_key, aliases)
			else:
				obj = result

		if not obj:
			logger.log_err(f"Could not create obstacle! {vars(self)}")
			self.msg("There was a problem creating the obstacle.")
			return

		# launch the menu
		FormatEvMenu(self.caller, get_classpath(ObstacleMenu), obstacle=obj, startnode="menunode_choose_source")


	def multimatch_msg(self, target, lst, match_cmd=False):
		# avoid modifying the source list because that always confuses me
		lst = lst + [f"Create a new {target}"]
		return super().multimatch_msg(target, lst, match_cmd=match_cmd)

	def process_multimatch(self, option, lst, free_text=False):
		lst = lst + ["create"]
		return super().process_multimatch(option, lst, free_text)


class ObstacleBuilderCmdSet(CmdSet):
	key = "Obstacle BuilderCmdSet"

	def at_cmdset_creation(self):
		super().at_cmdset_creation()

		self.add(CmdObstacle)



class ObstacleMenu(MenuTree):

	_footer = "Press 'q' to finish or cancel"

	@property
	def _header(self):
		if obstacle := getattr(self, 'obstacle', None):
			return f"Modifying {obstacle.name} (#{obstacle.id})"
		else:
			return ''
	
	def _pre_menu(self, caller, *args, **kwargs):
		super()._pre_menu(caller, *args, **kwargs)
		self.obstacle = self.menu.obstacle
		if not (location := self.obstacle.location):
			location = caller.location
		self.location = location

	def menunode_choose_source(self, caller, raw_string, **kwargs):
		# TODO: get current sources for the obstacle
		sources = self.obstacle.moves.get_sources()

		if not sources:
			# we need to add one instead
			return self.menunode_add_source(caller, raw_string, **kwargs)

		text = "Which source do you want to modify?"

		options = [
			{
				'desc': f"{obj.key} (#{obj.id})",
				'goto': ('menunode_choose_route', {'source': obj})
			} for obj in sources
		]

		options.append(
			{ 'desc': 'Add a new source', 'goto': "menunode_add_source"}
		)

		return text, options
	
	def menunode_add_source(self, caller, raw_string, **kwargs):
		text = "Which source do you want to add a route from?"

		options = [ { 'desc': 'The room', 'goto': ('menunode_add_route', {'source': self.location}) } ]
		options += [
			{
				'desc': f"{obj.key} (#{obj.id})",
				'goto': ('menunode_add_route', {'source': obj})
			} for obj in self.location.contents_get(content_type='obstacle') if obj != self.obstacle
		]

		return text, options

	def menunode_choose_route(self, caller, raw_string, source, **kwargs):
		text = "Which route do you want to modify?"

		routes = self.obstacle.moves.get(source)

		def _prettify_route(route):
			t = route.verb
			if hasattr(route, 'direction'):
				t += " "+route.direction
			t += f" ({route.skill}: {route.dc})"
			if hasattr(route, 'speed') and route.speed:
				t += f" (max {route.speed}s)"
			return t

		def _refine_data(route):
			d = { k:v for k,v in vars(route).items() if k in _ALL_KEYS }
			d['registry_key'] = route.key
			return d

		options = [
			{
				'desc': _prettify_route(r),
				'goto': ('menunode_modify_route', {'source': source, 'route_data': _refine_data(r)})
			} for r in routes
		]

		options.append(
			{ 'desc': 'Add a new route', 'goto': ('menunode_add_route', {'source': source}) }
		)

		return text, options

	def menunode_add_route(self, caller, raw_string, source, route_data=None, **kwargs):
		return self._route_node(caller, raw_string, source, route_data=route_data, return_to="menunode_add_route", **kwargs)

	def menunode_modify_route(self, caller, raw_string, source, route_data=None, **kwargs):
		return self._route_node(caller, raw_string, source, route_data=route_data, return_to="menunode_modify_route", **kwargs)

	def _route_node(self, caller, raw_string, source, route_data=None, return_to="menunode_add_route", **kwargs):
		text = f"Current working route from {source}:\n"
		route_data = route_data or {}
		if route_data:
			template = "\t{verb} ({direction})\n\tspeed: {speed}\n\t{skill}: {dc}\n\t{parts}\n\tUsing the {registry_key} move type"
			fallback = { key: "N/A" for key in ('skill', 'dc', 'verb', 'direction', 'speed', 'registry_key')}
			format_data = fallback | route_data
			if 'req_parts' in format_data:
				format_data['parts'] = f"This requires {iter_to_str(numbered_name(*item) for item in format_data['req_parts'].items())}"
			else:
				format_data['parts'] = f"This requires no particular parts usage."
			text += template.format(**format_data)
		
		else:
			text += "\t(None)"

		text += "\n\n(Any $h(highlighted) options are required.)"

		if errs := kwargs.get('error'):
			text = f"|r{errs}|n\n\n{text}"

		node_kwargs = {'source': source, 'route_data': route_data, 'return_to': return_to}

		options = [
			{ 'desc': 'Set $h(verb)' + (f" ({route_data['verb']})" if 'verb' in route_data else ''), 'goto': ('menunode_enter_verb', node_kwargs) },
			{ 'desc': 'Set $h(skill)' + (f" ({route_data['skill']})" if 'skill' in route_data else ''), 'goto': ('menunode_select_skill', node_kwargs) },
			{ 'desc': 'Set $h(difficulty)' + (f" ({route_data['dc']})" if 'dc' in route_data else ''), 'goto': ('menunode_enter_dc', node_kwargs) },
			{ 'desc': 'Set speed' + (f" ({route_data['speed']})" if 'speed' in route_data else ''), 'goto': ('menunode_enter_speed', node_kwargs) },
			{ 'desc': 'Set direction' + (f" ({route_data['direction']})" if 'direction' in route_data else ''), 'goto': ('menunode_enter_direction', node_kwargs) },
			{ 'desc': 'Update required parts', 'goto': ('menunode_set_req_parts', node_kwargs) },
			{ 'desc': 'Choose custom move type', 'goto': ('menunode_select_move', node_kwargs) },
		] # TODO: specify custom move class

		if all(item in route_data.keys() for item in _REQUIRED_KEYS):
			options.append(
				{ 'desc': 'Save this route', 'goto': (self._set_route, node_kwargs) }
			)

		return text, options

	def _set_route_attr(self, caller, raw_string, source, route_attr, route_data=None, **kwargs):
		if not (new_attr := kwargs.get('new_value')):
			new_attr = raw_string.strip().lower()
		if new_attr:
			route_data[route_attr] = new_attr
		return_to = kwargs.get('return_to','menunode_choose_source')
		return return_to, {'source': source, 'route_data': route_data}

	def menunode_enter_verb(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (verb := route_data.get('verb')):
			text = f"You can currently {verb} from {source}.\n\n"

		text += 'Enter a new verb:'

		option = { 'key': '_default', 'goto': (self._set_route_attr, kwargs | {'route_attr': 'verb', 'source': source, 'route_data': route_data}) }

		return text, option
	
	def menunode_select_skill(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (skillkey := route_data.get('skillkey')):
			text = "You currently require {skillname} to take this route from {source}.\n\n"

		# for mechanics-related choices, you can combine this with the
		# informational options approach to give specific info
		text += f"Choose a new skill:"

		options = []
		node_kwargs = {'route_attr': 'skill', 'source': source, 'route_data': route_data}
		# build the list of options from the right category of your dictionary
		for skill in ALL_SKILLS:
			if skill['key'] == skillkey:
				skillname = skill['name']
				opt_desc = f"Keep {skill['name']}"
			else:
				opt_desc = skill['name']
			options.append(
				{"desc": opt_desc, "goto": (self._set_route_attr, kwargs | node_kwargs | { 'new_value': skill['key'] } )}
			)
		return text, options

	def menunode_enter_dc(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (dc := route_data.get('dc')):
			text = f"The skill-check threshold for {source} is currently {dc}.\n\n"

		text += 'Enter a new difficulty:'

		option = { 'key': '_default', 'goto': (self._set_route_attr, kwargs | {'route_attr': 'dc', 'source': source, 'route_data': route_data}) }

		return text, option

	def menunode_enter_direction(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (direction := route_data.get('direction')):
			text = f"The direction from {source} is currently {direction}.\n\n"

		text += 'Enter a new direction:'

		option = { 'key': '_default', 'goto': (self._set_route_attr, kwargs | {'route_attr': 'direction', 'source': source, 'route_data': route_data}) }

		return text, option

	def menunode_enter_speed(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (speed := route_data.get('speed')):
			text = f"The maximum time window to {route_data.get('verb', 'move')} from {source} is currently $h({speed}) seconds.\n\n"

		text += f'Medium speed: {switchboard.MED_SPEED}\nFast speed: {switchboard.FAST_SPEED}\n\nEnter a new speed:'

		option = { 'key': '_default', 'goto': (self._set_route_attr, kwargs | {'route_attr': 'speed', 'source': source, 'route_data': route_data}) }

		return text, option

	def _set_route(self, caller, raw_string, source, route_data, return_to="menunode_add_route", **kwargs):
		try:
			route_data['dc'] = int(route_data['dc'])
		except ValueError:
			return ("menunode_modify_route", {'source': source, 'route_data': route_data, 'error': "Difficulty must be a number."})
		if 'speed' in route_data:
			try:
				route_data['speed'] = int(route_data['speed'])
			except ValueError:
				return ("menunode_modify_route", {'source': source, 'route_data': route_data, 'error': "Speed must be a number."})

		try:
			self.obstacle.moves.set(source, **route_data)
		except Exception as e:
			return ("menunode_modify_route", {'source': source, 'route_data': route_data, 'error': f"Error adding route: {e}."})
		self.obstacle.cmdset.remove_default()
		return "menunode_choose_source"

	def menunode_set_req_parts(self, caller, raw_string, source, route_data=None, **kwargs):
		text = ''
		if route_data and (partsdict := route_data.get('req_parts',{})):
			text = f"You currently require using the following parts to take this route from {source}:\n\t"
			parts = [ numbered_name(*item) for item in partsdict.items() ]
			text += "\n\t".join(parts)

		else:
			text = f"You don't currently require the use of any specific parts to take this route from {source}."

		options = []
		node_kwargs = {'source': source, 'route_data': route_data}
		# build the list of options from the right category of your dictionary
		for part in partsdict.keys():
			options.append(
				{"desc": f"Remove $h({part}) requirement", "goto": (self._update_req_parts, kwargs | node_kwargs | { 'part': part, 'count': 0 } )}
			)
		options.append(
			{ 'desc': 'Add a new part requirement', 'goto': ("menunode_add_part_type", kwargs | node_kwargs) }
		)
		options.append(
			{ 'desc': 'Modify something else', 'goto': (kwargs.get('return_to', 'menunode_choose_source'), node_kwargs) }
		)
		return text, options
	
	def menunode_add_part_type(self, caller, raw_string, **kwargs):
		text = "Enter the required part type:"
		option = {
			'key': '_default', 'goto': (self._pass_to_count, kwargs)
		}
		return text, option
	
	def _pass_to_count(self, caller, raw_string, **kwargs):
		part = raw_string.strip().lower()

		return "menunode_add_part_count", kwargs | {'part': part}


	def menunode_add_part_count(self, caller, raw_string, part, **kwargs):
		text = f"Enter the required number of $h({part}):"
		option = {
			'key': '_default', 'goto': (self._pass_to_update_parts, kwargs | { 'part': part })
		}
		return text, option

	def _pass_to_update_parts(self, caller, raw_string, **kwargs):
		count = raw_string.strip()
		try:
			count = int(count)
		except ValueError:
			return "menunode_add_part_count", kwargs
		node_kwargs = kwargs | { 'count': count }
		return self._update_req_parts(caller, raw_string, **node_kwargs )

	def _update_req_parts(self, caller, raw_string, source, part, count=1, route_data=None, **kwargs):
		partsdict = route_data.get('req_parts',{})
		if part in partsdict and not count:
			del partsdict[part]
		elif count:
			partsdict[part] = count
		route_data['req_parts'] = partsdict

		return 'menunode_set_req_parts', kwargs | {'source': source, 'route_data': route_data}

	def menunode_select_move(self, caller, raw_string, source, route_data=None, **kwargs):
		move_key = 'base'
		if route_data:
			move_key = route_data.get('registry_key', 'base')

		text = f"Currently using the $h({move_key}) move type.\n\nChoose a move type:"

		options = []
		node_kwargs = {'route_attr': 'registry_key', 'source': source, 'route_data': route_data}
		# build the list of options from the right category of your dictionary
		for key in PARKOUR_MOVES.keys():
			if key == move_key:
				opt_desc = f"Keep {key}"
			else:
				opt_desc = key
			options.append(
				{"desc": opt_desc, "goto": (self._set_route_attr, kwargs | node_kwargs | { 'new_value': key } )}
			)
		return text, options