

from random import randint
from utils.general import MergeDict

# snacks
SNACK_BAG = MergeDict({
	"key": "snack bag",
	"desc": "A clear plastic bag, for pre-packaged foods.",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ],
	"tags": [ ('closed','status'), ('snack_bag', 'recipe_key') ],
	"locks": "viewcon:true()",
})

DRINK_BOTTLE = MergeDict({
	"key": "plastic bottle",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ]
})

DRINK_CAN = MergeDict({
	"key": "can",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ]
})

_LOGO_BASE = {
	"key": "design",
	"typeclass": "base_systems.meta.base.MetaThing",
	"tags": [ ('external', 'attach_type'), ('design', 'part') ],
	'locks': 'get:false()'
}
TWINKIE_LOGO = _LOGO_BASE | {
	'desc': "A large, stylized rendering of the word TWINKLES in red letters, over a photograph of a small, cream-filled oblong cake."
	"\n\nIn the top corner is the Mostest logo.",
}
HOHO_LOGO = _LOGO_BASE | {
	'desc': "A large, stylized rendering of the word GO-GOS in red letters, over a photograph of a small, cream-filled rolled chocolate cake."
	"\n\nIn the top corner is the Mostest logo.",
}
DONETTE_LOGO = _LOGO_BASE | {
	'desc': "A large, stylized rendering of the word MINI-DOS in red letters, over a photograph of a tiny powdered donut."
	"\n\nIn the top corner is the Mostest logo.",
}

# Assembly dicts for final cakes and bags
_TWINKIES = {
	"recipe": "ASSEMBLE",
	"base": "FOOD_SMALL_YELLOW_CAKE",
	"shape": "narrow",
	"adds": ["FOOD_WHIPPED_CREAM",]
}
_DONETTES = {
	"recipe": "ASSEMBLE",
	"base": "FOOD_MINI_DONUT",
	"adds": [], # TODO: add the powdered sugar
}
_HOHOS = {
	"recipe": "ASSEMBLE",
	"base": "FOOD_SMALL_CHOCOLATE_CAKE",
	"shape": "rolled",
	"adds": ["FOOD_WHIPPED_CREAM",]
}

CRAPPY_SNACK_CHIPS = MergeDict({
	"key": "snack chip",
	"size": 1,
	"sat": 0.3,
	"typeclass": "base_systems.things.base.Thing",
	"attrs": [
		("behaviors", {'Consumable'}, "systems"),
	],
	"stats": {
			'quantity': {'base': 1, 'min': 0, 'max': 1, 'name': 'Quantity', 'trait_type': 'counter', 'descs': None, 'mult': 1.0, 'mod': 0, 'rate': 0, 'ratetarget': None, 'last_update': None}
			},
})


from data.materials import FLAVORFUL_MATERIAL

SNACK_MACHINE = [
	{
		"name": "Mostest Twinkles",
		"container": SNACK_BAG,
		"design": TWINKIE_LOGO,
		"recipes": [_TWINKIES]*2,
		"materials": {
			'sugar': [('sugar', { 'flavors': ['sweet'] })],
		},
		"price": 5,
	},
	{
		"name": "Mostest Go-Gos",
		"container": SNACK_BAG,
		"design": HOHO_LOGO,
		"recipes": [_HOHOS]*2,
		"materials": {
			'sugar': [('sugar', { 'flavors': ['sweet'] })],
			# TODO: add color for chocolate
			'cocoa': [('chocolate', { 'flavors': ['bitter'],	"color": "",
#	"format": "{color}",
	"pigment": (80, 30, 20),
	"color_quality": 4 })],
		},
		"price": 5,
	},
	{
		"name": "Mostest Mini-Dos",
		"container": SNACK_BAG,
		"design": DONETTE_LOGO,
		"recipes": [_DONETTES]*6,
		"materials": {
			'sugar': [('sugar', { 'flavors': ['sweet'] })],
		},
		"price": 5,
	},
]
