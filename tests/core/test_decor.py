from mock import MagicMock, patch

from utils.colors import strip_ansi
from utils.testing import NexusTest

def reaction_func(obj, changeable_dict):
	changeable_dict['changed'] = True

class DecorTest(NexusTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.obj = self.create_object("thing")
		self.obj2 = self.create_object("other thing")
		self.player = self.create_player()

	def test_add_remove(self):
		self.room.decor.add(self.obj)
		self.assertEqual(self.room.decor.get(self.obj), (self.obj, 'here'))
		self.room.decor.add(self.obj, 'against the wall')
		self.assertEqual(self.room.decor.get(self.obj), (self.obj, 'against the wall'))
		self.room.decor.remove(self.obj)
		self.assertEqual(self.room.decor.get(self.obj), None)
		
	@patch("core.ic.decor.randint", new=MagicMock(return_value=1))
	def test_desc(self):
		self.room.decor.add(self.obj, 'against the wall')
		self.assertEqual(self.room.decor.desc(self.player), 'Against the wall is |lclook thing|lta thing|le.')
		self.room.decor.add(self.obj)
		self.room.decor.add(self.obj2)
		self.assertEqual(self.room.decor.desc(self.player), '|lclook thing|ltA thing|le and |lclook other thing|ltan other thing|le are here.')

	def test_exclude_things(self):
		self.room.decor.add(self.obj)
		self.assertNotIn(self.obj, self.room._filter_things(self.room.contents))

	def test_coverage(self):
		self.obj.decor.add(self.obj2, cover=True)
		self.assertEqual("$head(thing)\nAn other thing is here.",strip_ansi(self.obj.return_appearance(self.player)))
	
	def test_covering_decor(self):
		obj3 = self.create_object('item')
		self.obj.decor.add(self.obj2)
		desc = self.obj.return_appearance(self.player)
		desc = strip_ansi(desc).strip()
		self.assertEqual(desc, "$head(thing)\nYou see nothing special.\nAn other thing is here.")
		self.obj.decor.add(obj3, cover=True)
		self.assertTrue(self.obj.effects.has(name='covered'))
		self.assertTrue(self.obj2.effects.has(name='covered'))
		desc = self.obj.return_appearance(self.player)
		desc = strip_ansi(desc).strip()
		self.assertEqual(desc, "$head(thing)\nAn item is here.")

	@patch("core.ic.decor.randint", new=MagicMock(return_value=1))
	def test_decor_parts(self):
		obj3 = self.create_object('item')
		self.obj.parts.attach(self.obj2)
		self.obj.decor.add(obj3, target=self.obj2)
		# FIXME: this should be "On a thing's other thing"
		self.assertEqual(self.obj.decor.desc(self.player), "On thing's other thing is |lclook item|ltan item|le.")
		self.assertTrue(self.obj.decor.remove(obj3))
		self.obj.decor.add(obj3, 'dangling')
		self.assertEqual(self.obj.decor.desc(self.player), 'Dangling is |lclook item|ltan item|le.')
