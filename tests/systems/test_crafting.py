"""
Tests for the crafting system

"""
import time
import unittest
from functools import partial
from mock import MagicMock, patch
from anything import Anything

from evennia.commands.command import InterruptCommand

from base_systems.prototypes.spawning import spawn
from systems.skills.skills import add_skill_tree
from utils.colors import strip_ansi

from utils.testing import NexusTest, NexusCommandTest, undelay
from utils.timing import delay_iter
from systems.crafting import commands, tool_prototypes, actions, automate
from data.recipes.clothing import CLOTHING_SLEEVE_SHORT, CLOTHING_TUNIC_BASE


CLOTHING_SLEEVE_SHORT |= {"recipe": "CLOTHING_SLEEVE_SHORT", "locks": "craftwith:perm(Player)",}
CLOTHING_TUNIC_BASE |= {"recipe": "CLOTHING_TUNIC_BASE", "locks": "craftwith:perm(Player)",}

TEST_SKILL_TREE = {
	"sewing": {
		"name": "Sewing",
		"base": "25",
		"cap": 50,
		"descs": {},
		"stat": "spd",
		"subskills": {
			"tailoring": { "name": "Tailoring", "base": 50, "cap": 100, "stat": "int" },
		}
	},
}

THREAD = 	{
		"key": "thread",
		"typeclass": "base_systems.things.base.Thing",
		"_sdesc_prefix": "spool of",
		"tags": [("thread", "craft_material"),],
		"desc": "A spool of plain, uncolored sewing thread.",
		"locks": "craftwith:perm(Player)",
		"size": 50,
}
FABRIC = {
		"key": "red linen",
		"typeclass": "base_systems.things.base.Thing",
		"_sdesc_prefix": "bolt of",
		"desc": "A bolt of red linen.",
		"tags": [("fabric", "craft_material"), ("fabric", "design_material")],
		"locks": "craftwith:perm(Player)",
		"materials": { "linen": { "color": "red", "pattern": "", "format": "{color} {pattern}", "pigment": (255, 0, 0), "color_quality": 4 } },
		"quality": (5, ""),
		"size": 50,
		"units": "yards",
}

ASSEMBLY = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_TUNIC_BASE",
	"adds": ["CLOTHING_SLEEVE_SHORT","CLOTHING_SLEEVE_SHORT",],
	"skill": "tailoring"
}

@patch('base_systems.actions.queue.delay', new=undelay)
class TestAutoCrafting(NexusTest):
	# @patch('utils.timing.delay', new=undelay)
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.player = self.create_player()

	@patch('utils.timing.delay', new=undelay)
	def test_generate_from_dict(self):
		recipes = [ CLOTHING_TUNIC_BASE, CLOTHING_SLEEVE_SHORT, CLOTHING_SLEEVE_SHORT, ASSEMBLY ]
		materials = { 'fabric': FABRIC['materials'].items() }
		gener = automate.generate_new_object(recipes, materials, location=self.room)
		delay_iter(gener)
		crafted = self.room.contents[-1]
		self.assertEqual(crafted.key, "red tunic")
		self.assertEqual(len(crafted.parts.all()), 2)
		desc = crafted.get_display_desc(self.player)
		self.assertEqual(desc, "A red linen tunic, with two short sleeves.")

	@patch('utils.timing.delay', new=undelay)
	def test_generate_from_keys(self):
		recipes = [ 'CLOTHING_TUNIC_BASE', 'CLOTHING_SLEEVE_SHORT', 'CLOTHING_SLEEVE_SHORT', ASSEMBLY ]
		materials = { 'fabric': FABRIC['materials'].items() }
		gener = automate.generate_new_object(recipes, materials, location=self.room)
		delay_iter(gener)
		crafted = self.room.contents[-1]
		self.assertEqual(crafted.key, "red tunic")
		self.assertEqual(len(crafted.parts.all()), 2)
		desc = crafted.get_display_desc(self.player)
		self.assertEqual(desc, "A red linen tunic, with two short sleeves.")

	@patch('utils.timing.delay', new=undelay)
	def test_generate_from_assembly(self):
		recipes = [ ASSEMBLY ]
		materials = { 'fabric': FABRIC['materials'].items() }
		gener = automate.generate_new_object(recipes, materials, location=self.room)
		delay_iter(gener)
		crafted = self.room.contents[-1]
		self.assertEqual(crafted.key, "red tunic")
		self.assertEqual(len(crafted.parts.all()), 2)
		desc = crafted.get_display_desc(self.player)
		self.assertEqual(desc, "A red linen tunic, with two short sleeves.")

	@patch('utils.timing.delay', new=undelay)
	def test_generate_pair(self):
		recipes = [ 'CLOTHING_SLEEVE_SHORT' ]
		materials = { 'fabric': FABRIC['materials'].items() }
		gener = automate.generate_new_object(recipes, materials, matched_set=True, location=self.room)
		delay_iter(gener)
		sleeves = self.room.contents[-2:]
		for obj in sleeves:
			self.assertEqual(obj.key, "short red sleeve")

		leftright = sleeves[0].tags.get(category='subtype')
		rightleft = sleeves[1].tags.get(category='subtype')
		self.assertNotEqual(leftright, rightleft)
		self.assertIn(leftright, ('left', 'right'))
		self.assertIn(rightleft, ('left', 'right'))


	@patch('utils.timing.delay', new=undelay)
	@patch('systems.crafting.automate.choice', new=lambda *args: args[0][0])
	def test_generate_with_opts(self):
		mat_opt = ( ("linen","cotton"), { "color": ("red","blue"), "pattern": "", "format": "{color} {pattern}", "pigment": (255, 0, 0), "color_quality": 4 } )
		recipes = [ 'CLOTHING_TUNIC_BASE', 'CLOTHING_SLEEVE_SHORT', 'CLOTHING_SLEEVE_SHORT', ASSEMBLY ]
		materials = { 'fabric': [ mat_opt ] }
		gener = automate.generate_new_object(recipes, materials, location=self.room)
		delay_iter(gener)
		crafted = self.room.contents[-1]
		self.assertEqual(crafted.key, "red tunic")
		self.assertEqual(len(crafted.parts.all()), 2)
		desc = crafted.get_display_desc(self.player)
		self.assertEqual(desc, "A red linen tunic, with two short sleeves.")
	

@patch('base_systems.actions.queue.delay', new=undelay)
class TestCraftingAction(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.room = self.create_room()
		self.player.location = self.room
		self.tools = spawn(tool_prototypes.TOOL_SEWING_SCISSORS, tool_prototypes.TOOL_SEWING_NEEDLE)
		self.materials = spawn(THREAD, FABRIC)
		for key, value in FABRIC['materials'].items():
			self.materials[1].materials.add(key, **value)
		for obj in self.tools + self.materials:
			obj.location = self.room
#		add_skill_tree(self.player, TEST_SKILL_TREE)
		self.player.skills.tailoring.base = 50

	#	@patch('base_systems.actions.queue.ActionQueue.add')
	# @patch('systems.crafting.actions.delay', new=undelay)
	@patch('systems.crafting.actions.delay')
	def test_initialize(self, mock_delay):
		crafter = self.player
		action = actions.CraftAction(crafter, {'recipe':'clothing_tunic_base', 'last': True})
		mock_delay.assert_not_called()
		self.assertEqual(action.quantity, 1)
		action = actions.CraftAction(crafter, {'recipe':'clothing_tunic_base', 'last': True}, quantity=2)
		self.assertEqual(action.quantity, 2)

	@patch('systems.crafting.actions.delay')
	def test_start(self, mock_delay):
		crafter = self.player
		action = actions.CraftAction(crafter, 'clothing_tunic_base')
		action.start()
		self.assertEqual(action.i, 1)
		self.assertEqual(action.do_args, (('tailoring',5), "red linen"))
		mock_delay.assert_called_once()

	@patch('systems.crafting.actions.delay')
	def test_do(self, mock_delay):
		crafter = self.player
		# set up the action
		action = actions.CraftAction(crafter, {'recipe':'clothing_tunic_base', 'last': True}, i=1, xp_gain=0)
		action.tools = self.tools
		action.ingredients = [(self.materials[1], 6, True), (self.materials[0], 1, False)]
		action.recipe = dict(CLOTHING_TUNIC_BASE)
		# test it
		self.assertTrue(action.do(('tailoring',5), "red linen"))
		self.assertEqual(action.do_args, (('tailoring',5), "red linen"))
		self.assertEqual(action.i, 2)
		mock_delay.assert_called_once()

	@patch('systems.crafting.actions.delay')
	def test_finish(self, mock_delay):
		crafter = self.player
		# the ingredients are supposed to be the ITEMS......
		action = actions.CraftAction(crafter, 'clothing_tunic_base', ingredients=self.materials)
		# run start just to initialize the data
		action.start()
		action.finish()
		self.assertEqual(self.materials[0].size,49) # thread
		self.assertEqual(self.materials[1].size,44) # fabric
		# self.assertEqual(len(crafter.ndb.craft_pieces),1)

	@patch('systems.crafting.actions.delay')
	def test_assemble(self, mock_delay):
		crafter = self.player
		pieces = spawn(CLOTHING_TUNIC_BASE, CLOTHING_SLEEVE_SHORT, CLOTHING_SLEEVE_SHORT)
		pieces[0].tags.add("clothing_tunic_base", category="recipe_key")
		pieces[1].tags.add("clothing_sleeve_short", category="recipe_key")
		pieces[2].tags.add("clothing_sleeve_short", category="recipe_key")
		for obj in pieces:
			obj.location = crafter
		self.assertEqual(len(crafter.contents), len(pieces))
		action = actions.AssembleAction(crafter, ASSEMBLY)
		action.start()
		# print(vars(action))
		self.assertEqual(len(crafter.contents), 1)
		mock_delay.assert_called_once()

	def test_generate_desc(self):
		# TODO: move this to the Things tests once i have some
		crafter = self.player
		piece = spawn(CLOTHING_TUNIC_BASE)[0]
		t0 = time.time()
		piece.generate_desc()
		t1 = time.time()
#		self.assertLess(t1-t0, 0.035)
		self.assertEqual(piece.key, "tunic")
		for obj in self.materials:
			for key, value in obj.materials.get("all", as_data=True):
				piece.materials.merge(key, **value)
		piece.generate_desc()
		self.assertEqual(piece.key, "red tunic")


class TestRecipeHandler(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.room = self.create_room()
		self.player.location = self.room
		self.tools = spawn(tool_prototypes.TOOL_SEWING_SCISSORS, tool_prototypes.TOOL_SEWING_NEEDLE)
		self.materials = spawn(THREAD, FABRIC)
		for key, value in FABRIC['materials'].items():
			self.materials[1].materials.add(key, **value)
		for obj in self.tools + self.materials:
			obj.location = self.room
		self.player.skills.add("tailoring", "Tailoring", max=100, min=0, base=50, trait_type="counter")

	def test_record_object(self):
		# with auto-key
		tunic = spawn(CLOTHING_TUNIC_BASE)[0]
		tunic.tags.add('clothing_tunic_base', category='recipe_key')
		self.assertTrue(self.player.recipes.record_object(tunic))
		self.assertIn("tunic", self.player.recipes._data)
		desc = self.player.recipes._data.get("tunic").get('desc')
		self.assertIn("Instructions on how to make a tunic", desc)
		# with user-set key
		self.assertTrue(self.player.recipes.record_object(tunic, key="fancy tunic"))
		self.assertIn("fancy tunic", self.player.recipes._data)


	def test_set_recipe(self):
		crafter = self.player
		self.assertTrue(self.player.recipes.set_recipe("clothing_tunic_base"))
		self.assertIn("tunic", self.player.recipes._data.keys())
		desc = self.player.recipes._data.get("tunic").get('desc')
		self.assertIn("Instructions on how to make a tunic with no sleeves", desc)
		self.assertTrue(self.player.recipes.set_recipe("clothing_tunic_base"))
		self.assertIn("tunic 1", self.player.recipes._data.keys())


class TestCraftingCommands(NexusCommandTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.caller.location = self.room

	def test_make(self):
		self.caller.recipes.set_recipe("clothing_tunic_base")
		materials = spawn(THREAD, FABRIC)
		for m in materials:
			m.location = self.caller
		self.call(commands.CmdMake(), "hat", "You don't know how to make $h(hat).")
		with patch('base_systems.actions.queue.ActionQueue.add') as mock_do:
			self.call(commands.CmdMake(), "tunic")
			mock_do.assert_called_once()
			mock_do.reset_mock()
			result = self.call(commands.CmdMake(), "tunic with linen")
			mock_do.assert_called_once()

	def test_record(self):
		tunic = spawn(CLOTHING_TUNIC_BASE)[0]
		tunic.location = self.caller
		tunic.key = "tunic"
		tunic.tags.add("CLOTHING_TUNIC_BASE", category="recipe_key")
		self.call(commands.CmdRecord(), "tunic", "You memorize how to make a tunic")
		self.call(commands.CmdRecord(), "tunic as fancy tunic", "You memorize how to make a tunic as $h(fancy tunic)")

	@patch('systems.crafting.actions.delay', new=undelay)
	def test_attach(self):
		tunic_recipe = CLOTHING_TUNIC_BASE | { "location": self.caller, "locks": "craftwith:true()", "key": "tunic" }
		sleeve_recipe = CLOTHING_SLEEVE_SHORT | { "location": self.caller, "locks": "craftwith:true()", "key": "sleeve" }
		tunic, sleeve = spawn(tunic_recipe, sleeve_recipe)
		self.call(commands.CmdAttach(), "sleeve to tunic", "Caller adds a sleeve to a tunic")

	@patch('systems.crafting.actions.delay', new=undelay)
	def test_detach(self):
		tunic_recipe = CLOTHING_TUNIC_BASE | { "location": self.caller, "locks": "craftwith:true()", "key": "tunic" }
		sleeve_recipe = CLOTHING_SLEEVE_SHORT | { "locks": "craftwith:true()", "key": "sleeve" }
		tunic, sleeve = spawn(tunic_recipe, sleeve_recipe)
		sleeve.tags.add("attached", category="crafting")
		sleeve.location = tunic
		self.call(commands.CmdDetach(), "sleeve from tunic", "Caller removes a sleeve from a tunic")

	# TODO: test ToolUse and Draw


def _fake_recipe(self, text):
	yield
	return text

class TestAutocraftCommand(NexusCommandTest):
	@patch('systems.crafting.commands.CmdAutoCraft._find_recipe', new=_fake_recipe)
	@patch('systems.crafting.commands.CmdAutoCraft.msg')
	def test_parse_subparts(self, mock_msg):
		cmd = commands.CmdAutoCraft()

		with self.assertRaises(InterruptCommand):
			list(cmd._parse_subparts("This has (mismatched parens"))
		
		unnested = "a, b, c"
		unnested_return = ['a', 'b', 'c']
		gener = cmd._parse_subparts(unnested)
		self.assertInteractiveResult(gener, unnested_return)

	@patch('systems.crafting.commands.CmdAutoCraft._find_recipe', new=_fake_recipe)
	@patch('systems.crafting.commands.CmdAutoCraft.msg')
	def test_condensed_parse_subparts(self, mock_msg):
		cmd = commands.CmdAutoCraft()
		# # the incoming arguments are comma separated but not space separated
		unnested = "a,b,c"
		unnested_return = ['a', 'b', 'c']
		gener = cmd._parse_subparts(unnested)
		self.assertInteractiveResult(gener, unnested_return)

	@patch('systems.crafting.commands.CmdAutoCraft._find_recipe', new=_fake_recipe)
	def test_nested_parse_subparts(self):
		cmd = commands.CmdAutoCraft()

		nest_once = "a, b (c, d), e"
		nest_once_result = ['a', {'b': ['c', 'd']}, 'e']
		gener = cmd._parse_subparts(nest_once)
		self.assertInteractiveResult(gener, nest_once_result)

		nest_twice = "a, b (c (e, f), g), h, i"
		nest_twice_result = ['a', {'b': [{'c': ['e', 'f']}, 'g']}, 'h', 'i']
		gener = cmd._parse_subparts(nest_twice)
		self.assertInteractiveResult(gener, nest_twice_result)

	@patch('systems.crafting.commands.CmdAutoCraft._find_recipe', new=_fake_recipe)
	def test_numbered_parse_subparts(self):
		cmd = commands.CmdAutoCraft()

		numbered = "2 a, b, 3 c"
		numbered_return = ['a', 'a', 'b', 'c', 'c', 'c']
		gener = cmd._parse_subparts(numbered)
		self.assertInteractiveResult(gener, numbered_return)

		nested_numbered = "a, 2 b (c, d), e"
		nested_numbered_return = ['a', {'b': ['c', 'd']}, {'b': ['c', 'd']}, 'e']
		gener = cmd._parse_subparts(nested_numbered)
		self.assertInteractiveResult(gener, nested_numbered_return)


#	@patch('systems.crafting.commands.CmdAutoCraft._find_recipe', new=_fake_recipe)
	@patch('utils.timing.delay', new=undelay)
	def test_cmd(self):
		result = self.call(commands.CmdAutoCraft(), "small round table with 4 short basic legs", "Initiating auto-crafting; check your location for the results.")
		# self.assertEqual(len(self.caller.contents), 1)
		table = self.caller.location.contents[-1]
		self.assertIn('table', table.name)
		self.assertEqual(len(table.parts.all()), 4)
		self.assertEqual(len(table.parts.search('leg')), 4)

from utils.menus import FormatEvMenu

_ERROR_FORMAT = """
===== Wanted message =======
{expected_msg}
===== Returned message =====
{returned_msg}
============================
""".rstrip()


class TestDrawing(NexusCommandTest):
	def setUp(self):
		super().setUp()
		self.player_setup(puppet=self.caller)
		self.session.msg = MagicMock()

	def initialize_menu(self, start_node):
		return FormatEvMenu(self.session, "systems.crafting.menus.drawing", startnode=start_node)

	def verify_msg(self, nodetext, options=[]):
		"""helper method to verify the message on a menu node"""
		mock_obj = self.session.msg
		mock_obj.assert_called_once()
		kwargs = self.session.msg.call_args_list[0].kwargs
		if not (text := kwargs.get('text')):
			raise AssertionError("'text' kwarg not found in session.msg call")
		if type(text) is str:
			text = strip_ansi(text.strip())
		else:
			text = strip_ansi(text[0].strip())
		nodetext = strip_ansi(nodetext)
		if not text.startswith(nodetext):
			raise AssertionError(
				_ERROR_FORMAT.format(expected_msg=nodetext, returned_msg=text)
			)
		for optstring in options:
			if optstring not in text:
				raise AssertionError(
					_ERROR_FORMAT.format(expected_msg=optstring, returned_msg=text)
				)
		self.session.msg.reset_mock()
	
	def test_draw_action(self):
		pass

	def test_draw_menu(self):
		pass