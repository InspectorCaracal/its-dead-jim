from mock import MagicMock, patch

from utils.colors import strip_ansi
from utils.testing import NexusCommandTest, NexusTest

from base_systems.maps import commands

class TestBuildingCmds(NexusCommandTest):

	def test_cmd_dig(self):
		self.call(commands.CmdDig(), "field, north")
		# create an exit in our location
		north = self.caller.search('north', quiet=True)[0]
		# it has an alias of n
		self.assertIn('n', north.aliases.all())
		# it leads to the new room, field
		self.assertEqual(north.destination.name, 'field')
		# a 'south' exit leads back
		south = north.destination.contents[0]
		self.assertEqual(south.name, 'south')
		# it has an alias of s
		self.assertIn('s', south.aliases.all())

		self.call(commands.CmdDig(), "house, in;enter=out;leave")
		# create an exit in our location
		door = self.caller.search('in', quiet=True)[0]
		# it has an alias of enter
		self.assertIn('enter', door.aliases.all())
		# it leads to the new room, house
		self.assertEqual(door.destination.name, 'house')
		# an 'out' exit leads back
		out = door.destination.contents[0]
		self.assertEqual(out.name, 'out')
		# it has an alias of leave
		self.assertIn('leave', out.aliases.all())

	def test_cmd_zone(self):
		cmd = commands.CmdZone()
		# checking an unzoned object's zone
		result = self.call(cmd, "here")
		self.assertIn("is not zoned", result)
		# zoning an object
		result = self.call(cmd, "here = area", 'Assigned zone $h(area) to A room')
		# zoning an object already in that zone
		result = self.call(cmd, "here = area", 'A room is already in zone $h(area); no change made')
		# re-zoning an object to a new zone
		result = self.call(cmd, "here = place", 'Removed zone $h(area) and assigned zone $h(place) to A room')
		# checking a zoned object's zone
		result = self.call(cmd, "here")
		self.assertIn("is zoned as $h(place)", result)

	def test_cmd_behavior(self):
		obj = self.create_object("thing")
		obj.location = self.caller
		cmd = commands.CmdAddRemBehavior()
		self.call(cmd, "on thing", "$head(Behaviors available to thing):|  None", cmdstring='behaviors')
		self.call(cmd, "add Consumable to thing", "Added behavior 'Consumable' to thing", cmdstring='behavior')
		self.assertTrue(obj.can_consume)
		self.call(cmd, "remove Consumable from thing", "Removed behavior 'Consumable' from thing", cmdstring='behavior')
		self.assertFalse(obj.can_consume)

	def test_cmd_destroy(self):
		obj = self.create_object("thing")
		obj.location = self.caller
		obj2 = self.create_object("thing")
		obj2.partof = obj
		obj3 = self.create_object("thing")
		obj3.location = obj
		self.account.permissions.add('developer')
		cmd = commands.CmdDestroy()
		self.call(cmd, "thing")
		self.assertIsNone(obj.pk)
		self.assertIsNone(obj2.pk)
		self.assertEqual(obj3.location, self.caller)

