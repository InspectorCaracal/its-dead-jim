"""
Customized crafting system

Sets up craftable recipes that are affected by the input materials.
"""
from random import choice
from collections import Counter

from evennia import ObjectDB
from evennia.utils import iter_to_str, logger
from base_systems.prototypes.spawning import spawn

from utils.strmanip import strip_extra_spaces, numbered_name
from utils.colors import strip_ansi

from data.recipes import RECIPE_DICTS

import inflect

_INFLECT = inflect.engine()

##############################################
#			   Recipes
##############################################

def assemble(recipe, crafter):
	"""
	Assemble several pieces together according to the instructions from
	the available candidate list.

	Returns:
		candidates (list): Updated list of candidate items, or None if failed.
	"""
#	crafter.msg("assembling")
	base = recipe["base"]
	adds_list = recipe["adds"]
	obj_list = crafter.ndb.craft_pieces
	mat_list = crafter.ndb.craft_materials
#	crafter.msg(f"{base} {adds_list} {obj_list}")
	duration = 3

	base_cands = [obj for obj in obj_list if obj.tags.has(base, category="recipe_key")]

#	crafter.msg(f"base candidates {base_cands}")

	if len(base_cands) <= 0:
		crafter.msg("You don't have enough ingredients for that.") 
		return -1

	base_obj = base_cands[0]
	base_obj.location = crafter

	add_objs = []
	for addon in adds_list:
		crafter.msg(f"checking for {addon}")
		add_cands  = [obj for obj in obj_list if obj.tags.has(addon, category="recipe_key") and obj not in add_objs]
		add_cands += [obj for obj in mat_list if obj.tags.has(addon, category="craft_material") and obj not in add_objs]
		crafter.msg(f"{add_cands}")
		if len(add_cands) <= 0:
			crafter.msg("You don't have enough ingredients for that.") 
			return -1
		add_objs.append(add_cands[0])

	for obj in add_objs:
		obj.move_to(base_obj,quiet=True)
		obj.tags.add("attached",category="crafting")
		if obj in obj_list:
			obj_list.remove(obj)
		else:
			mat_list.remove(obj)

	base_obj.at_crafted(ingredients=add_objs, fresh=True)
	base_obj.update_desc()
	# once i get assembly tools in, this will use that tool's energy cost instead
	crafter.energy['pool'] -= 2
	crafter.emote("puts together {}.".format(base_obj.get_display_name(obj,article=True)))
	return duration

def craft(recipe_dict, crafter, quantity=1):
	"""
	Craft the object defined by the recipe, using objects in obj_list
	as possible ingredients.

	Returns:
		objects (list): a list of created objects
	"""
#	obj_list = caller.ndb.craft_pieces
	mat_list = crafter.ndb.craft_materials
	tool_list = crafter.ndb.craft_tools
	reserved = []
	pos = 1

	recipe_key = recipe_dict['recipe']
	if not (recipe := RECIPE_DICTS.get(recipe_key)):
		crafter.msg("You can't make that.")
		return -1
	recipe = dict(recipe)

	if not recipe_dict.pop("last",False):
		candidate_pieces = [obj for obj in mat_list if obj.tags.has(recipe_key, category="recipe_key")]
		for obj in candidate_pieces:
			if len(reserved) >= quantity:
				break
			reserved.append(obj)
			crafter.ndb.craft_pieces.append(obj)
			crafter.ndb.craft_materials.remove(obj)

		if count := len(reserved):
			res_name = numbered_name(reserved[0].name, 1)
			res_names = Counter([obj.sdesc.get() for obj in reserved])
			res_name = iter_to_str([numbered_name(*item) for item in res_names.items()])
			crafter.delay_action("emote", (2, f"sets aside {res_name} to use."), index=pos)
			pos += 1
		quantity -= count
		if quantity < 1:
			return 1

#	recipe = RECIPE_DICTS.get(recipe_key)
#	crafter.msg(recipe)
#	if not recipe:
#		return None
#	recipe = dict(recipe_dict)

	# pop crafting-specific attributes
	difficulty = recipe["difficulty"]
	skill = recipe.pop("skill")
	skill_lvl = crafter.skills.get(skill).value
	quality_dict = recipe.pop("quality_levels")
	ingredients = recipe.pop("ingredients")
	tool_tags = recipe.pop("tools")

	quality = (skill_lvl - difficulty) // 2
	if quality < 0:
		crafter.msg(f"You aren't skilled enough at {skill} to continue.")
		return -1
	quality_str = [ value for key, value in quality_dict.items() if key <= quality ][-1]

	recipe["key"] = "something"
	recipe["quality"] = (quality, quality_str)
	taglist = recipe.get("tags",[])
	if "bulky" in taglist:
		recipe["location"] = crafter.location
	else:
		recipe["location"] = crafter
	recipe["tags"] = taglist + [ (recipe_key, "recipe_key") ]
	recipe["locks"] = "craftwith:perm(Player)"

	if not len(ingredients):
		# handle meta-materials
		recipe["location"] = None
		recipe_list = [recipe]*quantity
		outputs = spawn(*recipe_list, restart=False)
		crafter.ndb.craft_pieces += outputs
		return 1

#	crafter.msg(f"getting tools {tool_tags}")
	tools = []
	for tool_type in tool_tags:
		tool_cands = [obj for obj in tool_list if obj.tags.has(tool_type, category="craft_tool")]
#		crafter.msg(f"candidates for {tool_type}: {tool_cands}")
		if len(tool_cands) > 0:
#			crafter.msg(f"got our {tool_type}")
			tools.append(tool_cands[0])
		else:
#			crafter.msg("no {tool_type} found")
			crafter.msg(f"You don't have any {tool_type} available.")
			return -1

	# go through and mark objects to be used as ingredients
	used = []
	mat_names = []
	for type, quant, portion, visible in ingredients:
		quant = quant*quantity
		ingr_obj = [obj for obj in mat_list if obj.tags.has(type, category="craft_material")]
		for obj in ingr_obj:
			if visible:
				for mat in obj.materials.all:
					if mat not in mat_names:
						mat_names.append(mat)
			if portion:
				if quant >= obj.size:
					used.append((obj, obj.size, visible))
					quant -= obj.size
				else:
					used.append((obj, quant, visible))
					quant = 0
			else:
				used.append((obj, obj.size, visible))
				quant -= 1
			if quant <= 0:
				break
		if quant > 0:
			# we didn't have enough of the material
			crafter.msg(f"You don't have enough {type} to continue.")
			return -1
#	crafter.msg("got ingredients")

	making_name = recipe['format']['name'].format(material="", piece=recipe.get("piece",""))
	making_name = numbered_name(strip_extra_spaces("{} {}".format(recipe.get("_sdesc_prefix",""), making_name)),quantity)

	ingredient_names = iter_to_str([numbered_name(item[0].get_display_name(crafter),1) for item in used])
	crafter.msg("You begin making {} using {}.".format(making_name, ingredient_names))

	crafter.ndb.pose = strip_ansi(f"making {making_name}")
	crafter.prompt()

	xp_gain = 0
	skilluse_data = (skill,difficulty)
	for i, tool in enumerate(tools):
		crafter.delay_action(tool_use, (crafter, tool, skilluse_data, iter_to_str(mat_names)), index=i+pos)
		xp_gain += 2
	pos += i

	crafter.delay_action(finish_craft, (crafter, recipe, quantity, used, xp_gain if quality <= 9 else 0), index=pos+1)

#	crafter.msg("returning duration value")
	return 3

def tool_use(crafter, tool, skilluse_data, material):
	"""
	the method for queueing up a crafting step
	"""
	message = choice(tool.attributes.get("craft_strings", ["uses $gp(their) {tool}."]))
	message = message.format(tool=tool.name, material=material)
	energy = tool.attributes.get("energy",1)
	duration = tool.attributes.get("time",5)
	crafter.energy['pool'] -= energy
	crafter.emote(message)
	skill, dc = skilluse_data
	crafter.skills.use(**{skill:dc})
	crafter.prompt()

	return duration

def finish_craft(crafter, recipe_dicts, quantity, ingredients, xp):
	"""actually create the final output"""
	# process marked ingredients for material attributes
	mats = []
	delete_me = []
	# consume materials
	for obj, quant, visible in ingredients:
		if visible:
			mat_items = obj.materials.get("all",as_data=True)
			mats.extend(mat_items)
		if quant == obj.size:
#			mat_list.remove(obj)
			delete_me.append(obj)
#			obj.delete()
		else:
			obj.size -= quant

	outputs = spawn(*recipe_dicts)
	base_obj = outputs[0]
	try:
		_ = [ base_obj.materials.merge(tup[0], **tup[1]) for tup in mats ]
		base_obj.at_crafted(ingredients=ingredients)
		base_obj.update_desc()
	except AttributeError:
		pass

	outputs += [ObjectDB.objects.copy_object(base_obj) for _ in range(quantity-1)]

	for obj in delete_me:
		crafter.ndb.craft_materials.remove(obj)
		obj.delete()

	output_names = [obj.sdesc.get() for obj in outputs]
	output_names = Counter(output_names)
	output_string = iter_to_str([numbered_name(*item) for item in output_names.items()])

	crafter.emote(f"finishes making {output_string}.")
	crafter.ndb.craft_pieces += outputs
	crafter.ndb.pose = None
	crafter.prompt()

	return 2
