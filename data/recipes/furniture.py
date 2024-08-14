"""
Crafting recipes for various furniture items.
"""
from utils.general import MergeDict
from . import Ingredient

_CARPENTRY_DICT = MergeDict({
		"tags": [("carpentry", "skill")],
		"skill": "carpentry",
		"tools": ["saw",],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "masterwork"}
	})

_WHITTLING_DICT = MergeDict({
		"tags": [("whittling", "skill")],
		"skill": "whittling",
		"tools": ["knife"],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "expertly crafted"}
	})

# ingredient tuple: type, quant, portion, visible

###########################
#        Tabletops
###########################

_TABLE_DICT = _CARPENTRY_DICT + MergeDict({
		"tags": [("decor", "systems")],
		"req_pieces": ("leg",),
		"onword": "on top",
		"tools": [ "plane", "hammer" ],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_TABLE_ROUND_SMALL = _TABLE_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"ingredients": [Ingredient("wood", 5, True, True), Ingredient("nail", 4, True, False)],
		"piece": "table",
		"format": { "name": "small {material} {piece}", "desc": "circular {material} {piece}, just big enough for a few items" },
		"difficulty": 30,
		"size": 4,
	})

FURNITURE_TABLE_SQUARE_SMALL = _TABLE_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 6, True, True), Ingredient("nail", 4, True, False)],
		"piece": "table",
		"format": { "name": "small {material} {piece}", "desc": "square {material} {piece}, just big enough for a few items" },
		"difficulty": 20,
		"size": 4,
	})


##############################
#   Chairs and chair-parts
##############################

_CHAIR_DICT = _CARPENTRY_DICT + MergeDict({
		"tags": [("decor", "systems"), ("sittable", "systems")],
		"req_pieces": ["leg",],
		"onword": "on",
		"tools": [ "plane", ],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_CHAIR_STOOL = _CHAIR_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 4, True, True), Ingredient("nail", 4, True, False)],
		"piece": "stool",
		"format": { "name": "{material} {piece}", "desc": "round, simple {material} {piece}" },
		"difficulty": 20,
		"size": 3,
	})

FURNITURE_CHAIR_BASIC = _CHAIR_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"req_pieces": ["seat back",],
		"ingredients": [Ingredient("wood", 4, True, True), Ingredient("nail", 8, True, False)],
		"piece": "chair",
		"format": { "name": "{material} {piece}", "desc": "basic {piece} with a flat {material} seat" },
		"difficulty": 30,
		"size": 3,
	})

_CHAIR_BACK_DICT = _WHITTLING_DICT + MergeDict({
		"tags": [("seat back", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_CHAIR_BACK_SPINDLE = _CHAIR_BACK_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 4, True, True)],
		"piece": "spindle back",
		"format": { "name": "{material} {piece}", "desc": "slightly curved {material} {piece}" },
		"difficulty": 50,
		"size": 4,
	})



################################
#        Furniture Legs
################################

_LEG_DICT = _CARPENTRY_DICT + MergeDict({
		"tags": [("leg", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_LEG_BASIC_SHORT = _LEG_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 1, True, True)],
		"piece": "leg",
		"format": { "name": "short {material} {piece}", "desc": "short, rectangular {material} {piece}" },
		"difficulty": 5,
		"size": 3,
	})

FURNITURE_LEG_BASIC_MEDIUM = _LEG_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 2, True, True)],
		"piece": "leg",
		"format": { "name": "{material} {piece}", "desc": "rectangular {material} {piece}" },
		"difficulty": 10,
		"size": 4,
	})

FURNITURE_LEG_BASIC_TALL = _LEG_DICT + MergeDict({
		"tags": [("wood", "design_base")],
		"ingredients": [Ingredient("wood", 3, True, True)],
		"piece": "leg",
		"format": { "name": "tall {material} {piece}", "desc": "tall, rectangular {material} {piece}" },
		"difficulty": 10,
		"size": 5,
	})


################################
#      Cabinets and Cases
################################

_CABINET_DICT = _CARPENTRY_DICT + MergeDict({
		"tags": [("decor", "systems")],
		"req_pieces": ("shelf",),
		"onword": "in",
		"tools": [ "plane", "hammer" ],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_CABINET_BASIC_SMALL = _CABINET_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"size": 6,
		"ingredients": [Ingredient("wood", 10, True, True), Ingredient("nail", 8, True, False)],
		"piece": "cabinet",
		"format": { "name": "small {material} {piece}", "desc": "simple {material} {piece}, just big enough for a few items" },
		"difficulty": 40,
	})

FURNITURE_CABINET_BASIC_MEDIUM = _CABINET_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"size": 8,
		"ingredients": [Ingredient("wood", 25, True, True), Ingredient("nail", 14, True, False)],
		"piece": "cabinet",
		"format": { "name": "{material} {piece}", "desc": "simple {material} {piece}, with enough space for most things" },
		"difficulty": 40,
	})

FURNITURE_CABINET_BASIC_LARGE = _CABINET_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"size": 10,
		"ingredients": [Ingredient("wood", 50, True, True), Ingredient("nail", 20, True, False)],
		"piece": "cabinet",
		"format": { "name": "large {material} {piece}", "desc": "simple {material} {piece}, with more than enough space" },
		"difficulty": 50,
	})



################################
#           Shelves
################################

_SHELF_DICT = _CARPENTRY_DICT + MergeDict({
		"tags": [("decor", "systems"), ("shelf", "craft_material")],
		"onword": "on",
		"tools": [ "plane", ],
		"typeclass": "base_systems.things.base.Thing",
	})

FURNITURE_SHELF_SMALL = _SHELF_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"ingredients": [Ingredient("wood", 5, True, True)],
		"piece": "shelf",
		"format": { "name": "{material} {piece}", "desc": "small {material} {piece}" },
		"difficulty": 5,
		"size": 3,
	})
FURNITURE_SHELF_MEDIUM = _SHELF_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"ingredients": [Ingredient("wood", 5, True, True)],
		"piece": "shelf",
		"format": { "name": "{material} {piece}", "desc": "basic {material} {piece}" },
		"difficulty": 5,
		"size": 4,
	})
FURNITURE_SHELF_LARGE = _SHELF_DICT + MergeDict({
		"tags": [("wood", "design_base"),],
		"ingredients": [Ingredient("wood", 5, True, True)],
		"piece": "shelf",
		"format": { "name": "{material} {piece}", "desc": "large {material} {piece}" },
		"difficulty": 5,
		"size": 5,
	})

################################
#           Doors
################################
