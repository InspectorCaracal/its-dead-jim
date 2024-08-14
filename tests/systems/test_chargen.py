from mock import MagicMock, patch
from unittest import skip
from systems.chargen import gen
from utils.colors import strip_ansi
from utils.testing import NexusTest, undelay

class TestPartsGen(NexusTest):
	"""test generation of character parts"""
	def setUp(self):
		super().setUp()
		self.obj1 = self.create_object()
		self.obj1.archetype = None

	def test_core_parts_gen(self):
		gen.create_core_parts(self.obj1)
		parts = self.obj1.parts.all()
		self.assertEqual(len(parts), 6)
 
	def test_face_gen(self):
		gen.create_face_parts(self.obj1)
		parts = self.obj1.parts.all()
		self.assertEqual(len(parts), 8)
		self.assertTrue(self.obj1.parts.search("eye"))
	
	def test_arm_gen(self):
		gen.create_arm_parts(self.obj1, "left")
		parts = self.obj1.parts.all()
		self.assertEqual(len(parts), 13)
		self.assertEqual(len(self.obj1.parts.search("finger")), 4)

	def test_leg_gen(self):
		gen.create_leg_parts(self.obj1, "left")
		parts = self.obj1.parts.all()
		self.assertEqual(len(parts), 7)
		self.assertTrue(self.obj1.parts.search("foot"))

	def test_all_gen(self):
		self.obj1.tags.add('generating')
		for _ in gen.init_bodyparts(self.obj1):
			continue
		self.assertEqual(len(self.obj1.parts.all()),56)


class TestFeatureGen(NexusTest):
	"""test setting, generating, and otherwise updating features"""
	def setUp(self):
		super().setUp()
		self.player = self.create_player()

	def test_set_features(self):
		gen.set_character_feature(self.player, "eye", color='|#5A97D6blue|n')
		self.player.update_features() # apply changes from parts
		self.assertEqual(self.player.features.get('eye'), '|#5A97D6blue|n eyes')
		gen.set_character_feature(self.player, "eye", subtypes=['left'], color="|#5E391Fdark brown|n")
		self.player.update_features() # apply changes from parts
		eyes = self.player.features.get('eye')
		self.assertIn('|#5A97D6blue|n', eyes)
		self.assertIn('|#5E391Fdark brown|n', eyes)

	def test_reset_special(self):
		gen.set_character_feature(self.player, "eye", match={}, value='|#0000ffblue|n')
		gen.reset_special(self.player)
		self.assertNotIn('|#0000ffblue|n', self.player.features.view)
		eyes = self.player.features.get('eye')
		gen.set_character_feature(self.player, "ear", match={}, value='pointed')
		gen.reset_special(self.player)
		self.assertNotIn('pointed', self.player.features.view)
		# shouldn't affect non-special eyes
		self.assertIn(eyes, self.player.features.view)


	# TODO: initialize features test

from utils.menus import FormatEvMenu

_ERROR_FORMAT = """
===== Wanted message =======
{expected_msg}
===== Returned message =====
{returned_msg}
============================
""".rstrip()

class TestChargenMenu(NexusTest):
	def setUp(self):
		super().setUp()
		self.player_setup()
		self.player = self.create_player()
		self.session.new_char = self.player
		self.session.msg = MagicMock()

	def initialize_menu(self, start_node):
		return FormatEvMenu(self.session, "systems.chargen.menu", startnode=start_node)

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
	
	def test_start(self):
		menu = self.initialize_menu("menunode_welcome")
		self.verify_msg("Character Creation")
		menu.parse_input("1")
		self.verify_msg("Your Pronouns", options=["he/him", "she/her", "they/them"])

	def test_pronouns(self):
		menu = self.initialize_menu("menunode_pronouns")
		self.verify_msg("Your Pronouns", options=["he/him", "she/her", "they/them"])
		menu.parse_input("1")
		self.assertEqual(self.player.gender,"male")

	def test_archetypes(self):
		menu = self.initialize_menu("menunode_info_arch_base")
		arch_opts = [
			"mundane", "familiar", "elemental magic", "beast", "magic sense"
		]
		self.verify_msg("Choosing an Archetype", options=arch_opts)
		menu.parse_input("1")
		self.verify_msg(
				"Most of humanity doesn't have any magical abilities at all",
				options=["Choose this archetype"]+arch_opts[1:]
			)
		menu.parse_input("5")
		self.verify_msg(
				"Some humans are born with the ability to directly see the presence of magic",
				options=["Choose this archetype"]+arch_opts[:-1]
			)
		menu.parse_input("1")
		self.assertTrue(self.player.effects.has(name='archetype'))
		archetype = self.player.effects.get(name='archetype')
		self.assertEqual(type(archetype).__name__, 'MageArch' )
	
	def test_element(self):
		self.player.effects.add('systems.archetypes.base.SorcererArch')
		menu = self.initialize_menu("menunode_choose_element")
		element_list = [
			"earth", "fire", "water", "plant", "light", "shadow", "lightning",
		]
		self.verify_msg("Choose an element:", options=element_list)
		menu.parse_input("2")
		self.assertTrue(self.player.effects.has(name='innate magic'))
		magic = self.player.effects.get(name='innate magic')
		self.assertEqual(magic.element, 'fire')

	def test_build(self):
		menu = self.initialize_menu("menunode_build")
		self.verify_msg("Your Appearance, Part One", options=['height', 'bodytype', 'persona'])
		# body type
		menu.parse_input("1")
		self.verify_msg("Choose your bodytype:", options=['skinny'])
		menu.parse_input("2")
		self.verify_msg("Your Appearance, Part One")
		self.assertIn("skinny", self.player.build)
		# height
		menu.parse_input("2")
		self.verify_msg("Choose your height:", options=['diminutive'])
		menu.parse_input("1")
		self.verify_msg("Your Appearance, Part One")
		self.assertIn("diminutive", self.player.build)
		# persona
		menu.parse_input("3")
		self.verify_msg("Choose your persona:", options=['nobody', 'nerd'])
		menu.parse_input("3")
		self.verify_msg("Your Appearance, Part One")
		self.assertIn("nerd", self.player.build)
		# verify all three are set correctly
		self.assertEqual("diminutive, skinny nerd", self.player.build)
	
	# i'm not sure why, but this isn't giving a consistent list of options....
	@skip
	def test_sdesc(self):
		menu = self.initialize_menu("menunode_sdesc")
		print(self.player.build)
		self.verify_msg("Short Description", options=['height', 'body type', 'skin texture', 'skin color', 'hair texture', 'hair color', 'hair length'])
		menu.parse_input("1")
		print(self.player.sdesc.get())

	def test_features(self):
		menu = self.initialize_menu("menunode_features")
		self.verify_msg("Your Appearance, Part Two", options=['Customize your eyes', 'Customize your hair', 'Customize your skin'])
		menu.parse_input("1")
		self.verify_msg("", options=['eye color'])
		# NOTE: eye shape should NOT be present
		menu.parse_input("1")
		self.verify_msg("Customize your eye color", options=[' blue ', ' grey ', ' brown '])
		menu.parse_input("1")
		self.verify_msg("You have blue eyes.")
		self.assertEqual(self.player.features.get("eye"), "|#5A97D6blue|n eyes")

	# TODO: add sdesc menu node test

	@patch("utils.timing.delay", new=undelay)
	def test_finalize(self):
		self.player.db.charname = 'Monty'
		menu = self.initialize_menu("menunode_end")
		# print(f"all worn clothing: {self.player.clothing.all}")
		# print(f"all visible clothing: {self.player.clothing.visible}")
		self.assertEqual(len(self.player.clothing.all), 8)
		self.assertEqual(len(self.player.clothing.visible()), 4)

		# make sure all items were created
		self.assertEqual(len(self.player.contents), len(self.player.clothing.all)+2)

		# make sure name got assigned
		self.assertEqual("Monty", self.player.key)

	# TODO: add check for making a familiar
