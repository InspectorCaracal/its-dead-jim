from collections import defaultdict
from evennia import DefaultObject
from evennia.utils import iter_to_str, interactive, make_iter, logger
from evennia.utils.dbserialize import deserialize, pack_dbobj

from utils.handlers import HandlerBase

_PARTS_ATTR = "parts"
_PARTS_CAT = "systems"

class PartsCacher:
	"""
	Handles and caches the contents of an object to avoid excessive
	lookups (this is done very often due to cmdhandler needing to look
	for object-cmdsets). It is stored on the 'contents_cache' property
	of the ObjectDB.
	"""

	def __init__(self, obj):
		"""
		Sets up the contents handler.

		Args:
			obj (Object):  The object on which the
				handler is defined

		Notes:
			This was changed from using `set` to using `dict` internally
			in order to retain insertion order.

		"""
		self.obj = obj
		self._pkcache = {}
		self._pkdirect = {}
		self._idcache = obj.__class__.__instance_cache__
		self._typecache = defaultdict(dict)
		self.init()

	def load(self):
		"""
		Retrieves all objects from database. Used for initializing.

		Returns:
			Objects (list of ObjectDB)
		"""
		everything = DefaultObject.objects.all_family()

		direct = list(obj for obj in everything if obj != self.obj and obj.partof == self.obj)
		objects = list(obj for obj in everything if obj != self.obj and obj.baseobj == self.obj)
		return objects+direct, direct

	def init(self):
		"""
		Re-initialize the content cache

		"""
		objects, direct = self.load()
		self._pkcache = {obj.pk: obj for obj in objects}
		self._pkdirect = {obj.pk: obj for obj in direct}

	def get(self, direct=False):
		"""
		Return the contents of the cache.

		Keyword Args:
			direct (bool): Return only objects directly attached to owner

		Returns:
			objects (list): the Objects that are a part of this

		"""
		pks = self._pkdirect.keys() if direct else self._pkcache.keys()
		try:
			return [self._idcache[pk] for pk in pks]
		except KeyError:
			# this can happen if the idmapper cache was cleared for an object
			# in the contents cache. If so we need to re-initialize and try again.
			self.init()
			try:
				return [self._idcache[pk] for pk in pks]
			except KeyError:
				# this means an actual failure of caching. Return real database match.
				logger.log_err("parts cache failed for %s." % self.obj.key)
				oblist, dirlist = self.load()
				return dirlist if direct else oblist

	def add(self, obj):
		"""
		Add a new object to this location

		Args:
			obj (Object): object to add

		"""
		self._pkcache[obj.pk] = obj
		if obj.partof == self.obj:
			self._pkdirect[obj.pk] = obj

	def remove(self, obj):
		"""
		Remove object from this location

		Args:
			obj (Object): object to remove

		"""
		pk = obj.pk
		self._pkcache.pop(pk, None)
		self._pkdirect.pop(pk, None)

	def clear(self):
		"""
		Clear the contents cache and re-initialize

		"""
		self._pkcache = {}
		self._typecache = defaultdict(dict)
		self.init()


class PartsHandler(HandlerBase):
	# TODO: remove buff mods from parts that they're inheriting from being attached to the base
	# it's tricky because we don't want to remove mods that were applied directly to the parts

	@property
	def missing(self):
		if not hasattr(self, "_missing"):
			parts = self.obj.parts_cache.get()
			missing = []
			for val in self.required:
				if not any([obj.tags.has(val, category='part') for obj in parts]):
					missing.append(val)
			self._missing = missing
		
		return self._missing

	@property
	def external(self):
		if not hasattr(self, "_external"):
			parts = self.obj.parts_cache.get()
			external = []
			for obj in parts:
				if obj.tags.has('external', category='attach_type'):
					external.append(obj)
			self._external = external
		
		return self._external


	def __init__(self, obj, *args, **kwargs):
		super().__init__(obj, _PARTS_ATTR, _PARTS_CAT)
	
	def _load(self):
		super()._load()
		self.required = self._data.get('required',[])
		self.allowed = self._data.get('allowed')
		# reset the cached lists
		if hasattr(self, '_missing'):
			del self._missing
		if hasattr(self, '_external'):
			del self._external

	def _save(self):
		self._data = { "required": self.required, "allowed": self.allowed }
		super()._save()

	def all(self):
		"""
		Return a list of ALL attached objects.
		"""
		return self.obj.parts_cache.get()

	def attached(self):
		"""
		Return a list of all objects that are directly attached to the owning object.
		"""
		return self.obj.parts_cache.get(direct=True)

	def attach(self, obj, part=None, **kwargs):
		"""
		Attaches the object.

		If part is None, attaches directly to self.obj
		Otherwise, checks that part is attached and if so, attaches to it

		Returns True if the object was attached, False if it was not.
		"""
		if part and part != self.obj:
			if part not in self.all():
				return False
		else:
			part = self.obj

		try:
			obj.partof = part
		except RuntimeError as e:
			return False
		
		for ob in obj.attributes.get('_parts_chain', [], category='systems'):
			self.obj.parts_cache.add(ob)

		features = obj.features.get("all", as_data=True)
		for key, vals in features:
			newval = dict(vals) | { 'location': obj.key }
			self.obj.features.merge(key, **newval, soft=True)

		# reset the cached lists
		if hasattr(self, '_missing'):
			del self._missing
		if hasattr(self, '_external'):
			del self._external

		# attach was successful!
		return True
	
	def link(self, obj, part=None):
		"""
		Connects the object at the end of any "chained" objects.
		If there are no chained objects, this objects begins a chain.

		If part is None, creates a chain directly on self.obj
		Otherwise, checks that part is attached and if so, joins it or creates a new chain from it

		Returns True if the object was attached, False if it was not.
		"""
		if not part:
			part = self.obj

		# attach the part normally first
		if not self.attach(obj, part=part):
			return False

		if not part.tags.has("chain", category="systems"):
			# create a new chain with this object
			obj.tags.add("chain", category="systems")
			if not obj.attributes.has("_parts_chain", category="systems"):
				obj.attributes.add("_parts_chain", [], category="systems")
			return True

		else:
			if not (chain := part.attributes.get("_parts_chain", category="systems")):
				part.attributes.add("_parts_chain", [], category="systems")
				chain = part.attributes.get("_parts_chain", category="systems")

			if obj in chain:
				# it's already attached!
				return False
			chain.append(obj)
			return True


	def unlink(self, obj, location=None, quiet=False):
		"""
		Split a chain at obj, with obj as the head of the new chained piece
		"""
		# make sure links happen to the relevant part
		base = obj.baseobj
		if base == obj:
			return False
		if base != self.obj:
			return base.parts.unlink(obj, location=location, quiet=quiet)

		if obj not in self.all():
			return False

		# chains can only be in a chain container
		source = obj.partof
		if not source.tags.has("chain", category="systems"):
			return False
		if not (chain := source.attributes.get("_parts_chain", category="systems")):
			return False
		
		if obj in chain:
			i = chain.index(obj)
			# split the chain
			if tail := source.parts._split_chain(i):
				return self.detach(tail, location=location, quiet=quiet)
			else:
				# something went wrong
				return False
		else:
			return False
	
	def _split_chain(self, i):
		"""
		Split chained parts into two, at index i

		Returns the new chain part, or None if the split failed
		"""
		if not (chain := self.obj.attributes.get("_parts_chain", category="systems")):
			# there is no chain to split
			return None

		if i >= len(chain) or i < 0:
			# cannot split outside the length of the chain
			return None

		first = chain[:i]
		second = chain[i:]

		if not first:
			# the entire chain is being detached
			if len(second) == 1:
				# we only have one object, just return it
				return second[0]
			else:
				# return ourself as-is
				return self.obj
		
		if "part of" not in self.obj.sdesc.get():
			# FIXME: make this work properly wihout overriding existing prefixes
			self.obj.db._sdesc_prefix = "part of"

		self.obj.attributes.add("_parts_chain", first, category="systems")
		if len(second) == 1:
			# the segment being removed is only one part
			return second[0]

		chain_copy = self.obj.copy(new_key=self.obj.key)
		chain_copy.attributes.add("_parts_chain", second, category="systems")
		self.obj.baseobj.parts_cache.add(chain_copy)
		for obj in second:
			obj.partof = chain_copy
		return chain_copy

	def _clean_chain(self):
		if not (chain := self.obj.attributes.get("_parts_chain", category="systems")):
			return
		for i in range(len(chain)-1, -1, -1):
			if chain[i] == None:
				if i > 0:
					del chain[i]
					if (removed := self._split_chain(i)):
						self.obj.baseobj.parts.detach(removed)
				elif len(chain) == 2:
					self.detach(chain[1])
					self.obj.delete()
				else:
					self.obj.attributes.add("_parts_chain", chain[1:], category="systems")
					if self.obj.baseobj != self.obj:
						self.obj.baseobj.parts.detach(self.obj)


	def detach(self, obj, clean=False, location=None, quiet=False, delete=False):
		"""
		Detaches the object.

		Returns True if the object was removed, False if it was left attached, and None if it wasn't attached in the first place.
		"""
		if not obj and not clean:
			return False

		fall = False
		base = obj.baseobj
		source = obj.partof
		if not location:
			location = base.location
			fall = True

		if clean:
			direct = obj.parts_cache.get(direct=True)
			if not all( [self.detach(ob, location=location, quiet=quiet) for ob in direct] ):
				return False

		if obj not in self.all():
			return False

		if location == base.location:
			fall = True

		try:
			del obj.partof
		except RuntimeError:
			return False

		if not obj.move_to(location, quiet=True):
			# move failed
			return False
		
		decache = obj.attributes.get("_parts_chain", [], category="systems")
		# take our chain with us
		for ob in decache:
			base.parts_cache.remove(ob)
			source.parts_cache.remove(obj)
		
		base.features.reset(match={'location': obj.key})
		# make sure to break any link as well
		if chain := source.attributes.get("_parts_chain", category="systems"):
			if obj in chain:
				i = chain.index(obj)
				chain[i] = None
				source.parts._clean_chain()
		# this kinda sucks
		if not delete and fall and not quiet:
			obj.emote(f'falls from @{base.sdesc.get(strip=True)}.', action_type="move")

		# reset the cached lists
		if hasattr(self, '_missing'):
			del self._missing
		if hasattr(self, '_external'):
			del self._external

		# detach was successful!
		# if this is a virtual container, make sure to clean up if empty
		# TODO: remove this once the virtual container typeclass is working
		if source.tags.has("virtual_container", category="systems"):
			if not self.all():
				source.delete()

		return True

	def search(self, search_term, part=False):
		candidates = self.all()
		if part:
			obj_list = [ obj for obj in candidates if obj.tags.has(search_term, category='part')]
		else:
			obj_list = self.obj.search(search_term, candidates=candidates, quiet=True)
		return obj_list
