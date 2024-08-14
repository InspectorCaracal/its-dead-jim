from mock import MagicMock, patch
from unittest import skip
from evennia.utils.test_resources import EvenniaTest

from utils.testing import NexusTest, undelay

from systems.spells import actions, effects

class DummySpell(actions.SpellAction):
	effect = "test"

class SpellActionTest(NexusTest):
	"""
	testing specific werewolf archetype logic
	"""
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.player = self.create_player('Alex')
		self.player.effects.add('systems.archetypes.base.MagicAbility', element='fire')
	
	def test_spell_start(self):
		# test invalid effect
		fake_msg = MagicMock()
		self.player.msg = fake_msg
		action = actions.SpellAction(self.player, self.player)
		action.start('')
		self.assertIn("(That ability is not yet implemented.)", fake_msg.call_args.args)

		# test normal start
		self.player.effects.add = MagicMock()
		action = DummySpell(self.player, self.player)
		action.start('')
		self.player.effects.add.assert_called_once_with('test', source=self.player)
		# test start on someone else
		player2 = self.create_player('Bob')
		player2.effects.add = MagicMock()
		action = DummySpell(self.player, player2)
		action.start('')
		player2.effects.add.assert_called_once_with('test', source=self.player)
#		self.assertIn("(That ability is not yet implemented.)", fake_msg.call_args_list)

	def test_spell_status(self):
		# on ourself
		action = DummySpell(self.player, self.player)
		self.assertEqual(action.status(), "You have |#ff3c00spell magic|n on yourself.")
		# on someone else
		player2 = self.create_player('Bob')
		action = DummySpell(self.player, player2)
		self.assertEqual(action.status(), "You have |#ff3c00spell magic|n on a person.")
	
	def test_spell_saving(self):
		action = DummySpell(self.player, self.player)
		self.player.db.active_spell = action
		self.assertEqual(self.player.db.active_spell, action)