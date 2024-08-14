BASE_MATERIAL = {
	"pigment": (255, 254, 250),
	"color_quality": 4
}
COLORING_COLORS = (
		(24, 24, 24), (149, 145, 140), (240, 0, 0), (250, 250, 0), (0, 128, 0), (31, 117, 254), (240, 240, 240),
		(134, 1, 175), (255, 127, 0), (215, 72, 148), (255, 254, 250),
	)

PATTERNED_MATERIAL = BASE_MATERIAL | {
	"color": "", # TODO: multiple colors
	"pattern": "",
	"format": "{color} {pattern} ",
}

FLAVORFUL_MATERIAL = BASE_MATERIAL | {
	"flavors": [''],
}

COLORED_MATERIAL = BASE_MATERIAL | {
	"color": "",
	"format": "{color} ",
}

TEXTURED_MATERIAL = BASE_MATERIAL | {
	"texture": "",
	"format": "{texture} ",
}

MATERIAL_TYPES = {
	"generic": BASE_MATERIAL,
	"fabric": PATTERNED_MATERIAL,
	"leather": COLORED_MATERIAL,
	"wood": TEXTURED_MATERIAL,
	'color': COLORED_MATERIAL,
	'pencil': COLORED_MATERIAL,
}
MATERIAL_NAMES = {
	"fabric": ( "linen", "cotton", "silk", "velvet" ),
	"leather": ( 'leather', 'suede', 'patent leather', 'rawhide' ),
	"wood": ( 'oak', 'pine', 'cherry', 'mahogany', ),
	"pencil": ('pencil',),
}
MATERIAL_COLORS = {
	"fabric":  COLORING_COLORS,
	"leather": ( (188, 93, 88), ),
	"wood": ( (188, 93, 88), ),
	"color": COLORING_COLORS,
	"pencil": COLORING_COLORS,
}
MATERIAL_TEXTURES = {
	"wood": ("", "smooth", "rough", 'polished'),
}
MATERIAL_PATTERNS = {
	"fabric": ("", "polka-dot", 'checkered', 'striped'),
}

