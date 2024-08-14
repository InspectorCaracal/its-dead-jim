import networkx
from collections import Counter, defaultdict
from evennia.utils import iter_to_str, logger, is_iter, make_iter
from base_systems.maps.building import get_by_id

from core.ic.base import BaseObject
from utils.handlers import HandlerBase
from utils.strmanip import numbered_name

from switchboard import INFLECT

########### Default settings ###########

_CLOTHING_TAG_CATEGORY = "clothing"


# Display order for different clothing types, or None to disable.
# Any types not in the list will be unsorted at the end, but still visible.
_CLOTHING_TYPE_ORDER = [
	"hat",
	"jewelry",
	"top",
	"undershirt",
	"gloves",
	"fullbody",
	"bottom",
	"underpants",
	"socks",
	"shoes",
	"accessory",
]

# The maximum number of each type of clothes that can be worn.
# Any types not specified are not limited.
_CLOTHING_TYPE_LIMITS = {} #{"hat": 1, "gloves": 1, "socks": 1, "shoes": 1}

# The maximum number of clothing items that can be worn, or None for unlimited.
_CLOTHING_TOTAL_LIMIT = 20

class ClothingHandler(HandlerBase):
	"""
	Tracks a character's worn objects and visible outfit.
	"""

	def __init__(self, obj):
		# self._graph = networkx.DiGraph()
		super().__init__(obj, "clothing", "systems", default_data=[])
	
	# def _init_data(self):
	# 	self._graph = networkx.DiGraph()
	# 	self._graph.add_node(self.obj.id)
	# 	for p in self.obj.parts.all():
	# 		part = p.tags.get(category='part')
	# 		if subt := p.tags.get(category='subtype'):
	# 			part = (part, subt)
	# 		self._graph.add_edge(p.id, self.obj.id, slot=part, parts=[p.id])
	# 	# save initial graph data
	# 	self._save()

	# def _load(self):
	# 	super()._load()
	# 	if self._data:
	# 		self._graph = networkx.DiGraph(self._data)
	# 	else:
	# 		# initialize from body parts
	# 		self._init_data()
	# 	objs = [get_by_id(cid) for cid in self._graph.nodes.keys()]
	# 	self._list = [obj for obj in objs if obj.baseobj != self.obj]

	# def _save(self):
	# 	self._data = networkx.to_dict_of_dicts(self._graph)
	# 	super()._save()

	@property
	def all(self):
		return self._data

	def visible(self, viewer=None, **kwargs):
		"""Returns a list of all *visible* articles of clothing, regardless of how much is visible"""
		return [c for c in self._data if c.is_visible(viewer)]

	def _get_coverage(self, obj):
		covered_parts = []
		for cov in obj.tags.get(category="parts_coverage", return_list=True):
			part, *subs = cov.split(',', maxsplit=1)
			result = self.obj.parts.search(part, part=True)
			if subs:
				result = [p for p in result if p.tags.has(subs, category='subtype')]
			covered_parts += result
		return covered_parts
		

	def add(self, obj, style=None, quiet=False):

		adjust = False

		uncovered = set(self.visible())
		uncovered_parts = set(p for p in self.obj.parts.all() if not p.tags.has('hidden', category='systems'))
		base_coverage = self._get_coverage(obj)
		for p in base_coverage:
			p.decor.add(obj, position=style, cover=True)

		# add the parts
		for p in obj.parts.all():
			coverage = self._get_coverage(p)
			for c in coverage:
				c.decor.add(obj, cover=True)

		covered = uncovered.difference(set(self.visible()))
		covered_parts = uncovered_parts.difference(set(p for p in self.obj.parts.all() if not p.tags.has('hidden', category='systems')))

		covered_names = [ob.sdesc.get() for ob in covered]
		covered_feats = [p.features.view for p in covered_parts if p.features.view]

		if obj not in self.all:
			self._data.append(obj)
		self._save()
		# Return nothing if quiet
		if quiet:
			message = None
		# Return a message to echo if otherwise
		# TODO: add back in adjustment vs wearing
		else:
			if adjust:
				message = f"adjusts $gp(their) {obj.sdesc.get()}"
			else:
				message = f"puts on {numbered_name(obj.sdesc.get(),1)}"
			if covered_names or covered_feats:
				covered_names = [ numbered_name(*tup, pair=True) for tup in Counter(covered_names).items() ]
				# this sucks
				covered_names += [
						numbered_name(feat, count, prefix=False)
						if count > 1
						and (feat.startswith('a ') or feat.startswith('an '))
						else feat for feat, count in Counter(covered_feats).items()
					]
				message += f", covering {iter_to_str(covered_names)}"
			message += '.'

		if covered_feats:
			self.obj.features._cache()
		return message

	def remove(self, obj_list, quiet=False, save=True):
		"""Removes worn clothes and optionally echoes to the room."""
		obj_list = make_iter(obj_list)

		uncovered = set(self.visible())
		uncovered_parts = set(p for p in self.obj.parts.all() if not p.tags.has('hidden', category='systems'))

		for obj in obj_list:
			base_coverage = self._get_coverage(obj)
			for p in base_coverage:
				p.decor.remove(obj)

			# remove the parts
			for p in obj.parts.all():
				coverage = self._get_coverage(p)
				for c in coverage:
					c.decor.remove(obj)

		new_uncovered = set(self.visible()).difference(uncovered)
		new_uncovered_parts = set(p for p in self.obj.parts.all() if not p.tags.has('hidden', category='systems')).difference(uncovered_parts)

		uncovered_names = [ob.sdesc.get() for ob in new_uncovered]
		# FIXME: this prevents having lots of "skin"s but breaks other plurals
		uncovered_feats = set(p.features.view for p in new_uncovered_parts if p.features.view)

		self._data = [ob for ob in self._data if ob not in obj_list]
		if save:
			self._save()

		if quiet:
			message = None

		else:
			uncovered = [numbered_name(*item) for item in Counter(uncovered_names).items()] + list(uncovered_feats)
			removed = [ obj.sdesc.get() for obj in obj_list ]
			removed = [numbered_name(*item) for item in Counter(removed).items()]
			message = f"removes {iter_to_str(removed)}"
			if uncovered:
				message += f", revealing {iter_to_str(uncovered)}"
			message += "."

		if uncovered_feats:
			self.obj.features._cache()

		return message

	def clear(self):
		"""Remove ALL worn clothing"""
		for obj in self._data:
			self.remove(obj, save=False)
		self._save()

	def can_add(self, obj):
		"""
		Checks whether the object can be worn.
		"""
		if obj in self._data:
			return True

		clothing_type = obj.tags.get(category=_CLOTHING_TAG_CATEGORY)
		if not clothing_type:
			self.obj.msg("You can't wear that.")
			return False

		# Enforce overall clothing limit.
		if _CLOTHING_TOTAL_LIMIT and len(self._data) >= _CLOTHING_TOTAL_LIMIT:
			self.obj.msg("You can't wear anything else.")
			return False

		if clothing_type in _CLOTHING_TYPE_LIMITS:
			if self.count_type(clothing_type) >= _CLOTHING_TYPE_LIMITS[clothing_type]:
				self.obj.msg("You can't wear any more of those.")
				return False

		return True

	def can_remove(self, obj):
		obj_list = make_iter(obj)
		if not (removable := [ob for ob in obj_list if ob in self.all]):
			self.obj.msg(f"You aren't wearing {'that' if len(removable) == 1 else 'those'}.")
			return False

		if not (removable := [ ob for ob in removable if not ob.effects.has(name='covered') ]):
			self.obj.msg(f"{'That' if len(removable) == 1 else 'Those'} are currently covered by something else.")
			return False
		return removable

	def can_cover(self, to_cover, cover_with):
		# check if clothing already covered
		if to_cover.db.covered_by:
			self.obj.msg("Your %s is already covered by %s." % (to_cover.sdesc.get(), numbered_name(to_cover.db.covered_by.sdesc.get(),1)))
			return False

		# check if the covering item can cover things
		if not cover_with.tags.has(category=_CLOTHING_TAG_CATEGORY):
			self.obj.msg("Your %s isn't clothes." % cover_with.sdesc.get())
			return False
		if True in cover_with.tags.has([], category=_CLOTHING_TAG_CATEGORY, return_list=True):
			self.obj.msg("You can't cover anything with %s." % numbered_name(cover_with.sdesc.get(),1))
			return False
		if to_cover == cover_with:
			self.obj.msg("You can't cover an item with itself.")
			return False
		if cover_with.db.covered_by:
			self.obj.msg("Your %s is covered by %s." % (cover_with.sdesc.get(), numbered_name(cover_with.db.covered_by.sdesc.get(),1)))
			return False

		return True

	def count_type(self, type):
		count = 0
		for obj in self._data:
			if obj.tags.has(type, category=_CLOTHING_TAG_CATEGORY):
				count += 1

		return count

	def get_outfit(self, looker=None, sorted=True):
		"""
		Returns the appearance of all worn and visible clothing items.

		Args:
			sorted (bool): Whether or not the resulting list is sorted by _LAYERS_ORDER

		Returns:
			list of strings
		"""
		# sort the worn objects by the order options
		if sorted and _CLOTHING_TYPE_ORDER:
			obj_dict = {}
			extra = []
			for obj in self.visible(looker):
				# separate visible clothing by type, for sorting
				type = obj.tags.get(category=_CLOTHING_TAG_CATEGORY)
				if type in _CLOTHING_TYPE_ORDER:
					if type in obj_dict:
						obj_dict[type].append(obj)
					else:
						obj_dict[type] = [obj]
				else:
					extra.append(obj)
			obj_list = []
			# add the clothing objects in the type order
			for type in _CLOTHING_TYPE_ORDER:
				if type in obj_dict:
					obj_list += obj_dict[type]
			# anything not specified in the order list goes at the end
			obj_list += extra
		else:
			obj_list = self.visible()
		# get the actual appearances
		appearance_list = []
		erase_list = []
		for obj in obj_list:
			try:
				appearance = obj.get_worn_desc()
				if appearance in appearance_list:
					if appearance not in erase_list:
						erase_list.append(appearance)
					appearance = obj.get_worn_desc(plural=True)
					# this is garbage, but, makes sure the counts come out right
					if appearance not in appearance_list:
						appearance_list.append(appearance)
			except:
				# fallback to allow other classes of objects to be worn
				appearance = numbered_name(obj.sdesc.get(),1)
				if wearstyle := obj.db.worn:
					appearance = f"{appearance} {wearstyle}"
				if appearance in appearance_list + erase_list:
					if appearance not in erase_list:
						erase_list.append(appearance)
					appearance = INFLECT.plural(obj.sdesc.get())
					# this is garbage, but, makes sure the counts come out right
					if appearance not in appearance_list:
						appearance_list.append(appearance)

			appearance_list.append(appearance)

		appearance_list = [appearance for appearance in appearance_list if appearance not in erase_list]
		counts = Counter(appearance_list)

		appearance_list = [ numbered_name(desc, count, pair=True, pluralize=False) for desc, count in counts.items() ]
		return appearance_list