"""
Crafting recipes for various furniture items.
"""
from utils.general import MergeDict
from . import Ingredient

_WHITTLING_DICT = MergeDict({
		"tags": [("whittling", "skill")],
		"skill": "whittling",
		"tools": ["knife"],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "expertly crafted"}
	})

_STONE_CARVING_DICT = MergeDict({
		"tags": [("stonecarving", "skill")],
		"skill": "stonecarving",
		"tools": ["chisel",],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "masterwork"}
	})


# base blocks for carving wood
_WOOD_FIGURE_DICT = _WHITTLING_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"typeclass": "base_systems.things.base.Thing",
	})


CARVING_WOOD_TINY = _WOOD_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("wood", 1, True, True)],
		"piece": "carving",
		"format": { "name": "tiny {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 1,
	})
CARVING_WOOD_SMALL = _WOOD_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("wood", 2, True, True)],
		"piece": "carving",
		"format": { "name": "small {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 2,
	})
CARVING_WOOD_MEDIUM = _WOOD_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("wood", 4, True, True)],
		"piece": "carving",
		"format": { "name": "medium {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 4,
	})
CARVING_WOOD_LARGE = _WOOD_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("wood", 6, True, True)],
		"piece": "carving",
		"format": { "name": "large {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 6,
	})
CARVING_WOOD_HUGE = _WOOD_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("wood", 8, True, True)],
		"piece": "carving",
		"format": { "name": "enormous {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 8,
	})



# base blocks for carving stone
_STONE_FIGURE_DICT = _STONE_CARVING_DICT + MergeDict({
		"tags": [("stone", "design_base")],
		"typeclass": "base_systems.things.base.Thing",
	})

CARVING_STONE_TINY = _STONE_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("stone", 1, True, True)],
		"piece": "carving",
		"format": { "name": "tiny {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 1,
	})
CARVING_STONE_SMALL = _STONE_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("stone", 2, True, True)],
		"piece": "carving",
		"format": { "name": "small {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 2,
	})
CARVING_STONE_MEDIUM = _STONE_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("stone", 4, True, True)],
		"piece": "carving",
		"format": { "name": "medium {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 4,
	})
CARVING_STONE_LARGE = _STONE_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("stone", 6, True, True)],
		"piece": "carving",
		"format": { "name": "large {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 6,
	})
CARVING_STONE_HUGE = _STONE_FIGURE_DICT + MergeDict({
		"ingredients": [Ingredient("stone", 8, True, True)],
		"piece": "carving",
		"format": { "name": "enormous {material} {piece}", "desc": "" },
		"difficulty": 1,
		"size": 8,
	})
