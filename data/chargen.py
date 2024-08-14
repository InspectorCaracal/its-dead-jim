BUILD_OPTS = {
	# the key is your category; the value is a list of options, in the order you want them to appear
	"bodytype": [
		"skeletal",
		"skinny",
		"slender",
		"slim",
		"athletic",
		"muscular",
		"broad",
		"round",
		"curvy",
		"stout",
		"chubby",
	],
	"height": ["diminutive", "short", "average", "tall", "towering"],
	"persona": [ "nobody", "person", "nerd", "brawler", "socialite", "bum", "athlete", "jock", "hipster", "academic", "brute", "waif", "urbanite",
			"beatnik", "kid", "miscreant", "deadbeat", "go-getter", "punk", "loner", "eccentric", "scrapper", "vagrant", "vagabond", "citizen" ],
}

_natural_eye_colors = [ ( "|#5E391Fdark brown|n", (94, 57, 31) ), ( "|#B98A69light brown|n", (185, 138, 105) ), ( "|#85852Chazel|n", (133, 133, 44) ), ( "|#508337green|n", (80, 131, 55) ), ( "|#519899blue-green|n", (81, 152, 153) ), ( "|#5A97D6blue|n", (90, 151, 214) ), ( "|#92AEC8blue-grey|n", (146, 174, 200) ), ( "|#B2B2B2grey|n", (178, 178, 178) ),	]
_natural_hair_colors = [ ( "|#E5D4B2blonde|n", (229, 212, 178) ), ( "|#A7895Dash blonde|n", (167, 137, 93) ), ( "|#4C3B19ash brown|n", (76, 59, 25) ), ( "|#2D283Dblack|n", (45, 40, 61) ), ( "|#47291Fwarm black|n", (71, 41, 31) ), ( "|#814223brown|n", (129, 66, 35) ), ( "|#B75735coppery|n", (183, 87, 53) ), ( "|#DE8E66strawberry blonde|n", (222, 142, 102) ),	]
_natural_skin_colors = [ ( "|#402510dark|n", (64, 37, 16) ), ( "|#583516dark brown|n", (88, 53, 22) ), ( "|#7A491Ebrown|n", (122, 73, 30) ), ( "|#A46828light brown|n", (164, 104, 40) ), ( "|#C08D5Ctanned|n", (192, 141, 92) ), ( "|#E7C8BDpale|n", (231, 200, 189) ),	]

FEATURE_OPTS = {
	"hair": {
		"texture": [ "straight", "wavy", "curly", "ringlet", "coily", "frizzy", "fluffy", "spiky" ],
		"color": [ item[0] for item in _natural_hair_colors ],
		"length": [ "no", "shaved", "very short", "short", "medium-short", "medium-long", "long", "very long" ], 
	},
	"eye": {
		"shape": [ "", ],
		"color": [ item[0] for item in _natural_eye_colors ],
	},
	"skin": {
		"texture": [ "smooth", "scarred", "freckled", "wrinkled", "" ],
		"color": [ item[0] for item in _natural_skin_colors ],
	},
	"mouth": {
		"shape": [ "thin", "full-lipped", "wide", "small", "large", ],
		"color": [ '' ],
	},
}

WEREWOLF_FEATURE_OPTS = {
	"fur": ( "fluffy", "sleek", "spiky", "thick", "dense", "rough", ),
	"claws": ( "sharp", "heavy", "vicious", "curved", "talon-like", "blunt", "delicate", ),
	"fangs": ( "long", "pointed", "curved", "delicate", "vicious", "protruding", "sharp" ),
}

# [ ( "|#eb0828cadmium red|n", (235, 8, 40) ),
# ( "|#fd5308persimmon|n", (253, 83, 8) ), 
# ( "|#fa9600tangerine|n", (250, 150, 0) ),
 # ( "|#ffd028sunglow|n", (255, 208, 40) ),
 # ( "|#ffff32yellow|n", (255, 255, 50) ), 
 # ( "|#c8e114bitter lemon|n", (200, 225, 20) ), 
 # ( "|#64af32grass green|n", (100, 175, 50) ), 
 # ( "|#00afbeaqua|n", (0, 175, 190) ), 
 # ( "|#0046ffpalatinate blue|n", (0, 70, 255) ),
 # ( "|#3c00aapicotee blue|n", (60, 0, 170) ), 
# ( "|#8700afviolet|n", (135, 0, 175) ), 
# ( "|#a0194bred violet|n", (160, 25, 75) ),	],

# color code data for eye/magic color generation
ELEMENT_OPTS = {
	"earth": (221, 148, 117, 0),
	"fire": (255, 60, 0, 1),
	"water": (0, 125, 255, 1),
	"plant": (0, 255, 0, 0),
	"light": (234, 224, 200, 1),
	"shadow": (255, 255, 0, 0),
	"lightning": (210, 200, 255, 1),
}

STARTING_SPELLS = {
	"earth": "barrier",
	"fire": "hit",
	"water": "hit",
	"plant": "grab",
	"light": "illusion",
	"shadow": "armor",
	"lightning": "area",
}

FAMILIAR_OPTS = {
	"form": ( "feline", "canine", "avian", "vulpine", "reptilian", "serpentine", ),
	"personality": ( "sleek", "friendly", "aloof", "quiet", "energetic", "alert", "placid" ),
}


DEFAULT_FEATURES = [
	( "hair", { "format": "{length} {texture} {color}", "texture": "", "length": "", "color": "", "unique": True, "article": False, }),
	( "skin", { "format": "{texture} {color}", "texture": "", "color": "", "unique": True, "article": False, }),
]

# Assembly dicts for outfit pieces
_ANKLE_BOOT = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_BOOT_LACEUP_ANKLE_LEATHER",
	"adds": ["CLOTHING_TOE_SQUARE","CLOTHING_SOLE_RUBBER", "CLOTHING_HEEL_SHORT_RUBBER",]
}
_LEG_WITH_POCKET = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_LEG_LONG",
	"adds": ["CLOTHING_POCKET_MEDIUM"],
}
_TROUSERS = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_TROUSER_BASE",
	"adds": [_LEG_WITH_POCKET, _LEG_WITH_POCKET],
	"subtypes": True
}
_VNECK_TSHIRT = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_VNECK_BASE",
	"adds": ["CLOTHING_SLEEVE_SHORT","CLOTHING_SLEEVE_SHORT",],
	"subtypes": True
}
_GLASSES = {
	"recipe": "ASSEMBLE",
	"base": "CLOTHING_FACTORY_GLASSES_FRAME",
	"adds": ["CLOTHING_FACTORY_GLASSES_LENS","CLOTHING_FACTORY_GLASSES_LENS",],
}

from data.materials import PATTERNED_MATERIAL, COLORED_MATERIAL

STARTING_OUTFITS = {
	"default": [{
			"recipes": ["CLOTHING_BOXERS", _TROUSERS],
			"materials": {
				'fabric': [("cotton", PATTERNED_MATERIAL | {"pigment": ( (211, 211, 211), (149, 145, 140), (54, 69, 79), (255, 250, 250), (20, 20, 20) )})],
			},
		},{
			"recipes": ["CLOTHING_BASIC_UNDERSHIRT", _VNECK_TSHIRT],
			"materials": {
				'fabric': [("cotton", PATTERNED_MATERIAL | {"pigment": ( (211, 211, 211), (149, 145, 140), (54, 69, 79), (255, 250, 250), (20, 20, 20) )})],
			},
		},{
			"recipes": [ "CLOTHING_SOCK_ANKLE", _ANKLE_BOOT ],
			"materials": {
				'yarn': [("cotton", PATTERNED_MATERIAL | {"pigment": ((211, 211, 211), (149, 145, 140), (54, 69, 79), (255, 250, 250), (20, 20, 20))})],
				'leather': [("leather", COLORED_MATERIAL | {"pigment": ((136, 84, 11), (101, 67, 33), (205, 87, 0))})],
				'rubber': [("rubber", COLORED_MATERIAL | {"pigment": ((54, 69, 79), (20, 20, 20), (101, 67, 33))})],
			},
			"subtypes": True,
		},
	],
}