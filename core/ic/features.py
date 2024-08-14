"""
A handler for managing the feature-based appearance of an object.
"""
from evennia.utils import list_to_string, logger, is_iter, make_iter
from evennia.utils.dbserialize import deserialize

#from evennia.utils.ansi import strip_ansi
from utils.colors import strip_ansi
from utils.strmanip import strip_extra_spaces, numbered_name

from switchboard import INFLECT

_FEATURE_ATTR = "features"
_FEATURE_CAT = "systems"

class FeatureError(RuntimeError):
	"""
	Appearance or feature error.
	"""

class FeatureHandler:
	"""
	Saves and returns an object's feature-based appearance.
	"""
	feature_attr = _FEATURE_ATTR

	_feature_str = ""

	def __init__(self, obj, feature_attr=_FEATURE_ATTR):
		"""
		Initialize the handler.
		"""
		self.obj = obj
		self.feature_attr = feature_attr

		if not obj.attributes.has(feature_attr, category=_FEATURE_CAT):
			obj.attributes.add(feature_attr, [], category=_FEATURE_CAT)
		self.load()

	def load(self):
		data = deserialize(self.obj.attributes.get(self.feature_attr, category=_FEATURE_CAT))
		self.feature_strs = {}
		self.unique = { key: val for key, val in data if val.get("unique") }
		self.features = [ (key, val) for key, val in data if not val.get("unique") ]
		self._cache()

	def _cache(self):
		data = list(self.unique.keys())
		for feat in self.features:
			if feat[0] not in data:
				data.append(feat[0])
		self.feature_strs = {}
		# parse the features here
		for feature_key in data:
			if fdesc := self.get(feature_key):
				self.feature_strs[feature_key] = fdesc
		self._feature_str = list_to_string(self.feature_strs.values())

	def save(self):
		data = list(self.unique.items())
		data += self.features
		self.obj.attributes.add(self.feature_attr, data, category=_FEATURE_CAT)
		self._cache()

	@property
	def all(self):
		data = list(self.unique.keys())
		for item in self.features:
			if subtype := item[1].get('subtype'):
				data.append( (item[0], subtype) )
			else:
				data.append( item[0] )
		return data

	@property
	def view(self):
		if not self._feature_str:
			self.load()
		return self._feature_str

	def _to_str(self, feature, feature_data):
		feature_name = feature
		data = {}
		if type(feature_data) is list:
			# we're handling multiple non-unique features of the same type, possibly more than one
			count = 0
			for feature_dict in feature_data:
				# visibility check!
				part_loc = feature_dict.get("location",feature)
				# check if location is a part
				if parts := self.obj.parts.search(part_loc, part=True):
					# the location is a valid part, do we need a subtype
					if stype := feature_dict.get("subtype"):
						# get the right part
						parts = [p for p in parts if p.tags.has(stype, category="subtype")]
					# we have a valid part, check visibility
					if not any(part.is_visible(self.obj) for part in parts):
						# not visible, don't add it
						continue
				count += 1
				for key, val in feature_dict.items():
					if entry := data.get(key):
						if key in ( 'article', 'format', 'unique', 'prefix' ) and entry != val:
							raise FeatureError("Incompatible feature display data. Non-unique features must have matching format values.")
						if type(entry) is list:
							if type(val) is list:
								data[key] += [item for item in val if item not in entry]
							elif val not in entry:
								data[key].append(val)
						else:
							if type(val) is list:
								data[key] = [entry]+[item for item in val if item not in entry]
							elif val != entry:
								data[key] = [entry, val]
					else:
						data[key] = val

		else:
			count = 1
			part_loc = feature_data.get("location", feature)
			# check if location is a part
			if parts := self.obj.parts.search(part_loc):
				# the location is a valid part, do we need a subtype
				if stype := feature_data.get("subtype"):
					# get the right part
					parts = [p for p in parts if p.tags.has(stype, category="subtype")]
				# we have valid parts, check visibility
				if not any(part.is_visible(self.obj) for part in parts):
					# not visible
					return ''
			data = feature_data

		if not data:
			return ''
		# get the appearance of the feature
		article = data.get('article', True)
		if string := data.get('format'):
			# format with key values
			stringable = {key: list_to_string(value) if (type(value) is not str and is_iter(value)) else value for key, value in data.items()}
			string = string.format(**stringable)
		else:
			string = data.get('value', '')
			string = list_to_string(string) if type(string) not in (str, int, float) else string
		string = f"{data['prefix']} {string}" if data.get('prefix') else string
		# add an article if the feature specifies to do so
		# add feature
		if count > 1:
			feature_name = INFLECT.plural_noun(feature_name)
		string = f"{string} {feature_name}"
		string = strip_extra_spaces(string)
		if article and count == 1:
			string = numbered_name(string, count)
		if location := data.get('location'):
			if type(location) is not str:
				location = list_to_string(location)
			if not (feature == location or location.endswith(feature)):
				string += f" on $pron(your) {location}"

		if cqual := data.get('color_quality'):
			if cqual < 5:
				string = strip_ansi(string)

		return string

	def options(self, name):
		"""
		View the possible attributes for different features
		"""
		if feat := self.get(name, as_data=True):
			if type(feat) is list:
				feat = feat[0]
			# feature doesn't have any options
			if not feat.get('format'):
				return None

			# feature has options, get them
			else:
				feature = dict(feat)
				feature.pop('format',None)
				feature.pop('article',None)
				feature.pop('prefix',None)
				feature.pop('unique',None)
				feature.pop('location',None)
				feature.pop('subtype',None)
				return([key for key in feature.keys() if not key.startswith("_")])

		else:
			# feature doesn't exist
			print('no such feature')
			return None
		
	def get(self, name, option=None, default=False, as_data=False, match={}, **kwargs):
		"""
		Returns a formatted string for the feature.
		"""
		if name == "all":
			return self.features + list(self.unique.items()) if as_data else self.view

		# if we just want the whole feature string, check cache
		if not any((match, option, as_data)):
			# if we have a cached version, we can use that
			if res := self.feature_strs.get(name):
				return res

		# check if it's a unique feature
		if feature := self.unique.get(name):
			if option:
				if default:
					return feature.get(f"_default_{option}", feature.get(option))
				return feature.get(option)
			elif as_data:
				return dict(feature)
			else:
				if feature.get('invisible') and not kwargs.get('force'):
					return ''
				if not (res := self.feature_strs.get(name)):
					if res := self._to_str(name, feature):
						self.feature_strs[name] = res
				return res
				
		# check for any matching non-unique features
		matches = []
		for key, feature in self.features:
			if key == name:
				if feature.get('invisible') and not kwargs.get('force'):
					continue
				if all( feature.get(match_key) == match_val for match_key, match_val in match.items()):
					# don't include fallback values
					matches.append({ k: v for k, v in feature.items() })

		if option:
			if default:
				matches = [ feature.get(f"_default_{option}", feature.get(option)) for feature in matches ]
			else:
				matches = [ feature.get(option) for feature in matches ]
		elif not as_data:
			matches = self._to_str(name, matches)

		return matches[0] if len(matches) == 1 else matches

	def set(self, name, soft=False, match={}, distinct=False, save=True, **kwargs):
		"""
		Sets specific values or options
		"""

		def _update_feature(dict_ref):
			for key, value in kwargs.items():
				default_key = f"_default_{key}"
				if soft:
					# save "real" values before doing soft assignment
					if default_key not in dict_ref:
						dict_ref[default_key] = dict_ref[key]
				else:
					# this IS the new default
					if default_key in dict_ref:
						dict_ref[default_key] = value
				dict_ref[key] = value
			return dict_ref


		if feature := self.unique.get(name):
			# it's a unique feature, easy mode
			self.unique[name] = _update_feature(dict(feature))

		else:
			matches = []
			# gotta check for matching features
			for i, data in enumerate(self.features):
				key, feature = data
				if key == name:
					if not match:
						matches.append(i)
					elif all( feature.get(match_key) == match_value for match_key, match_value in match.items()):
						# don't include fallback values
						matches.append(i)
			if not matches:
				raise FeatureError(f"Feature \"{name}\" does not exist on object '{self.obj}', use .add instead.")
			if len(matches) > 1 and distinct:
				raise FeatureError(f"Cannot update feature \"{name}\" - too many matches.")
			for i in matches:
				name, feature = self.features[i]
				self.features[i] = (name, _update_feature(feature))

		if save:
			self.save()
		else:
			self._cache()

	def merge(self, name, soft=False, match={}, distinct=False, save=True, **kwargs):
		"""
		Merges additional values into feature options, or adds a new
		feature if it doesn't exist.
		"""
		unique = kwargs.get("unique")
		if not (matches := self.get(name, match=match, as_data=True)):
			if not soft:
				self.add(name, **kwargs)
				return
			else:
				matches = {}
		elif type(matches) is list and distinct:
			raise FeatureError(f"Cannot update feature \"{name}\" - too many matches.")

		if type(matches) is not list:
			matches = [matches]

		if len(matches) > 1 and unique:
			raise FeatureError(f"Cannot merge unique feature - non-unique features with key {name} exist.")
		
		elif matches:
			if matches[0].get("unique"):
				unique = True

		for feature in matches:
			new_feature = dict(feature)
			if not soft:
				# reset the feature before doing a "hard" merge
				self.reset(name, match=dict(feature))

			for key, value in kwargs.items():
				if key.startswith("_default"):
					continue

				if current := feature.get(key):
					default_key = f"_default_{key}"
					if soft:
						# save "real" values before doing soft merge
						if default_key not in new_feature:
							# logger.log_msg(f"didn't find {default_key}, adding")
							new_feature[default_key] = current
					# reset back to "real" values before hard merge
					if type(current) is not str and is_iter(current):
						if value not in current:
							new_feature[key] += make_iter(value)
					elif value != current:
						new_feature[key] = value
				elif soft:
					# the key doesn't have a default
					default_key = f"_default_{key}"
					new_feature[default_key] = None
					new_feature[key] = value
				else:
					new_feature[key] = value

			if unique:
				self.unique[name] = new_feature
			elif (name, feature) in self.features:
				i = self.features.index((name, feature))
				self.features[i] = (name, new_feature)
			else:
				self.features.append((name, new_feature))

		if save:
			self.save()


	def add(self, name, value=None, format=None, force=False, prefix=None, article=False, save=True, **kwargs):
		if name in self.unique and not force:
			raise FeatureError(f"Unique feature \"{name}\" already exists.")
		feature = { "format": format, "article": article, "prefix": prefix }
		feature |= kwargs
		if value != None:
			feature['value'] = value
		elif not kwargs:
			raise FeatureError("No valid values provided when adding a feature.")

		if kwargs.get("unique"):
			self.unique[name] = feature
		else:
			self.features.append((name, feature))

		if save:
			self.save()
	
	def remove(self, name, match={}, distinct=False, save=True):
		if name in self.unique:
			self.unique.pop(name)
		else:
			matches = []
			# gotta check for matching features
			for i, data in enumerate(self.features):
				key, feature = data
				if key == name:
					if all(feature.get(match_key) == match_value for match_key, match_value in match.items()):
						# don't include fallback values
						matches.append(i)
			if len(matches) > 1 and distinct:
				raise FeatureError(f"Cannot remove feature \"{name}\" - too many matches.")
			elif not matches:
				return
			del self.features[i]

		if save:
			self.save()

	def reset(self, feature="all", match={}, save=True):
		def _reset_feature(dict_ref):
			for key, value in dict(dict_ref).items():
				if key.startswith("_"):
					continue
				default_key = f"_default_{key}"
				if default_key in dict_ref:
					if default_value := dict_ref.get(default_key):
						dict_ref[key] = default_value
					else:
						del dict_ref[key]
					del dict_ref[default_key]
			return dict_ref

		if feature == "all":
			for feature_key, feature_dict in dict(self.unique).items():
				if all( feature_dict.get(mkey) == mval for mkey, mval in match.items() ):
					if post_reset := _reset_feature(dict(feature_dict)):
						self.unique[feature_key] = post_reset
					else:
						del self.unique[feature_key]
			for i, data in enumerate(self.features):
				if all( data[1].get(mkey) == mval for mkey, mval in match.items() ):
					post_reset = _reset_feature(data[1])
					self.features[i] = (data[0], post_reset)
			self.features = [ item for item in self.features if item[1] ]

		elif feature in self.unique:
			if post_reset := _reset_feature(self.unique[feature]):
				self.unique[feature] = post_reset
			else:
				self.unique.pop(feature)

		else:
			matches = []
			# gotta check for matching features
			for i, data in enumerate(self.features):
				if data[0] == feature:
					if all(data[1].get(match_key) == match_value for match_key, match_value in match.items()):
						# don't include fallback values
						matches.append((i, data[1]))
			if len(matches) > 1:
				raise FeatureError(f"Cannot reset feature \"{feature}\" - too many matches.")
			elif not matches:
				return
			match = matches[0]
			feature_dict = _reset_feature(match[1])
			if not feature_dict:
				del self.features[match[0]]
			else:
				self.features[match[0]] = (feature, feature_dict)

		if save:
			self.save()

	def clear(self):
		self.unique = {}
		self.features = []
		self.save()
