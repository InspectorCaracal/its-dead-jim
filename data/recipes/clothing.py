"""
Crafting recipes for various wearables.

Includes the recipe classes for all types of craftable clothing.
All crafted wearables have names and descriptions based on the
materials used to create them.
"""
from systems.clothing.general import cover_parts
from utils.general import MergeDict
from . import Ingredient

_TAILOR_DICT = MergeDict({
		"skill": "tailoring",
		"tools": ["shears", "sewing needle"],
		"tags": [("tailoring","skill")],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "perfectly tailored"}
	})

_KNITTING_DICT = MergeDict({
		"skill": "knitting",
		"tools": ["knitting needle", "knitting needle"],
		"tags": [("knitting","skill")],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "perfectly tailored"}
	})

_COBBLER_DICT = MergeDict({
		"skill": "cobbling",
		"tags": [("cobbling","skill")],
#		"tools": ["sewing needle", "awl", "carving knife"],
		"tools": ["shears", "awl", "sewing needle"],
		"quality_levels": {0: "crude", 1: "", 5: "neat", 7: "fine", 9: "expertly crafted"}
	})

# ingredient tuple: type, quant, portion, visible

###########################
#        Top Bases
###########################

_TOP_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("top","clothing")],
		"typeclass": "systems.clothing.things.ClothingObject",
		"req_pieces": ["sleeve"],
	})

CLOTHING_TUNIC_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "tunic",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 5,
		"size": 4,
	})

CLOTHING_VNECK_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "shirt",
		"format": { "name": "{material} {piece}", "desc": "{material} v-neck {piece}" },
		"difficulty": 30,
		"size": 4,
	})

CLOTHING_UNECK_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "shirt",
		"format": { "name": "{material} {piece}", "desc": "{material} scoop-neck {piece}" },
		"difficulty": 40,
		"size": 4,
	})

CLOTHING_BUTTONUP_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "shirt",
		"req_pieces": ["button"],
		"format": { "name": "{material} {piece}", "desc": "{material} button-up {piece}" },
		"difficulty": 40,
		"size": 4,
	})

CLOTHING_LACEUP_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "shirt",
		"req_pieces": ['cord'],
		"format": { "name": "{material} {piece}", "desc": "{material} lace-up {piece}" },
		"difficulty": 20,
		"size": 4,
	})

CLOTHING_CROPTOP_BASE = _TOP_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("chest", ("back", "upper")),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "crop top",
		"format": { "name": "{material} {piece}", "desc": "very short {material} {piece}" },
		"difficulty": 5,
		"size": 4,
	})


###########################
#        Sleeves
###########################

_SLEEVE_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("sleeve", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
		"subtypes": [ "left", "right" ],
	})

CLOTHING_SLEEVE_SHORT = _SLEEVE_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("shoulder"),
		"ingredients": [Ingredient("fabric", 2, True, True), Ingredient("thread", 1, True, False)],
		"piece": "sleeve",
		"format": { "name": "short {material} {piece}", "desc": "short {material} {piece}" },
		"difficulty": 20,
		"size": 2,
	})

CLOTHING_SLEEVE_CAP = _SLEEVE_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts('shoulder'),
		"ingredients": [Ingredient("fabric", 3, True, True), Ingredient("thread", 1, True, False)],
		"piece": "cap sleeve",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 40,
		"size": 2,
	})

CLOTHING_SLEEVE_LONG = _SLEEVE_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("shoulder", "upper arm", "elbow", "lower arm"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "sleeve",
		"format": { "name": "long {material} {piece}", "desc": "long, straight {material} {piece}" },
		"difficulty": 25,
		"size": 3,
	})

CLOTHING_SLEEVE_DRAPE = _SLEEVE_DICT + MergeDict({
		"tags": [ ("fabric", "design_base") ] + cover_parts("shoulder", "upper arm", "elbow", "lower arm", "wrist"),
		"ingredients": [Ingredient("fabric", 9, True, True), Ingredient("thread", 1, True, False)],
		"piece": "sleeve",
		"format": { "name": "{material} drape {piece}", "desc": "long, loose {material} {piece}" },
		"difficulty": 30,
		"size": 4,
	})


###########################
#      Shirt Collars
###########################
_COLLAR_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("collar", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
	})

CLOTHING_COLLAR_STANDING = _COLLAR_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("neck"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "collar",
		"format": { "name": "{material} {piece}", "desc": "{material} standing {piece}" },
		"difficulty": 20,
		"size": 2,
	})

CLOTHING_COLLAR_POINT = _COLLAR_DICT + MergeDict({
		"tags": [("fabric", "design_base")],
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "collar",
		"format": { "name": "{material} point {piece}", "desc": "{material} {piece} with folded-down points" },
		"difficulty": 40,
		"size": 2,
	})

CLOTHING_COLLAR_ROUND = _COLLAR_DICT + MergeDict({
		"tags": [("fabric", "design_base")],
		"ingredients": [Ingredient("fabric", 2, True, True), Ingredient("thread", 1, True, False)],
		"piece": "collar",
		"format": { "name": "rounded {material} {piece}", "desc": "rounded, folded-down {material} {piece}" },
		"difficulty": 55,
		"size": 2,
	})


###############################
#        Bottom Bases
###############################

_BOTTOM_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("bottom","clothing")],
		"typeclass": "systems.clothing.things.ClothingObject",
		"_sdesc_prefix": "pair of",
	})

CLOTHING_TROUSER_BASE = _BOTTOM_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("butt"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ["leg"],
		"piece": "trousers",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 30,
		"size": 4,
	})


###############################
#          Legs
###############################
_LEG_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("leg", "craft_material"),("fabric","design_base")],
		"typeclass": "base_systems.things.base.Thing",
		"subtypes": [ "left", "right" ],
	})

CLOTHING_LEG_SHORT = _LEG_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("hip"),
		"ingredients": [Ingredient("fabric", 4, True, True), Ingredient("thread", 1, True, False)],
		"piece": "leg",
		"format": { "name": "short {material} {piece}", "desc": "short {material} {piece}" },
		"difficulty": 40,
		"size": 3,
	})

CLOTHING_LEG_CAPRI = _LEG_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("hip", "upper leg", "knee"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "leg",
		"format": { "name": "{material} capri {piece}", "desc": "{material} capri {piece}" },
		"difficulty": 40,
		"size": 4,
	})

CLOTHING_LEG_LONG = _LEG_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("hip", "upper leg", "knee", "lower leg"),
		"ingredients": [Ingredient("fabric", 9, True, True), Ingredient("thread", 2, True, False)],
		"piece": "leg",
		"format": { "name": "long {material} {piece}", "desc": "long, straight {material} {piece}" },
		"difficulty": 40,
		"size": 5,
	})

CLOTHING_LEG_LOOSE = _LEG_DICT + MergeDict({
		"tags": [("fabric", "design_base")] + cover_parts("hip", "upper leg", "knee", "lower leg"),
		"ingredients": [Ingredient("fabric", 12, True, True), Ingredient("thread", 2, True, False)],
		"piece": "leg",
		"format": { "name": "loose {material} {piece}", "desc": "skirt-like {material} {piece} which hangs to ankle length" },
		"difficulty": 20,
		"size": 6,
	})

###############################
#          Skirts
###############################
_SKIRT_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("bottom", "clothing"),("fabric","design_base")],
		"typeclass": "systems.clothing.things.ClothingObject",
	})

CLOTHING_SKIRT_MINI = _SKIRT_DICT + MergeDict({
		"tags": cover_parts("hip"),
		"ingredients": [Ingredient("fabric", 3, True, True), Ingredient("thread", 1, True, False)],
		"piece": "miniskirt",
		"format": { "name": "{material} {piece}", "desc": "{material} {piece}" },
		"difficulty": 30,
		"size": 3,
	})

CLOTHING_SKIRT_MID = _SKIRT_DICT + MergeDict({
		"tags": cover_parts("hip", "upper leg", "knee"),
		"ingredients": [Ingredient("fabric", 6, True, True), Ingredient("thread", 1, True, False)],
		"piece": "skirt",
		"format": { "name": "{material} {piece}", "desc": "straight-cut {material} {piece} at just about knee length" },
		"difficulty": 30,
		"size": 4,
	})

CLOTHING_SKIRT_TIER = _SKIRT_DICT + MergeDict({
		"tags": cover_parts("hip", "upper leg", "knee", "lower leg"),
		"ingredients": [Ingredient("fabric", 12, True, True), Ingredient("thread", 1, True, False)],
		"piece": "skirt",
		"format": { "name": "{material} tier {piece}", "desc": "long, multi-tiered {piece} made of {material}" },
		"difficulty": 20,
		"size": 6,
	})


###############################
#          Underpants
###############################
_UNDERPANTS_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("underpants", "clothing"),("fabric","design_base")],
		"typeclass": "systems.clothing.things.ClothingObject",
	})

CLOTHING_BRIEFS = _UNDERPANTS_DICT + MergeDict({
		"_sdesc_prefix": "pair of",
		"tags": cover_parts("butt"),
		"ingredients": [Ingredient("fabric", 2, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{material} briefs", "desc": "{material} briefs" },
		"difficulty": 20,
		"size": 2,
	})

CLOTHING_BOXERS = _UNDERPANTS_DICT + MergeDict({
		"_sdesc_prefix": "pair of",
		"tags": cover_parts("butt", "hip"),
		"ingredients": [Ingredient("fabric", 3, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{material} boxers", "desc": "{material} boxers" },
		"difficulty": 30,
		"size": 3,
	})

CLOTHING_PANTIES = _UNDERPANTS_DICT + MergeDict({
		"_sdesc_prefix": "pair of",
		"tags": cover_parts("butt"),
		"ingredients": [Ingredient("fabric", 2, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{material} panties", "desc": "lightweight {material} panties" },
		"difficulty": 20,
		"size": 2,
	})

###############################
#          Undershirts
###############################
_UNDERSHIRT_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("undershirt", "clothing"),("fabric","design_base")],
		"typeclass": "systems.clothing.things.ClothingObject",
	})

CLOTHING_BASIC_BRA = _UNDERSHIRT_DICT + MergeDict({
		"tags": cover_parts("chest"),
		"ingredients": [Ingredient("fabric", 3, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{material} bra", "desc": "basic {material} brasierre" },
		"difficulty": 40,
		"size": 2,
	})

CLOTHING_BASIC_UNDERSHIRT = _UNDERSHIRT_DICT + MergeDict({
		"tags": cover_parts("chest", "abdomen", "back"),
		"ingredients": [Ingredient("fabric", 3, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{material} undershirt", "desc": "form-fitting {material} shirt" },
		"difficulty": 15,
		"size": 3,
	})


################################
#          Footwear
################################
_SHOE_DICT = _COBBLER_DICT + MergeDict({
		"tags": [("shoes", "clothing")],
		"typeclass": "systems.clothing.things.ClothingObject",
		"subtypes": [ "left", "right" ],
	})

# Shoe form
CLOTHING_SHOE_SLIPON_LEATHER = _SHOE_DICT + MergeDict({
		"tags": [("leather","design_base")] + cover_parts("foot"),
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole"),
		"piece": "shoe",
		"format": { "name": "{material} {piece}", "desc": "{material} slip-on {piece}" },
		"difficulty": 15,
		"size": 2,
	})
CLOTHING_SHOE_SLIPON_CLOTH = _SHOE_DICT + MergeDict({
		"tags": [("fabric","design_base")] + cover_parts("foot"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole"),
		"piece": "shoe",
		"format": { "name": "{material} {piece}", "desc": "{material} slip-on {piece}" },
		"difficulty": 5,
		"size": 2,
	})

CLOTHING_SHOE_LACEUP_LEATHER = _SHOE_DICT + MergeDict({
		"tags": [("leather","design_base")] + cover_parts("foot"),
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole","cord"),
		"piece": "shoe",
		"format": { "name": "{material} {piece}", "desc": "lace-up {material} {piece}" },
		"difficulty": 30,
		"size": 2,
	})
CLOTHING_SHOE_LACEUP_CLOTH = _SHOE_DICT + MergeDict({
		"tags": [("fabric","design_base")] + cover_parts("foot"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole","cord"),
		"piece": "shoe",
		"format": { "name": "{material} {piece}", "desc": "lace-up {material} {piece}" },
		"difficulty": 20,
		"size": 2,
	})

CLOTHING_BOOT_ANKLE_LEATHER = _SHOE_DICT + MergeDict({
		"tags": [("leather","design_base")] + cover_parts("foot", "ankle"),
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole"),
		"piece": "boot",
		"format": { "name": "low {material} {piece}", "desc": "{material} {piece} just reaching ankle height" },
		"difficulty": 30,
		"size": 3,
	})
CLOTHING_BOOT_ANKLE_CLOTH = _SHOE_DICT + MergeDict({
		"tags": [("fabric","design_base")] + cover_parts("foot", "ankle"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole"),
		"piece": "boot",
		"format": { "name": "low {material} {piece}", "desc": "{material} {piece} just reaching ankle height" },
		"difficulty": 30,
		"size": 3,
	})

CLOTHING_BOOT_LACEUP_ANKLE_LEATHER = _SHOE_DICT + MergeDict({
		"tags": [("leather","design_base")] + cover_parts("foot", "ankle"),
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole","cord"),
		"piece": "boot",
		"format": { "name": "low {material} {piece}", "desc": "lace-up {material} {piece} just reaching ankle height" },
		"difficulty": 35,
		"size": 3,
	})
CLOTHING_BOOT_LACEUP_ANKLE_CLOTH = _SHOE_DICT + MergeDict({
		"tags": [("fabric","design_base")] + cover_parts("foot", "ankle"),
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("toe","heel","sole","cord"),
		"piece": "boot",
		"format": { "name": "low {material} {piece}", "desc": "lace-up {material} {piece} just reaching ankle height" },
		"difficulty": 35,
		"size": 3,
	})

CLOTHING_SANDAL_LEATHER = _SHOE_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("heel","sole"),
		"piece": "sandal",
		"format": { "name": "{material} {piece}", "desc": "simple {material} thong {piece}" },
		"difficulty": 5,
		"size": 2,
	})
CLOTHING_SANDAL_CLOTH = _SHOE_DICT + MergeDict({
		"tags": [("fabric","design_base")],
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"req_pieces": ("heel","sole"),
		"piece": "sandal",
		"format": { "name": "{material} {piece}", "desc": "simple {material} thong {piece}" },
		"difficulty": 5,
		"size": 2,
	})

#############################
#         Shoe Toes
#############################
_TOE_DICT = _COBBLER_DICT + MergeDict({
		"tags": [("toe", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
	})


CLOTHING_TOE_ROUND = _TOE_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "toe",
		"format": { "name": "round {material} {piece}", "desc": "blunt, rounded {material} {piece}" },
		"difficulty": 40,
	})
CLOTHING_TOE_POINT = _TOE_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "toe",
		"format": { "name": "pointed {material} {piece}", "desc": "sharply pointed {material} {piece}" },
		"difficulty": 70,
	})
CLOTHING_TOE_SQUARE = _TOE_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "toe",
		"format": { "name": "square {material} {piece}", "desc": "square {material} {piece}" },
		"difficulty": 70,
	})
CLOTHING_TOE_SIMPLE_CLOTH = _TOE_DICT + MergeDict({
		"ingredients": [Ingredient("fabric", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "toe",
		"format": { "name": "{material} {piece}", "desc": "simple {material} {piece}" },
		"difficulty": 20,
	})
CLOTHING_TOE_SIMPLE_LEATHER = _TOE_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "toe",
		"format": { "name": "{material} {piece}", "desc": "simple {material} {piece}" },
		"difficulty": 20,
	})

#############################
#         Shoe Soles
#############################
CLOTHING_SOLE_WOOD = _COBBLER_DICT + MergeDict({
		"tags": [("sole", "craft_material"),("wood","design_base")],
		"typeclass": "base_systems.things.base.Thing",
		"piece": "sole",
		"ingredients": [Ingredient("wood", 1, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "wooden {piece}", "desc": "{material} {piece}" },
		"difficulty": 20,
		"size": 2,
	})
CLOTHING_SOLE_LEATHER = _COBBLER_DICT + MergeDict({
		"tags": [("sole", "craft_material"),("leather","design_base")],
		"typeclass": "base_systems.things.base.Thing",
		"piece": "sole",
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "smooth {piece}", "desc": "{material} {piece}" },
		"difficulty": 40,
		"size": 2,
	})
CLOTHING_SOLE_RUBBER = _COBBLER_DICT + MergeDict({
		"tags": [("sole", "craft_material"),("rubber","design_base")],
		"typeclass": "base_systems.things.base.Thing",
		"piece": "tread",
		"ingredients": [Ingredient("rubber", 1, True, True), Ingredient("thread", 1, True, False)],
		"format": { "name": "{piece}", "desc": "{material} {piece}" },
		"difficulty": 40,
		"size": 2,
	})

#############################
#         Shoe Heels
#############################
_HEEL_DICT = _COBBLER_DICT + MergeDict({
		"tags": [("heel", "craft_material")],
		"typeclass": "base_systems.things.base.Thing",
	})

CLOTHING_HEEL_FLAT_LEATHER = _HEEL_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "flat heel", "desc": "flat {material} {piece}" },
		"difficulty": 5,
	})
CLOTHING_HEEL_SHORT_LEATHER = _HEEL_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "short heel", "desc": "short {material} {piece}" },
		"difficulty": 20,
	})
CLOTHING_HEEL_TALL_LEATHER = _HEEL_DICT + MergeDict({
		"tags": [("leather","design_base")],
		"ingredients": [Ingredient("leather", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "tall heel", "desc": "tall, tapered {material} {piece}" },
		"difficulty": 60,
	})

CLOTHING_HEEL_FLAT_RUBBER = _HEEL_DICT + MergeDict({
		"tags": [("rubber","design_base")],
		"ingredients": [Ingredient("rubber", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "flat heel", "desc": "flat {material} {piece}" },
		"difficulty": 5,
	})
CLOTHING_HEEL_SHORT_RUBBER = _HEEL_DICT + MergeDict({
		"tags": [("rubber","design_base")],
		"ingredients": [Ingredient("rubber", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "short heel", "desc": "short {material} {piece}" },
		"difficulty": 20,
	})
CLOTHING_HEEL_TALL_RUBBER = _HEEL_DICT + MergeDict({
		"tags": [("rubber","design_base")],
		"ingredients": [Ingredient("rubber", 1, True, True), Ingredient("thread", 1, True, False)],
		"piece": "heel",
		"format": { "name": "tall heel", "desc": "tall, square {material} {piece}" },
		"difficulty": 60,
	})


################################################
#             Socks and Stockings
################################################

_SOCK_DICT = _KNITTING_DICT + MergeDict({
		"subtypes": [ "left", "right" ],
		"tags": [("socks", "clothing"),("fabric","design_base")],
		"typeclass": "systems.clothing.things.ClothingObject",
	})

CLOTHING_SOCK_ANKLE = _SOCK_DICT + MergeDict({
		"tags": cover_parts("foot", "ankle"),
		"ingredients": [Ingredient("yarn", 6, True, True)],
		"piece": "sock",
		"format": { "name": "{material} {piece}", "desc": "{material} ankle-height {piece}" },
		"difficulty": 40,
		"size": 2,
	})

CLOTHING_SOCK_KNEE = _SOCK_DICT + MergeDict({
		"tags": cover_parts("foot", "ankle", "lower leg"),
		"ingredients": [Ingredient("yarn", 12, True, True)],
		"piece": "sock",
		"format": { "name": "{material} {piece}", "desc": "{material} knee-high {piece}" },
		"difficulty": 50,
		"size": 3,
	})


################################################
#                  Pockets!
################################################

_POCKET_DICT = _TAILOR_DICT + MergeDict({
		"tags": [("pocket", "craft_material"), ('container', 'systems')],
		"typeclass": "base_systems.things.base.Thing",
	})
_HIDDEN_POCKET = _POCKET_DICT + MergeDict({
		"tags": [("hidden", "systems")],
	})
_UTILITY_POCKET = _POCKET_DICT + MergeDict({
		"tags": [("external", "attach_type")],
	})

CLOTHING_POCKET_SMALL = _POCKET_DICT + MergeDict({
		"ingredients": [Ingredient("fabric", 1, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "pocket", "desc": "small pocket" },
		"piece": "pocket",
		"difficulty": 10,
		"size": 1,
	})

CLOTHING_POCKET_MEDIUM = _POCKET_DICT + MergeDict({
		"ingredients": [Ingredient("fabric", 2, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "pocket", "desc": "pocket" },
		"piece": "pocket",
		"difficulty": 10,
		"size": 2,
	})

CLOTHING_POCKET_LARGE = _POCKET_DICT + MergeDict({
		"ingredients": [Ingredient("fabric", 4, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "pocket", "desc": "large pocket" },
		"piece": "pocket",
		"difficulty": 10,
		"size": 3,
	})

CLOTHING_HIDDEN_POCKET_SMALL = _HIDDEN_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 1, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "hidden pocket", "desc": "small hidden pocket" },
		"piece": "pocket",
		"difficulty": 30,
		"size": 1,
	})

CLOTHING_HIDDEN_POCKET_MEDIUM = _HIDDEN_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 2, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "hidden pocket", "desc": "hidden pocket" },
		"piece": "pocket",
		"difficulty": 45,
		"size": 2,
	})

CLOTHING_HIDDEN_POCKET_LARGE = _HIDDEN_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 4, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "hidden pocket", "desc": "large hidden pocket" },
		"piece": "pocket",
		"difficulty": 60,
		"size": 3,
	})

CLOTHING_UTILITY_POCKET_SMALL = _UTILITY_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 1, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "utility pocket", "desc": "small utility pocket" },
		"piece": "pocket",
		"difficulty": 20,
		"size": 1,
	})

CLOTHING_UTILITY_POCKET_MEDIUM = _UTILITY_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 2, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "utility pocket", "desc": "utility pocket" },
		"piece": "pocket",
		"difficulty": 10,
		"size": 2,
	})

CLOTHING_UTILITY_POCKET_LARGE = _UTILITY_POCKET + MergeDict({
		"ingredients": [Ingredient("fabric", 4, True, False), Ingredient("thread", 1, True, False)],
		"format": { "name": "utility pocket", "desc": "large utility pocket" },
		"piece": "pocket",
		"difficulty": 5,
		"size": 3,
	})
