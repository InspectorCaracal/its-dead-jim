from unittest import skip
import time
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from base_systems.things.base import Thing
from base_systems.characters.base import Character

@skip
class TestEmoteSpeed(EvenniaTest):
	def setUp(self):
		super().setUp()
		loc = self.room2
		for i in range(450):
			create_object( Thing, key=f"Object{i}", location=loc)
		for i in range(50):
			create_object( Character, key=f"Character{i}", location=loc)

	def test_msg_contents_funcparser(self):
		print(f"Messaging {len(self.room1.contents)} objects 100 times")
		start = time.time()
		for _ in range(100):
			self.char1.emote("frowns sternly")
		end = time.time()
		print(f"Average execution time: {round((end-start)/100,5)}s")
		self.char1.location = self.room2
		print(f"Messaging {len(self.room2.contents)} objects 100 times")
		start = time.time()
		for _ in range(100):
			self.char1.emote("frowns sternly")
		end = time.time()
		print(f"Average execution time: {round((end-start)/100,5)}s")
		
