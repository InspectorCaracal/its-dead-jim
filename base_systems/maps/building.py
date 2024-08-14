from collections import defaultdict
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.tags import Tag
from evennia.utils.search import search_tag, search_script_tag
from evennia.utils.create import create_object, create_script
from evennia.utils import logger, is_iter

def get_obj_family(obj, **kwargs):
	"""
	Get the "family" of the object: character, room, exit, or thing
	"""
	families = {
		"character": "base_systems.characters.base.Character",
		"room": "base_systems.rooms.base.Room",
		"exit": "base_systems.exits.base.Exit",
		"thing": "base_systems.things.base.Thing",
		"meta": "base_systems.meta.base.MetaThing",
		"script": "core.scripts.Script",
	}

	obj_mro = obj.__class__.mro()
	for key, path in families.items():
		if any( hasattr(cls, "path") and cls.path == path for cls in obj_mro ):
			return key
	return None

def gen_zone_ids(zone, caller):
	obj_list = list(search_tag(zone, category="zone")) + list(search_script_tag(zone, category="zone"))
	if not obj_list:
		caller.msg(f"There is nothing in zone {zone}; removing it.")
		_ = list(Tag.objects.filter(db_key=zone, db_category="zone").delete())
		return

	obj_sorted = defaultdict(list)
	for obj in obj_list:
		match get_obj_family(obj):
			case "character":
				prefix = "C"
			case "room":
				prefix = "R"
			case "exit":
				prefix = "X"
			case "thing":
				prefix = "O"
			case "meta":
				prefix = "M"
			case "script":
				prefix = "S"
			case _:
				caller.msg(f"ID generation for {zone} failed: {obj} #{obj.id} is not a valid ID-able object.")
				raise ValueError(f"{obj} #{obj.id} is not a valid ID-able object.")
		obj_sorted[prefix].append(obj)

	for key, objs in obj_sorted.items():
		has_id = []
		needs_id = []
		prefix = key+zone
		for obj in objs:
			if obj.uid:
				has_id.append(obj)
			else:
				needs_id.append(obj)
		i = len(has_id)
		for obj in needs_id:
			while get_by_uid(f"{prefix}{i}"):
				i += 1
			obj.uid = f"{prefix}{i}"
			i += 1
		if i > len(objs):
			logger.log_warn(f"UID gaps in {prefix}. Total objects: {len(objs)} vs max subscript: {i} - was something deleted?")

	caller.msg(f"UIDs generated for all parts of zone {zone}.")


def update_or_create_object(uid, **kwargs):
	"""
	Updates an existing object with the given unique ID, or creates one.

	Args:
		uid (str): the unique identifier for this object
	
	Keyword args:
		(any): any keywords which `create_object` can take

	Returns:
		obj (Object): the object for uid
	"""
	if obj := get_by_uid(uid):
		obj = update_object(obj, **kwargs)
	else:
		cmdset = kwargs.pop('cmdset', None)
		attrs = kwargs.get('attributes', []) + [("uid", uid, "systems")]
		kwargs['attributes'] = attrs
		if key := kwargs.pop('name',None):
			kwargs['key'] = key
		if desc := kwargs.pop('desc', None):
			kwargs['attributes'].append( ('desc', desc) )
		if loc := kwargs.get('location'):
			kwargs['location'] = get_by_id(loc)
		if dest := kwargs.get('destination'):
			kwargs['destination'] = get_by_id(dest)
		if home := kwargs.get('home'):
			kwargs['home'] = get_by_id(home)

		obj = create_object(**kwargs)
		if cmdset:
			obj.cmdset_storage = cmdset
	return obj


def update_or_create_script(uid, **kwargs):
	"""
	Updates an existing script with the given unique ID, or creates one.

	Args:
		uid (str): the unique identifier for this script
	
	Keyword args:
		(any): any keywords which `create_script` can take

	Returns:
		script (Script): the object for uid
	"""
	# we know by this point that all objects HAVE been made
	# so we can deref the script's object if there is one
	if 'obj' in kwargs:
		kwargs['obj'] = deref_uids(kwargs['obj'])
	if script := get_by_uid(uid):
		script = update_script(script, **kwargs)
	else:
		attrs = kwargs.get('attributes', []) + [("uid", uid, "systems")]
		kwargs['attributes'] = attrs
		if key := kwargs.pop('name',None):
			kwargs['key'] = key
		if desc := kwargs.pop('desc', None):
			kwargs['attributes'].append( ('desc', desc) )

		script = create_script(**kwargs)
	return script

def get_by_id(dbref_or_uid):
	if obj := ObjectDB.objects.get_id(dbref_or_uid):
		return obj
	return get_by_uid(dbref_or_uid)

def get_by_uid(uid):
	"""
	Finds an existing object with the given unique ID.

	Args:
		uid (str): the unique identifier for this object

	Returns:
		obj or None: the matching object for the UID, or None

	Raises:
		KeyError: If there are somehow multiple objects with the UID 
	"""
	candidates = ObjectDB.objects.filter(
			db_attributes__db_key="uid", db_attributes__db_category="systems", db_attributes__db_value=uid
		)
	candidates = list(candidates) + list(ScriptDB.objects.filter(
			db_attributes__db_key="uid", db_attributes__db_category="systems", db_attributes__db_value=uid
		))
	print(candidates)
	match len(candidates):
		case 1:
			return candidates[0]
		case 0:
			return None
		case _:
			raise KeyError(f"Too many objects match {uid}! dbrefs for the matches: {' '.join(str(ob.id) for ob in candidates)}")


def deref_uids(value):
	"""
	Replace any UIDs with an object reference.
	"""
	# def _unpack_uid(obj):
	# 	if isinstance(value, str):
	# 		if value.startswith('uid#'):
	# 			_, uid = value.split('#', maxsplit=1)
	# 			return get_by_uid(uid)
	# 	return obj

	# print(f"dereferencing uids in {value}")

	if isinstance(value, str):
		if value.startswith('uid#'):
			_, uid = value.split('#', maxsplit=1)
			return get_by_uid(uid)
			print(get_by_uid(uid))
			return value
		
	if hasattr(value, 'deserialize'):
		value = value.deserialize()
	
	if isinstance(value, dict):
		new_val = {}
		for key, val in value.items():
			new_val[deref_uids(key)] = deref_uids(val)
		return new_val
		print(new_val)
		return value

	if is_iter(value):
		cls = type(value)
		return cls(deref_uids(val) for val in value)
		print(cls(deref_uids(val) for val in value))
		return value

	return value


def ref_uids(value):
	"""
	Parse an object looking for any UID'd database objects
	"""
	def _flatten_uid(obj):
		if hasattr(obj, 'uid'):
			return f"uid#{obj.uid}"
		return obj

	if hasattr(value, 'deserialize'):
		value = value.deserialize()

	if hasattr(value, 'uid'):
		return f"uid#{value.uid}"
	
	if isinstance(value, dict):
		new_val = {}
		for key, val in value.items():
			new_val[_flatten_uid(key)] = ref_uids(val)
		
		return new_val

	if is_iter(value):
		cls = type(value)
		try:
			return cls(ref_uids(val) for val in value)
		except TypeError as e:
			print(cls)
			raise TypeError(e)
	
	return value


def update_object(obj, reset=False, **kwargs):
	"""
	Updates the data for obj.

	Args:
		obj (Object): The object to update.

	Keyword args:
		any keywords available to create_object
	
	Returns:
		obj (Object): the object
	"""
	if typeclass := kwargs.get('typeclass'):
		if reset or typeclass != obj.typeclass_path:
			obj.swap_typeclass(typeclass)
	
	if cmdset := kwargs.get('cmdset'):
		obj.cmdset_storage = cmdset

	if (key := kwargs.get('key')) or (key := kwargs.get('name')):
		obj.key = str(key)

	if desc := kwargs.get('desc'):
		obj.db.desc = str(desc)
	elif reset:
		obj.db.desc = None

	if home := kwargs.get('home'):
		if type(home) in (str, int):
			home = get_by_id(home)
		obj.home = home
	
	if location := kwargs.get('location'):
		if type(location) in (str, int):
			location = get_by_id(location)
		obj.location = location
	elif reset:
		obj.location = None

	if destination := kwargs.get('destination'):
		if type(destination) in (str, int):
			destination = get_by_id(destination)
		obj.destination = destination
	elif reset:
		obj.destination = None

	if attrs := kwargs.get('attributes'):
		attrs = [ (key, deref_uids(val), cat) for key, val, cat in attrs ]
		obj.attributes.batch_add(*attrs) if len(attrs) > 1 else obj.attributes.add(*attrs[0])
	elif reset:
		obj.attributes.clear()
	
	if tags := kwargs.get('tags'):
		obj.tags.batch_add(tags) if len(tags) > 1 else obj.tags.add(*tags[0])
	elif reset:
		obj.tags.clear()

	if aliases := kwargs.get('aliases'):
		obj.aliases.batch_add(aliases) if len(aliases) > 1 else obj.aliases.add(aliases[0])
	elif reset:
		obj.tags.clear()

	return obj

def update_script(script, reset=False, **kwargs):
	"""
	Updates the data for script.

	Args:
		script (Script): The script to update.

	Keyword args:
		any keywords available to create_script
	
	Returns:
		script (Script): the object
	"""
	if typeclass := kwargs.get('typeclass'):
		if reset or typeclass != script.typeclass_path:
			script.swap_typeclass(typeclass)
	
	if (key := kwargs.get('key')) or (key := kwargs.get('name')):
		script.key = str(key)

	if desc := kwargs.get('desc'):
		script.db.desc = str(desc)
	elif reset:
		script.db.desc = None

	if obj := kwargs.get('obj'):
		if type(obj) in (str, int):
			obj = get_by_id(obj)
		script.obj = obj
	
	if attrs := kwargs.get('attributes'):
		attrs = [ (key, deref_uids(val), cat) for key, val, cat in attrs ]
		script.attributes.batch_add(*attrs) if len(attrs) > 1 else script.attributes.add(*attrs[0])
	elif reset:
		script.attributes.clear()
	
	if tags := kwargs.get('tags'):
		script.tags.batch_add(tags) if len(tags) > 1 else script.tags.add(*tags[0])
	elif reset:
		script.tags.clear()

	return script


def write_object_creation(obj, file):
	"""
	Renders the object in the context of calling `update_or_create_object`
	"""
	data = {}
	uid = obj.uid
	data['typeclass'] = obj.typeclass_path
	data['name'] = obj.name
	data['desc'] = obj.db.desc
	data['home'] = obj.home.uid
	if obj.location:
		data['location'] = obj.location.uid
	if obj.destination:
		data['destination'] = obj.destination.uid
	if attrs := obj.attributes.all():
		data['attributes'] = [ (attr.key, ref_uids(attr.value), attr.category) for attr in attrs ]
	if nattrs := obj.nattributes.all():
		data['nattributes'] = { nattr.key: ref_uids(nattr.value) for nattr in nattrs }
	if aliases := obj.aliases.all():
		data['aliases'] = aliases
	if tags := obj.tags.all(return_key_and_category=True):
		data['tags'] = tags
	data['locks'] = str(obj.locks)
	if cmdset := obj.cmdset_storage:
		data['cmdset'] = cmdset

	file.write(f"data = {data}\n")
	file.write(f"obj = update_or_create_object('{uid}', **data)\n")


def write_script_creation(script, file):
	"""
	Renders the object in the context of calling `update_or_create_script`
	"""
	data = {}
	uid = script.uid
	data['typeclass'] = script.typeclass_path
	data['name'] = script.name
	data['desc'] = script.db.desc
	data['obj'] = ref_uids(script.obj)
	data['interval'] = script.interval
	data['repeats'] = script.repeats
	data['persistent'] = script.persistent
	data['start_delay'] = script.start_delay
	if attrs := script.attributes.all():
		data['attributes'] = [ (attr.key, ref_uids(attr.value), attr.category) for attr in attrs ]
	if tags := script.tags.all(return_key_and_category=True):
		data['tags'] = tags
	data['locks'] = str(script.locks)

	file.write(f"data = {data}\n")
	file.write(f"obj = update_or_create_script('{uid}', **data)\n")