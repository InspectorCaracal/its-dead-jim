"""
Room

Rooms are simple containers that has no location of their own.

"""
from collections import Counter, defaultdict
from random import randrange

from evennia.utils import iter_to_str, logger
from networkx.exception import NodeNotFound

from utils.colors import strip_ansi
from utils.strmanip import isare
from base_systems.maps import pathing
from utils.strmanip import numbered_name, strip_extra_spaces
from core.ic.base import BaseObject


class Room(BaseObject):
	appearance_template = """
{header}
$head({name})
{desc}
{decor}
{meta}

{characters} {things}

{obstacles}

{doors}

{area}

{exits}
{footer}
"""

	def at_object_creation(self, **kwargs):
		super().at_object_creation(**kwargs)
#		self.db.onword = "there"

	def get_area_contents(self, looker, **kwargs):
		"""
		Returns a dict of lists
		 
		The dict keys are distance and the value is a list of potentially visible objects
		"""
		try:
			# area is a dict of lists of tuples in the form direction: [(room, distance)]
			area = pathing.visible_area(self, looker, kwargs.get('visibility',self.db.visibility or 1))
		except NodeNotFound:
			return {}
		result = defaultdict(list)
		for _, rooms in area.items():
			if not rooms:
				continue
			for room, dist in rooms:
				charas = [ obj for obj in room.contents_get(content_type="character") if obj.size >= 2**dist ]
				things = [ obj for obj in room._filter_things(room.contents_get(content_type="object")) if obj.size >= 2**dist ]
				result[dist].extend(charas)
				result[dist].extend(things)
		
		return result


	def get_display_area(self, looker, **kwargs):
		"""
		Returns a string describing objects and characters visible within the surrounding area.

		Args:
			looker (Character): the character doing the looking
		
		Keyword args:

		Returns:
			str: the description of the contents of the area
		"""
		if kwargs.get("look_in") or not looker:
			return ''
		# TODO: accept a "direction" keyword arg to only show the cone in that direction, for look-in purposes
		try:
			# area is a dict of lists of tuples in the form direction: [(room, distance)]
			area = pathing.visible_area(self, looker, kwargs.get('visibility',self.db.visibility or 1))
		except NodeNotFound:
			return ''
		message = []
		sep = ", you see "
		dist_strings = ( "To the {direction}", "A short ways {direction}", "A long ways {direction}" )
		further_strings = ( "Further {direction}", "Even further {direction}" )
		for direction, rooms in area.items():
			if not rooms:
				continue
			cone = []
			last_dist = -1
			for room, dist in rooms:
				charas = [ obj for obj in room.contents_get(content_type="character") if obj.size >= 2**dist ]
				things = [ obj for obj in room._filter_things(room.contents_get(content_type="object")) if obj.size >= 2**dist ]
				if not (charas or things):
					continue
				if last_dist < dist:
					cone.append({'things': [], 'charas': [], 'dist': dist})
					last_dist = dist
				cone[-1]['charas'] += charas
				cone[-1]['things'] += things
#			looker.msg(cone)
			cmessage = []
			for i, item in enumerate(cone):
				thinglist = item['things']
				charlist = item['charas']
				if not (thinglist or charlist):
					continue
				dist = item['dist']
				if i and i <= len(further_strings):
					rmsg = further_strings[i-1] + sep
				elif dist > len(dist_strings):
					rmsg = dist_strings[-1] + sep
				else:
					rmsg = dist_strings[dist-1] + sep
				if charlist:
					charnames = self.get_display_characters(looker, obj_list=charlist, bypass_loc=True, **kwargs | { 'pose': False})
				else:
					charnames = ''
				if thinglist:
					obnames = self.get_display_things(looker, obj_list=thinglist, bypass_loc=True, **kwargs | { 'pose': False})
				else:
					obnames = ''
				if charnames and obnames:
					rmsg += f"{charnames}, with {obnames}"
				else:
					rmsg += f"{charnames} {obnames}".strip()
				rmsg = rmsg.format(direction=direction).strip() + '.'
				cmessage.append(rmsg)
			message.append("\n ".join(cmessage))
		return "\n\n".join(message)

	def get_display_things(self, looker, obj_list=None, **kwargs):
		"""
		Get the 'things' component of the object description. Called by `return_appearance`.

		Args:
			looker (Object): Object doing the looking.
			**kwargs: Arbitrary data for use when overriding.
		Returns:
			str: The things display data.

		"""
		if not kwargs.get('visibility',1):
			return ''
		if kwargs.get('look_in', False):
			return ""

		# sort and handle same-named things
		if not obj_list:
			obj_list = self.contents_get(content_type="object")
		if looker:
			things = looker._filter_visible(obj_list, **kwargs)
		else:
			things = obj_list

		things = self._filter_things(things)

		if kwargs.get("pose", True):
			grouped_things = defaultdict(list)
			for thing in things:
				if not (pose := thing.get_pose(**kwargs)):
					pose = "here"
				grouped_things[pose].append(thing.get_display_name(looker, link=True, article=False, noid=True, pose=False))
			
			display_strings = []
			
			for pose, names in grouped_things.items():
				name_str = iter_to_str([ numbered_name(*nametup) for nametup in sorted(Counter(names).items()) ])
				if randrange(4) == 0 and pose != "here":
					display_str = f"{pose} {isare(len(names))} {name_str}."
				else:
					display_str = f"{name_str} {isare(len(names))} {pose}."
				display_str = display_str[0].upper() + display_str[1:]
				display_strings.append(display_str)

			if not display_strings:
				return ""
			return "  ".join(display_strings)

		else:
			display_strings = [ thing.get_display_name(looker, link=True, article=False, noid=True, pose=False) for thing in things ]
			return iter_to_str([ numbered_name(*nametup) for nametup in sorted(Counter(display_strings).items()) ])

	def get_display_characters(self, looker, obj_list=None, look_in=False, **kwargs):
		"""
		Get the 'characters' component of the object description. Called by `return_appearance`.

		Args:
			looker (Object): Object doing the looking.
			**kwargs: Arbitrary data for use when overriding.
		Returns:
			str: The character display data.

		"""
		if not kwargs.get('visibility',1):
			return ''

		pose = kwargs.get("pose", True)

		kwargs["article"] = True
		kwargs["ref"] = 't' if pose else '~'

		if obj_list is None:
			obj_list = self.contents_get(content_type="character")
		if looker:
			characters = looker._filter_visible(obj_list)
		else:
			characters = obj_list

		if pose:
			character_names = "  ".join(
				char.get_display_name(looker, noid=True, **kwargs | { 'pose': pose }) for char in characters
			)
		else:
			character_names = iter_to_str( [char.get_display_name(looker, noid=True, **kwargs | { 'pose': pose }) for char in characters] )

		return f"{character_names}" if character_names else ""

	def get_display_obstacles(self, looker, **kwargs):
		if not kwargs.get('visibility',1):
			return ''
		if kwargs.get('look_in', False):
			return ""

		obj_list = self.contents_get(content_type="obstacle")
		if looker:
			obstacles = looker._filter_visible(obj_list, **kwargs)
		else:
			obstacles = obj_list

		if obstacles:
			if poses := self.posing.get(looker):
				location = poses[0].get_display_name(looker, pose=False, noid=True, article=True, tags=False, link=True)
				# THIS SOLUTION IS SO HACKY AAAAAA
				obstr = iter_to_str( [ob.get_display_name(looker, tags=True, pose=False, noid=True, article=True, **kwargs) for ob in obstacles if ob != poses[0]] )
			else:
				location = 'here'
				obstr = iter_to_str( [ob.get_display_name(looker, tags=True, pose=False, noid=True, article=True, **kwargs) for ob in obstacles] )
			if obstr:
				return f"From {location}, you might reach: {obstr}."
		return ''

	def get_display_exits(self, looker, **kwargs):
		if kwargs.get('visibility',1) and not kwargs.get('look_in'):
			return super().get_display_exits(looker, nodoors=True, **kwargs)
		else:
			return ''

	def get_display_desc(self, looker, **kwargs):
		if kwargs.get('visibility',1):
			return super().get_display_desc(looker, **kwargs)
		else:
			return ''

	def format_appearance(self, appearance, looker, **kwargs):
		if kwargs.get('oob', True):
			return (strip_extra_spaces(appearance), {"target": "location"})
		else:
			return strip_extra_spaces(appearance)

	def get_display_name(self, looker, **kwargs):
		dn = super().get_display_name(looker, **kwargs)
		if kwargs.get('look_in'):
			dn = strip_ansi(dn)
		return dn

	#####
	# these are reimplemented core changes because i'm not using a mixin any more
	#####
	_content_types = ("room",)
	lockstring = (
		"control:id({account_id}) or perm(Admin); "
		"delete:id({account_id}) or perm(Admin); "
		"edit:id({account_id}) or perm(Admin)"
	)
	def basetype_setup(self):
		"""
		Simple room setup setting locks to make sure the room cannot be picked up.
		"""
		super().basetype_setup()
		self.locks.add(
			";".join([
				"get:false()",
				"getfrom:true()",
				"puppet:false()",
				"teleport:false()",
				"teleport_here:true()"])
		)  # would be weird to puppet a room ...
		self.location = None
