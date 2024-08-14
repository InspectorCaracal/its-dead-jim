from evennia.utils.test_resources import EvenniaTest
from parameterized import parameterized
from mock import MagicMock, patch

from core.commands import Command
from utils.colors import strip_ansi
from utils.testing import NexusCommandTest, NexusTest

def reaction_func(obj, changeable_dict):
	changeable_dict['changed'] = True

class CommandTest(NexusTest):
	def setUp(self):
		super().setUp()
		self.command = Command()
	
	@parameterized.expand(
		[
			('box', (1, 'box')),
			('boxes', (None, 'box')),
			('2 box', (2, 'box')),
			('2 boxes', (2, 'box')),
			('all boxes', (None, 'box')),
			('some boxes', (None, 'box')),
			('a box', (1, 'box')),
		]	
	)
	def test_parse_num(self, search_term, expected):
		self.assertEqual(self.command._parse_num(search_term), expected)
	
	def test_collapse_stacks(self):
		self.command.caller = self.create_player()
		obj_list = []
		for _ in range(3):
			obj_list.append(self.create_object("thing"))
		for _ in range(2):
			obj_list.append(self.create_object("item"))
		
		collapsed = self.command._collapse_stacks(obj_list)
		self.assertEqual(len(collapsed), 2)
		self.assertNotEqual(collapsed[0].name, collapsed[1].name)

	def test_collapse_ordinal(self):
		self.command.caller = self.create_player()
		obj_list = []
		for _ in range(3):
			obj_list.append(self.create_object("thing"))
		for _ in range(2):
			obj_list.append(self.create_object("item"))
		
		# first item from each list
		collapsed = self.command._collapse_ordinal(obj_list, 1)
		self.assertEqual(len(collapsed), 2)
		# first "thing" is index 0
		self.assertEqual(collapsed[0], obj_list[0])
		# first "item" is index 3
		self.assertEqual(collapsed[1], obj_list[3])

		# third item from each list
		collapsed = self.command._collapse_ordinal(obj_list, 3)
		# there are only 2 items, so it should be just the thing
		self.assertEqual(len(collapsed), 1)
		self.assertEqual(collapsed[0].name, "thing")
		
	def test_parse_splitters(self):
		self.command.splitters = (',',)
		self.command.args = "a, b, c"
		self.command.parse()
		self.assertEqual(self.command.argslist, ['a', 'b', 'c'])

	def test_parse_prefixes(self):
		self.command.prefixes = ('with',)
		self.command.args = "a with b"
		self.command.parse()
		self.assertEqual(self.command.argsdict[None], ['a'])
		self.assertEqual(self.command.argsdict['with'], ['b'])

	@parameterized.expand(
		[
			('a with b', {None: ['a'], 'with': ['b']}),
			('a with b, c', {None: ['a'], 'with': ['b', 'c']}),
			('a, c with b', {None: ['a','c'], 'with': ['b']}),
			('a with b,c', {None: ['a'], 'with': ['b','c']}),
			('a,c with b', {None: ['a','c'], 'with': ['b']}),
			('a, c with b, d', {None: ['a','c'], 'with': ['b','d']}),
		]	
	)
	def test_parse_prefixes_and_splitters(self, cmd_args, expected):
		self.command.prefixes = ('with',)
		self.command.splitters = (',',)
		self.command.args = cmd_args
		self.command.parse()
		self.assertEqual(self.command.argsdict, expected)

