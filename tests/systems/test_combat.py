import unittest
from unittest.mock import Mock, patch
from anything import Anything

from systems.combat import commands
from utils.testing import NexusCommandTest, undelay


def first_target(target, **kwargs):
	if not (parts := target.parts.all()):
		return target

	return sorted(parts, key=lambda x: x.id)[0]

@patch("systems.combat.actions.get_hit_location", new=first_target)
class TestAssaultCommands(NexusCommandTest):
	@patch("utils.timing.delay", new=undelay)
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.caller.key = "Alex"
		self.chara = self.create_player("Bobby")
		self.obj1 = self.create_object("thing")
		self.obj2 = self.create_object("stuff")
		self.obj1.size = 1
		self.obj2.size = 2
		self.caller.location = self.chara.location = self.obj1.location = self.obj2.location = self.room
		
	@patch('systems.combat.actions.delay', new=undelay)
	def test_melee(self):
		self.caller.skills.martial.base = 10
		self.call(
			commands.CmdAttack(), "thing", "Alex hits a thing"
		)
		self.call(
			commands.CmdAttack(), "thing with left hand", "Alex hits a thing with $gp(their) left hand"
		)

		self.call(
			commands.CmdAttack(), "person", "Alex hits at a person"
		)

	@patch('systems.combat.actions.delay', new=undelay)
	def test_throw(self):
		# throw it
		self.obj1.location = self.caller
		self.caller.hold(self.obj1)
		self.call(
			commands.CmdThrow(), 'thing', 'Alex throws a thing'
		)
		self.assertEqual(self.obj1.location, self.caller.location)

		# try to throw a thing you aren't holding and don't have
		self.assertNotIn(self.obj1, self.caller.holding(None).values())
		self.call(
			commands.CmdThrow(), 'thing', "You don't have anything like $h(thing) to throw."
		)

		# try to throw a thing you don't have but ARE holding
		self.caller.hold(self.obj1)
		self.assertEqual(self.obj1.location, self.caller.location)
		self.call(
			commands.CmdThrow(), 'thing', 'Alex throws a thing'
		)

		self.obj1.location = self.caller
		self.caller.hold(self.obj1)
		# self.call(
		# 	commands.CmdThrow(), 'thing at person', 'Alex throws a thing at a person'
		# )
		self.call(
			commands.CmdThrow(), 'thing at person', 'Alex throws a thing'
		)
		self.assertEqual(self.obj1.location, self.caller.location)
