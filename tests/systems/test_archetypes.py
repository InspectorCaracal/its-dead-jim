from mock import MagicMock, patch
from unittest import skip
from evennia.utils.test_resources import EvenniaTest

from utils.testing import NexusTest, undelay

from systems.archetypes import base

@skip
class BaseArchTest(EvenniaTest):
	"""
	test logic for the generic archetype
	"""
	def test_initialize(self):
		pass

def faux_msg(*args, **kwargs):
	if args:
		return args
	if text := kwargs.get("text"):
		return text

class WerewolfTest(NexusTest):
	"""
	testing specific werewolf archetype logic
	"""
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.player.effects.add(base.WerewolfArch)
		self.room = self.create_room()
		self.player.location = self.room

	def test_shifting(self):
		shifts = base.WerewolfArch._default['shifts']
		# toggle shifted status - should go to partial
		emote = self.player.do_shift("part")
		self.assertEqual(emote, shifts[("off", "partial")])
		self.assertTrue(self.player.effects.has('systems.archetypes.effects.ShiftedEffect'))
		# toggle shifted status - should go to human
		emote = self.player.do_shift("off")
		self.assertEqual(emote, shifts[(None, "off")])
		self.assertFalse(self.player.effects.has('systems.archetypes.effects.ShiftedEffect'))
	
	# def test_tracking(self):
	# 	pass
	
	def test_commands(self):
		self.assertTrue(self.player.cmdset.has("Werewolf CmdSet"))
		fake_msg = MagicMock()
		self.player.msg = fake_msg

		# check shift first
		self.player.execute_cmd("shift")
		message = fake_msg.call_args.kwargs['text']
		self.validate_msg(message, 'Player gets a lot hairier, sprouting fangs and claws.')
		self.player.execute_cmd("shift")
		message = fake_msg.call_args.kwargs['text']
		self.validate_msg(message, 'Player looks perfectly human again.')

class WitchTest(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.player.effects.add(base.SorcererArch)
	
	def test_familiar(self):
		self.assertTrue(self.player.can_familiar)
		fam = self.player.do_familiar(update={'form': 'feline'})
		self.assertEqual(fam, self.player.attributes.get('familiar', category='systems'))
		fam = self.player.do_familiar(rename="test")
		self.assertEqual(fam.key, "test")
		# TODO: test commands

	@skip
	def test_familiar_element(self):
		"""setting and retrieving element info and colors"""
		# check validation
		self.player.do_familiar(update={'form': "feline"})
		familiar = self.player.archetype._familiar
		self.player.archetype.color = (255,255,255,1)
		self.assertEqual(self.player.archetype.color, "#ffffff")
		self.assertIn("#ffffff", familiar.features.get("hide"))
		self.assertIn("#ffffff", familiar.features.get("eyes"))
		self.player.archetype.color = (255,255,255,0)
		self.assertEqual(self.player.archetype.color, "#7f7f7f")
		self.assertIn("#7f7f7f", familiar.features.get("hide"))
		self.assertIn("#ffffff", familiar.features.get("hide"))

	def test_commands(self):
		# verify correct cmdsets are present
		self.assertTrue(self.player.cmdset.has("Familiar CmdSet"))
		# actually test the commands later

class MagicAbilityTest(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()

	def test_element(self):
		"""setting and retrieving element info and colors"""
		# check validation
		with self.assertRaises(ValueError):
			self.player.effects.add(base.MagicAbility)
		with self.assertRaises(ValueError):
			self.player.effects.add(base.MagicAbility, element="red")
		self.player.effects.add(base.MagicAbility, element="fire")
		self.assertTrue(self.player.effects.has(name='innate magic'))
		magic = self.player.effects.get(name='innate magic')
		self.assertEqual(magic.element, "fire")
		self.assertEqual(magic.color, '#ff3c00')

	# TODO: add tests to verify eye color and familiar colors apply properly

	def test_commands(self):
		self.player.effects.add(base.MagicAbility, element="fire")
		# verify correct cmdsets are present
		self.assertTrue(self.player.cmdset.has("Spell CmdSet"))
		# actually test the commands later


class VampireTest(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.player.effects.add(base.VampireArch)

	@skip
	def test_element(self):
		"""setting and retrieving element info and colors"""
		# check validation
		with self.assertRaises(ValueError):
			self.player.archetype.color = "red"

		self.player.archetype.color = (255,255,255,1)
		self.assertEqual(self.player.archetype.color, "#ffffff")
		self.assertIn("#ffffff", self.player.features.get("eye"))
		self.player.archetype.color = (255,255,255,0)
		self.assertEqual(self.player.archetype.color, "#7f7f7f")
	# 	self.assertIn("#ffffff", self.player.features.get("eye"))

	def test_commands(self):
		# bite commands
		self.assertTrue(self.player.cmdset.has("Vampire CmdSet"))
	
	# TODO: test behaviors

@skip
class MageTest(NexusTest):

	def test_commands(self):
		pass

@skip
class FaerieTest(NexusTest):

	def test_commands(self):
		pass
