
from copy import copy

from switchboard import MAX_SKILL


SKILL_LEVELS = {
		0: "Unskilled",
		1: "Dabbling",
		3: "Novice",
		6: "Competent",
		10: "Skilled",
		15: "Adept",
		22: "Expert",
		30: "Master",
	}
_PARENT_SKILL_LEVELS = {
		0: "N/A",
		1: "Dabbling",
		7: "Novice",
		14: "Competent",
		20: "Adept",
	}

SKILL_TREE = {
	"athletics": {
		"name": "Athletics",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "str",
		"subskills": {
			"aim": { "name": "Aiming", "stat": "wit" },
			"climbing": { "name": "Climbing", "stat": "str" },
			"jumping": { "name": "Jumping", "stat": "sen" },
			"running": { "name": "Running", "stat": "spd" },
		}
	},
	"martial": {
		"name": "Martial Arts",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "pos",
		"subskills": {
			"wrestling": { "name": "Wrestling", "stat": "str" },
			"striking": { "name": "Striking", "stat": "spd" },
			"weaponry": { "name": "Weapons-Handling", "stat": "wit" },
			"evasion": { "name": "Evasion", "stat": "sen" },
		}
	},
	"woodwork": {
		"name": "Woodworking",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "sen",
		"subskills": {
			"carpentry": { "name": "Carpentry", "stat": "int" },
			"whittling": { "name": "Wood Carving", "stat": "spd" },
		}
	},
	"stonework": {
		"name": "Stonecraft",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "str",
		"subskills": {
			"stonecarving": { "name": "Stone Carving", "stat": "sen" },
#			"masonry": { "name": "Masonry", "stat": "str" },
			"gemcutting": { "name": "Gem Cutting", "stat": "int" },
		}
	},
	"metalwork": {
		"name": "Metallurgy",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "sen",
		"subskills": {
#			"forging": { "name": "Forging", "stat": "str" },
			"wireworking": { "name": "Wireworking", "stat": "spd" },
			"metalcast": { "name": "Metal Casting", "stat": "int" },
			"soldering": { "name": "Soldering", "stat": "pos" },
		}
	},
	"sewing": {
		"name": "Sewing",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "spd",
		"subskills": {
			"embroidery": { "name": "Embroidery", "stat": "wit" },
			"tailoring": { "name": "Tailoring", "stat": "int" },
			"quilting": { "name": "Quilting", "stat": "sen" },
		}
	},
	"leather": {
		"name": "Leathercraft",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "int",
		"subskills": {
#			"tanning": { "name": "Tanning", "stat": "str" },
			"cobbling": { "name": "Shoe-Making", "stat": "sen" },
			"leathergrave": { "name": "Leather Carving", "stat": "pos" },
		}
	},
	"fibers": {
		"name": "Fiber Arts",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "int",
		"subskills": {
#			"spinning": { "name": "Spinning", },
			"weaving": { "name": "Weaving", "stat": "sen" },
			"knitting": { "name": "Knitting", "stat": "pos" },
			"crochet": { "name": "Crochet", "stat": "spd" },
		}
	},
	"culinary": {
		"name": "Culinary Arts",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "wit",
		"subskills": {
			"baking": { "name": "Baking", "stat": "int" },
			"cooking": { "name": "Cooking", "stat": "sen" },
			"grilling": { "name": "Grilling", "stat": "sen" },
			"seasoning": { "name": "Seasoning", "stat": "wit" },
#			"tasting": { "name": "Tasting", "stat": "int" },
		}
	},
	"design": {
		"name": "Design",
		"cap": MAX_SKILL // 2,
		"descs": _PARENT_SKILL_LEVELS,
		"stat": "int",
		"subskills": {
			"sketching": { "name": "Sketching", "stat": "wit" },
			"calligraphy": { "name": "Calligraphy", "stat": "int" },
#			"presenting": { "name": "Presentation", "stat": "sen" },
			"paint": { "name": "Painting", "stat": "sen" },
#			"polish": { "name": "Polishing", },
		}
	},
	# "chemical": {
	# 	"name": "Chemical Arts",
	# 	"cap": MAX_SKILL // 2,
	# 	"descs": _PARENT_SKILL_LEVELS,
	# 	"subskills": {
	# 		"dyes": { "name": "Dyecraft", },
	# 		"medicine": { "name": "Medicine", },
	# 		"mixology": { "name": "Mixology", },
	# 		"ferment": { "name": "Fermentation", },
	# 	}
	# },
	# "papercraft": {
	# 	"name": "Paper Crafts",
	# 	"cap": MAX_SKILL // 2,
	# 	"descs": _PARENT_SKILL_LEVELS,
	# 	"subskills": {
	# 		"papermaking": { "name": "Paper-Making", },
	# 		"bookbinding": { "name": "Book Binding", },
	# 		"origami": { "name": "Paper Folding", },
	# 	}
	# },
	# "psychic": {
	# 	"name": "Mental Arts",
	# 	"cap": MAX_SKILL // 2,
	# 	"descs": _PARENT_SKILL_LEVELS,
	# 	"subskills": {
	# 		"telepathy": { "name": "Telepathy", },
	# 		"telekinesis": { "name": "Telekinesis", },
	# 	}
	# },
}

def pretty_print():
	# categories
	lines = []
	stats = { "wit": "Wits", "int": "Intellect", "spd": "Speed", "str": "Strength", "sen": "Sense", "pos": "Poise" }
	for data in SKILL_TREE.values():
		stat = data['stat']
#		header = "{group} ({stat})".format(group=data['name'], stat=stats[stat])
		header = data['name']
		lines.append(header)
		for skill in data['subskills'].values():
			skill_stats = (stat, skill['stat'])
			line = "  {skill} ({stats})".format(
				skill=skill['name'],
				stats=', '.join( (stat_name for key, stat_name in stats.items() if key in skill_stats ) )
			)
			lines.append(line)
		lines.append('')
	
	return "\n".join(lines)

def _flatten_skills(skilltree):
	skill_list = []
	for key, data in SKILL_TREE.items():
		sdata = copy(data)
		subskills = sdata.pop('subskills',{})
		skill_list.append({'key': key} | sdata)
		for skey, skill in subskills.items():
			skill_list.append({'key': skey} | skill)
	return skill_list

ALL_SKILLS = tuple(_flatten_skills(SKILL_TREE))