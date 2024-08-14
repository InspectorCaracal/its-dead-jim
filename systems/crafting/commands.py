import time
import re

from evennia import logger
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import InterruptCommand
from evennia.utils.utils import iter_to_str, inherits_from, is_iter
from evennia.utils import create, interactive
from base_systems.actions.base import InterruptAction
from base_systems.actions.commands import ActionCommand
from base_systems.things.commands import ToolActionCommand
from data.recipes import RECIPE_DICTS
from systems.crafting import actions

from systems.crafting.automate import generate_new_object
from utils.colors import strip_ansi
from core.commands import Command
# from data.colors import COLOR_CODES, COLOR_DICT

import inflect

from utils.timing import delay_iter
_INFLECT = inflect.engine()


class CmdDraw(Command):
	"""
	Draw, sketch, or otherwise create a piece of artwork on paper.
	
	Usage:
		draw on <obj> [with <material>]
	
	
	"""
	key = "draw"
	aliases = ("draw on", "sketch", "sketch on",)
	locks = "cmd:all()"
	splitters = ("with",)
	help_category = "Crafting"
	
	def func(self):
		if not self.args:
			self.msg("Draw on what?")

		caller = self.caller
		xp = 0

		obj = yield from self.find_targets(self.argslist[0], numbered=False)
		if not obj:
			return
		if not obj.access(caller, 'design'):
			caller.msg("You can't draw on that.")
			return
		
		if len(self.argslist) > 1:
			# optional
			mat_cands = [ obj for obj in caller.location.contents+caller.contents if obj.tags.has("sketching", category="crafting_tool") ]
			mat = yield from self.find_targets(self.argslist[1], candidates=mat_cands, numbered=False)
			if not mat:
				return
			if not mat.access(caller, 'craftwith'):
				caller.msg("You can't draw with that.")
				return
		else:
			mat = None

		if mat and mat not in caller.holding().values():
			if not caller.hold(mat):
				return

		if mat:
			tool = f" with @{mat.sdesc.get(strip=True)}"
		else:
			tool = ""

		try:
			action = actions.DrawAction(actor=caller, target=obj)
		except:
			logger.log_trace()
			self.msg(("Something went wrong...", {'type': 'system'}))
			return
		
		caller.actions.add(action, mat, tool)


class CmdWrite(Command):
	"""
	Write text onto a surface, like paper.
	
	Usage:
		write on <obj> [with <material>]
	
	
	"""
	key = "write"
	aliases = ("write on",)
	locks = "cmd:all()"
	splitters = ("with",)
	help_category = "Crafting"
	
	def func(self):
		if not self.args:
			self.msg("Draw on what?")

		caller = self.caller
		xp = 0

		obj = yield from self.find_targets(self.argslist[0], numbered=False)
		if not obj:
			return
		if not obj.access(caller, 'design'):
			caller.msg("You can't write on that.")
			return
		
		if len(self.argslist) > 1:
			# optional
			mat_cands = [ obj for obj in caller.location.contents+caller.contents if obj.tags.has("sketching", category="crafting_tool") ]
			mat = yield from self.find_targets(self.argslist[1], candidates=mat_cands, numbered=False)
			if not mat:
				return
			if not mat.access(caller, 'craftwith'):
				caller.msg("You can't write with that.")
				return
		else:
			mat = None

		if mat and mat not in caller.holding().values():
			if not caller.hold(mat):
				return

		if mat:
			tool = f" with @{mat.sdesc.get(strip=True)}"
		else:
			tool = ""

		try:
			action = actions.WriteAction(actor=caller, target=obj)
		except:
			logger.log_trace()
			self.msg(("Something went wrong...", {'type': 'system'}))
			return
		
		caller.actions.add(action, mat, tool)

class CmdCarve(Command):
	"""
	Carve a piece of wood or stone

	Usage:
		carve <obj>


	"""
	key = "carve"
	locks = "cmd:all()"
	help_category = "Crafting"

	def func(self):
		caller = self.caller

		skill_level = caller.skills.sketching.value


		candidates = [obj for obj in caller.location.contents+caller.contents if obj.tags.has(["wood", "stone"], category="design_base")]
		obj = yield from self.find_targets(self.lhs, candidates=candidates, numbered=False)
		if not obj:
			return
		if not obj.access(caller, 'design'):
			caller.msg("You can't carve that.")
			return

		base = obj.tags.get(category="design_base", return_list=True)
		if not base:
			caller.msg("You can't carve that.")
			return
		base = base[0]

		if base == "wood":
			tool_name = "knife"
		elif base == "stone":
			tool_name = "chisel"
		else:
			caller.msg("You can't carve that.")
			return

		tools = [obj for obj in caller.contents + caller.location.contents if obj.tags.has(tool_name, category="craft_tool")]
		if not tools:
			caller.msg(f"You need a {tool_name} to carve that.")
			return

		tool = tools[0]

		tool_str = f" with {tool.get_display_name(caller, article=True, process=False, noid=True)}"

		if not obj.descs.get_design():
			desc = yield(f"What do you carve into the {obj.get_display_name(caller, article=False)}?")
			desc = desc.replace("|/", "\n")
			desc = strip_ansi(desc)
			if len(desc) > 240:
				caller.msg("Your design is too long; please try again with a shorter description.")
				return

			caller.msg(f"Your carving will look like this:\n{desc}")
			confirm = yield("You can $h(|lccontinue|ltcontinue|le) to add details, $h(|lcstop|ltstop|le) to finish, or $h(|lccancel|ltcancel|le) to do nothing.")
			caller.ndb.last_active = time.time()
			if "continue" in confirm.lower() or "stop" in confirm.lower():
				caller.emote(
					f"@Me begins carving {obj.get_display_name(caller, article=True, process=False, noid=True)}{tool_str}.")
				caller.ndb.pose = f"carving {_INFLECT.an(obj.sdesc.get())}"
				obj.locks.add(f"design:id({caller.dbref})")
				obj.descs.add_design(desc)
				caller.exp += 1
				if "continue" in confirm.lower():
					self.add_detail(caller, skill_level, obj)
				elif "stop" in confirm.lower():
					self.finish_carving(caller, obj, 1)
			else:
				caller.msg("You don't carve anything.")
				return
		else:
			caller.emote(
				f"@Me begins carving {obj.get_display_name(caller, article=True, process=False, noid=True)}{tool_str}.")
			caller.ndb.pose = f"carving {_INFLECT.an(obj.sdesc.get())}"
			self.add_detail(caller, skill_level, obj)
			return

	@interactive
	def add_detail(self, caller, level, obj):
		xp_gain = 0
		max_details = int(level // 20)
		details = [ob for ob in obj.contents if
		           inherits_from(ob, 'core.typeclasses.DetailObject') and ob.tags.has("attached", category="crafting")]
		design = strip_ansi(obj.descs.get_design())
		while True:
			caller.ndb.last_active = time.time()
			detail = None
			info = []
			if len(details):
				info.append(f"You have added detail to {iter_to_str([ob.name for ob in details])}.")
			if len(details) < max_details:
				info.append(f"You are skilled enough to add new detail to {max_details - len(details)} more elements.")
			else:
				info.append("You cannot add new detail, only redo your current details.")
			caller.msg("\n".join(info))
			option = yield(
				"Enter an element you want to add more detail to (e.g. \"evergreen tree\"). Or, $h(|lclook|ltlook|le) to review your carving, or $h(|lcstop|ltstop|le) to finish.")
			option = option.strip().lower()
			if option in ("finish", "done", "stop",):
				self.finish_carving(caller, obj, xp_gain)
				return
			elif option in ("l", "look"):
				caller.msg((caller.at_look(obj), {"target": "look"}))
				continue

			results = caller.search(option, candidates=details, quiet=True)
			if len(results) == 0:
				# find matching text in image
				refind = re.compile(rf"\b({option})\b", re.I)
				results = refind.findall(design)
				if len(results) > 1:
					caller.msg("That element is too vague.")
					continue
				elif len(results) < 1:
					caller.msg(f"There is no {option} in your carving.")
					continue
				else:
					detail = create.object('core.typeclasses.DetailObject', key=option, location=obj)
					detail.tags.add("attached", category="crafting")
					xp_gain += 1
			elif len(results) > 1:
				# multimatch
				dstr = f"Which {option} do you want to change?\nEnter a number:\n "
				dstr += f"\n ".join([f"|lc{i + 1}|lt{i + 1}|le {ob.get_display_name(caller)}" for i, ob in enumerate(results)])
				di = yield(dstr)
				try:
					di = int(di)
					di -= 1
				except ValueError:
					caller.msg("Invalid choice.")
					continue
				if di > len(results):
					caller.msg("Invalid choice.")
					continue
				detail = results[di]
			else:
				detail = results[0]

			if detail:
				desc = yield(f"Describe the {option}:")
				desc = desc.replace("|/", "\n")
				desc = strip_ansi(desc)
				detail.materials.clear()
				detail.desc.add(desc)
				inp = yield(f"You added detail for {option}. Keep working?")
				if "Y" not in inp:
					break

		self.finish_carving(caller, obj, xp_gain)

	def finish_carving(self, caller, obj, xp):
		design = strip_ansi(obj.descs.get_design())
		obname = obj.sdesc.get()
		details = [ob for ob in obj.contents if
		           inherits_from(ob, 'core.typeclasses.DetailObject') and ob.tags.has("attached", category="crafting")]
		for detail in details:
			name = detail.name
			design = design.replace(name, f"|lclook at {name} on {obname}|lt{name}|le")
		obj.descs.add_design(design)
		caller.ndb.last_active = time.time()
		caller.exp += xp
		caller.nattributes.remove("pose")
		caller.emote("@Me stops carving.")

class CmdRecipes(Command):
	"""
	Manage your memorized recipes

	Usage:
		recipes
		recipe <recipe name>
		rename recipe <recipe> as <new name>
		forget recipe <recipe>
	
	Examples:
		recipe cabinet
		rename recipe large cabinet as chonky boi
	"""
	key = "recipes"
	aliases = ("recipe", "rename recipe", "forget recipe")
	locks = "cmd:all()"
	help_category = "Crafting"
	prefixes = ("as",)

	def func(self):
		if self.cmdstring == "rename recipe":
			old_name = self.argsdict.get(None)
			new_name = self.argsdict.get("as")
			if not (old_name and new_name):
				self.msg("Usage: rename recipe <old name> as <new name>")
				return
			old_name = old_name[0]
			new_name = new_name[0]
			matches = self.caller.recipes.search(old_name)
			if not matches:
				self.msg(f"You don't know any recipes like $h({old_name}).")
				return
			elif len(matches.keys()) > 1:
				recipes = [ (val, key) for key, val in matches.items() ]
				self.multimatch_msg(old_name, recipes, match_cmd=True) # hacky fix
				index = yield ("Enter a number (or $h(c) to cancel):")
				recipe = self.process_multimatch(index, recipes)
				if not recipe:
					return
				old_name = recipe[1]
			else:
				old_name = tuple(matches.keys())[0]

			if old_name == new_name:
				self.msg(f"$h({old_name} is already named $h({new_name}).")
				return
			# do the rename!
			if not self.caller.recipes.rename_recipe(old_name, new_name):
				self.msg(f"You couldn't rename $h({old_name}) to $h({new_name}).")
			else:
				self.msg(f"Recipe $h({old_name}) renamed to $h({new_name}).")
		
		elif self.cmdstring == "forget recipe":
			if not self.args:
				self.msg("Forget which recipe?")
				return
			matches = self.caller.recipes.search(self.args)
			if not matches:
				self.msg(f"You don't know any recipes like $h({self.args}).")
				return
			elif len(matches.keys()) > 1:
				recipes = [ (val, key) for key, val in matches.items() ]
				self.multimatch_msg(self.args, recipes, match_cmd=True) # hacky fix
				index = yield ("Enter a number (or $h(c) to cancel):")
				recipe = self.process_multimatch(index, recipes)
				if not recipe:
					return
				recipe_key = recipe[1]
			else:
				recipe_key = tuple(matches.keys())[0]
			if not self.caller.recipes.remove(recipe_key):
				self.msg(f"You couldn't forget $h({recipe_key}).")
			else:
				self.msg(f"You no longer know a recipe named $h({recipe_key}).")

		elif not self.args:
			# TODO: paginate
			self.msg("Your memorized recipes:")
			self.msg(iter_to_str(self.caller.recipes.keys()))

		else:
			matches = self.caller.recipes.search(self.args)
			if not matches:
				self.msg(f"You don't know any recipes like $h({self.args}).")
			elif len(matches.keys()) > 1:
				self.msg(f"You know the following recipes like $h{self.args}:")
				self.msg(iter_to_str(matches.keys()))
			else:
				key, data = tuple(matches.items())[0]
				self.msg(text=(f"$head({key})\n"+data.get('desc'), {'target': 'modal'}))

			

class CmdMake(Command):
	"""
	Make something using a memorized recipe.

	Usage:
		make <recipe> [with <ingredient>, <ingredient>]
	"""
	key = "make"
	aliases = ("craft",)
	locks = "cmd:all()"
	help_category = "Crafting"
	prefixes = ("with",)
	splitters = ','

	def parse(self):
		super().parse()
		self.recipe_key = ''
		self.materials = []
		if self.argsdict:
			if recipe_key := self.argsdict.get(None):
				self.recipe_key = ",".join(recipe_key)
			for key in self.argsdict.keys():
				if key:
					self.materials += self.argsdict.get(key)
		elif self.argslist:
			self.recipe_key = self.argslist[0]
		if len(self.argslist) > 1:
			self.materials = self.argslist[1].split(',')

	def func(self):
		"""Implement command"""
		caller = self.caller
		if not self.recipe_key:
			caller.msg("Make what?")
			return

		recipes = caller.recipes.search(self.recipe_key)
		if not recipes:
			self.msg(f"You don't know how to make $h({self.recipe_key}).")
			return
		elif len(recipes.keys()) == 1:
			recipe = tuple(recipes.values())[0]
		else:
			recipes = [ (val, key) for key, val in recipes.items() ]
			self.multimatch_msg(self.recipe_key, recipes, match_cmd=True) # hacky fix
			index = yield ("Enter a number (or $h(c) to cancel):")
			recipe = self.process_multimatch(index, recipes)
			if not recipe:
				return
			recipe = recipe[0]

		# get materials
		materials = []
		for sterm in self.materials:
			use_obj = yield from self.find_targets(sterm, stack=True)
			if not use_obj:
				return
			materials += use_obj

		if not (recipe_list := recipe.get('recipes')):
			self.msg("Invalid recipe.")
			return
		
		started = False
		for do_me in recipe_list:
			action_type = actions.AssembleAction if do_me['recipe'] == 'ASSEMBLE' else actions.CraftAction
			try:
				action = action_type(caller, do_me, ingredients=materials)
			except InterruptAction:
				if not started:
					self.msg(f"Could not make {self.recipe_key}")
				return
			started = True
			caller.actions.add(action)

class CmdRecord(Command):
	"""
	Memorize instructions on how to craft a replica of an existing object.

	Usage:
		memorize <obj> [as <name>]
	"""
	key = "memorize"
	locks = "cmd:all()"
	prefixes = ("as",)
	help_category = "Crafting"

	def parse(self):
		super().parse()
		self.obj_name = ''
		self.recipe_key = ''
		if self.argsdict:
			self.obj_name = self.argsdict.pop(None, '')
			if self.obj_name:
				self.obj_name = self.obj_name[0]
			if self.argsdict:
				# TODO: this is janky
				if custom_key := list(self.argsdict.values())[0]:
					self.recipe_key = custom_key[0].strip()
		else:
			self.obj_name = self.args

	def func(self):
		caller = self.caller

		if not self.args:
			caller.msg("You need a craftable object to memorize.")
			return

		crafted = yield from self.find_targets(self.obj_name, numbered=False)
		if not crafted:
			return
		# TODO: skill checks
		if caller.recipes.record_object(crafted, key=self.recipe_key):
			if self.recipe_key:
				self.msg(f"You memorize how to make {crafted.get_display_name(caller, article=True, noid=True)} as $h({self.recipe_key}).")
			else:
				self.msg(f"You memorize how to make {crafted.get_display_name(caller, article=True, noid=True)}.")
		else:
			caller.msg("You couldn't memorize how to make that.")


class CmdAttach(ToolActionCommand):
	"""
	Attach or add one crafted piece to another.
	
	Usage:
		attach <obj>[, ... <obj>] to <obj>
		add <obj> to <obj>
	
	Examples:
		attach sleeve to shirt
		add sliced ham, lettuce to sandwich

	"""
	key = "attach"
	aliases = ["add"]
	prefixes = ("to",)
	locks = "cmd:all()"
	help_category = "Crafting"
	action = actions.AttachAction
	err_msg = "You cannot combine those."

	# TODO: proper parse function
	def parse(self):
		super().parse()
		self.targets = self.argsdict.get(None)
		self.base_obj = self.argsdict.get('to')

	def _validate_targets(self, targets, **kwargs):
		return [obj for obj in targets if obj.access(self.caller, 'craftwith')]

	def _filter_candidates(self, candidates, **kwargs):
		return [obj for obj in candidates if obj.access(self.caller, 'craftwith')]


class CmdDetach(ActionCommand):
	"""
	Detach a removable piece from a crafted object
	
	Usage:
		detach <obj>[, ... <obj>] from <obj>
		remove <obj> from <obj>
	
	Examples:
		detach sleeve from shirt
		remove sliced ham, lettuce from sandwich

	"""
	key = "detach"
	aliases = ["remove"]
	prefixes = ("from",)
	locks = "cmd:all()"
	help_category = "Crafting"
	action = actions.DetachAction
	err_msg = "You cannot remove that."


	# TODO: proper parse function
	def parse(self):
		super().parse()
		self.targets = self.argsdict.get(None)
		self.base_obj = self.argsdict.get('from')

	def _validate_targets(self, targets, **kwargs):
		return [obj for obj in targets if obj.access(self.caller, 'craftwith')]

	def _filter_candidates(self, candidates, **kwargs):
		return [obj for obj in candidates if obj.access(self.caller, 'craftwith')]


	def func(self):
		target = None
		if base_obj := self.base_obj:
			base_obj = base_obj[0]
			if getattr(self, 'tail', None):
				target, tail = yield from self.find_targets(base_obj[0], filter_cands=self._validate_targets, numbered=False, tail=True)
				self.tail_str = tail
			else:
				target = yield from self.find_targets(base_obj, filter_cands=self._validate_targets, numbered=False)
			self.tail = False
		else:
			self.msg("Remove from what?")
			return
		if not target:
			return
		self.action_kwargs |= { 'base_obj': target }
		self.location = target
		yield from super().func()


class CmdAutoCraft(Command):
	"""
	Builder tool for automatically generating crafted items.

	Example:
	  autocraft tunic base with 2 short sleeves (round button)
	"""
	key = "autocraft"
	prefixes = ('with',)
	splitters = (',',)
	locks = "cmd:pperm(Builder)"

	def parse(self):
		"""build the dict and subdicts for the crafting"""
		super().parse()
		self.base = self.argsdict.get(None)
		self.addons = ",".join(self.argsdict.get('with',[]))
	
	def _parse_subparts(self, text: str):
		def _count_and_find(r):
			num, term = self._parse_num(r)
			num = num or 1
			key = yield from self._find_recipe(term)
			if not key:
				raise InterruptCommand
			return key, num

		if text.count('(') != text.count(')'):
			self.msg("Invalid input! You have mismatched parentheses.")
			raise InterruptCommand
		if "(" not in text:
			recipes = [t.strip() for t in text.split(',') if t]
			results = []
			for r in recipes:
				key, num = yield from _count_and_find(r)
				results.extend([key]*num)
			return results

		start, middle = text.split('(', maxsplit=1)
		middle, end = middle.rsplit(')', maxsplit=1)

		results = []
		start = [ t.strip() for t in start.split(',') if t]
		end = [ t.strip() for t in end.split(',') if t]
		middle_key = start[-1]
		middle = yield from self._parse_subparts(middle)
		start = start[:-1]

		# build the start
		for r in start:
			key, num = yield from _count_and_find(r)
			results.extend([key]*num)
	
		# now the middle
		middle_key, num = yield from _count_and_find(middle_key)
		middle = {middle_key: middle}
		results.extend([middle]*num)
		
		# and finally the tail
		for r in end:
			key, num = yield from _count_and_find(r)
			results.extend([key]*num)

		return results
	
	def _find_recipe(self, search_term):
		parts = search_term.lower().split()
		matches = [key for key in RECIPE_DICTS if all(p in key for p in parts)]
		if len(matches) > 1:
			self.multimatch_msg(search_term, matches)
			index = yield("Enter a number (or $h(c) to cancel):")
			key = self.process_multimatch(index, matches)
		elif not matches:
			self.msg(f"No recipe keys match '{search_term}'")
			key = ''
		else:
			key = matches[0]
		return key


	def func(self):
		if not self.base:
			self.msg("You have to make something....")
			return

		if len(self.base) > 1 and self.addons:
			self.msg("You can only generate one base object with parts at a time.")
			return
		
		if self.args.startswith("search"):
			_, search_term = self.args.split(' ', maxsplit=1)
			parts = search_term.split()
			matches = [key for key in RECIPE_DICTS if all(p in key for p in parts)]
			if matches:
				self.msg(f"Recipe keys matching '{search_term}':\n"+", ".join(matches))
			else:
				self.msg(f"No recipe keys match '{search_term}'.")
			return
		
		numbered_bases = [ self._parse_num(recipe) for recipe in self.base ]
		base_recipes = []
		for num, base in numbered_bases:
			recipe = yield from self._find_recipe(base)
			if not recipe:
				return
			num = num or 1
			base_recipes.append((num, recipe))
		if self.addons:
			quantity, base = base_recipes[0]
			addons = yield from self._parse_subparts(self.addons)
			recipes = [{"recipe": "ASSEMBLE", "base": base, "adds": addons }]*quantity
		else:
			recipes = []
			for num, recipe in base_recipes:
				recipes.extend([recipe]*num)

		self.msg(f"Initiating auto-crafting; check your {'location' if self.caller.location else 'contents'} for the results.")

		dropoff = self.caller.location or self.caller

		gener = generate_new_object(recipes, {}, dropoff)
		delay_iter(gener, 0.1)


# CmdSet for all crafting skills

class CraftingCmdSet(CmdSet):
	"""
	Command set for crafting disciplines.
	"""

	key = "Crafting CmdSet"

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
		self.add(CmdRecord())
		self.add(CmdRecipes())
		self.add(CmdMake())
		self.add(CmdDraw())
		self.add(CmdWrite())
		# self.add(CmdCarve())
		# self.add(CmdToolUse())
		self.add(CmdAttach())
		self.add(CmdDetach())
		self.add(CmdAutoCraft)


class CraftableCmdSet(CmdSet):
	"""
	Command set for manipulating craftable objects.
	"""

	key = "Craftables CmdSet"

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
