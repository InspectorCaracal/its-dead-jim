"""
See core contrib for docs
"""
from evennia.utils.dbserialize import deserialize
from evennia.utils.utils import is_iter, iter_to_str

from utils.strmanip import strip_extra_spaces
from utils.colors import strip_ansi

_VOICE_PARTS = ["quality", "style", "voice"]

class SdescError(Exception):
	pass

class RecogError(Exception):
	pass


# TODO: this needs to be updated to dynamically load changed feature attributes again

class SdescHandler:
	"""
	This Handler wraps all operations with sdescs.
	"""
	def __init__(self, obj):
		"""
		Initialize the handler

		Args:
			obj (Object): The entity on which this handler is stored.

		"""
		self.obj = obj
		self.base_dict = None
		self._load()

	def _load(self):
		"""
		Cache data from storage
		"""
		# TODO: figure out how to make this only 2 attribute fetches, maybe?
		self.sdesc = None
		self.slist = deserialize(self.obj.attributes.get("_sdesc_list",[], category="systems"))
		self.base_dict = deserialize(self.obj.attributes.get("build",{}, category="systems"))
		self._prefix = self.obj.attributes.get("_sdesc_prefix","")

	def add(self, desc_list, **kwargs):
		"""
		Args:
			desc_list (list): list of attribute keys

		Returns:
			sdesc (str): The sdesc as it will appear.

		Raises:
			SdescError: If `desc_list` includes invalid keys.

		"""
		# validate
		for desc_key in desc_list:
			if not desc_key:
				raise SdescError("Cannot include empty items in sdesc.")
			if desc_key in self.base_dict.keys():
				continue
			parts = desc_key.split()
			if self.obj.features.get(*parts):
				continue
			else:
				raise SdescError(f"Invalid feature key {desc_key}")
		sdesc_list = [ f"{{{item}}}" for item in desc_list ]

		# store to attributes
		self.obj.attributes.add("_sdesc_list", sdesc_list, category="systems")
		self.update()

		return self.get()

	def update(self):
		self._load()
		if self.slist:
			# get necessary features
			format_dict = {}
			slist = list(self.slist)
			for skey in slist:
				key = skey[1:-1]
				if key in self.base_dict:
					# not a feature
					continue
				parts = key.split()
				if val := self.obj.features.get(*parts):
					if is_iter(val):
						val = iter_to_str(set(val))
					if parts[0] == 'build':
						strn = val
					elif parts[0] not in ("fur", "hide"):
						strn = f"{val}-{parts[0]}"
						if strn[-1] == 's':
							strn = strn[:-1]
						if strn[-1] == 'n' and not strn.endswith("horn"):
							strn += 'n'
						if strn[-2:] != 'ed':
							strn += "d" if strn[-1] == "e" else "ed"
					else:
						strn = val
					format_dict[key] = strn
				else:
					# something went wrong so we'll use an empty string as fallback
					format_dict[key] = ""

			if self.base_dict:
				format_dict |= self.base_dict

			sdesc = " ".join(slist)
			sdesc = strip_extra_spaces(sdesc.format(**format_dict)) or self.obj.name
		else:
			sdesc = self.obj.name
		
		if self._prefix:
			sdesc = f"{self._prefix} {sdesc}" 
		self.sdesc = sdesc


	def get(self, viewer=None, strip=False, **kwargs):
		"""
		gaaaaaaaaaaaaaaaahhhhhhhhhhhh
		"""
		# if not self.sdesc:
		# 	self.update()
		self.update() # FIXME
		return strip_ansi(self.sdesc) if strip else self.sdesc


class VdescHandler:
	"""
	This Handler wraps all operations with sdescs. We
	need to use this since we do a lot preparations on
	sdescs when updating them, in order for them to be
	efficient to search for and query.

	The handler stores data in the following Attributes

		_sdesc   - a string
	"""
	def __init__(self, obj):
		"""
		Initialize the handler

		Args:
			obj (Object): The entity on which this handler is stored.

		"""
		self.obj = obj
		self._cache()

	def _cache(self):
		"""
		Cache data from storage
		"""
		self.data = deserialize(self.obj.attributes.get("_vdescs",{}))

	def add(self, vkey, value, **kwargs):
		"""
		Args:
			vkey (str): which portion of the voice is being set
			value (str): what the new value should be

		Returns:
			vdesc (str): The vdesc as it will appear.

		Raises:
			SdescError: If vkey is an invalid key, or if there are too many.

		"""
		# validate
		if vkey not in self.data and vkey not in _VOICE_PARTS:
			raise SdescError(f"Invalid voice feature {vkey}")
		if len(self.data.keys()) < 3:
			self.data[vkey] = str(value)
			# store to attributes
			self.obj.attributes.add("_vdescs", self.data)
		else:
			raise SdescError(f"Maximum voice features reached: {' '.join(self.data.keys())}")

		return self.get()

	def get(self, viewer=None, strip=False, **kwargs):
		if not self.data:
			return None
		else:
			sdesc = " ".join(self.data.values())

		return strip_ansi(sdesc) if strip else sdesc


class RecogHandler:
	"""
	This handler manages the recognition mapping
	of an Object.

	The handler stores data in Attributes as dictionaries of
	the following names:

		_recog_ref2recog
		_recog_obj2recog

	"""

	def __init__(self, obj):
		"""
		Initialize the handler

		Args:
			obj (Object): The entity on which this handler is stored.

		"""
		self.obj = obj
		# mappings
		if not obj.attributes.has("recogs", category="systems"):
			obj.attributes.add("recogs", {}, category="systems")
		self._cache()

	def _cache(self):
		"""
		Load data to handler cache
		"""
		self.obj2recog = self.obj.attributes.get("recogs", category="systems").deserialize()

	def _save(self):
		self.obj.attributes.add("recogs", self.obj2recog, category="systems")

	def add(self, obj, recog, max_length=60):
		"""
		Assign a custom recog (nick) to the given object.

		Args:
			obj (Object): The object ot associate with the recog
				string. This is usually determined from the sdesc in the
				room by a call to parse_sdescs_and_recogs, but can also be
				given.
			recog (str): The replacement string to use with this object.
			max_length (int, optional): The max length of the recog string.

		Returns:
			recog (str): The (possibly cleaned up) recog string actually set.

		Raises:
			SdescError: When recog could not be set or sdesc longer
				than `max_length`.

		"""
		if not obj.access(self.obj, "enable_recog", default=True):
			raise SdescError("This person is unrecognizeable.")

		# make an recog clean of ANSI codes
		cleaned_recog = strip_ansi(recog)

		if not cleaned_recog:
			raise SdescError("Recog string cannot be empty.")

		if len(cleaned_recog) > max_length:
			raise RecogError(
				"Recog string cannot be longer than {} chars (was {} chars)".format(max_length, len(cleaned_recog))
			)

		# mapping #dbref:obj
		self.obj2recog[obj] = cleaned_recog
		return cleaned_recog

	def get(self, obj):
		"""
		Get recog replacement string, if one exists.

		Args:
			obj (Object): The object, whose sdesc to replace
		Returns:
			recog (str or None): The replacement string to use, or
				None if there is no recog for this object.

		Notes:
			This method will respect a "enable_recog" lock set on
			`obj` (True by default) in order to turn off recog
			mechanism. This is useful for adding masks/hoods etc.
		"""
		if not obj:
			return None
		if obj.access(self.obj, "enable_recog", default=True):
			# check an eventual recog_masked lock on the object
			# to avoid revealing masked characters. If lock
			# does not exist, pass automatically.
			return self.obj2recog.get(obj, None)
		else:
			# recog_mask lock not passed, disable recog
			return None

	def all(self):
		"""
		Get a mapping of the recogs stored in handler.

		Returns:
			recogs (dict): A mapping of {recog: obj} stored in handler.

		"""
		return {self.obj2recog[obj]: obj for obj in self.obj2recog.keys()}

	def remove(self, obj):
		"""
		Clear recog for a given object.

		Args:
			obj (Object): The object for which to remove recog.
		"""
		if obj in self.obj2recog:
			del self.obj2recog[obj]
			self._save()
