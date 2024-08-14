from typing import NamedTuple

class Ingredient(NamedTuple):
	type: str
	quantity: int
	portion: bool
	visible: bool

#Ingredient = namedtuple("Ingredient", "type quantity portion visible")

from . import clothing, furniture, food, art, accessories, commercial

RECIPE_DICTS = {
		name.lower():recipe for name, recipe in vars(clothing).items() if not name.startswith('_') and name != "MergeDict"
	} | {
		name.lower():recipe for name, recipe in vars(furniture).items() if not name.startswith('_') and name != "MergeDict"
	} | {
		name.lower():recipe for name, recipe in vars(food).items() if not name.startswith('_') and name != "MergeDict"
	} | {
		name.lower():recipe for name, recipe in vars(art).items() if not name.startswith('_') and name != "MergeDict"
	} | {
		name.lower():recipe for name, recipe in vars(accessories).items() if not name.startswith('_') and name != "MergeDict"
	} | {
		name.lower():recipe for name, recipe in vars(commercial).items() if not name.startswith('_') and name != "MergeDict"
	}

