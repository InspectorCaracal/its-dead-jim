from copy import deepcopy
from evennia.utils import delay, logger, create
from random import choice, randint
from data import chargen
from data.skills import SKILL_TREE
from base_systems.prototypes.spawning import spawn
from core.ic.features import FeatureError
from systems.chargen import gen
from systems.crafting.automate import generate_new_object
from systems.skills.skills import init_skills
from utils.timing import delay_iter

_DEFAULT_BUILD = {
	'height': '',
	'bodytype': '',
	'persona': 'nobody',
}

def create_person(chara):
	"""
	initializes a character to be a (meta)human
	"""
	chara.tags.add("generating")
	chara.features.add('build', format="{height}, {bodytype} {persona}", unique=True, invisible=True, **_DEFAULT_BUILD)
	randomize_build(chara)
#	chara.attributes.add('build', { "persona": "nobody" }, category="systems")
	chara.sdesc.add(["build persona"])
	chara.vdesc.add("voice", "voice")

	# initialize the timestamps
	stamps = ('heal',)
	chara.timestamps.stamp(*stamps)

	init_stats(chara)
	init_skills(chara)
	gener = init_bodyparts(chara)
	delay_iter(gener, 0.2)


def randomize_build(character):
	build_dict = {}
	for key, options in chargen.BUILD_OPTS.items():
		build_dict[key] = choice(options)
	character.features.set("build", **build_dict)


def init_features(character):
	skin_feature = None
	for key, vals in chargen.DEFAULT_FEATURES:
		if key == 'skin':
			character.features.add(key, **vals, save=False)
			skin_feature = vals
	if not skin_feature:
		raise Exception('Failed to initialize default features')
	character.features.save()	
	for obj in character.parts.all():
		if any(obj.tags.has(('eye', 'mouth',), category='part')):
			# these don't have the skin tone
			continue
		obj.features.add("skin", **skin_feature)
	# initialize the features on the character itself
	character.update_features()
	# apply random values
	randomize_features(character)
	# update to show the new random values
	# character.update_features()

def init_stats(character):
	character.stats.add("int", "Intellect", trait_type="static", base=4, mod=0)
	character.stats.add("wit", "Wits", trait_type="static", base=4, mod=0)
	character.stats.add("str", "Strength", trait_type="static", base=4, mod=0)
	character.stats.add("spd", "Speed", trait_type="static", base=4, mod=0)
	character.stats.add("pos", "Poise", trait_type="static", base=4, mod=0)
	character.stats.add("sen", "Sense", trait_type="static", base=4, mod=0)

def init_bodyparts(character):
	if not character.tags.has('generating'):
		return
	head = create.object(key="head", tags=[('head', 'part'),('bony_flesh','damage_effects'),('indestructible')], attributes=[('size', 4)])
	head.partof = character
	hair = create.object(key="hair", tags=[('hair', 'part'),], attributes=[('size', 3)])
	hair.features.add("hair", **chargen.DEFAULT_FEATURES[0][1])
	hair.partof = head
	yield
	create_face_parts(head)
	yield
	create_core_parts(character)
	yield
	create_arm_parts(character, "left")
	yield
	create_arm_parts(character, "right")
	yield
	create_leg_parts(character, "left")
	yield
	create_leg_parts(character, "right")
	yield
	init_features(character)
	yield
	character.tags.remove('generating')

def create_core_parts(character):
	obj = create.object(key="neck", tags=[('neck', 'part'),('indestructible'),('flesh','damage_effects')], attributes=[('size', 2)])
	obj.partof = character
	obj = create.object(key="chest", tags=[('chest', 'part'),('indestructible'),('bony_flesh','damage_effects')], attributes=[('size', 4)])
	obj.partof = character
	obj = create.object(key="abdomen", tags=[('abdomen', 'part'),('indestructible'),('flesh','damage_effects')], attributes=[('size', 4)])
	obj.partof = character
	obj = create.object(key="back", tags=[("upper", 'subtype'),('back', 'part'),('indestructible'),('flesh','damage_effects')], attributes=[('size', 4)])
	obj.partof = character
	obj = create.object(key="back", tags=[("lower", 'subtype'),('back', 'part'),('indestructible'),('flesh','damage_effects')], attributes=[('size', 4)])
	obj.partof = character
	obj = create.object(key="butt", tags=[('butt', 'part'),('indestructible'),('flesh','damage_effects')], attributes=[('size', 4)])
	obj.partof = character


def create_face_parts(head):
	nose = create.object(key="nose", tags=[('nose', 'part'),('bony_flesh','damage_effects')])
	nose.features.add("nose", format="{size} {shape}",  article=True, size="", shape="", save=False)
	nose.partof = head
	mouth = create.object(key="mouth", tags=[('mouth', 'part'),('indestructible'),('flesh','damage_effects')])
	mouth.features.add("mouth", format="{shape} {color}", article=True, color="", shape="", unique=True, save=False)
	mouth.partof = head
	for side in ('right', 'left'):
		eye = create.object(key="eye", tags=[(side, 'subtype'),('eye', 'part'),('flesh','damage_effects')])
		eye.features.add("eye", format="{shape} {color}", article=True, color='', shape='', save=False)
		eye.partof = head
		ear = create.object(key=f"ear", tags=[(side, 'subtype'),('ear', 'part'),('flesh','damage_effects')])
		ear.features.add("ear", value="", article=True, save=False)
		ear.partof = head
		cheek = create.object(key="cheek", tags=[(side, 'subtype'),('cheek', 'part'),('indestructible'),('flesh','damage_effects')])
		cheek.partof = head

def create_arm_parts(character, side):
	shoulder = create.object(key=f"{side} shoulder", tags=[(side, 'subtype'),('shoulder', 'part'),('fleshy_joint','damage_effects')], attributes=[('size', 2)])
	shoulder.partof = character
	arm = create.object(typeclass="base_systems.things.meta.VirtualContainer", key=f"{side} arm", tags=[(side, 'subtype'),('arm', 'part'),('chain', 'systems'),('virtual_container', 'systems')])
	arm.partof = shoulder
	obj = create.object(key=f"upper {side} arm", tags=[(side, 'subtype'),('upper arm', 'part'),('bony_flesh','damage_effects')], attributes=[('size', 2)])
	arm.parts.link(obj)
	obj = create.object(key=f"{side} elbow", tags=[(side, 'subtype'),('elbow', 'part'),('fleshy_joint','damage_effects')], attributes=[('size', 2)])
	arm.parts.link(obj)
	obj = create.object(key=f"{side} forearm", tags=[(side, 'subtype'),('forearm', 'part'),('bony_flesh','damage_effects')], attributes=[('size', 2)])
	arm.parts.link(obj)
	obj = create.object(key=f"{side} wrist", tags=[(side, 'subtype'),('wrist', 'part'),('fleshy_joint','damage_effects')])
	arm.parts.link(obj)
	hand = create.object(key=f"{side} hand", tags=[(side, 'subtype'),('hand', 'part'),('bony_flesh','damage_effects')], attributes=[('size', 2)])
	arm.parts.link(hand)
	for digit in ( "index", "middle", "ring", "pinky", ):
		finger = create.object(key=f"{side} {digit} finger", tags=[(side, 'subtype'),(digit, 'subtype'),('finger', 'part'),('bony_flesh','damage_effects')])
		finger.partof = hand

	obj = create.object(key=f"{side} thumb", location=obj, tags=[(side, 'subtype'),('thumb', 'part'),('bony_flesh','damage_effects')])
	obj.partof = hand
	obj = create.object(key=f"{side} palm", location=obj, tags=[(side, 'subtype'),('palm', 'part'),('indestructible'),('flesh','damage_effects')])
	obj.partof = hand

def create_leg_parts(character, side):
	hip = create.object(key=f"{side} hip", tags=[(side, 'subtype'),('hip', 'part'),('fleshy_joint','damage_effects')], attributes=[('size', 2)])
	hip.partof = character
	leg = create.object(typeclass="base_systems.things.meta.VirtualContainer", key=f"{side} leg", tags=[(side, 'subtype'),('leg', 'part'),('chain', 'systems'),('virtual_container', 'systems')])
	leg.partof = hip
	obj = create.object(key=f"upper {side} leg", tags=[(side, 'subtype'),('bony_flesh','damage_effects'),('upper leg', 'part')], attributes=[('size', 4)])
	leg.parts.link(obj)
	obj = create.object(key=f"{side} knee", tags=[(side, 'subtype'),('knee', 'part'),('fleshy_joint','damage_effects')], attributes=[('size', 2)])
	leg.parts.link(obj)
	obj = create.object(key=f"lower {side} leg", tags=[(side, 'subtype'),('bony_flesh','damage_effects'),('lower leg', 'part')], attributes=[('size', 2)])
	leg.parts.link(obj)
	obj = create.object(key=f"{side} ankle", tags=[(side, 'subtype'),('ankle', 'part'),('fleshy_joint','damage_effects')])
	leg.parts.link(obj)
	obj = create.object(key=f"{side} foot", tags=[(side, 'subtype'),('bony_flesh','damage_effects'),('foot', 'part')], attributes=[('size', 2)])
	leg.parts.link(obj)

def randomize_features(character):
	exclusions = []
	match character.archetype.__class__.__name__:
		case 'WerewolfArch':
			_random_werewolf_features(character)
		case "VampireArch":
			exclusions += ["eye", "ear"]
	_random_base_features(character, exclude=exclusions)


def randomize_shift(character):
	_random_werewolf_features(character)

def _random_base_features(character, exclude=[]):
	features = list(character.features.all)
	character.features.reset()
	for key in features:
		subtypes = []
		if type(key) is tuple:
			feat_key = key[0]
			if not randint(0,3):
				# randomized chance of randomizing all of a non-unique feature vs individual
				subtypes.append(key[1])
		else:
			feat_key = key
		if feat_key in exclude:
			continue
		if not (opts := chargen.FEATURE_OPTS.get(feat_key)):
			continue
		if type(opts) is dict:
			kwargs = { opt_key: choice(opt_val) for opt_key, opt_val in opts.items() }
		else:
			kwargs = { "value": choice(opts) }
		set_character_feature(character, feat_key, subtypes=subtypes, **kwargs)
	# character.features.save()
	character.update_features()

def _random_werewolf_features(character):
	werefeatures = {}
	for key, opts in chargen.WEREWOLF_FEATURE_OPTS.items():
		werefeatures[key] = choice(opts)
	
	character.ndb.werefeatures |= werefeatures

def set_character_feature(character, key, **kwargs):
	values = dict(kwargs)
	parts = character.parts.all() + [character]
	subtypes = values.pop('subtypes',[])
	for obj in parts:
		if not any(key in fkey for fkey in obj.features.all):
			continue
		if subtypes and not any(obj.tags.has(subtypes, category="subtype", return_list=True)):
			continue
		data = obj.features.get(key, as_data=True)
		if type(data) is list:
			data = data[0]
		if data.get('location') and key in data['location']:
			continue
		try:
			obj.features.set(key, **values | { 'save': obj!=character })
		except FeatureError as e:
			logger.log_trace(e)
			continue

def reset_special(chara):
	if chara.tags.has('generating'):
		# we're still initializing the character, nothing to reset
		return
	
	# TODO: make fangs mouth features
	# clear vampiric eyes first
	eyes = chara.features.get("eye", as_data=True)
	valid_opts = chargen.FEATURE_OPTS['eye']['color']
	if eyes[0].get("color") not in valid_opts:
		gen.set_character_feature(chara, "eye", value=choice(chargen.FEATURE_OPTS['eye']['color']))
	# clear vampiric ears too
	ears = chara.features.get("ear", as_data=True)
	if ears[0].get("value") == 'pointed':
		gen.set_character_feature(chara, "ear", value='')

	# clear any "temporary" chargen features
	chara.features.reset(match={"chargen": True})
	del chara.ndb.prev_node

def create_starting_outfit(chara, key):
	"""generate and wear the starter clothes for the outfit key"""
	outfit = chargen.STARTING_OUTFITS.get(key)
	if not outfit:
		raise Exception("Invalid outfit key for character creation")
	for chunk in outfit:
		subtypes = chunk.pop('subtypes', False)
		gener = generate_new_object(chunk['recipes'], chunk['materials'], chara, wear=True, matched_set=subtypes)
		delay_iter(gener, 0.1)

def create_starter_phone(chara):
	base = create.object(key='cell phone', typeclass='systems.electronics.things.Electronics',
		  attributes=[('desc', 'It sure is a cell phone. It can probably even make calls.')], location=chara
		)
	parts = spawn('BASE_SIMCARD', 'BASE_SPEAKER', 'BASE_MICROPHONE', 'BASE_CPU', 'BASE_POWER', 'BASE_DISPLAY', 'BASE_DATA_STORAGE', 'BASE_DIGICAM')
	cpu = None
	for part in parts:
		if part.key == 'display':
			part.db.desc == 'The screen is pretty small.'
		elif part.tags.has('cpu', category='part'):
			cpu = part
		part.partof = base
	if cpu:
		for appname in ('Phone', 'Messages', 'Contacts', 'Gallery', 'Camera'):
			cpu.apps.install_app(appname)
