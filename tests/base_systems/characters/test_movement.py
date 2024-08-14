"""
Tests for various character movement things

"""
from unittest.mock import Mock, patch

from base_systems.characters import movement
from utils.testing import NexusCommandTest, undelay

class TestMovementCommands(NexusCommandTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.caller.location = self.room

	def test_sit(self):
		"""sit on the ground"""
		# sit down
		self.call(
			movement.CmdSit(), "", "Caller sits down"
		)
		self.assertTrue(self.caller.tags.has('sitting', category='status'))
		self.call(
			movement.CmdSit(), "", "You are already sitting"
		)
		# sit up
		self.caller.tags.remove(category='status')
		self.caller.tags.add('lying down', category='status')
		self.call(
			movement.CmdSit(), "", "Caller sits up"
		)
		self.assertTrue(self.caller.tags.has('sitting', category='status'))
		self.assertFalse(self.caller.tags.has('lying down', category='status'))
	
	def test_sit_on_thing(self):
		"""sit on an object"""
		obj = self.create_object("thing")
		obj.location = self.room
		self.call(
			movement.CmdSit(), "thing", "Caller sits down on a thing"
		)
		self.assertTrue(self.caller.tags.has('sitting', category='status'))

	def test_sit_on_character(self):
		"""sit on a character"""
		obj = self.create_character()
		obj.location = self.room
		output = self.call(
			movement.CmdSit(), "person", "Requesting permission to sit"
		)
		self.assertIn("Caller sits down on a person", output)
		self.assertTrue(self.caller.tags.has('sitting', category='status'))

	def test_lie_down(self):
		"""lie on the ground"""
		# lie down
		self.call(
			movement.CmdLieDown(), "", "Caller lies down"
		)
		self.assertTrue(self.caller.tags.has('lying down', category='status'))
		self.call(
			movement.CmdLieDown(), "", "You are already lying down"
		)

	def test_lie_on_thing(self):
		"""lie on an object"""
		obj = self.create_object("thing")
		obj.location = self.room
		self.call(
			movement.CmdLieDown(), "thing", "Caller lies down on a thing"
		)
		self.assertTrue(self.caller.tags.has('lying down', category='status'))
		self.assertIn(obj, self.room.posing.get(self.caller))

	def test_lie_on_character(self):
		"""lie on a character"""
		obj = self.create_character()
		obj.location = self.room
		output = self.call(
			movement.CmdLieDown(), "person", "Requesting permission to lie down"
		)
		self.assertIn("Caller lies down on a person", output)
		self.assertTrue(self.caller.tags.has('lying down', category='status'))
		self.assertIn(obj, self.room.posing.get(self.caller))
	
	def test_stand_up(self):
		"""stand up"""
		self.caller.tags.add('sitting', category='status')
		self.call(
			movement.CmdStand(), "", "Caller stands up"
		)
		self.assertFalse(self.caller.tags.has('sitting', category='status'))
		self.call(
			movement.CmdStand(), "", "You're already standing"
		)

	def test_stand_on_thing(self):
		"""stand on an object"""
		obj = self.create_object("thing")
		obj.location = self.room
		self.call(
			movement.CmdStand(), "thing", "Caller stands on a thing"
		)
		self.assertIn(obj, self.room.posing.get(self.caller))

	def test_stand_on_character(self):
		"""lie on a character"""
		obj = self.create_character()
		obj.location = self.room
		output = self.call(
			movement.CmdStand(), "person", "Requesting permission to stand"
		)
		self.assertIn("Caller stands on a person", output)
		self.assertIn(obj, self.room.posing.get(self.caller))
	