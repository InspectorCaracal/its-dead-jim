from data.recipes import Ingredient
from utils.general import MergeDict

from .base import _UNCRAFTABLE_DICT

# snacks
SNACK_BAG = _UNCRAFTABLE_DICT + MergeDict({
	"key": "bag",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ]
})

DRINK_BOTTLE = _UNCRAFTABLE_DICT + MergeDict({
	"key": "plastic bottle",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ]
})

DRINK_CAN = _UNCRAFTABLE_DICT + MergeDict({
	"key": "can",
	"size": 2,
	"typeclass": "base_systems.things.base.Thing",
	"effects": [ 'base_systems.things.effects.SealedEffect' ]
})

CRAPPY_SNACK_CHIPS = _UNCRAFTABLE_DICT + MergeDict({
	"key": "snack chip",
	"size": 1,
	"sat": 0.3,
	"typeclass": "base_systems.things.base.Thing",
	"attrs": [
		("behaviors", {'Consumable'}, "systems"),
	],
})

FACTORY_PAPER = _UNCRAFTABLE_DICT + MergeDict({
	"key": "paper",
	"_sdesc_prefix": "sheet of",
	'size': 3,
	"attrs": [
		("sides", {'front', 'back'}, "systems"),
	],
	"tags": [
		("front", "side_up"),
	],
	"locks": "craftwith:perm(player);design:perm(player)",
})

FACTORY_COLORED_PENCIL = _UNCRAFTABLE_DICT + MergeDict({
	"ingredients": [Ingredient("pencil", 1, False, True)],
	"piece": "pencil",
	"format": { "name": "{material} {piece}", "desc": "{material}" },
	"locks": "craftwith:perm(player)",
	"tags": [
		("sketching", "crafting_tool"),
	],
})

GLASS_DOOR = _UNCRAFTABLE_DICT + MergeDict({
	"key": "glass door",
	"size": 10,
	"tags": [ "transparent", ],
	"locks": "get:perm(builder);craftwith:false()"
})