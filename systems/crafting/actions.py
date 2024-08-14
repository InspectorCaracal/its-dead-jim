import time
from collections import Counter
from random import choice

from evennia.utils import delay, iter_to_str
from base_systems.prototypes.spawning import spawn

from core.ic.base import BaseObject
from base_systems.actions.base import Action, InterruptAction
from data.recipes import RECIPE_DICTS
from utils.colors import get_name_from_rgb, rgb_to_hex, strip_ansi
from utils.menus import FormatEvMenu
from utils.strmanip import numbered_name, strip_extra_spaces

class AssembleAction(Action):
	"""
	putting something together
	"""
	move = "assemble"

	def __init__(self, actor, recipe, **kwargs):
		"""
		initialize the action and create the crafting generator
		"""
		self.actor = actor
		self.recipe = recipe
		super().__init__(**kwargs)

	def _get_base_obj(self, base, candidates):
		base_cands = [obj for obj in candidates if obj.tags.has(base, category="recipe_key")]
		if len(base_cands) <= 0:
			self.actor.msg("You don't have enough ingredients for that.") 
			return
		base_obj = base_cands[0]
		base_obj.location = self.actor

		return base_obj

	def _get_addon_objs(self, addon_list, candidates):
		add_objs = []
		for addon in addon_list:
			add_cands  = [obj for obj in candidates if (obj.tags.has(addon, category="recipe_key") or obj.tags.has(addon, category="craft_material")) and obj not in add_objs]
			if len(add_cands) <= 0:
				self.actor.msg("You don't have enough pieces for that.") 
				return
			add_objs.append(add_cands[0])
		
		return add_objs

	def start(self, *args, **kwargs):
		candidates = [obj for obj in self.actor.contents + self.actor.location.contents if
		              obj.at_pre_craft(self.actor) and obj not in self.actor.clothing.all]
		candidate_mats = [obj for obj in candidates if obj.tags.has(category="craft_material")]
		candidate_tools = [obj for obj in candidates if obj.tags.has(category="craft_tool")]

		reserved = self.actor.ndb.craft_pieces or []
		candidates = reserved + candidates

		base = self.recipe["base"].lower()
		adds_list = [ add.lower() for add in self.recipe["adds"] ]
		self.duration = 2
		if not (base_obj := self._get_base_obj(base, candidates)):
			return
		candidates.remove(base_obj)
		if not (addon_objs := self._get_addon_objs(adds_list, candidates)):
			return
		self.base_obj = base_obj
		self.addon_objs = addon_objs

		super().start(*args, **kwargs)


	def do(self, *args, **kwargs):
		"""
		Assemble several pieces together according to the instructions from
		the available candidate list.
		"""
		for obj in self.addon_objs:
			if not self.base_obj.parts.attach(obj):
				return False

		# base_obj.generate_desc()
		self.base_obj.at_crafted(ingredients=self.addon_objs, fresh=True)
		self._end_at = time.time() + self.duration
		# TODO: once i get assembly tools in, this will use that tool's energy cost instead
		self.actor.life.energy -= 2
		self.actor.emote("puts together {}.".format(self.base_obj.get_display_name(obj,article=True)))
		self._task = delay(self.duration, self.end)

	def end(self, *args, **kwargs):
		self.actor.exp += 2
		super().end()


class CraftAction(Action):
	"""
	using a tool on some materials
	"""
	move = "craft"
	dbobjs = ["actor", "tools", "ingredients"]

	def __init__(self, actor, recipe, **kwargs):
		"""
		initialize the action and create the crafting generator
		"""
		self.actor = actor
		self.recipe = {}
		if type(recipe) is str:
			recipe = {'recipe': recipe } | RECIPE_DICTS.get(recipe.lower())
		if data_recipe := RECIPE_DICTS.get(recipe['recipe']):
			self.recipe = {'recipe': recipe['recipe']} | dict(data_recipe)
		else:
			self.recipe = dict(recipe)
		if not self.recipe:
			raise InterruptAction
		self.tools = kwargs.pop('tools',[])
		self.ingredients = kwargs.pop('ingredients',[])
		self.quantity = kwargs.pop('quantity', 1)
		super().__init__(**kwargs)

	def do(self, skill_data, material):
		"""
		the method for queueing up a crafting step
		"""
		if self.i > len(self.tools):
			return self.finish()
		self.do_args = (skill_data, material)
		skill_key, skill_dc = skill_data
		tool = self.tools[self.i-1]
		
		# TODO: package the skill use data into one attribute
		message = choice(tool.attributes.get("emotes", ["uses $gp(their) {tool}."], category="skills"))
		message = message.format(tool=tool.sdesc.get(strip=True), material=material)
		duration = tool.attributes.get("time",5, category="skills")

		if self.actor.skills.use(**{skill_key:skill_dc}):
			self.actor.emote(message)
			energy = tool.attributes.get("energy",1, category="skills")
			self.actor.life.energy -= energy
			self._next_step = time.time() + duration
			self.i += 1
			# TODO: have xp gain be more dynamic
			self.xp_gain += 2
			self._task = delay(duration, self.do, skill_data, material)
			return True
		else:
			self.actor.msg("That is too difficult for you.")
			if self.i:
				# this has already looped once somehow; make sure it gets dequeued
				super().end()

	def start(self):
		self.i = 0
		candidates = [obj for obj in self.actor.contents + self.actor.location.contents if
		              obj.at_pre_craft(self.actor) and obj not in self.actor.clothing.all]
		candidate_mats = [obj for obj in candidates if obj.tags.has(category="craft_material")]
		candidate_tools = [obj for obj in candidates if obj.tags.has(category="craft_tool")]

		ingredients = [obj for obj in self.ingredients if obj.at_pre_craft(self.actor)]
		candidate_mats = ingredients + candidate_mats

		mat_list = candidate_mats
		tool_list = candidate_tools
		reserved = self.actor.ndb.craft_pieces or []

		recipe_key = self.recipe['recipe']
		recipe = self.recipe

		candidate_pieces = [obj for obj in mat_list if obj.tags.has(recipe_key, category="recipe_key")]
		for obj in candidate_pieces:
			if len(reserved) >= self.quantity:
				break
			reserved.append(obj)
			mat_list.remove(obj)

		if count := len(reserved):
			res_names = Counter([obj.sdesc.get() for obj in reserved])
			res_name = iter_to_str([numbered_name(*item) for item in res_names.items()])
			self.actor.emote(f"sets aside {res_name} to use.")
		self.quantity -= count
		if self.quantity < 1:
			# no need to do this crafting
			return super().end()

		# pop crafting-specific attributes
		difficulty = recipe.get("difficulty",1)
		if skill := recipe.pop("skill", None):
			skill_lvl = self.actor.skills.get(skill).value
		else:
			skill_lvl = 1
		quality_dict = recipe.pop("quality_levels")
		ingredients = recipe.pop("ingredients")
		tool_tags = recipe.pop("tools")

		quality = (skill_lvl - difficulty) // 2
		if quality < 0:
			self.actor.msg(f"You aren't skilled enough at {skill} to continue.")
			return super().end()
		quality_str = [ value for key, value in quality_dict.items() if key <= quality ][-1]

		recipe["key"] = "something"
		recipe["quality"] = (quality, quality_str)
		taglist = recipe.get("tags",[])
		if "bulky" in taglist:
			recipe["location"] = self.actor.location
		else:
			recipe["location"] = self.actor
		recipe["tags"] = taglist + [ (recipe_key, "recipe_key") ]
		recipe["locks"] = "craftwith:perm(Player)"

		self.recipe = recipe

		if not len(ingredients):
			# handle meta-materials
			recipe["location"] = None
			recipe_list = [recipe]*self.quantity
			outputs = spawn(*recipe_list, restart=False)
			self.actor.db.craft_pieces += outputs
			return super().end()

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
				self.actor.msg(f"You don't have any {tool_type} available.")
				return super().end()

		# go through and mark objects to be used as ingredients
		used = []
		mat_names = []
		for mat_type, quant, portion, visible in ingredients:
			quant = quant*self.quantity
			ingr_obj = [obj for obj in mat_list if obj.tags.has(mat_type, category="craft_material")]
			for obj in ingr_obj:
				if visible:
					for mat in obj.materials.all:
						mat_name = obj.materials.get(mat)
						if mat_name not in mat_names:
							mat_names.append(mat_name)
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
				self.actor.msg(f"You don't have enough {mat_type} to continue.")
				return super().end()

		self.ingredients = used
		making_name = self.recipe['format']['name'].format(material="", piece=self.recipe.get("piece",""))
		making_name = numbered_name(strip_extra_spaces("{} {}".format(self.recipe.get("_sdesc_prefix",""), making_name)),self.quantity)

		ingredient_names = iter_to_str([numbered_name(item[0].get_display_name(self.actor),1) for item in used])
		self.actor.msg("You begin making {} using {}.".format(making_name, ingredient_names))
		self.status_msg = strip_ansi(f"making {making_name}")
		self.actor.prompt()

		self.xp_gain = 0
		skilluse_data = (skill,difficulty)
		duration = 2
		self._next_step = time.time() + duration
		self.do_args = (skilluse_data, iter_to_str(mat_names))
		self.i = 1
		self._task = delay(duration, self.do, *self.do_args)

	def finish(self):
		# finish crafting
		mats = []
		delete_me = []
		# consume materials
		for obj, quant, visible in self.ingredients:
			if visible:
				mat_items = obj.materials.get("all",as_data=True)
				mats.extend(mat_items)
			if quant == obj.size:
	#			mat_list.remove(obj)
				delete_me.append(obj)
	#			obj.delete()
			else:
				obj.size -= quant
		
		# FIXME: if you make 3 shirts using 2 kinds of fabric they should be different
		# this method makes them all the same
		outputs = spawn(self.recipe, restart=False)
		base_obj = outputs[0]
		try:
			_ = [ base_obj.materials.merge(tup[0], **tup[1]) for tup in mats ]
			base_obj.at_crafted(ingredients=self.ingredients)
			base_obj.generate_desc()
		except AttributeError:
			pass

		outputs += [BaseObject.objects.copy_object(base_obj) for _ in range(self.quantity-1)]

		for obj in delete_me:
			obj.delete()

		output_names = [obj.sdesc.get() for obj in outputs]
		output_names = Counter(output_names)
		output_string = iter_to_str([numbered_name(*item) for item in output_names.items()])

		try:
			del self.do_arg
		except AttributeError:
			pass
		self.end(output_string)

	def end(self, *args):
		if args:
			output_string = args[0]
			self.actor.emote(f"finishes making {output_string}.")
		super().end()


class DrawAction(Action):
	move = "draw"
	dbobjs = ['actor', 'target']
	exp = 0
	skill = "sketching"
	max_details = 0

	def __init__(self, **kwargs):
		"""
		initialize the action and create the crafting generator
		"""
		super().__init__(**kwargs)
		# self.actor = None
		# self.target = None
		# self.suffix = ''
	
	def status(self):
		if actor := self.actor:
			# FIXME: this uses emote ref syntax in the tool string
			return f"You are drawing on {self.target.get_display_name(self.actor)}{self.tool_str}."

	def start(self, material=None, suffix='', **kwargs):
		skill_level = self.actor.skills.get(self.skill).value
		self.max_details = skill_level//10
		self.tool_str = suffix
		designs = self.target.parts.search('design', part=True)
		self.designs = [d for d in designs if d.get_lock(self.actor, 'view')]

		includes = [self.target]
		if self.tool_str:
			includes.append(material)
		self.actor.emote(f"begins to draw on @{self.target.sdesc.get(strip=True)}{self.tool_str}", include=includes)
		super().start(designs=designs, material=material)

	def do(self, designs = [], material=None, **kwargs):
		design = None
		if designs:
			# TODO: set up the menu to choose one of the available designs from a list
			self.design = designs[0]
			startnode = "menunode_choose_detail"
		else:
			startnode = "menunode_begin_drawing"
		
		FormatEvMenu(
			self.actor,
			"systems.crafting.menus.drawing",
			startnode=startnode,
			action=self,
			design=design,
			material=material,
			cmd_on_exit=self.end
		)
	
	def end(self, *args, **kwargs):
		self.finish(*args, **kwargs)
		return super().end(*args, **kwargs)
	
	def finish(self, *args, **kwargs):
		if obj := getattr(self, 'design', None):
			design = strip_ansi(obj.descs.get(self.actor))
			obname = self.target.sdesc.get(strip=True)
			details = obj.parts.search('design_detail', part=True)
			for detail in details:
				name = detail.name
				# FIXME: this should probably be materials, not features
				if mats := detail.features.all:
					mat = mats[0]
					color = detail.features.get(mat, as_data=True).get("pigment")
					if color:
						ccode = rgb_to_hex(color)
						name = f"|{ccode}{name}|n"
				design = design.replace(name, f"|lclook at {name} on {obname}|lt{name}|le")
			obj.db.desc = design
			self.actor.exp += self.exp
		self.actor.emote("stops drawing")

class WriteAction(Action):
	move = "write"
	exp = 0
	skill = "calligraphy"
	
	def status(self):
		if actor := self.actor:
			# FIXME: this uses emote ref syntax in the tool string
			return f"You are writing on {self.target.get_display_name(self.actor)}{self.tool_str}."

	def start(self, material=None, suffix='', **kwargs):
		skill_level = self.actor.skills.get(self.skill).value
		self.tool_str = suffix
		texts = self.target.parts.search('writing', part=True)
		self.writing = [d for d in texts if d.get_lock(self.actor, 'view')]
		self.handwriting = self.actor.db.handwriting or "writing"

		includes = [self.target]
		if self.tool_str:
			includes.append(material)
		self.actor.emote(f"begins to write on @{self.target.sdesc.get(strip=True)}{self.tool_str}", include=includes)
		super().start(texts=texts, material=material)

	def do(self, texts = [], material=None, **kwargs):
		writing = None
		if texts:
			# TODO: set up the menu to choose one of the available texts from the list
			writing = texts[0]
		startnode = "menunode_begin_writing"
		
		FormatEvMenu(
			self.actor,
			"systems.crafting.menus.writing",
			startnode=startnode,
			action=self,
			design=writing,
			material=material,
			cmd_on_exit=self.end
		)
	
	def end(self, *args, **kwargs):
		self.finish(*args, **kwargs)
		return super().end(*args, **kwargs)
	
	def finish(self, *args, **kwargs):
		self.actor.exp += self.exp
		self.actor.emote("stops writing")


class AttachAction(Action):
	def __init__(self, actor, targets, **kwargs):
		self.targets = targets
		self.actor = actor
		if not (base_obj := kwargs.get('use_on')):
			raise InterruptAction
		self.base_obj = base_obj[0]
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		# found valid objects, check if they can be attached to each other
		taglist = self.base_obj.tags.get(category="skill", return_list=True)
		invalid = [obj for obj in self.targets if not any(obj.tags.has(taglist, category="skill", return_list=True)) or not obj.tags.has(category="craft_material") ]
		if len(invalid):
			message = "You cannot add {namelist} to {basename}.".format(
					namelist = iter_to_str([obj.get_display_name(self.base_obj, article=True) for obj in invalid], endsep=', or'),
					basename = self.base_obj.get_display_name(self.base_obj, article=True)
				)
			self.actor.msg(message)
			return super().end()

		for obj in self.targets:
			self.base_obj.parts.attach(obj)

		basename = self.base_obj.sdesc.get()
		self.base_obj.at_crafted(ingredients=self.targets)
		# base_obj.update_desc()
		newname = self.base_obj.sdesc.get()
		if basename != newname:
			message = "adds {namelist} to {basename}, making {newname}."
		else:
			message = "adds {namelist} to {basename}."

		names = [obj.sdesc.get() for obj in self.targets]
		namecount = Counter(names)
		namelist = [numbered_name(key, value) for key, value in namecount.items()]

		message = message.format(
					namelist = iter_to_str(namelist),
					basename = numbered_name(basename,1),
					newname = numbered_name(newname,1),
				)
		self.actor.emote(message)

		super().do(*args, **kwargs)

class DetachAction(Action):
	def __init__(self, actor, targets, **kwargs):
		self.targets = targets
		self.actor = actor
		if not (base_obj := kwargs.get('base_obj')):
			raise InterruptAction
		self.base_obj = base_obj
		super().__init__(**kwargs)

	def do(self, *args, **kwargs):
		if hasattr(self.base_obj, "full_size"):
			if self.base_obj.full_size and self.base_obj.size < self.base_obj.full_size:
				ratio = self.base_obj.size / self.base_obj.full_size
				invalid = [obj for obj in self.targets if (ratio*obj.size) < 1]
				if len(invalid):
					names = iter_to_str([numbered_name(*item) for item in Counter([obj.sdesc.get() for obj in invalid]).items()], endsep=', or')
					message = "There is not enough of {namelist} left in {basename} to remove.".format(
							namelist = names,
							basename = self.base_obj.get_display_name(self.actor, article=True)
						)
					self.actor.msg(message)
					return super().end()

		for obj in self.targets:
			self.base_obj.parts.detach(obj)
		basename = self.base_obj.sdesc.get()
		self.base_obj.at_crafted(ingredients=self.targets, remove=True)
		# base_obj.update_desc()
		newname = self.base_obj.sdesc.get()
		if basename != newname:
			message = "removes {namelist} from {basename}, leaving it {newname}."
		else:
			message = "removes {namelist} from {basename}."

		names = [obj.sdesc.get() for obj in self.targets]
		namecount = Counter(names)
		namelist = [numbered_name(key, value) for key, value in namecount.items()]

		message = message.format(
					namelist = iter_to_str(namelist),
					basename = numbered_name(basename,1),
					newname = numbered_name(newname,1),
				)
		self.actor.emote(message)
		
		super().do(*args, **kwargs)

