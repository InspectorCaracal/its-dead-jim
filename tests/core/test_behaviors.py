from mock import MagicMock, patch
from unittest import skip
from evennia.utils.test_resources import EvenniaTest

from core.ic.behaviors import Behavior, NoSuchBehavior

class BaseBehavior(Behavior):
	"""
	Base behavior for testing
	"""
	priority = 3

	def myaction(obj, **kwargs):
		return f"base action on {obj}"

class DummyOne(Behavior):
	"""
	Test behavior for merging and unmerging with low priority
	"""
	priority = 1

	def myaction(obj, **kwargs):
		return f"action one on {obj}"
	
	def myfunc(obj, **kwargs):
		return f"func call on {obj}"

class DummyTwo(Behavior):
	"""
	Test behavior for merging and unmerging with higher priority
	"""
	priority = 10

	def myaction(obj, **kwargs):
		return f"action two on {obj}"

_DUMMY_REGISTRY = {
	'BaseBehavior': BaseBehavior,
	'DummyOne': DummyOne,
	'DummyTwo': DummyTwo,
}



class BehaviorTest(EvenniaTest):
	"""
	test logic for behavior sets
	"""
	@patch('base_systems.characters.base.Character.at_object_creation')
	def setUp(self, thing):
		super().setUp()

	@patch('core.ic.behaviors.BEHAVIOR_REGISTRY', new=_DUMMY_REGISTRY)
	def test_do(self):
		self.obj1.behaviors.add("BaseBehavior")
		self.assertTrue(self.obj1.behaviors.can_do("myaction"))
		self.assertEqual("base action on Obj", self.obj1.do_myaction())
		with self.assertRaises(NoSuchBehavior):
			self.obj1.do_myfunc()

	@patch('core.ic.behaviors.BEHAVIOR_REGISTRY', new=_DUMMY_REGISTRY)
	def test_add(self):
		self.obj1.behaviors.add("BaseBehavior")
		self.assertIn(
			"BaseBehavior",
			self.obj1.attributes.get("behaviors", category="systems")
		)
		self.assertIn(
			"BaseBehavior",
			self.obj1.behaviors._behave_set
		)
	
	@patch('core.ic.behaviors.BEHAVIOR_REGISTRY', new=_DUMMY_REGISTRY)
	def test_add_del_methods(self):
		self.obj1.behaviors._add_methods(BaseBehavior)
		self.assertIn("myaction", self.obj1.behaviors.behaviors)
		self.obj1.behaviors._del_methods(BaseBehavior)
		self.assertNotIn("myaction", self.obj1.behaviors.behaviors)
		self.obj1.behaviors._add_methods(BaseBehavior, default=True)
		self.assertIn("myaction", self.obj1.behaviors._default)

	@patch('core.ic.behaviors.BEHAVIOR_REGISTRY', new=_DUMMY_REGISTRY)
	def test_merge_unmerge(self):
		# try merging nothing first
		self.obj1.behaviors.merge(self.obj2)
		# now merge actual behaviors
		self.obj2.behaviors.add("DummyOne")
		self.obj1.behaviors.merge(self.obj2)
		# merge extra functionality behavior
		self.assertTrue(self.obj1.behaviors.can_do("myfunc"))
		self.assertEqual("action one on Obj", self.obj1.do_myaction())
		# unmerge
		self.obj1.behaviors.unmerge(self.obj2)
		# verify extra functionality is gone
		self.assertFalse(self.obj1.behaviors.can_do("myfunc"))
		with self.assertRaises(NoSuchBehavior):
			self.obj1.do_myaction()
	
	@patch('core.ic.behaviors.BEHAVIOR_REGISTRY', new=_DUMMY_REGISTRY)
	def test_merge_at_lower_priority(self):
		pass

