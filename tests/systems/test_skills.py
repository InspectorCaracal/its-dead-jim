from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.create import create_object
from systems.parkour.actions import ParkourMove
from systems.skills.handler import SkillsHandler
from systems.skills.skills import Skill

from utils.testing import undelay

class TestSkillsHandler(EvenniaTest):
	"""
	Test the skills handler
	"""
	def setUp(self):
		self.obj = create_object(key='test')
		handler = SkillsHandler(self.obj)
		handler._load = MagicMock()
		handler._save = MagicMock()
		handler.data = {}
		handler._data = {}
		self.handler = handler

	def test_add_remove(self):
		"""add skills to the handler"""
		# add to the handler
		self.assertTrue(self.handler.add("combat", "Combat Skill"))
		# verify it was added
		self.assertEqual(len(self.handler.data.keys()), 1)
		self.assertIn('combat', self.handler.data.keys())
		# verify it was initialized properly
		skill = self.handler.data['combat']
		self.assertEqual(type(skill), Skill)
		self.assertEqual(skill.name, "Combat Skill")
		self.assertEqual(skill.key, "combat")
		# shouldn't allow you to add a skill twice
		self.assertFalse(self.handler.add("combat", "Combat Skill"))

		# remove from the handler
		self.assertTrue(self.handler.remove('combat'))
		# verify it was removed
		self.assertEqual(len(self.handler.data.keys()), 0)
		self.assertNotIn('combat', self.handler.data.keys())
		# can't remove a non-existent skill
		self.assertFalse(self.handler.remove('monty'))

	def test_check(self):
		"""check if skills pass"""
		self.handler.add("combat", "Combat Skill")
		self.handler.combat.base = 10
		self.assertTrue(self.handler.check(combat=5))
		self.assertFalse(self.handler.check(combat=20))
		self.assertFalse(self.handler.check(combat=5, monty=5))
		self.assertEqual(self.handler.check(combat=5, monty=5, return_list=True), [True, False])

	def test_use(self):
		"""mark the skill as used if it passes"""
		self.handler.add("combat", "Combat Skill")
		self.handler.combat.base = 10
		self.assertFalse(self.handler.use(combat=20))
		self.assertEqual(self.handler.combat.practice, 0)
		self.assertTrue(self.handler.use(combat=5))
		self.assertEqual(self.handler.combat.practice, 1)
	
	def tearDown(self):
		self.obj.delete()