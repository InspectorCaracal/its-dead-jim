"""
Crafting recipes for various food items.
"""
from utils.general import MergeDict
from . import Ingredient

_COOKING_DICT = MergeDict({
		"tags": [("cooking", "skill")],
		"skill": "cooking",
		"tools": [],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "masterwork"},
		"attrs": [
			("behaviors", {'Consumable'}, "systems"),
		],
	})

_BAKING_DICT = MergeDict({
		"tags": [("baking", "skill")],
		"skill": "baking",
		"tools": ["oven"],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "expertly crafted"},
		"attrs": [
			("behaviors", {'Consumable'}, "systems"),
		],
	})

# ingredient tuple: type, quant, portion, visible

###########################
#        Breads
###########################

_DOUGH_DICT = _BAKING_DICT + MergeDict({
		"tags": [("raw", "food")],
		"tools": [ "bowl" ],
		"piece": "dough",
		# TODO: how am i going to represent "kneading the dough" as a step???
		# this should actually just make the base dough, kneading/shaping/baking are separate
		"typeclass": "base_systems.things.base.Thing",
	})

FOOD_SMALL_YEAST_BREAD = _DOUGH_DICT + MergeDict({
		"ingredients": [Ingredient("flour", 4, True, True), Ingredient("yeast", 1, True, False), Ingredient("water", 1, True, False)],
		"_sdesc_prefix": "lump of",
		"size": 3,
		"cooked_piece": "bread",
		"format": { "name": "{material} {piece}", "desc": "small {shape} lump of {material} {piece}" },
		"difficulty": 1,
	})

###########################
#        Cakes
###########################

_BATTER_DICT = _BAKING_DICT + MergeDict({
		"tags": [("raw", "food")],
		"tools": [ "bowl" ],
		"piece": "batter",
		# "typeclass": "base_systems.things.liquids.LiquidThing",
		# TODO: once i implement proper baking, it should start as LiquidThing
		"typeclass": "base_systems.things.base.Thing",
	})

FOOD_SMALL_YELLOW_CAKE = _BATTER_DICT + MergeDict({
		"ingredients": [
			Ingredient("flour", 2, True, False), Ingredient("baking powder", 1, True, False),
			Ingredient("milk", 2, True, False), Ingredient("egg", 1, True, False), Ingredient("sugar", 1, True, False)
			],
		"size": 2,
		"sat": 7,
		# this is a hack for now
		"cooked_piece": "cake",
		"format": { "name": "{material} {piece}", "desc": "plain {material} {piece}" },
		"difficulty": 1,
		"stats": {
			'quantity': {'base': 5, 'min': 0, 'max': 5, 'name': 'Quantity', 'trait_type': 'counter', 'descs': None, 'mult': 1.0, 'mod': 0, 'rate': 0, 'ratetarget': None, 'last_update': None}
		},
	})

FOOD_SMALL_CHOCOLATE_CAKE = _BATTER_DICT + MergeDict({
		"ingredients": [
			Ingredient("flour", 2, True, False), Ingredient("cocoa", 2, True, False), Ingredient("baking powder", 1, True, False),
			Ingredient("milk", 2, True, False), Ingredient("egg", 1, True, False), Ingredient("sugar", 1, True, False)
			],
		"size": 2,
		"sat": 7,
		"cooked_piece": "cake",
		"format": { "name": "{material} {piece}", "desc": "chocolate {material} {piece}" },
		"difficulty": 1,
		"stats": {
			'quantity': {'base': 5, 'min': 0, 'max': 5, 'name': 'Quantity', 'trait_type': 'counter', 'descs': None, 'mult': 1.0, 'mod': 0, 'rate': 0, 'ratetarget': None, 'last_update': None}
		},
	})

# TODO: the batter really should make multiple donuts idk this is a hack
FOOD_MINI_DONUT = _BATTER_DICT + MergeDict({
		"ingredients": [
			Ingredient("flour", 1, True, False), Ingredient("baking powder", 1, True, False),
			Ingredient("milk", 1, True, False), Ingredient("egg", 1, True, False), Ingredient("sugar", 1, True, False)
			],
		"size": 1,
		"sat": 3,
		# this is a hack for now
		"cooked_piece": "donut",
		"format": { "name": "mini {material} {piece}", "desc": "miniature {material} {piece}" },
		"difficulty": 1,
		"stats": {
			'quantity': {'base': 3, 'min': 0, 'max': 3, 'name': 'Quantity', 'trait_type': 'counter', 'descs': None, 'mult': 1.0, 'mod': 0, 'rate': 0, 'ratetarget': None, 'last_update': None}
		},
	})


#######################################
#          Fillings & Toppings
#######################################

FOOD_WHIPPED_CREAM = _COOKING_DICT + MergeDict({
		"ingredients": [Ingredient("milk", 2, True, True), Ingredient("sugar", 2, True, True), ],
		"size": 1,
		"sat": 2,
		"piece": "whipped cream",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 1,
		"stats": {
			'quantity': {'base': 2, 'min': 0, 'max': 2, 'name': 'Quantity', 'trait_type': 'counter', 'descs': None, 'mult': 1.0, 'mod': 0, 'rate': 0, 'ratetarget': None, 'last_update': None}
		},
	})



#######################################
#               Salads
#######################################

_SALAD_DICT = _COOKING_DICT + MergeDict({
#		"tools": ["bowl"],
		"typeclass": "core.objects.typeclasses.EdibleObject",
	})

FOOD_MEAT_SALAD = _SALAD_DICT + MergeDict({
		"tags": [("meat", "craft_material")],
		"tools": ["knife", "bowl", "spoon"],
		"size": 2,
		"ingredients": [ Ingredient("meat", 4, True, True), Ingredient("condiment", 1, True, False) ],
		"piece": "salad",
		"format": { "name": "{material} salad", "desc": "{material} salad" },
		# extras like veggies, pickles, etc are add-ons
	})

#######################################
#             Sandwiches
#######################################

_SANDWICH_DICT = _COOKING_DICT + MergeDict({
		"tools": [],
		"typeclass": "core.objects.typeclasses.EdibleObject",
		"self_destruct": True,
		"name_include": ["meat", "cheese"],
		"name_exclude": ["bread"],
		"req_pieces": ["bread"],
	})

FOOD_SANDWICH_BASE = _SANDWICH_DICT + MergeDict({
		"ingredients": [],
		"piece": "sandwich",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 1,
		"size": 2,
	})

