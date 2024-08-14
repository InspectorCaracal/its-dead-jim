"""
Defines various constants that can be changed to tune behavior and balancing
"""
lol = """
|B                                éÉÉé 
                              éÉÉÉÉÉ               
                              é                   
  ppPPPPPp               kk    éÉÉé     mM  MM    
pP|yPPPPPPPPP|BP       kKK  k|yKK|BK é|yÉÉÉÉÉ|BÉ   M|yM|BM  |yM|BM      nNNNn
PP|yPPPP|Bp  P|yPP|BP       |BK|yKKKKK|BK é|yÉÉ|Bé |yéÉ|Bé  M|yMM|BM M|yM|BM        N|yNN|Bn  NNN
   |BP|yPPP|Bp  |yP|BP   oOOOo K|yKK|BK   É|yÉÉ|Bé|yé|BÉ |BéÉ M|yMMMMMM|BM   oOOOo |yNNN|Bnn|yNN|BN
    P|yPPPPP|BP  oO|yo|yOOOO|Bo |yKKKK|Bk  |Bé|yÉÉÉÉÉÉ|BÉ |BM|yMM|BM|yMMM|BM oO|yo|yOOOO|Bo |yNNNNN|BN
     P|yPPP|BP  O|yOO|Bo o|yOO|Bo |yK |Bk|yKKK|Bk  ÉÉÉÉ  m|yMMM M|Bm|yM |BO|yOO|Bo o|yOO|Bo |yNNNNN|BN
      P|yPP|Bp  O|yOOOOOO|BO |BK|yK    |BK|yKK|BKk     MMMm   M O|yOOOOOO|BO |yN NNN|BN
       P|yPP|BP  OOOOo   KK       KKk           mMm OOOo nNN |yNNN|BN
        P|yPP|Bp                                             |yNN|BN
        |BPPPP                                             NNN
"""

##### system #####
GAME_VERSION = "N/A"
try:
	import toml
	with open('pyproject.toml', 'r') as f:
		GAME_VERSION = toml.load(f)['project']['version']
except:
	pass

##### language ######

import inflect
INFLECT = inflect.engine()
# customize plurals etc here if needed

GENERAL_STOPWORDS = []
with open('utils/stopwords.txt') as file:
	GENERAL_STOPWORDS = list(word.strip() for word in file.readlines() if word.strip())

###### Object Statistics #####
CAPACITY_RATIO = 10

###### Status Things #####
NOT_STANDING = ("sitting", "lying down", "lying")
IMMOBILE = ("sitting", "lying down", "immobile")
# tags indicating severe injury or damage
SEVERE_TAGS = ( 'broken', 'unusable', 'disabled', 'sprained' )

###### Characters ######
# Number of seconds for each point of energy regen
ENERGY_REGEN_RATE = 5
# The "size" of a character's carry capacity per free arm, as an equivalent object size
CHARACTER_CARRY_CAPACITY = 4
# Number of seconds for each heal tick on a basic character
HEAL_RATE = 86400
# Total stat points available to all characters
TOTAL_STATS = 15
# Stat listing (index+1 values, "max value" is len)
STAT_VALUES = ['Lousy', 'Fine', 'Good', 'Great', 'Amazing']
# Formula for the skill mod from a stat
STAT_TO_SKILL_MOD = lambda x: x-2
# Maximum base skill level
MAX_SKILL = 20
# Default window on counterable actions to be countered
COUNTER_WINDOW = 20
# speed considered "fast"
FAST_SPEED = 15
# speed considered "medium"
MED_SPEED = 30

######  Players   #######
# Maximum capacity for temporary exp
MAX_TEMP_XP = 100
# Number of seconds for each point of exp transfer
XP_TRICKLE_RATE = 10
# Defines the XP cost scaling for training skills
XP_COST = 5
# The number of levels you have to buy at once when learning a new skill
MIN_NEW_SKILL = 1 # DEPRECATED
# How long (in seconds) since logging out is required to count as a new play session
SESSION_GAP = 1800

######  Crafting  #######
MAX_DESIGN_LENGTH = 240
MAX_WRITING_LENGTH = 500



######## Forum ########
POSTS_PER_PAGE = 10