"""
Defines what effects are applied at what percentages of what damage types.

The percentages are referencing how much damage of that type is done *at once*.
"""

BASE_DAMAGES = {
	"impact": None,
	"slice": None,
	"puncture": None,
	"burn": None,
}

FLESH_DAMAGES = BASE_DAMAGES | {
	"impact": { 10: "damage.Bruised" },
	"slice": { 10: "damage.Bleeding", },
	"puncture": { 30: "damage.Bleeding" },
	"burn": { 10: "damage.BurnDamage", },
}

BONY_FLESH_DAMAGES = FLESH_DAMAGES | {
	"impact": { 5: "damage.Bruised", 50: "damage.BrokenBone" },
}

FLESHY_JOINT_DAMAGES = FLESH_DAMAGES | {
	"impact": { 10: "damage.Bruised", 30: "damage.Sprained", 60: 'damage.BrokenBone' },
}