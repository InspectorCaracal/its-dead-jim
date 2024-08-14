"""
Tests for item manipulation/interaction commands

"""
from unittest.mock import patch

from base_systems.things import commands
from utils.testing import NexusCommandTest, undelay

class TestItemCommands(NexusCommandTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.obj1 = self.create_object("thing")
		self.obj2 = self.create_object("stuff")
		self.obj1.size = 1
		self.obj2.size = 2
		self.caller.location = self.obj1.location = self.obj2.location = self.room
	
	def test_get(self):
		# get obj
		self.call(
			commands.CmdGet(), "thing", "Caller picks up a thing."
		)
		# get obj from obj (with permission)
		self.obj1.location = self.obj2
		self.obj2.locks.add("getfrom:all()")
		self.call(
			commands.CmdGet(), "thing from stuff", "Caller gets a thing from a stuff."
		)
		# get obj from obj (without permission)
		self.obj1.location = self.obj2
		self.obj2.locks.add("getfrom:false()")
		self.call(
			commands.CmdGet(), "thing from stuff", "You can't find $h(stuff)."
		)
		# get multiple objects
		self.obj1.location = self.room
		gotten = self.call(
			commands.CmdGet(), "thing, stuff", "Caller picks up"
		)
		self.assertIn("a thing", gotten)
		self.assertIn("a stuff", gotten)

	def test_look(self):
		self.room.db.desc = "An empty room."
		self.obj1.db.desc = "Some kind of a thing."
		self.obj2.db.desc = "A bunch of stuff."
		self.obj2.locks.add("viewcon:all()")
		# location
		viewed = self.call(commands.CmdLook(), "", "A room")
		self.assertIn("An empty room", viewed)
		# obj
		viewed = self.call(commands.CmdLook(), "thing", "thing")
		self.assertIn("Some kind of a thing.", viewed)
		# obj in obj
		self.obj1.location = self.obj2
		viewed = self.call(commands.CmdLook(), "thing in stuff", "thing")
		self.assertIn("Some kind of a thing.", viewed)
		# in obj
		viewed = self.call(commands.CmdLook(), "in stuff", "stuff")
		self.assertIn("A bunch of stuff.", viewed)
		self.assertIn("thing", viewed)
		# in obj without permissions
		# self.obj2.locks.add("viewcon:false();getfrom:false()")
		# self.call(commands.CmdLook(), "in stuff", "You can't look there.")
		# this should just hide the contents, actually

	def test_put(self):
		# put obj on nothing
		self.call(
			commands.CmdPut(), "thing", "Put it where?"
		)
		# put obj in non-container
		self.obj2.locks.add("getfrom:all()")
		self.obj1.location = self.caller
		# self.call(
		# 	commands.CmdPut(), "thing in stuff", "You can't put that there."
		# )

		# put obj in thing (with permission)
		self.obj2.tags.add("container", category="systems")
		self.obj1.location = self.caller
		self.call(
			commands.CmdPut(), "thing in stuff", "Caller puts a thing in a stuff."
		)
		# alternate "on" splitter
		self.obj1.location = self.caller
		self.call(
			commands.CmdPut(), "thing on stuff", "Caller puts a thing on a stuff."
		)
		# put obj on obj (without permission)
		self.obj1.location = self.caller
		self.obj2.locks.add("getfrom:false()")
		self.call(
			commands.CmdPut(), "thing in stuff", "You can't put things there."
		)

	def test_drop(self):
		# drop obj on the ground
		self.obj1.location = self.caller
		self.call(
			commands.CmdDrop(), "thing", "Caller puts down a thing"
		)
		self.assertEqual(self.obj1.location, self.caller.location)

	def test_place(self):
		# test without permissions
		self.call(
			commands.CmdPlace(), "thing", "You can't decorate here."
		)
		# test with permissions
		self.room.locks.add('decorate:all()')
		self.call(
			commands.CmdPlace(), "thing", "Caller places a thing here."
		)
		self.assertIn(self.obj1, self.room.decor.all())
		self.call(
			commands.CmdPlace(), "thing against the wall", "Caller places a thing against the wall."
		)
		self.assertEqual((self.obj1, 'against the wall'), self.room.decor.get(self.obj1))

	def test_grab_release(self):
		self.obj1.location = self.caller
		self.call(
			commands.CmdGrab(), "thing", "Caller grabs a thing"
		)
		self.assertIn(self.obj1, self.caller.holding().values())
		self.call(
			commands.CmdRelease(), "thing", "Caller lets go of a thing"
		)
		self.assertNotIn(self.obj1, self.caller.holding().values())

	def test_give(self):
		player = self.create_player()
		player.location = self.room
		# give obj you don't have
		self.obj1.location = self.room
		self.call(
			commands.CmdGive(), "thing to person", "You don't have any $h(thing)."
		)
		# give obj
		self.obj1.location = self.caller
		self.call(
			commands.CmdGive(), "thing to person", "Caller gives a thing to a person"
		)
		# give multiple objects
		self.obj1.location = self.caller
		self.obj2.location = self.caller
		self.call(
			commands.CmdGive(), "thing, stuff to person", "Caller gives a thing and a stuff to a person"
		)
