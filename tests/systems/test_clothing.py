"""
Tests for decor system

"""
from mock import MagicMock, patch
from anything import Anything
from unittest import skip
from evennia import create_object

from systems.clothing import handler
from systems.clothing.general import cover_parts
from utils.testing import NexusTest, undelay

_leggings = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "leggings",
	"tags": cover_parts("butt", "hip", "upper leg") + [ ("bottom", handler._CLOTHING_TAG_CATEGORY) ],
}

_left_leg = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "leg",
	"tags": cover_parts("butt", ("hip", "left"), ("upper leg", "left")),
}

_right_leg = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "leg",
	"tags": cover_parts("butt", ("hip", "right"), ("upper leg", "right")),
}

_underwear = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "underwear",
	"tags": cover_parts("butt") + [ ("underpants", handler._CLOTHING_TAG_CATEGORY) ],
}
_eyepatch = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "eyepatch",
	"tags": cover_parts(("eye", "left")) + [ ("underpants", handler._CLOTHING_TAG_CATEGORY) ],
}
_sunglasses = {
	"typeclass": "base_systems.things.base.Thing",
	"key": "sunglasses",
	"tags": cover_parts("eye") + [ ("underpants", handler._CLOTHING_TAG_CATEGORY) ],
}

class TestClothingUtils(NexusTest):
	def test_cover_parts(self):
		one_tag = [ ("head", "parts_coverage") ]
		multi_tags = [ ("chest", "parts_coverage"), ("back", "parts_coverage") ]
		subtype_tag = [ ("back,upper", "parts_coverage") ]

		self.assertEqual(cover_parts("head"), one_tag)
		self.assertEqual(cover_parts("chest", "back"), multi_tags)
		self.assertEqual(cover_parts(("back", "upper")), subtype_tag)

class TestClothingHandler(NexusTest):
	def setUp(self):
		super().setUp()
		with patch("systems.chargen.gen.choice", new=lambda *args: args[0][0]):
			self.player = self.create_player()
		self.leggings = create_object(location=self.player, **_leggings)
		self.underwear = create_object(location=self.player, **_underwear)

	def test_add_remove(self):
		clothes = self.player.clothing
		self.assertEqual(clothes.all,[])
		message = clothes.add(self.underwear)
		self.assertIn(self.underwear, clothes.all)
		self.assertEqual(message, "puts on an underwear, covering smooth |#402510dark|n skin.")

		message = clothes.add(self.leggings)
		self.assertIn(self.leggings, clothes.all)
		self.assertTrue(self.underwear.effects.has(name='covered'))
		self.assertEqual(message, "puts on a leggings, covering an underwear and smooth |#402510dark|n skin.")

		message = clothes.remove(self.leggings)
		self.assertFalse(self.leggings in clothes.all)
		self.assertEqual(message, "removes a leggings, revealing an underwear and smooth |#402510dark|n skin.")

	def test_coverage(self):
		clothes = self.player.clothing
		clothes.add(self.underwear)
		clothes.add(self.leggings)
		# leggings completely cover underwear
		self.assertTrue(self.underwear.tags.has("hidden", category="systems"))
		self.assertTrue(self.underwear.effects.has(name='covered'))
		# leggings are not hidden
		self.assertFalse(self.leggings.tags.has("hidden", category="systems"))
		self.assertEqual(clothes.visible(self.player), [self.leggings])

	# FIXME: partial coverage is not a thing
	@skip
	def test_partial_coverage(self):
		clothes = self.player.clothing
		clothes.clear()
		clothes.add(self.leggings)
		clothes.add(self.underwear)
		# underwear don't completely cover leggings
		self.assertFalse(self.underwear.tags.has("hidden", category="systems"))
		self.assertFalse(self.leggings.tags.has("hidden", category="systems"))

		second_leggings = create_object(location=self.player, **_leggings)
		clothes.clear()
		clothes.add(self.leggings)
		clothes.add(second_leggings)
		# completely cover with identical coverage
		self.assertTrue(self.leggings.tags.has("hidden", category="systems"))

		# cover only one of a subtype
		eyepatch = create_object(location=self.player, **_eyepatch)
		message = clothes.add(eyepatch)
		self.assertIn("a |#5E391Fdark brown|n eye", message)
		self.assertIn("a |#5E391Fdark brown|n eye", self.player.features.view)
		clothes.remove(eyepatch)

		# cover both of a subtype
		sunglasses = create_object(location=self.player, **_sunglasses)
		message = clothes.add(sunglasses)
		self.assertIn("|#5E391Fdark brown|n eyes", message)
		self.assertNotIn("|#5E391Fdark brown|n eye", self.player.features.view)
	
	def test_parts_coverage(self):
		clothes = self.player.clothing

		leftleg = create_object(**_left_leg)
		rightleg = create_object(**_right_leg)
		leftleg.partof = self.underwear
		rightleg.partof = self.underwear
		base = create_object(location=self.player, **{
			"typeclass": self.object_typeclass,
			"key": "pants",
			"tags": cover_parts("butt") + [ ("bottom", handler._CLOTHING_TAG_CATEGORY) ],
		})
		leftleg = create_object(**_left_leg)
		rightleg = create_object(**_right_leg)
		leftleg.partof = base
		rightleg.partof = base

		# now try to cover the one with the other
		clothes.add(self.underwear)
		clothes.add(base)
		# TODO: figure out the best way to check if object A has an effect sourced from object B


	def test_can_add(self):
		clothes = self.player.clothing
		# create non-wearable object
		thing = create_object(location=self.player, typeclass=self.object_typeclass, key="something")
		self.assertFalse(clothes.can_add(thing))
		self.assertTrue(clothes.can_add(self.leggings))
	
	def test_clear(self):
		clothes = self.player.clothing
		# completely cover
		clothes.add(self.underwear)
		clothes.add(self.leggings)
		self.assertEqual(clothes.all, [self.underwear, self.leggings])
		clothes.clear()
		self.assertEqual(clothes.all, [])

	def test_get_outfit(self):
		clothes = self.player.clothing
		# completely cover
		clothes.add(self.underwear)
		clothes.add(self.leggings)
		self.assertEqual(clothes.get_outfit(), ["a leggings"])

		# don't completely cover
		# FIXME: partial coverage isn't implemented
		# clothes.clear()
		# clothes.add(self.leggings)
		# clothes.add(self.underwear)
		# self.assertEqual(clothes.get_outfit(), ["a leggings", "an underwear"])