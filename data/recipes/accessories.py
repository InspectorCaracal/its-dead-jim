"""
Crafting recipes for accessory-type wearables.

"""
from systems.clothing.general import cover_parts
from utils.general import MergeDict
from . import Ingredient
from .base import _UNCRAFTABLE_DICT

_KNITTING_DICT = MergeDict({
		"skill": "knitting",
		"tools": ["knitting needle", "knitting needle"],
		"tags": [("knitting","skill")],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "perfectly knit"}
	})

_WIREWORK_DICT = MergeDict({
		"skill": "wirework",
		"tags": [("wirework","skill")],
		"tools": ["pliers"],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "expertly crafted"}
	})

# ingredient tuple: type, quantity, portion, visible

###########################################
#                Scarves
###########################################

_SCARF_KNIT_DICT = _KNITTING_DICT + MergeDict({
	"tags": [("accessory", "clothing")],
	"typeclass": "systems.clothing.things.ClothingObject",
})

CLOTHING_SCARF_BASIC = _SCARF_KNIT_DICT + MergeDict({
		"ingredients": [Ingredient("yarn", 9, True, True)],
		"piece": "scarf",
		"format": { "name": "{material} {piece}", "desc": "practical {material} {piece}" },
		"difficulty": 5,
		"size": 2,
	})

CLOTHING_SCARF_XTRA_LONG = _SCARF_KNIT_DICT + MergeDict({
		"ingredients": [Ingredient("yarn", 26, True, True)],
		"piece": "scarf",
		"format": { "name": "long {material} {piece}", "desc": "extremely long {material} {piece}" },
		"difficulty": 15,
		"size": 3,
	})

CLOTHING_SHAWL_BASIC = _SCARF_KNIT_DICT + MergeDict({
		"ingredients": [Ingredient("yarn", 15, True, True)],
		"piece": "shawl",
		"format": { "name": "{material} {piece}", "desc": "triangular {material} {piece}" },
		"difficulty": 30,
		"size": 3,
	})

###########################################
#               Uncraftable!
###########################################

CLOTHING_FACTORY_GLASSES_FRAME = _UNCRAFTABLE_DICT + MergeDict({
	"_sdesc_prefix": "pair of",
	"tags": [("accessory", "clothing")],
	"req_pieces": ["lens"],
	"typeclass": "systems.clothing.things.ClothingObject",
	"ingredients": [Ingredient("plastic", 1, True, True)],
	"piece": "glasses",
	"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
	"size": 2,
})

CLOTHING_FACTORY_GLASSES_LENS = _UNCRAFTABLE_DICT + MergeDict({
	"tags": [("lens", "craft_material")] + cover_parts("eye"),
	"typeclass": "base_systems.things.base.Thing",
	"subtypes": [ "left", "right" ],
	"ingredients": [Ingredient("plastic", 1, True, True)],
	"piece": "lens",
	"format": { "name": "tinted {piece}", "desc": "tinted {material} {piece}" },
	"size": 1,
})
