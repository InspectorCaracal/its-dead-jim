from collections import Counter, defaultdict
from evennia.utils.utils import iter_to_str
from random import randint

from utils.strmanip import isare, numbered_name


class DecorHandler:

	def __init__(self, obj):
		self.obj = obj
		self._load()
	
	def _load(self):
		self._desc = None
		self.decor_list = []
		self.decor_dict = defaultdict(list)
		
		decor_candidates = self.obj.get_all_contents()
		if self.obj.location:
			decor_candidates += self.obj.location.get_all_contents()
		if self.obj.baseobj != self.obj:
			decor_candidates += self.obj.baseobj.get_all_contents()
		for obj in decor_candidates:
			if obj in self.decor_list:
				continue
			if self.obj in obj.attributes.get('wearing', [], category='systems'):
				position = obj.db.pose or obj.db.pose_default
				self.decor_dict[position].append(obj)
				self.decor_list.append((obj, position))

	def all(self):
		# grab just the objects
		return list([t[0] for t in self.decor_list])
	
	def get(self, obj):
		for tup in self.decor_list:
			if tup[0] == obj:
				return tup

	def add(self, obj, position=None, target=None, cover=False, **kwargs):
		"""
		returns True if the object was successfully placed
		"""
		if target:
			self._desc = None
			return target.decor.add(obj, position=position, cover=cover, **kwargs)

		if cover:
			obj.tags.add('covering', category='systems')
			if hasattr(self.obj, 'size') and obj.size <= self.obj.size:
				self.obj.effects.add("base_systems.effects.effects.CoveredEffect", source=obj)

		if position:
			obj.db.pose = position
		else:
			position = obj.db.pose_default
		

		if tup := self.get(obj):
			# object is already placed and being moved
			self.decor_list.remove(tup)
			self.decor_dict[tup[1]].remove(obj)
			if not self.decor_dict[tup[1]]:
				del self.decor_dict[tup[1]]
		# cover all the relevant decor and parts below it
		# TODO: how do we handle not-covering specific parts?
		if cover:
			for dec, _ in self.decor_list:
				if dec.size <= obj.size:
					dec.effects.add("base_systems.effects.effects.CoveredEffect", source=obj)
		self.decor_list.append((obj, position))
		self.decor_dict[position].append(obj)
		if (decorated := obj.attributes.get('wearing', category='systems')):
			if self.obj not in decorated:
				decorated.append(self.obj)
		else:
			decorated = [self.obj]
		obj.attributes.add('wearing', decorated, category='systems')

		self._desc = None

		return True
	
	def remove(self, obj, target=None, **kwargs):
		"""
		returns True if the object was successfully displaced
		"""
		if target:
			self._desc = None
			return target.decor.remove(obj, **kwargs)
		
		if obj.effects.has(name='covered'):
			# we can't remove it while it's covered
			return False
		if tup := self.get(obj):
			self.obj.effects.remove("base_systems.effects.effects.CoveredEffect", source=obj, stacks="all")
			for dec, _ in self.decor_list:
				if obj != dec:
					dec.effects.remove("base_systems.effects.effects.CoveredEffect", source=obj, stacks="all")
			self.decor_list.remove(tup)
			self.decor_dict[tup[1]].remove(obj)
			if not self.decor_dict[tup[1]]:
				del self.decor_dict[tup[1]]

			del obj.db.pose
			if decorated := obj.attributes.get('wearing', category='systems'):
				decorated = decorated.deserialize()
				decorated.remove(self.obj)
				obj.attributes.add('wearing', decorated, category='systems')
			self._desc = None

			return True
		
		else:
			# check if it's on one of our parts first
			if decorated := obj.attributes.get('wearing', category='systems'):
				decorated = decorated.deserialize()
				decorated_parts = [ob for ob in decorated if ob in self.obj.parts.all()]
				if not decorated_parts:
					return False
				return all([p.decor.remove(obj) for p in decorated_parts])
	
	def desc(self, looker, **kwargs):
		# get all the parts too
		decor_dict = { key: [it for it in val if it.is_visible(looker)] for key, val in self.decor_dict.items() }
		# clean up any positions with only invisible items
		decor_dict = { key: val for key, val in decor_dict.items() if val }
		for p in self.obj.parts.all():
			# TODO: should this use .db.onword? I think no
			key_str = f"on {p.get_display_name(looker, **kwargs)}"
			decor_dict |= { f'{key} {key_str}' if key != 'here' else key_str: val for key, val in p.decor.decor_dict.items() }

		if not self._desc:
			appearance_list = []
			for position, obj_list in decor_dict.items():
				if position != "here" and randint(1,4) == 1:
					form = "{position} {verb} {{{position}}}."
				else:
					form = "{{{position}^}} {verb} {position}."
				desc = form.format(
#						names = list_to_string([numbered_name(*name) for name in name_counts.items()),
						position = position,
						verb = isare(len(obj_list)),
					)
				appearance_list.append(desc[0].upper() + desc[1:])

			self._desc = " ".join(appearance_list) if len(appearance_list) > 0 else None

		if not self._desc:
			# still ain't anything
			return ''

		format_dict = {}
		for position, obj_list in decor_dict.items():
			name_counts = Counter([(obj.get_display_name(looker, article=False), obj.sdesc.get(strip=True)) for obj in obj_list])
			name_counts = list(name_counts.items())
			first_display, first_sdesc = name_counts[0][0]
			first_count = name_counts[0][1]
			first_name =     f"|lclook {first_sdesc.replace(',','')}|lt{numbered_name(first_display, first_count)}|le"
			first_name_cap = f"|lclook {first_sdesc.replace(',','')}|lt{numbered_name(first_display, first_count, cap=True)}|le"
			name_counts = [ (n[0][0], n[0][1], n[1]) for n in name_counts[1:] ]
			names = [ f"|lclook {name[1].replace(',','')}|lt{numbered_name(name[0], name[2])}|le" for name in name_counts ]
			format_dict[position] = iter_to_str( [first_name] + names )
			format_dict[position+"^"] = iter_to_str( [first_name_cap] + names )

		return self._desc.format(**format_dict)