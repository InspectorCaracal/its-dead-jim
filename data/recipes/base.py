# from data.recipes import clothing, furniture, food, art, accessories

# RECIPE_DICTS = {
# 		name.lower():recipe for name, recipe in vars(clothing).items() if not name.startswith('_') and name != "MergeDict"
# 	} | {
# 		name.lower():recipe for name, recipe in vars(furniture).items() if not name.startswith('_') and name != "MergeDict"
# 	} | {
# 		name.lower():recipe for name, recipe in vars(food).items() if not name.startswith('_') and name != "MergeDict"
# 	} | {
# 		name.lower():recipe for name, recipe in vars(art).items() if not name.startswith('_') and name != "MergeDict"
# 	} | {
# 		name.lower():recipe for name, recipe in vars(accessories).items() if not name.startswith('_') and name != "MergeDict"
# 	}

from utils.general import MergeDict


_UNCRAFTABLE_DICT = MergeDict({
		"skill": "factory",
		"tags": [("factory","skill")],
		"quality_levels": {0: "cheap", 1: "", 6: "stylish", 9: "high-end"},
		"quality": 0,
		"difficulty": 99,
	})
