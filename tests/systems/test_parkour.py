from unittest.mock import patch
from evennia.utils.create import create_object
from systems.parkour.actions import ParkourMove

from utils.testing import NexusTest, undelay

class TestObstacles(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player()
		self.room = self.create_room()
		self.player.location = self.room
		self.obstacle = create_object('systems.parkour.obstacles.Obstacle', key="ledge", location=self.room)
		self.obstacle.moves.add(self.room, verb="climb", skill="climbing", dc=1)
		
	def test_obstacle_footer(self):
		move_action = self.obstacle.moves.data[0]
		expected = "You can $h(|lcclimb ledge|ltclimb|le) onto this."
		self.assertEqual(expected, self.obstacle.get_display_footer(self.player))

		# fail skill DC
		move_action.dc = 10
		expected = "You could $h(climb) onto this if you get better at climbing."
		self.assertTrue(expected, self.obstacle.get_display_footer(self.player))

		# fail speed
		move_action.dc = 1
		move_action.speed = 10
		expected = "You could $h(climb) onto this if you were |rmoving fast|n."
		self.assertTrue(expected, self.obstacle.get_display_footer(self.player))

		# fail skill DC AND speed
		move_action.dc = 10
		expected = "You could $h(climb) onto this if you were |rmoving fast|n and  get better at climbing."
		self.assertTrue(expected, self.obstacle.get_display_footer(self.player))

	def test_obstacle_name(self):
		self.assertEqual(self.obstacle.get_display_name(self.player, link=False), "ledge")
		self.assertIn("(|lcclimb ledge|ltclimb|le)", self.obstacle.get_display_name(self.player, tags=True))

	def test_get_action_for_mover(self):
		target_move = self.obstacle.moves.data[0]
		self.assertEqual(self.obstacle.get_mover_action(self.player, "climb"), target_move)
		

class TestObstacleHandler(NexusTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.obstacle = create_object('systems.parkour.obstacles.Obstacle', key="ledge", location=self.room)

	def test_add_remove(self):
		self.obstacle.moves.add(self.room, verb="climb", skill="climbing", dc=1)
		moves = self.obstacle.moves.data
		self.assertEqual(len(moves), 1)
		self.obstacle.moves.remove(moves[0])
		self.assertEqual(len(moves), 0)

	def test_get_moves(self):
		obj = self.create_object()
		self.obstacle.moves.add(self.room, verb="climb", skill="climbing", dc=1)
		moves = self.obstacle.moves.get()
		self.assertEqual(len(moves), 1)
		moves = self.obstacle.moves.get(self.room)
		self.assertEqual(len(moves), 1)
		moves = self.obstacle.moves.get(obj)
		self.assertFalse(moves)

	def test_get_verbs(self):
		obj = self.create_object()
		self.obstacle.moves.add(self.room, verb="climb", skill="climbing", dc=1)
		self.assertEqual(self.obstacle.moves.get_verbs(), ["climb"])
		self.assertEqual(self.obstacle.moves.get_verb(self.room), "climb")

		self.obstacle.moves.add(self.room, verb="climb", skill="acrobatics", dc=1)
		self.assertEqual(self.obstacle.moves.get_verbs(), ["climb"])
		self.assertEqual(self.obstacle.moves.get_verb(self.room), "climb")

		self.assertIsNone(self.obstacle.moves.get_verb(obj))

	def test_get_speed(self):
		self.obstacle.moves.add(self.room, verb="jump", skill="acrobatics", dc=1, speed=10)
		self.assertEqual(self.obstacle.moves.get_speed(self.room), 10)


#@patch('base_systems.actions.queue.delay', new=undelay)
class TestParkourAction(NexusTest):
	def setUp(self):
		super().setUp()
		self.room = self.create_room()
		self.obstacle = create_object('systems.parkour.obstacles.Obstacle', key="ledge", location=self.room)
		self.action_kwargs = {
				'obstacle': self.obstacle,
				'source': self.room,
				'verb': 'climb',
				'skill': 'climbing',
				'dc': 1,
			}

	def test_init(self):
		action = ParkourMove(**self.action_kwargs)
		move_vars = vars(action)
		self.assertTrue(all(move_vars[key] == val for key, val in self.action_kwargs.items()))

	def test_action(self):
		action = ParkourMove(**self.action_kwargs)
		action.start()
