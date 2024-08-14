from evennia.utils.test_resources import EvenniaTest
from mock import patch

from utils.testing import undelay

def reaction_func(changeable_dict):
	changeable_dict['changed'] = True

class ReactionTest(EvenniaTest):
	"""
	test reaction handler and interface
	"""
	def test_add(self):
		# simple function trigger
		self.obj1.react.add("trigger", reaction_func)
		self.assertIn((reaction_func.__name__, reaction_func.__module__,), self.obj1.react._data['trigger'])
		# trigger added with "on" prefix
		self.obj1.react.add("on_happen", reaction_func)
		self.assertIn((reaction_func.__name__, reaction_func.__module__,), self.obj1.react._data['happen'])

#	@patch('utils.timing.delay', new=undelay)
	@patch('core.ic.reactions.delay', new=undelay)
	def test_on(self):
		self.obj1.react.add("trigger", reaction_func)
		test_dict = {}
		# verify subscribed func is called
		self.obj1.react.on("trigger", test_dict)
		self.assertTrue(test_dict.get('changed'))

#	@patch('utils.timing.delay', new=undelay)
	@patch('core.ic.reactions.delay', new=undelay)
	def test_integrated_on(self):
		self.obj1.react.add("trigger", reaction_func)
		test_dict = {}
		# verify subscribed func is called
		self.obj1.on_trigger(test_dict)
		self.assertTrue(test_dict.get('changed'))
