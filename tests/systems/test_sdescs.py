"""
Tests for RP system

"""
import time
from mock import patch
from unittest import skip
from anything import Anything
from evennia.utils.test_resources import EvenniaTest
from evennia import create_object

from base_systems.characters.base import Character
from core.ic import sdescs

# Testing of emoting / sdesc / recog system
sdesc0 = "nice sender of emotes"
sdesc1 = "first receiver of emotes."
sdesc2 = "nice colliding sdesc-guy for tests"
recog01 = "Mr Receiver"
recog02 = "Mr Receiver2"
recog10 = "Ms Sender"
emote = 'With a flair, @me looks at @first and @colliding sdesc-guy. She says "This is a test."'
case_emote = "@Me looks at @first. Then, @me looks at @FIRST, @First and @Colliding twice."
poss_emote = "@Me frowns at @first for trying to steal @me's test."

@skip
class TestRPSystem(EvenniaTest):
	maxDiff = None

	def setUp(self):
		super().setUp()
		self.speaker = self.char1
		self.speaker.key = "Sender"
		self.receiver1 = create_object( Character, key="Receiver1", location=self.room1 )
		self.receiver2 = create_object( Character, key="Receiver2", location=self.room1 )

	def test_sdesc_handler(self):
		self.speaker.sdesc.add(sdesc0)
		self.assertEqual(self.speaker.sdesc.get(), sdesc0)
		self.speaker.sdesc.add("This is {#324} ignored")
		self.assertEqual(self.speaker.sdesc.get(), "This is 324 ignored")

	@skip
	def test_recog_handler(self):
		self.speaker.sdesc.add(sdesc0)
		self.receiver1.sdesc.add(sdesc1)
		self.speaker.recog.add(self.receiver1, recog01)
		self.speaker.recog.add(self.receiver2, recog02)
		self.assertEqual(self.speaker.recog.get(self.receiver1), recog01)
		self.assertEqual(self.speaker.recog.get(self.receiver2), recog02)
		self.speaker.recog.remove(self.receiver1)
		self.assertEqual(self.speaker.recog.get(self.receiver1), None)

		self.assertEqual(self.speaker.recog.all(), {"Mr Receiver2": self.receiver2})

	# def test_parse_language(self):
		# self.assertEqual(
			# rpsystem.parse_language(self.speaker, emote),
			# (
				# "With a flair, @me looks at @first and @colliding sdesc-guy. She says {##0}",
				# {"##0": (None, '"This is a test."')},
			# ),
		# )

	@patch('systems.rpsystem.actually_send_emote')
	def test_parse_sdescs_and_recogs(self, mock_actual):
		speaker = self.speaker
		speaker.sdesc.add(sdesc0)
		self.receiver1.sdesc.add(sdesc1)
		self.receiver2.sdesc.add(sdesc2)
		ref0 = f"#{speaker.id}~"
		ref1 = f"#{self.receiver1.id}~"
		ref2 = f"#{self.receiver2.id}~"
		candidates = (self.receiver1, self.receiver2)
		result = (
			"With a flair, {"
			+ ref0
			+ "} looks at {"
			+ ref1
			+ "} and {"
			+ ref2
			+ '}. She says "This is a test."',
			{
				ref2: self.receiver2,
				ref1: self.receiver1,
				ref0: speaker,
			},
		)
		t0 = time.time()
		sdescs.parse_sdescs_and_recogs(speaker, candidates, emote, case_sensitive=False)
		t1 = time.time()
#		self.assertLess(t1-t0,0.01)
		self.assertEqual(mock_actual.call_args[0][2:], result)
		# self.speaker.recog.add(self.receiver1, recog01)
		# rpsystem.parse_sdescs_and_recogs(speaker, candidates, emote, case_sensitive=False)
		# self.assertEqual(mock_actual.call_args[0][2:], result)

	@patch('systems.rpsystem.actually_send_emote')
	def test_possessive_selfref(self, mock_actual):
		speaker = self.speaker
		speaker.sdesc.add(sdesc0)
		self.receiver1.sdesc.add(sdesc1)
		self.receiver2.sdesc.add(sdesc2)
		ref0 = f"#{speaker.id}~"
		ref1 = f"#{self.receiver1.id}~"
		ref2 = f"#{self.receiver2.id}~"
		candidates = (self.receiver1, self.receiver2)
		result = (
			"{" + ref0 + "} frowns at {" + ref1 + "} for trying to steal {" + ref0 + "}'s test.",
			{
				ref1: self.receiver1,
				ref0: speaker,
			},
		)
		sdescs.parse_sdescs_and_recogs(speaker, candidates, poss_emote, case_sensitive=False)
		self.assertEqual(mock_actual.call_args[0][2:], result)

	def test_get_sdesc(self):
		looker = self.speaker  # Sender
		target = self.receiver1  # Receiver1
		looker.sdesc.add(sdesc0)  # A nice sender of emotes
		target.sdesc.add(sdesc1)  # The first receiver of emotes.

		# sdesc with no processing
		self.assertEqual(looker.get_sdesc(target, process=False), "first receiver of emotes.")
		# sdesc with processing
		self.assertEqual(
			looker.get_sdesc(target, process=True), "|bfirst receiver of emotes.|n"
		)

		# looker.recog.add(target, recog01)  # Mr Receiver

		# # recog with no processing
		# self.assertEqual(looker.get_sdesc(target, process=False), "Mr Receiver")
		# # recog with processing
		# self.assertEqual(looker.get_sdesc(target, process=True), "|mMr Receiver|n")

	def test_send_emote(self):
		speaker = self.speaker
		receiver1 = self.receiver1
		receiver2 = self.receiver2
		receivers = [speaker, receiver1, receiver2]
		speaker.sdesc.add(sdesc0)
		receiver1.sdesc.add(sdesc1)
		receiver2.sdesc.add(sdesc2)
		speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
		receiver1.msg = lambda text, **kwargs: setattr(self, "out1", text)
		receiver2.msg = lambda text, **kwargs: setattr(self, "out2", text)
		sdescs.send_emote(speaker, receivers, emote, case_sensitive=False)
		self.assertEqual(
			self.out0[0],
			"With a flair, |mSender|n looks at |ba first receiver of emotes.|n "
			'and |ba nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n',
		)
		self.assertEqual(
			self.out1[0],
			"With a flair, |ba nice sender of emotes|n looks at |mReceiver1|n and "
			'|ba nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n',
		)
		self.assertEqual(
			self.out2[0],
			"With a flair, |ba nice sender of emotes|n looks at |ba first "
			'receiver of emotes.|n and |mReceiver2|n. She says |w"This is a test."|n',
		)

	def test_send_case_sensitive_emote(self):
		"""Test new case-sensitive rp-parsing"""
		speaker = self.speaker
		receiver1 = self.receiver1
		receiver2 = self.receiver2
		receivers = [speaker, receiver1, receiver2]
		speaker.sdesc.add(sdesc0)
		receiver1.sdesc.add(sdesc1)
		receiver2.sdesc.add(sdesc2)
		speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
		receiver1.msg = lambda text, **kwargs: setattr(self, "out1", text)
		receiver2.msg = lambda text, **kwargs: setattr(self, "out2", text)
		t0 = time.time()
		sdescs.send_emote(speaker, receivers, case_emote)
		t1 = time.time()
#		self.assertLess(t1-t0, 0.01)
		self.assertEqual(
			self.out0[0],
			"|mSender|n looks at |ba first receiver of emotes.|n. Then, |mSender|n "
			"looks at |bA FIRST RECEIVER OF EMOTES.|n, |bA first receiver of emotes.|n "
			"and |bA nice colliding sdesc-guy for tests|n twice.",
		)
		self.assertEqual(
			self.out1[0],
			"|bA nice sender of emotes|n looks at |mReceiver1|n. Then, "
			"|ba nice sender of emotes|n looks at |mReceiver1|n, |mReceiver1|n "
			"and |bA nice colliding sdesc-guy for tests|n twice.",
		)
		self.assertEqual(
			self.out2[0],
			"|bA nice sender of emotes|n looks at |ba first receiver of emotes.|n. "
			"Then, |ba nice sender of emotes|n looks at |bA FIRST RECEIVER OF EMOTES.|n, "
			"|bA first receiver of emotes.|n and |mReceiver2|n twice.",
		)

	def test_search(self):
		self.speaker.sdesc.add(sdesc0)
		self.receiver1.sdesc.add(sdesc1)
		self.receiver2.sdesc.add(sdesc2)
		self.speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
		self.assertEqual(self.speaker.search("receiver of emotes"), self.receiver1)
		self.assertEqual(self.speaker.search("colliding"), self.receiver2)
