from collections import Counter, defaultdict

from evennia.utils import iter_to_str, logger, lazy_property, string_partial_matching

from data.skills import SKILL_TREE
from utils.handlers import HandlerBase
from utils.strmanip import numbered_name, strip_extra_spaces
from utils.colors import strip_ansi

import switchboard

from .crafting import assemble, craft
from data.recipes import RECIPE_DICTS


# TODO: make stored recipes more easily sortable by skills

class RecipeHandler(HandlerBase):
	"""
	Stores all learned recipes for a character
	"""
	def __init__(self, obj, **kwargs):
		super().__init__(obj, "recipes")
	
	def add(self, key, recipe, **kwargs):
		"""
		adds a new recipe under `key`

		returns False if the key already exists, or True if it was successfully added
		"""
		# TODO: add some validation i guess
		if key in self._data:
			return False
		else:
			self._data[key] = recipe
			self._save()
			return True

	def remove(self, key, **kwargs):
		"""
		removes the recipe under `key`

		returns False if the key did not exist, or True if it was successfully removed
		"""
		if key in self._data:
			del self._data[key]
			self._save()
			return True
		else:
			return False

	def keys(self):
		"""return a list of all keys"""
		return list(self._data.keys())

	def get(self, key=None, **kwargs):
		if key:
			return self._data.get(key)
		else:
			return list(self._data.values())
	
	def search(self, search_term, **kwargs):
		"""
		search for a recipe key

		returns a dict of recipes where the key matches
		"""
		if recipe := self.get(search_term):
			return {search_term: recipe}
		keys = string_partial_matching(self._data.keys(), search_term, ret_index=False)
		return {key: self.get(key) for key in keys}
	
	def rename_recipe(self, old_name, new_name):
		if not (data := self._data.get(old_name)):
			return False
		del self._data[old_name]
		self._data[new_name] = data
		self._save()
		return True

	def record_object(self, obj, **kwargs):
		"""
		Takes an output object and analyzes it, recording the necessary
		tools, ingredients, and steps in order to create it.

		Args:
			obj (Object): the craftable object being recorded

		Returns:
			(boolean): whether recording succeeded or failed
		"""
		base_recipe = obj.tags.get(category="recipe_key")
		if base_recipe not in RECIPE_DICTS or not obj.tags.has(category="skill"):
			return False

		desc_str, skill_list, recipe_list, ingredient_list, tool_list = self._analyze_recipes(obj)

		# total ingredients for all crafting
		ingredients = {}
		for ingredient, quant, portion, _ in ingredient_list:
			if ingredient in ingredients:
				ingredients[ingredient]["quant"] += quant
			else:
				ingredients[ingredient] = {}
				ingredients[ingredient]["quant"] = quant
				ingredients[ingredient]["portion"] = portion

		# trim out duplicate tools and skills
		tools = []
		for tool in tool_list:
			if tool not in tools:
				tools.append(tool)
		skills = {}
		for skill, level in skill_list:
			skills[skill] = max(level, skills.get(skill, 0))

		new_recipe = {
			"skills": skills,
			"recipes": recipe_list,
			"tools": tools,
			"ingredients": ingredients,
			"desc": desc_str,
		}

		new_recipe = self._format_recipe(new_recipe)

		if not (nkey := kwargs.get("key")):
			fbase = obj.db.format
			thing = fbase.get('desc', fbase.get('name', 'something'))
			thing = thing.format(material="", prefix=obj.db._sdesc_prefix or "", piece=obj.db.piece or "")
			thing = thing.strip()
			i = 0
			nkey = thing
			while nkey in self._data:
				i += 1
				nkey = f"{thing} {i}"
		return self.add(strip_extra_spaces(nkey), new_recipe)

	def set_recipe(self, recipe_key, **kwargs):
		"""
		Looks up a recipe by key, then analyzes it, recording the necessary
		tools, ingredients, and steps in order to create it.

		Args:
			recipe_key (string): the key for the recipe being set

		Returns:
			(boolean): whether recording succeeded or failed
		"""
		if recipe_key not in RECIPE_DICTS:
			return False

		recipe = RECIPE_DICTS[recipe_key]

		ingredient_list = recipe["ingredients"]
		tool_list = recipe["tools"]
		skill = recipe["skill"]
		difficulty = recipe["difficulty"]
		format = recipe['format']
		piece = recipe.get('piece', "")
		sdesc_prefix = recipe.get("_sdesc_prefix", "")

		# total ingredients for all crafting
		ingredients = {}
		for ingredient, quant, portion, _ in ingredient_list:
			if ingredient in ingredients:
				ingredients[ingredient]["quant"] += quant
			else:
				ingredients[ingredient] = {}
				ingredients[ingredient]["quant"] = quant
				ingredients[ingredient]["portion"] = portion


		new_recipe = {
			"skills": {skill: difficulty},
			"recipes": [{"recipe": recipe_key}],
			"tools": tool_list,
			"ingredients": ingredients,
		}

		thing = format.get("desc", format.get('name',"something"))
		thing = thing.format(material="", prefix=sdesc_prefix, piece=piece)
		desc = thing
		thing = thing.strip()
		if reqs := recipe.get("req_pieces"):
			reqs = [numbered_name(req, 0) for req in reqs]
			reqs = "with {}".format(iter_to_str(reqs, endsep=", or"))
			desc = f"{desc} {reqs}"
		new_recipe['desc'] = desc

		new_recipe = self._format_recipe(new_recipe)

		i = 0
		nkey = thing
		while nkey in self._data:
			i += 1
			nkey = f"{thing} {i}"

		return self.add(nkey, new_recipe)


	def _format_recipe(self, recipe_dict, **kwargs):
		"""add a new recipe to your recipe book"""
		skillkeys = set(recipe_dict['skills'].keys())
		subskills = {}
		for key, val in SKILL_TREE.items():
			subskills.update(val['subskills'])
		for key in skillkeys:
			skillnames = subskills[key]['name']

		desc = "Instructions on how to make {}.".format(
			numbered_name(recipe_dict['desc'], 1)) + "\nRequires:\n {}\n {}\n {}".format(
			iter_to_str(skillnames),
			iter_to_str(recipe_dict['tools']),
			iter_to_str([f"{key} ({value['quant']})" for key, value in recipe_dict['ingredients'].items()]),
		)
		recipe_dict['desc'] = strip_extra_spaces(desc)
		return recipe_dict
	
	def _analyze_recipes(self, obj, **kwargs):
		"""
		Recursively analyzes an object's components to record
		the necessary steps.
		"""
		skill_list = []
		recipe_list = []
		ingredient_list = []
		tool_list = []
		part_descs = []
		desc_str = ''

		recipe_key = obj.tags.get(category="recipe_key")

		if recipe_key not in RECIPE_DICTS:
			ingredient_list.append((obj.tags.get(category="craft_material"), 1, True, False))

		else:
			# this is a craftable object
			skill_list.append((obj.tags.get(category="skill"), obj.db.difficulty))

			desc_str = obj.db.format.get("desc", "something")
			desc_str = desc_str.format(material="", prefix=obj.db._sdesc_prefix or "", piece=obj.db.piece or "")

			attached = obj.parts.attached()
			for part in attached:
				part_str, skills, recipes, ingredients, tools = self._analyze_recipes(part)
				skill_list += skills
				recipe_list += recipes
				ingredient_list += ingredients
				tool_list += tools
				part_descs.append(part_str)

			if recipe_key in RECIPE_DICTS:
				recipe_list.append({"recipe": recipe_key})
				recipe = RECIPE_DICTS[recipe_key]
				ingredient_list += recipe["ingredients"]
				tool_list += recipe["tools"]
			else:
				ingredient_list.append((obj.db.piece, 1, False))

			if len(attached) > 0:
				assembly = {
					"base": recipe_key,
					"adds": [part.tags.get(category="recipe_key") or part.tags.get(category="craft_material") for part in
					         attached],
					"skill": obj.tags.get(category="skill"),
					"recipe": "ASSEMBLE"
				}

				partcount = Counter(part_descs)
				part_list = [numbered_name(key, value) for key, value in partcount.items()]

				desc_str += " with {}".format(iter_to_str(part_list))
				recipe_list.append(assembly)
			#				skill_list.append((obj.tags.get(category="skill"),obj.db.difficulty))
			# tool_list.append(ASSEMBLY_TOOL[obj.db.skill]) # add this when i have the dict made

			desc_str = switchboard.INFLECT.an(desc_str) if desc_str else obj.tags.get(category="craft_material")

		return (desc_str, skill_list, recipe_list, ingredient_list, tool_list)

	def use_recipe(self, user, recipe_key, **kwargs):
		"""
		Initiates crafting
		"""
		if not (recipe_list := self.db.recipes.get('recipes', {}).get(recipe_key)):
			user.msg("Craft what?")
			return
		# contents first prioritizes objects being held over objects in the room
		candidates = [obj for obj in user.contents + user.location.contents if
		              obj.at_pre_craft(user) and obj not in user.clothing.all]
		candidate_mats = [obj for obj in candidates if obj.tags.has(category="craft_material")]
		candidate_parts = [obj for obj in candidates if obj.db.recipe in recipe_list]
		candidate_tools = [obj for obj in candidates if obj.tags.has(category="craft_tool")]
		candidates = candidate_parts + candidate_mats

		inputs = [obj for obj in kwargs.get("targets", []) if obj.at_pre_craft(user)]
		candidates = inputs + candidates

		user.ndb.craft_materials = candidates
		#		user.ndb.craft_pieces = candidate_parts
		user.ndb.craft_pieces = []
		user.ndb.craft_tools = candidate_tools
		key_list = [recipe['recipe'] for recipe in recipe_list]
		key_counts = Counter(key_list)
		completed = []

		end = len(recipe_list) - 1
		for i, recipe in enumerate(recipe_list):
			recipe_key = recipe['recipe']
			if i == end:
				recdict = dict(recipe) | {"last": True}
			else:
				recdict = dict(recipe)
			if recipe_key == "ASSEMBLE":
				user.delay_action(assemble, (recdict, user))
			elif recipe_key in completed:
				continue
			else:
				user.delay_action(craft, (recdict, user, key_counts[recipe_key]))
				completed.append(recipe_key)
		user.msg("You begin to craft.")

	def at_pre_use(self, user):
		"""
		Verifies that user has the required tools and ingredients
		"""
		candidate_mats = [(obj, obj.size, obj.tags.get(category="craft_material", return_list=True) + [obj.db.piece]) for
		                  obj in user.contents + user.location.contents if
		                  obj.tags.has(category="craft_material") and obj.at_pre_craft(user)]

		pre_candidate_tools = [tag for obj in user.contents + user.location.contents if obj.at_pre_craft(user) for tag in
		                       obj.tags.get(category="craft_tool", return_list=True)]

		candidate_tools = []
		for tool in pre_candidate_tools:
			if tool not in candidate_tools:
				candidate_tools.append(tool)

		if len(candidate_mats) > 0 and len(candidate_tools) > 0:
			# check if all required tools are available
			# filter out any tools this obj counts for
			tool_list = [tool for tool in self.db.tools if tool not in candidate_tools]
			# if tools are remaining, we are missing tools
			if len(tool_list) > 0:
				user.msg("You don't have enough tools.")
				return False
			max_skills = {}
			for skill, level in self.db.skills.items():
				max_skills[skill] = max(max_skills.get(skill, 0), level)

			if not user.skills.check(**max_skills):
				user.msg("You don't have the skill needed to make this.")
				return False

			# check if all required materials are available
			# mat_list = dict(self.db.ingredients) # (ingr type, quantity, portion or item)
			# for type, data in mat_list.items():
			# quant = data['quant']
			# if data['portion']:
			# amt = sum([tup[1] for tup in candidate_mats if type in tup[2]])
			# else:
			# amt = len([tup[1] for tup in candidate_mats if type in tup[2]])

			# if quant > amt:
			# # not enough of the material
			# user.msg("You don't have enough {}.".format(type))
			# return False

			# all validation passed!
			return True

		else:
			# no available tools and/or materials
			user.msg("You don't have anything to craft with.")
			return False
