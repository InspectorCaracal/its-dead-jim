"""
Tests for the character skills system

"""
import time
import unittest
from anything import Anything
from parameterized import parameterized
from evennia.utils.test_resources import EvenniaTest

import utils.strmanip

from utils import colors

class TestGeneralUtils(EvenniaTest):

	@parameterized.expand(
		[
			(1, "a |rred|n book", {}),
			(2, "two |rred|n books", {}),
			(0, "no |rred|n books", {}),
			(2, "a pair of |rred|n books", {'pair': True}),
			(2, "two |rred|n book", {'pluralize': False}),
			(1, "A |rred|n book", {'cap': True}),
		]
	)
	def test_numbered_name(self, num, expected, kwargs):
		self.assertEqual(
				utils.strmanip.numbered_name("|rred|n book", num, **kwargs),
				expected
			)

	def test_strip_extra_spaces(self):
		original = "This has  a lot   of\n \n\n\n\nextra\n\nspace."
		self.assertEqual(
			utils.strmanip.strip_extra_spaces(original),
			"This has a lot of\n\nextra\n\nspace."
		)

class TestColorUtils(EvenniaTest):
	@parameterized.expand(
		[
			("#555555", "=i"),
			("#8a22ff", "205"),
		]
	)
	def test_hex_to_xterm(self, hex, xterm):
		message = "A |{color}color|n code"
		input = message.format(color=hex)
		output = message.format(color=xterm)
		self.assertEqual(colors.hex_to_xterm(input), output)

	@parameterized.expand(
		[
			("=i", "#585858"),
			("205", "#6919e1"),
		]
	)
	def test_xterm_to_hex(self, xterm, hex):
		message = "A |{color}color|n code"
		input = message.format(color=xterm)
		output = message.format(color=hex)
		self.assertEqual(colors.xterm_to_hex(input), output)
	
	def test_ev_to_html(self):
		message = "Testing |bcolors|n, |lclook|ltcommands|le, |205xterm|n and |#123456hex|n."
		output = colors.ev_to_html(message)
		expected = 'Testing <span style="color: var(--blue1);">colors</span>, <span class="mxplink" data-command="look">commands</span>, <span style="color: #6919e1;">xterm</span> and <span style="color: #123456;">hex</span>.'
		self.assertEqual(output, expected)