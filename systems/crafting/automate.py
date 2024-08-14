"""
Automation of crafted objects, for code-level building.
"""
from collections import Counter
from copy import copy
from random import choice, choices
from evennia import ObjectDB
from evennia.utils import delay, logger, iter_to_str
from base_systems.prototypes.spawning import spawn
from core.ic.base import BaseObject

from data.recipes import RECIPE_DICTS
from data import materials
from utils.colors import get_name_from_rgb

##############################################
#			   Recipes
##############################################

def assemble(recipe, object_list):
	"""
	Assemble several pieces together according to the instructions from
	the objects list.

	Returns:
		obj_list (list): the update list of objects
	"""
	base = recipe["base"].lower()
	adds_list = recipe["adds"]
	count = recipe.get('quantity',1)
	# logger.log_msg(f"assembling {base} from {iter_to_str(adds_list)}")

	base_cands = [obj for obj in object_list if obj.tags.has(base, category="recipe_key")]
	filtered_bases = []
	for base_cand in base_cands:
		if not (base_parts := base_cand.parts.all()):
			filtered_bases.append(base_cand)
			continue
		accounted_for = []
		for addon in adds_list:
			if any(obj.tags.has(addon, category='recipe_key') for obj in base_parts):
				# this addon is already accounted for
				accounted_for.append(addon)
		if len(adds_list) > len(accounted_for):
			filtered_bases.append(base_cand)

	for i in range(min(count, len(filtered_bases))):
		base_obj = filtered_bases[i]
		# TODO: this will require a special SHAPE recipe type to do right so parts can be shaped
		if shape := recipe.get('shape'):
			base_obj.db.piece = f"{shape} {base_obj.db.piece}"
		subtypes = base_obj.tags.get(category="subtypes", return_list=True)

		add_objs = []
		for addon in adds_list:
			addon = addon.lower()
			add_cands  = [obj for obj in object_list
										if (obj.tags.has(addon, category="recipe_key") or obj.tags.has(addon, category="craft_material"))
										and obj not in add_objs]
			if subtypes:
				add_cands = [ obj for obj in add_cands if all(obj.tags.has(subtypes, category="subtypes", return_list=True)) ]
			if not add_cands:
				logger.log_err(f"Not enough candidates for {addon} - current picks are {add_objs}")
				return None
			add_objs.append(add_cands[0])
		
		materials = base_obj.materials.get("all", as_data=True)
		for obj in add_objs:
			existing = obj.materials.all
			for mat, data in materials:
				if mat in existing:
					obj.materials.set(mat, soft=False, **data)
			obj.generate_desc()
			obj.tags.remove('descme')
			obj.partof = base_obj
			object_list.remove(obj)

		base_obj.at_crafted(ingredients=add_objs, fresh=True)
		# logger.log_msg(f"object list post-assembly: {object_list}")
		base_obj.generate_desc()
		base_obj.tags.remove('descme')
	return object_list

def craft(recipe_dict, material_dict, object_list):
	"""
	Craft the object defined by the recipe, using the materials data provided

	Returns:
		objects (list): an updated list of objects, or None if something goes wrong
	"""
	if not (recipe_key := recipe_dict.get('recipe')):
		logger.log_err(f"No 'recipe' key found?\n{recipe_dict}")
		return None
	if recipe_key == "ASSEMBLE":
		return assemble(recipe_dict, object_list)
	recipe = dict(recipe_dict)

	# pop crafting-specific attributes
	quality_dict = recipe.pop("quality_levels")
	quantity = recipe.pop("quantity",1)
	# logger.log_msg(f"going to make {quantity} {recipe_key}")
	_ = recipe.pop("skill","")
	_ = recipe.pop("tools","")
	ingredients = recipe.pop("ingredients",[])
	material_list = []
	for ingredient in ingredients:
		invisible = not ingredient.visible
		if not (materials := material_dict.get(ingredient.type,[])):
			materials = [ (ingredient.type, {'value': ''}) ]
		update_mats = []

		for mat, data in materials:
			data = dict(data)
			if invisible:
				data |= { 'invisible': True }
			if type(mat) is not str:
				mat = choice(mat)
			# color handling
			if pigment := data.pop('pigment', None):
				if not type(pigment[0]) is int:
					pigment = choice(pigment)
			if 'color' in data:
				colorword = get_name_from_rgb(pigment) or ''
				# set color to pigment word only if not already set to a non-empty value
				data['color'] = data.get('color') or colorword
			data = { prop: choice(val) if type(val) in (list, tuple) else val for prop, val in data.items() }
			if pigment:
				data['pigment'] = pigment
			update_mats.append( (mat, data) )

		material_list += update_mats

	quality = 3
	quality_str = [ value for key, value in quality_dict.items() if key <= quality ][-1]

	if recipe.get('key') and not recipe.get('format'):
		recipe['format'] = {'name': recipe['key'], 'desc': recipe['key']}
	recipe["key"] = recipe.get('key',"something")
	recipe["quality"] = (quality, quality_str)
	taglist = recipe.get("tags",[])
	recipe["tags"] = taglist + [ (recipe_key, "recipe_key") ]
	locks = recipe.get('locks', "craftwith:perm(Player)")
	if "craftwith" not in locks:
		locks += ";craftwith:perm(Player)"
	recipe["locks"] = locks
	recipe["location"] = None


	crafted = 0
	subtypes = recipe.pop('subtypes',[None])
	stepsize = quantity//len(subtypes)
	for sub in subtypes:
		amt = min(stepsize, quantity-crafted)
		taglist = recipe['tags'] + ( [(sub, 'subtype')] if sub else [] )
		outputs = spawn(recipe | {'tags': taglist}, restart=False)
		base_obj = outputs[0]
		# logger.log_msg(base_obj.materials.get("all",as_dict=True))

		_ = [ base_obj.materials.merge(tup[0], **tup[1]) for tup in material_list ]
		# kind of hacky but it should work
		base_obj.tags.add('descme')
		if sub:
			coverage = base_obj.tags.get(category="parts_coverage", return_list=True)
			if coverage:
				base_obj.tags.remove(category="parts_coverage")
				base_obj.tags.add(list([ f"{part},{sub}" for part in coverage]), category="parts_coverage")
		outputs += [BaseObject.objects.copy_object(base_obj) for _ in range(amt-1)]
		object_list += outputs
		crafted += len(outputs)

	# logger.log_msg(f"current objects: {object_list}")
	return object_list


def generate_new_object(recipe_list, material_dict, location, matched_set=False, wear=False, decor=False):
	recipe_keys = []
	parts = []
	assembly_dicts = []
	recipe_dicts = []
	object_list = []
	def _parse_assembly(recipe):
		parts.append(recipe.get('base'))
		addons = recipe.get('adds', [])
		newadds = []
		for item in addons:
			if isinstance(item, str):
				newadds.append(item)
				parts.append(item)
			else:
				if item.get('recipe') == 'ASSEMBLE':
					item = _parse_assembly(item)
					assembly_dicts.append(item)
					newadds.append(item['base'])
					# parts.extend(item.get('adds', []))
				else:
					newadds.append(item['recipe'])
					recipe_dicts.append(item)
		if newadds:
			recipe['adds'] = newadds
			# parts.extend(newadds)
#				parts += r.get('adds',[])
		return recipe
	
	for r in recipe_list:
		if type(r) is str:
			recipe_keys.append(r)
		else:
			if not (rkey := r.get('recipe')):
				recipe_dicts.append(r)
				continue
			if rkey == 'ASSEMBLE':
				r = _parse_assembly(r)
				assembly_dicts.append(r)
			else:
				recipe_keys.append(rkey)

	# assembled_pieces = list([r for r in parts if isinstance(r, dict)])
	# NOTE: this is potentially buggy, we may need to refactor this in the future
	needed_pieces = Counter([k.lower() for k in parts])# if isinstance(k, str)] + [r['base'].lower() for r in assembled_pieces])
	stated_pieces = Counter(k.lower() for k in recipe_keys)
	recipe_pieces = []
	keylist = list(stated_pieces.keys()) + [key for key in needed_pieces.keys() if key not in stated_pieces]
	for key in keylist:
		recipe_pieces.append( (key, max(needed_pieces.get(key,0), stated_pieces.get(key,0))) )

	ingredients = set()
	subtypes = set()
	for recipe_key, quantity in recipe_pieces:
		# get the recipe by key instead of the actual dict
		recipe_key = recipe_key.lower()
		if recipe := RECIPE_DICTS.get(recipe_key):
			recipe = recipe | {"recipe": recipe_key, "quantity": quantity}
			subtypes.update(set(recipe.get('subtypes',set())))
			for ingredient in recipe.get('ingredients', []):
				if ingredient.visible:
					ingredients.add(ingredient.type)
		else:
			logger.log_err(f"Could not find data for '{recipe_key}'.")
			continue
		recipe_dicts.append(recipe)

	needed_mats = ingredients.difference(set(material_dict.keys()))
	for mat in needed_mats:
		material_dict |= populate_material(mat)

	recipe_dicts += assembly_dicts

	for recipe in recipe_dicts:
		if matched_set:
			recipe |= { 'quantity': recipe.get('quantity',1)*( len(subtypes) or 1 )}
		if objects := craft(recipe, material_dict, object_list):
			for obj in objects:
				# TODO: when i implement cooking, just check and hit the `do_cook` behavior
				if obj.tags.has('raw', category='food'):
					if cooked := obj.db.cooked_piece:
						obj.db.piece = cooked
						del obj.db.cooked_piece
					obj.tags.remove('raw', category='food')
			object_list = objects
		else:
			logger.log_err(f"Something went wrong creating {recipe}")
		yield

	# we're all done!
	# logger.log_msg(f"finalizing {object_list}, wear: {wear}, decor: {decor}")
	for obj in object_list:
		if obj.tags.has("descme"):
			obj.generate_desc()
			obj.tags.remove('descme')
		obj.location = location
		if wear:
			location.clothing.add(obj, style=(wear if type(wear) is str else None), quiet=True)
		elif decor:
			location.decor.add(obj, decor)
	return object_list

def populate_material(material, num=1):
	"""
	populates the randomization options for a given material classification
	
	returns a generic material of name `material` if no specific options exist
	"""
	base_dict = materials.MATERIAL_TYPES.get(material, materials.MATERIAL_TYPES['generic'])
	features = materials.MATERIAL_NAMES.get(material, material)
	base_dict = copy(base_dict)

	def _naive_weights(iter):
		"""adds simple order-based weighting so the first items are weighted more than the last"""
		opts = []
		for i, item in enumerate(reversed(iter)):
			opts.extend([item]*(i+1))
		return tuple(opts)

	if pigment_opts := materials.MATERIAL_COLORS.get(material):
		base_dict['pigment'] = choice(_naive_weights(pigment_opts))
	if 'texture' in base_dict:
		if texture_opts := materials.MATERIAL_TEXTURES.get(material):
			base_dict['texture'] = choice(_naive_weights(texture_opts))
	if 'pattern' in base_dict:
		if pattern_opts := materials.MATERIAL_PATTERNS.get(material):
			base_dict['pattern'] = choice(_naive_weights(pattern_opts))

	result = { material: [( choices(features, k=num), base_dict )] }

	return result

