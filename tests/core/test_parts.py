from mock import MagicMock, patch
from unittest import skip
from evennia.utils.test_resources import EvenniaTest


class PartsTest(EvenniaTest):
	"""
	test logic for the parts-handling system
	"""
	def test_parts_caching(self):
		obj3 = self.obj2.copy(new_key="Obj3")
		self.obj1.parts.attach(self.obj2)
		self.obj1.parts.attach(obj3, part=self.obj2)

		# obj2 should be in obj1 cache, and directly attached
		self.assertIn(self.obj2, self.obj1.parts_cache.get())
		self.assertIn(self.obj2, self.obj1.parts_cache.get(direct=True))
		# obj3 should be in obj1 cache, NOT directly attached
		self.assertIn(obj3, self.obj1.parts_cache.get())
		self.assertNotIn(obj3, self.obj1.parts_cache.get(direct=True))
		# obj3 should be in obj2 cache, and directly attached
		self.assertIn(obj3, self.obj2.parts_cache.get())
		self.assertIn(obj3, self.obj2.parts_cache.get(direct=True))

	def test_attach_detach(self):
		obj3 = self.obj2.copy(new_key="Obj3")

		# attaching
		self.assertTrue(self.obj1.parts.attach(self.obj2))
		self.assertEqual(self.obj2.baseobj, self.obj1)
		self.assertIn(self.obj2, self.obj1.parts.all())
		self.assertIsNone(self.obj2.location)
	
		# detaching
		self.assertTrue(self.obj1.parts.detach(self.obj2))
		self.assertEqual(self.obj2.baseobj, self.obj2)
		self.assertEqual(self.obj1.location, self.obj2.location)
		# self.assertNotIn(self.obj2, self.obj1.parts.all())

		# attaching subparts
		self.obj1.parts.attach(self.obj2)
		self.obj1.parts.attach(obj3, part=self.obj2)
		self.assertIn(obj3, self.obj2.parts.all())
		self.assertIn(obj3, self.obj1.parts.all())

		# detaching with subparts
		self.assertTrue(self.obj1.parts.detach(self.obj2))
		self.assertNotIn(self.obj2, self.obj1.parts.all())
		self.assertNotIn(obj3, self.obj1.parts.all())
		self.assertEqual(obj3.baseobj, self.obj2)

	def test_chain_link_unlink(self):
		link1 = self.obj2.copy(new_key="link1")
		link2 = link1.copy(new_key="link2")
		chain = self.obj2.copy(new_key="chain")
		# creating a chain
		self.assertTrue(self.obj1.parts.link(chain))
		self.assertTrue(chain.tags.has("chain", category="systems"))
		self.assertIn(chain, self.obj1.parts.all())
		# extending a chain
		self.assertTrue(chain.parts.link(link1))
		self.assertIn(link1, self.obj1.parts.all())
		self.assertIn(chain, self.obj1.parts.all())
		self.assertEqual(link1.partof, chain)
		self.assertIn(link1, chain.attributes.get("_parts_chain", category="systems"))
		# breaking a chain
		self.assertTrue(self.obj1.parts.unlink(link1))
		self.assertNotIn(link1, self.obj1.parts.all())
		self.assertEqual(self.obj1.location, link1.location)

		# splitting a chain
		self.obj1.parts.link(chain)
		chain.parts.link(link1)
		chain.parts.link(link2)
		self.assertIn(link1, self.obj1.parts.all())
		self.assertTrue(self.obj1.parts.unlink(link1))
		self.assertNotIn(link2, self.obj1.parts.all())
		self.assertEqual(link2.partof.location, self.obj1.location)


	def test_delete_break(self):
		link1 = self.obj2.copy(new_key="link1")
		link2 = link1.copy(new_key="link2")
		link3 = link1.copy(new_key="link3")
		chain = self.obj2.copy(new_key="chain")
		chain.tags.add("chain", category="systems")
		self.obj1.parts.attach(chain)
		chain.parts.link(link1)
		chain.parts.link(link2)
		chain.parts.link(link3)

		# this is the actual testing part
		# first, delete the middle link
		link2.delete()
		# make sure link 3 fell
		self.assertNotIn(link3, self.obj1.parts.all())
		self.assertEqual(link3.location, self.obj1.location)

		# next, delete the chain
		chain.delete()
		# make sure link 1 fell
		self.assertEqual(link1.location, self.obj1.location)


	def test_search(self):
		obj3 = self.obj2.copy(new_key="Obj3")
		obj3.tags.add("obj", category="part")
		self.obj1.parts.attach(self.obj2)
		self.obj1.parts.attach(obj3)

		# name search
		result = self.obj1.parts.search("obj")
		self.assertIn(obj3, result)
		self.assertIn(self.obj2, result)

		# tag search
		result = self.obj1.parts.search("obj", part=True)
		self.assertIn(obj3, result)
		self.assertNotIn(self.obj2, result)