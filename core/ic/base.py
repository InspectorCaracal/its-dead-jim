import string
from collections import Counter
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from evennia.utils import lazy_property, logger, dbref, make_iter, iter_to_str, variable_from_module
from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultObject
from evennia.contrib.rpg.traits import TraitHandler

from utils.colors import strip_ansi
from utils.strmanip import isare, numbered_name, strip_extra_spaces
from base_systems.effects.handler import EffectsHandler
from base_systems.maps.building import get_by_uid

from . import sdescs, emotes
from .behaviors import BehaviorSet, NoSuchBehavior
from .decor import DecorHandler
from .descs import DescsHandler
from .features import FeatureHandler
from .meta import MetaDataHandler
from .parts import PartsCacher, PartsHandler
from .poses import PoseHandler
from .reactions import ReactionHandler
from .sides import SidesHandler

from evennia.utils.funcparser import FuncParser, ACTOR_STANCE_CALLABLES
from utils.funcparser_callables import FUNCPARSER_CALLABLES as LOCAL_FUNCPARSER_CALLABLES

parser = FuncParser(ACTOR_STANCE_CALLABLES | LOCAL_FUNCPARSER_CALLABLES)

# FIXME: I don't need this to be separate, do I?
_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))

class BaseObject(DefaultObject):
	appearance_template = """
{header}
$head({name})
{desc}
{decor}
{meta}

{characters} {things}

{exits}
{footer}
"""

	covered_template = """
{header}
$head({name})
{decor}
{meta}

{footer}
"""

	@property
	def sides(self):
		return SidesHandler(self)
		if sides := self.attributes.get("sides", category='systems'):
			return sides.deserialize()
		return []

	@property
	def can_talk(self):
		return False

	# parts getsetter
	def __partof_get(self):
		"""Get what we're attached to"""
		return self.attributes.get("attached", category="systems")

	def __partof_set(self, obj):
		"""Set attachment, checking for loops and allowing dbref"""
		if isinstance(obj, (str, int)):
			# allow setting of #dbref
			dbid = dbref(obj, reqhash=False)
			if dbid:
				try:
					obj = ObjectDB.objects.get(id=dbid)
				except ObjectDoesNotExist:
					# maybe it is just a name that happens to look like a dbid
					pass
		try:

			def is_loc_loop(loc, depth=0):
				"""Recursively traverse target obj, trying to catch a loop."""
				if depth > 10:
					# this is bad, it still allows loops
					return None
				elif loc == self:
					raise RuntimeError
				elif not loc:
					# it's fine
					return None
				return is_loc_loop(loc.attributes.get("attached", category="systems"), depth + 1)

			try:
				is_loc_loop(obj)
			except RuntimeWarning:
				# we caught an infinite loop!
				# (location1 is in location2 which is in location1 ...)
				pass

			# if we get to this point we are ready to change attachment
			old_location = self.attributes.get("attached", category="systems")
			self.attributes.add("attached", obj, category="systems")

			# update the contents cache
			if old_location:
				if old_location.baseobj != old_location:
					old_location.baseobj.parts_cache.remove(self)
					old_location.behaviors.unmerge(self)
				old_location.parts_cache.remove(self)
				old_location.behaviors.unmerge(self)

			if hasattr(self, "_baseobj") and (self._baseobj != self):
				self._baseobj.parts_cache.remove(self)
				self._baseobj.behaviors.unmerge(self)

			if obj:
				obj.parts_cache.add(self)
				obj.behaviors.merge(self)
				self._baseobj = obj.baseobj
				if self._baseobj != obj:
					self._baseobj.parts_cache.add(self)
					self._baseobj.behaviors.merge(self)

		except RuntimeError:
			errmsg = "Error: %s.partof = %s creates an attachment loop." % (self.key, obj)
			raise RuntimeError(errmsg)
		except Exception:
			# raising here gives more info for now
			raise
			# errmsg = "Error (%s): %s is not a valid location." % (str(e), location)
			# raise RuntimeError(errmsg)
		if obj:
			self.location = None
		return

	def __partof_del(self):
		"""Cleanly delete the location reference"""
		base = self._baseobj
		base.parts_cache.remove(self)
		base.behaviors.unmerge(self)
		if hasattr(self, "_baseobj"):
			del self._baseobj
		if source := self.attributes.get("attached", category="systems"):
			source.parts_cache.remove(self)
			source.behaviors.unmerge(self)
			self.attributes.remove("attached", category="systems")
		self.parts_cache.init()
		for obj in self.parts_cache.get():
			base.parts_cache.remove(obj)
			if source:
				source.parts_cache.remove(obj)
			if hasattr(obj, "_baseobj"):
				del obj._baseobj

	partof = property(__partof_get, __partof_set, __partof_del)

	@property
	def baseobj(self):
		def get_base(obj):
			if obj.partof:
				# handle objects being deleted without having been detached
				if not obj.partof.pk:
					return obj
				return get_base(obj.partof)
			else:
				return obj

		base = getattr(self, '_baseobj', None)
		if not base or not base.pk:
			self._baseobj = get_base(self)

		return self._baseobj

	@lazy_property
	def parts_cache(self):
		return PartsCacher(self)

	@lazy_property
	def behaviors(self):
		return BehaviorSet(self)

	@lazy_property
	def decor(self):
		return DecorHandler(self)

	@lazy_property
	def react(self):
		return ReactionHandler(self)

	def __getattr__(self, attr):
		if attr.startswith("do_"):
			attr = attr[3:]
			if not self.behaviors.can_do(attr):
				raise NoSuchBehavior(f"'{type(self).__name__}' has no attribute 'do_{attr}'")
			def func(*args, **kwargs):
				return self.behaviors.do(attr, self, *args, **kwargs)
			return func

		elif attr.startswith("can_"):
			attr = attr[4:]
			return self.behaviors.can_do(attr)

		elif attr.startswith("on_"):
			attr = attr[3:]
			def func(*args, **kwargs):
				self.react.on(attr, *args, **kwargs)
			return func

		else:
			raise AttributeError(f"'{type(self).__name__}' has no attribute '{attr}'")

	def __name_set(self, value):
		old_name = self.key
		self.key = value
		self.at_rename(old_name, value)

	@property
	def gender(self):
		return 'neutral'

	@property
	def weight(self):
		return (self.db.weight or 0) + sum([obj.weight for obj in self.contents])

	@property
	def inventory(self):
		return self.contents

	@lazy_property
	def metadata(self):
		return MetaDataHandler(self)

	@lazy_property
	def features(self):
		return FeatureHandler(self)

	@lazy_property
	def descs(self):
		return DescsHandler(self)

	@lazy_property
	def sdesc(self):
		return sdescs.SdescHandler(self)

	@lazy_property
	def vdesc(self):
		return sdescs.VdescHandler(self)

	@lazy_property
	def posing(self):
		return PoseHandler(self)

	@lazy_property
	def stats(self):
		return TraitHandler(self, db_attribute_key="stats")

	@lazy_property
	def parts(self):
		return PartsHandler(self)

	@property
	def lighting(self):
		"""
		Returns the current light level within or generated by this object
		"""
		if not self.ndb._light_level:
			self.ndb._light_level = self.attributes.get("_light_level", default=1)
		# TODO: change the default of 1 to 0 once lighting is implemented
		return max([self.ndb._light_level] + [obj.lighting for obj in self.contents]) or 1

	@property
	def visibility(self):
		"""
		Returns the range of visibility from within this object, assuming no obstacles.
		"""
		if self.ndb.visibility is None:
			return self.attributes.get('visibility',1)
		return self.ndb.visibility

	@property
	def uid(self):
		return self.attributes.get('uid', category="systems")

	@uid.setter
	def uid(self, value):
		if get_by_uid(value):
			raise KeyError(f"Object {value} already exists.")
		self.attributes.add('uid', value, category="systems")

	def search(
		self,
		searchdata,
		global_search=False,
		use_nicks=True,
		typeclass=None,
		location=None,
		attribute_name=None,
		quiet=False,
		exact=False,
		candidates=None,
		nofound_string=None,
		multimatch_string=None,
		use_dbref=None,
		filter=None,
		stacked=0,
		**kwargs
	):
		"""
		Returns an Object matching a search string/condition, taking
		sdescs into account.

		Perform a standard object search in the database, handling
		multiple results and lack thereof gracefully. By default, only
		objects in the current `location` of `self` or its inventory are searched for.

		Args:
			searchdata (str or obj): Primary search criterion. Will be matched
				against `object.key` (with `object.aliases` second) unless
				the keyword attribute_name specifies otherwise.
				**Special strings:**
				- `#<num>`: search by unique dbref. This is always
					a global search.
				- `me,self`: self-reference to this object
				- `<num>-<string>` - can be used to differentiate
					between multiple same-named matches
			global_search (bool): Search all objects globally. This is overruled
				by `location` keyword.
			use_nicks (bool): Use nickname-replace (nicktype "object") on `searchdata`.
			typeclass (str or Typeclass, or list of either): Limit search only
				to `Objects` with this typeclass. May be a list of typeclasses
				for a broader search.
			location (Object or list): Specify a location or multiple locations
				to search. Note that this is used to query the *contents* of a
				location and will not match for the location itself -
				if you want that, don't set this or use `candidates` to specify
				exactly which objects should be searched.
			attribute_name (str): Define which property to search. If set, no
				key+alias search will be performed. This can be used
				to search database fields (db_ will be automatically
				appended), and if that fails, it will try to return
				objects having Attributes with this name and value
				equal to searchdata. A special use is to search for
				"key" here if you want to do a key-search without
				including aliases.
			quiet (bool): don't display default error messages - this tells the
				search method that the user wants to handle all errors
				themselves. It also changes the return value type, see
				below.
			exact (bool): if unset (default) - prefers to match to beginning of
				string rather than not matching at all. If set, requires
				exact matching of entire string.
			candidates (list of objects): this is an optional custom list of objects
				to search (filter) between. It is ignored if `global_search`
				is given. If not set, this list will automatically be defined
				to include the location, the contents of location and the
				caller's contents (inventory).
			nofound_string (str):  optional custom string for not-found error message.
			multimatch_string (str): optional custom string for multimatch error header.
			use_dbref (bool or None): If None, only turn off use_dbref if we are of a lower
				permission than Builder. Otherwise, honor the True/False value.

		Returns:
			match (Object, None or list): will return an Object/None if `quiet=False`,
				otherwise it will return a list of 0, 1 or more matches.

		Notes:
			To find Accounts, use eg. `evennia.account_search`. If
			`quiet=False`, error messages will be handled by
			`settings.SEARCH_AT_RESULT` and echoed automatically (on
			error, return will be `None`). If `quiet=True`, the error
			messaging is assumed to be handled by the caller.

		"""

		def search_globally(dbref):
			"helper wrapper for searching"
			return ObjectDB.objects.object_search( dbref, use_dbref=True )

		is_string = isinstance(searchdata, str)
		extra = ""

		if is_string:
			# searchdata is a string; wrap some common self-references
			if kwargs.get('partial'):
				tocheck, *rest = searchdata.split(' ', maxsplit=1)
				if tocheck.lower() in ("here",):
					ret_obj = [self.location] if quiet else self.location
					return (ret_obj, " ".join(rest))
				elif tocheck.lower() in ("me", "self"):
					ret_obj = [self] if quiet else self
					return (ret_obj, " ".join(rest))
			else:
				if searchdata.lower() in ("here",):
					return [self.location] if quiet else self.location
				if searchdata.lower() in ("me", "self"):
					return [self] if quiet else self

		if use_nicks:
			# do nick-replacement on search
			searchdata = self.nicks.nickreplace(
				searchdata, categories=("object", "account"), include_account=True
			)

		if is_string and searchdata.startswith("#") and searchdata[1:].isdigit():
			global_search = True
		
		if global_search:
			results = search_globally(searchdata)

		else:
			if candidates is None:
				# no custom candidates given - get them automatically
				if location:
					# location(s) were given
					candidates = set()
					for obj in make_iter(location):
						candidates.update(obj.get_all_contents())
						candidates.update(obj.parts.all())
				else:
					# local search
					# Candidates are taken from own contents/parts and location contents/parts
					location = self.location
					candidates = set()
					candidates.update(self.get_all_contents() + self.parts.all() + [self])
					if location:
						candidates.update([location] + location.get_all_contents() + location.parts.all())
				if dist := kwargs.get('distance') and hasattr(location, 'get_area_contents'):
					for d, objs in location.get_area_contents(self).items():
						if d <= dist:
							candidates.update(objs)

			candidates = list(candidates) if candidates else []

			if filter and callable(filter):
				candidates = filter(candidates)

			# the sdesc-related substitution
			is_builder = self.permissions.check("Builder")
			use_dbref = is_builder if use_dbref is None else use_dbref

			results = emotes.ic_search(
				self, candidates, searchdata, exact=exact, **kwargs
			)
			if kwargs.get("partial"):
				results, extra = results

			# if not results and is_builder:
			# 	# builders get a chance to use system search
			# 	results = search_globally(searchdata)
			# else:
			# 	# global searches / #drefs end up here. Global searches are
			# 	# only done in code, so is controlled, #dbrefs are turned off
			# 	# for non-Builders.
			# 	results = search_globally(searchdata)

		if quiet:
			if kwargs.get("partial"):
				return results, extra
			return results
		# TODO: actually use this setting for custom result handling
		return _AT_SEARCH_RESULT(
			results,
			self,
			query=searchdata,
			nofound_string=nofound_string,
			multimatch_string=multimatch_string,
		)

	def web_desc(self):
		string = self.get_display_desc(None)
		string = parser.parse(string, caller=self, receiver=None)
		string = strip_ansi(string)
		paras = [ bit for bit in string.split("\n") if bit ]
		return paras

	# alias for access checks
	def get_lock(self, *args, **kwargs):
		return self.access(*args, **kwargs)

	def is_visible(self, looker, **kwargs):
		"""
		Check if this object is visible to the entity looking.
		Returns:
			boolean: visibility to looker
		"""

		def _open_up(obj):
			"""
			this is such an annoyingly structured function but whatever
			"""
			if not obj:
				return False
			if obj != obj.baseobj:
				return _open_up(obj.partof)
			if obj == obj.baseobj and not obj.location:
				return True # originally False but THAT'S BREAKING EVERYTHING
			if looker.location == obj.location or obj.ndb.prev_location == looker.location:
				return True
			if area := looker.location.ndb.area:
				room_list = []
				for rooms in area.values():
					room_list.extend(rooms)
				if obj.location in room_list:
					return True
				if obj.ndb.prev_location in room_list:
					return True
			if not obj.location.access(looker, "viewcon") and not obj.location.access(looker, "getfrom"):
				return False
			return _open_up(obj.location)

		if self.tags.has("hidden", category="systems"):
			return False
		if not looker:
			# i hate this
			return True
		if not looker.location:
			# i hate this too???
			return True
		if not self.access(looker, "view"):
			return False
		return kwargs.get("bypass_loc") or _open_up(self)

	def is_audible(self, hearer, vol=1, **kwargs):
		"""
		Check if another object can hear this object.
		"""
		if vol <= 0:
			return False
		# more complicated stuff will go here eventually, maybe
		return True
	
	def is_usable(self, **kwargs):
		"""
		Check if this object can be used.

		Returns:
			bool
		"""
		if hasattr(self.baseobj, 'holding'):
			if self.baseobj.holding(self) or self.baseobj.holding(self.partof):
				return False
		unusable = ['disabled','broken']
		if any(self.tags.has(unusable, category='status')):
			return False
		for p in self.get_affected_parts(include_self=False):
			if any(p.tags.has(unusable, category='status')):
				return False
		# everything checked out!
		return True

	def get_affected_parts(self, include_self=True):
		"""
		Get any sibling parts that would be affected by using this part.

		Returns:
			parts (list)
		"""
		parent = self.partof
		if not (chain := parent.attributes.get('_parts_chain', category='systems')):
			# it isn't a chain, just return ourself
			return [parent, self] if include_self else [parent]
		chain = chain.deserialize()
		end = chain.index(self)+ (1 if include_self else 0)
		return [parent] + chain[:end]
	

	def get_all_contents(self):
		return self.contents

	def at_server_reload(self):
		super().at_server_reload()
#		self.effects.save()

	def at_server_start(self):
		# this has no supers from here
		self.effects = EffectsHandler(self)
		self.parts
		# self.sdesc.get()

	def at_object_creation(self):
		"""
		Called at initial creation.
		"""
		super().at_object_creation()
		self.at_server_start()
		# emoting/recog data
		self.db.pose = ""
		self.db.pose_default = "here"

	def get_numbered_name(self, count, looker, **kwargs):
		name = self.sdesc.get(viewer=looker)
		# returning both for backwards compatability
		return numbered_name(name, 1), numbered_name(name, count)

	def get_pose(self, fallback=True, on_target=False, looker=None, **kwargs):
		statuses = self.tags.get(category="status", return_list=True)
		if not (pose := self.ndb.pose):
			if pose := self.db.pose:
				statuses.append(pose)
		if extras := kwargs.get("extras"):
			# extras must be a list
			statuses += extras
		position = None
		if self.location and hasattr(self.location, 'posing'):
			if position := self.location.posing.get(self):
				posed_on, _ = position
				if posed_on:
					onword = posed_on.db.onword or 'on'
					if on_target:
						onname = "this"
					elif looker:
						onname = posed_on.get_display_name(looker, article=True)
					else:
						onname = numbered_name(posed_on.sdesc.get(), 1)
					position = f"{onword} {onname}".strip()
				else:
					position = None

		if statuses:
			pose = iter_to_str(statuses)
		elif fallback and not position:
			pose = self.db.pose_default
		else:
			pose = None

		poses = []
		if pose:
			poses.append(pose)
		if position:
			poses.append(position)

		if not poses:
			return None

		return " ".join(poses)

	def _filter_visible(self, obj_list, **kwargs):
		"""
		Filters a list of objects to only those visible to self
		Args:
			obj_list (list of Object)
		Returns
			list of Object
		"""
		return [obj for obj in obj_list if obj != self and obj.is_visible(self, **kwargs)]

	def get_posed_sdesc(self, sdesc, **kwargs):
		"""
		Displays the object with its current pose string.
		Returns:
			pose (str): A string containing the object's sdesc and
				current or default pose.
		"""
		# get the current pose
		pose = self.get_pose(**kwargs)
		# return formatted string, or sdesc as fallback
		return f"{sdesc} is {pose}." if pose else sdesc
	
	def _filter_things(self, thing_list, **kwargs):
		"""customize what things to exclude from the thing list"""
		return [thing for thing in thing_list if thing not in self.decor.all()]

	def get_display_things(self, looker, **kwargs):
		"""
		Get the 'things' component of the object description. Called by `return_appearance`.
		Args:
			looker (Object): Object doing the looking.
			**kwargs: Arbitrary data for use when overriding.
		Returns:
			str: The things display data.
		"""
		# check if we can see the contents of this thing
		if not self.get_lock(looker, "viewcon") and not self.get_lock(looker, "getfrom"):
			return ''

		# sort and handle same-named things
		if looker:
			things = looker._filter_visible(self.contents_get(content_type="object"))
		else:
			things = self.contents_get(content_type="object")
		things = self._filter_things(things)

		my_name = strip_ansi(self.get_display_name(looker, article=False, noid=True, link=False, contents=False))
		thing_names = [thing.get_display_name(looker, article=False, noid=True, pose=False, link=False) for thing in things]
		if kwargs.get('link', True):
			things_str = iter_to_str(
				[f"|lclook {strip_ansi(nametup[0].replace(',',''))} on {my_name}|lt{numbered_name(*nametup)}|le" for nametup in
				Counter(thing_names).items()])
		else:
			things_str = iter_to_str([f"{numbered_name(*nametup)}" for nametup in Counter(thing_names).items()])

		if things_str:
			return self._format_display_things(things_str, count=len(things))

		else:
			return ""

	def get_display_characters(self, looker, **kwargs):
		# check if we can see the contents of this thing
		if not self.get_lock(looker, "viewcon"):
			return ''
		return super().get_display_characters(looker, **kwargs)

	def _format_display_things(self, things_str, count, **kwargs):
		onword = self.db.onword or "inside"
		onword = onword[0].upper() + onword[1:]
		return f"{onword} {isare(count)} {things_str}."

	def get_display_exits(self, looker, **kwargs):
		if not looker:
			return ""
		
		exits = self.contents_get(content_type="exit")
		if kwargs.get('nodoors',False):
			exits = [ ex for ex in exits if ex not in self.contents_get(content_type="exit") or not ex.db.door ]
		exits = looker._filter_visible(exits)

		exit_names = iter_to_str((exi.get_display_name(looker, **kwargs) for exi in exits if exi.get_lock(looker, 'traverse')), endsep=", or")

		return f"You can go {exit_names}" if exit_names else ''


	def get_xcards(self, looker, **kwargs):
		"""
		Get a list of display strings for any active x-cards in this location.
		"""
		card_strs = []
		template = "|{c}-X- {played} a {cword} X-card active here. Please respect it.|n"
		from base_systems.characters.players import PlayerCharacter
		kwargs.pop('process',None)
		for chara in PlayerCharacter.objects.filter(db_location=self):
			if cdata := chara.db.xcard:
				card, anon, ooc = cdata
				fkeys = {}
				match card:
					case 0:
						card = 'red'
					case 1:
						card = 'yellow'
					case 2:
						card = 'green'
				
				fkeys['cword'] = card
				fkeys['c'] = card[0]
				if anon:
					fkeys['played'] = "There is"
				else:
					fkeys['played'] = f"{chara.get_display_name(looker, process=False, **kwargs)}'s player has"
				card_strs.append(template.format(**fkeys))

		return card_strs

	def get_display_footer(self, looker, **kwargs):
		footer = super().get_display_footer(looker, **kwargs)
		if not looker:
			return footer
		footer = []
		if any(p.get_lock(looker, 'view') for p in self.parts.search('text', part=True)):
			footer.append(f"You could |lcread {self.sdesc.get(strip=True)}|ltread|le this.")

		if looker.location == self or kwargs.get('look_in'):
				if xcards := self.get_xcards(looker, **kwargs):
					footer.append('')
					footer.extend(xcards)
		
		return "\n".join(footer)

	def get_display_doors(self, looker, **kwargs):
		if kwargs.get('look_in'):
			return ''

		show_all = kwargs.get('all_doors')
		doors = [door for door in self.contents_get(content_type="door") if door.db.door]
		if not doors:
			return ''
		if len(doors) == 1:
			template = 'A door ({doors}) is here.'

		else:
			count = len(doors)
			if count < 4:
				numword = 'a few'
				show_all=True
			elif count < 8:
				numword = 'several'
			else:
				numword = 'many'
			if show_all:
				template = f'There are {numword} doors here:\n  '+'{doors}'
			else:
				template = f'There are |lclook doors|lt{numword}|le doors here.'
		
		if '{doors}' in template:
			door_names = iter_to_str(door.get_display_name(looker, **kwargs) for door in doors)
			return template.format(doors=door_names)
		else:
			return template

	def get_display_name(self, looker, article=False, process=True, **kwargs):
		"""
		Displays the name of the object in a viewer-aware manner.
		Args:
			looker (TypedObject): The object or account that is looking
				at/getting inforamtion for this object.
		Keyword Args:
			pose (bool): Include the pose (if available) in the return.
			ref (str): The reference marker found in string to replace.
				This is on the form #{num}{case}, like '#12^', where
				the number is a processing location in the string and the
				case symbol indicates the case of the original tag input
				- `t` - input was Titled, like /Tall
				- `^` - input was all uppercase, like /TALL
				- `v` - input was all lowercase, like /tall
				- `~` - input case should be kept, or was mixed-case
			noid (bool): Don't show DBREF even if viewer has control access.
		Returns:
			name (str): A string of the sdesc containing the name of the object,
				if this is defined. By default, included the DBREF if this user
				is privileged to control said object.
		"""
		# can they see us?
		visibility = self.is_visible(looker) if looker else True
		try:
			# get the sdesc looker should see, with formatting
			sdesc = looker.get_sdesc(self, article=article, process=process, visible=visibility, **kwargs)
		except AttributeError as e:
			if 'get_sdesc' not in str(e):
				raise AttributeError(e)
			# use own sdesc as a fallback
			if looker == self:
				# process your key as recog since you recognize yourself
				sdesc = self.key
			else:
				if not visibility:
					sdesc = self.vdesc.get() or self.sdesc.get(strip=kwargs.get("strip"))
				else:
					# FIXME: this doesn't capitalize
					sdesc = self.sdesc.get(strip=kwargs.get("strip"))
				if article:
					sdesc = numbered_name(sdesc,1)

		return self.get_posed_sdesc(sdesc, looker=looker, **kwargs) if kwargs.get("pose") and visibility else sdesc

	def get_status(self, third=False, **kwargs):
		if pose := self.get_pose(fallback=False):
			msg = "{} {}.".format("$Gp(they) $pconj(is)" if third else "You are", pose)
		else:
			msg = "This has no current status."
		return f"{msg}"

	def damage_status(self, third=False, **kwargs):
		"""Return an assessment of the damage status"""
		return ''

	def emote(self, message, receivers=None, **kwargs):
		# TODO: prevent players from speaking if they don't pass .can_speak
		if not receivers:
			if not self.baseobj.location:
				self.msg("There's no one to see that.")
				return

		message = message.strip()
		if strip_ansi(message)[-1] not in string.punctuation:
			message += "."

		emotes.send(self, message, receivers, **kwargs)

	def format_appearance(self, appearance, looker, **kwargs):
		return strip_extra_spaces(appearance)

	def msg(self, text=None, from_obj=None, session=None, **kwargs):
		"""
		Emits something to a session attached to the object.
		Args:
			text (str or tuple, optional): The message to send. This
				is treated internally like any send-command, so its
				value can be a tuple if sending multiple arguments to
				the `text` oob command.
			from_obj (obj, optional): object that is sending. If
				given, at_msg_send will be called
			session (Session or list, optional): session or list of
				sessions to relay to, if any. If set, will
				force send regardless of MULTISESSION_MODE.
		Notes:
			`at_msg_receive` will be called on this Object.
			All extra kwargs will be passed on to the protocol.
		"""
		if text:
			parse_caller = from_obj if from_obj else self
#			logger.log_msg(text)

			if isinstance(text, tuple):
				# TODO: take this out later, it's a workaround for broken `py` output
				if isinstance(text[0], str):
					text = (parser.parse(text[0], caller=parse_caller, receiver=self), *text[1:])
				else:
					text = (str(text[0]), *text[1:])
			elif isinstance(text, str):
				text = parser.parse(text, caller=parse_caller, receiver=self)
			else:
				text = str(text)

		super().msg(text, from_obj=from_obj, session=session, **kwargs)

	def at_pre_get(self, getter, **kwargs):
		return self.baseobj == self

	def at_pre_move(self, *args, **kwargs):
		if self.tags.has('immobile', category='status'):
			return False
		return super().at_pre_move(*args, **kwargs)

	def at_pre_posed_on(self, poser, **kwargs):
		"""Determine whether or not poser is allowed to pose on this"""
		return True

	def announce_move_from(self, destination, msg=None, mapping=None, move_type="move", **kwargs):
		if not self.location:
			return

		if not msg:
			if destination:
				msg = f"@Me leaves for {destination.key}."
			else:
				msg = f"@Me leaves."

		self.emote(msg, receivers=self.location.contents, action_type="move")

	def announce_move_to(self, source_location, msg=None, mapping=None, move_type="move", **kwargs):
		if not (destination := self.location):
			return
		
		# TODO: make these names viewer-dynamic
		if not msg:
			if source_location:
				msg = f"@Me arrives at {destination.key} from {source_location.key}."
			else:
				msg = f"@Me arrives at {destination.key}."
		self.emote(msg, action_type="move")

	def at_post_move(self, source_location, move_type="move", skip=False, **kwargs):
		"""
		We make sure to look around after a move.
		"""
		if skip:
			return
		if self.location.access(self, "view"):
			message = self.at_look(self.location)
			tuple_kwargs = {"target": "location", "clear": True}
			if isinstance(message,tuple):
				if len(message) > 1:
					tuple_kwargs |= message[1]
					message = message[0]
				else:
					message = message[0]
			self.msg(text=(message, tuple_kwargs))
		self.on_move(source_location, move_type=move_type, **kwargs)

	def at_object_receive(self, obj, source, **kwargs):
		# print(f"received {obj}")
		self.on_object_enter(obj, source, **kwargs)
		for obj in self.contents:
			obj.on_arrival(obj, source, **kwargs)

	def at_object_leave(self, obj, destination, **kwargs):
		super().at_object_leave(obj, destination, **kwargs)
		self.decor.remove(obj)
		self.posing.remove(obj)
		self.on_object_leave(obj, destination, **kwargs)
		for ob in self.contents:
			ob.on_departure(obj, destination, **kwargs)

	def clear_contents(self):
		base = self.baseobj
		if base.location:
			# contents should fall to location, not be magicked away
			for obj in self.contents:
				obj.location = base.location
		else:
			# contents should be tagged as abandoned
			for obj in self.contents:
				if hasattr(obj, 'sessions'):
					for sess in obj.sessions.all():
						if acct := sess.get_account():
							acct.unpuppet_object(sess)
				obj.location = None
				if 'player' not in getattr(obj, '_content_types', []):
					obj.tags.add('orphaned')

	def at_object_delete(self):
		base = self.baseobj
		if base != self:
			if not base.parts.detach(self, clean=True, delete=True):
				return False
		if base.location:
			base.location.posing.remove(self)

		return super().at_object_delete()


	def delete(self, full=False):
		self.effects.clear()
		parts = list(self.parts.all())
		if not super().delete():
			return False
		if full:
			for obj in parts:
				obref = f"{obj.key}(#{obj.id})"
				if not obj.delete():
					logger.log_err(f"failed deleting part {obref}")
		return True


	def update_features(self):
		for obj in self.parts.all():
			subtypes = obj.tags.get(category='subtype', return_list=True)
			if not subtypes:
				subtypes = None
			elif len(subtypes) == 1:
				subtypes = subtypes[0]
			name = obj.key
			part = obj.tags.get(category='part') or name
			match = {'subtype': subtypes} if subtypes else {}
			self.features.reset(match=match | {'location': part}, save=False)
			features = obj.features.get("all", as_data=True)
			for key, vals in features:
				newval = dict(vals) | {'location': part }
				if vals.get('unique'):
					if extant := self.features.get(key, as_data=True):
						# check if the values are already matching
						if all(vals.get(exkey) == exval for exkey, exval in extant.items()):
							continue
				# if key == name or name.endswith(key):
				# 	newval |= {'subtype': subtypes}
				elif subtypes:
					newval |= {'subtype': subtypes}
				self.features.merge(key, **newval, match=match, soft=True, save=False)
		self.features.save()
		self.sdesc.update()

	def get_display_desc(self, looker, **kwargs):
		desc_str = self.descs.get(looker, **kwargs)

		# features = self.features.view

		# if features and kwargs.get('features', True):
		# 	desc_str = f"{desc_str}\n\n$Gp(they) $conj(have) {features}."

		return desc_str

	def get_display_decor(self, looker, **kwargs):
		if kwargs.get('look_in'):
			return ''
		return self.decor.desc(looker, **kwargs)

	def get_display_meta(self, looker, **kwargs):
		"""
		Check for meta attributes visible to looker and display them
		"""
		return self.metadata.display(looker, **kwargs)

	def return_appearance(self, looker, **kwargs):
		if "link" not in kwargs:
			kwargs["link"] = True if not kwargs.get("look_in") else False

		format_dict = {}
		for attr in dir(self):
			match attr.split("_"):
				case ["get", "display", k]:
					k_attr = getattr(self, attr)
					if callable(k_attr):
						format_dict[k] = k_attr(looker, **kwargs)
				case _:
					continue

		template = self.covered_template if self.effects.has(name='covered') else self.appearance_template
		template = kwargs.get('template', template)

		return self.format_appearance(template.format(**format_dict), looker, **kwargs)

	def format_appearance(self, appearance, looker, **kwargs):
		return strip_extra_spaces(appearance)

	def at_pre_craft(self, user, *args, **kwargs):
		# TODO: whatever needs to actually happen here
		return self.get_lock(user, 'craftwith')

	def at_spoken_to(self, speaker, message, **kwargs):
		message = message.strip()
		self.on_spoken_to(speaker, message, **kwargs)
		# TODO: change behavior below to be a trigger, maybe?
		try:
			self.do_parse_audio(speaker, message, **kwargs)
		except NoSuchBehavior:
			pass

	def at_rename(self, old_name, new_name, **kwargs):
		"""custom code to run when renamed"""
		super().at_rename(old_name, new_name)
		self.sdesc.update()
	
	def basetype_setup(self):
		super().basetype_setup()

		self.locks.add(
			";".join(
				[
					"viewcon:false()",  # view the contents
					"getfrom:is_open()",  # get objects from its contents
				]
			)
		)

	def at_first_save(self):
		"""
		This is called by the typeclass system whenever an instance of
		this class is saved for the first time. It is a generic hook
		for calling the startup hooks for the various game entities.
		When overloading you generally don't overload this but
		overload the hooks called by this method.

		"""
		self.basetype_setup()
		self.at_object_creation()
		# initialize Attribute/TagProperties
		self.init_evennia_properties()

		if hasattr(self, "_createdict"):
			# this will only be set if the utils.create function
			# was used to create the object. We want the create
			# call's kwargs to override the values set by hooks.
			cdict = self._createdict
			updates = []
			if not cdict.get("key"):
				if not self.db_key:
					self.db_key = "#%i" % self.dbid
					updates.append("db_key")
			elif self.key != cdict.get("key"):
				updates.append("db_key")
				self.db_key = cdict["key"]
			if cdict.get("location") and self.location != cdict["location"]:
				self.db_location = cdict["location"]
				updates.append("db_location")
			if cdict.get("home") and self.home != cdict["home"]:
				self.home = cdict["home"]
				updates.append("db_home")
			if cdict.get("destination") and self.destination != cdict["destination"]:
				self.destination = cdict["destination"]
				updates.append("db_destination")
			if updates:
				self.save(update_fields=updates)

			if cdict.get("permissions"):
				self.permissions.batch_add(*cdict["permissions"])
			if cdict.get("locks"):
				self.locks.add(cdict["locks"])
			if cdict.get("aliases"):
				self.aliases.batch_add(*cdict["aliases"])
			if cdict.get("location"):
				cdict["location"].at_object_receive(self, None)
				# self.at_post_move(None)
			if cdict.get("tags"):
				# this should be a list of tags, tuples (key, category) or (key, category, data)
				self.tags.batch_add(*cdict["tags"])
			if cdict.get("attributes"):
				# this should be tuples (key, val, ...)
				self.attributes.batch_add(*cdict["attributes"])
			if cdict.get("nattributes"):
				# this should be a dict of nattrname:value
				for key, value in cdict["nattributes"].items():
					self.nattributes.add(key, value)

			del self._createdict

		self.basetype_posthook_setup()