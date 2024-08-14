from unittest.mock import MagicMock, patch
from base_systems.actions.base import Action

from utils.testing import NexusTest, undelay


@patch('base_systems.actions.queue.delay', new=undelay)
class TestActionClass(NexusTest):
	def setUp(self):
		super().setUp()
		self.player = self.create_player("Alex")
		# self.obj1.name = "thing"
		# self.obj2.name = "stuff"
		# self.obj1.size = 1
		# self.obj2.size = 2
		# self.player.key = "Alex"
		# self.char2.key = "Bobby"
		# self.char2.sdesc.sdesc = 'person'
		
	def test_req_parts(self):
		action = Action(actor=self.player)
		action.do = MagicMock()
		action.end = MagicMock()

		# works normally
		action.start()
		action.do.assert_called_once()
		action.do.reset_mock()

		# requires a part that we have available
		action.min_req_parts = ( ('hand', 1), )
		action.start()
		action.do.assert_called_once()
		action.do.reset_mock()

		# requires a part that we have but won't work
		for hand in self.player.parts.search('hand', part=True):
			hand.tags.add('disabled', category='status')
		action.start()
		action.do.assert_not_called()
		action.do.reset_mock()
		for hand in self.player.parts.search('hand', part=True):
			hand.tags.remove('disabled', category='status')
		
		# requires a part we don't have
		action.min_req_parts = ( ('cpu', 1), )
		action.start()
		action.do.assert_not_called()
		action.do.reset_mock()

		# requires more parts than we have
		action.min_req_parts = ( ('hand', 3), )
		action.start()
		action.do.assert_not_called()
		action.do.reset_mock()

