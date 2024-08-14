from collections import defaultdict
from random import choice

from base_systems.prototypes.spawning import spawn
from evennia.utils import dedent, logger, is_iter, delay
from evennia.utils.evtable import EvTable, fill
from utils.colors import strip_ansi

from utils.strmanip import INFLECT

from data import chargen
from systems.archetypes.base import ARCHETYPE_INFO, reset_archetype
from utils.strmanip import numbered_name, strip_extra_spaces
from . import gen

#########################################################
#				   Helpers
#########################################################

def _random_choice(caller, raw_string, option_list=[], **kwargs):
	if option_list:
		picked = choice(option_list)
		if picked := picked.get("goto"):
			try:
				goto, data = picked
			except Exception as e:
				logger.log_trace(e)
				caller.msg("Something went wrong; please try again.")
				caller.new_char.db.chargen_step = "menunode_welcome"
				return
			
			if callable(goto):
				return goto(caller, raw_string, **data)
			else:
				return goto, data

	# if it got to here, it didn't work
	caller.msg("Something went wrong; please try again.")
	caller.new_char.db.chargen_step = "menunode_welcome"
	return

def _randomize_features(caller, raw_string, build=False, calling_node="menunode_welcome", **kwargs):
	chara = caller.new_char
	if build:
		gen.randomize_build(chara)
	else:
		gen.randomize_features(chara)
	return calling_node

def _randomize_werewolf(caller, raw_string, calling_node="menunode_welcome", **kwargs):
	chara = caller.new_char
	gen.randomize_shift(chara)
	return calling_node

#########################################################
#				   Welcome Page
#########################################################


def menunode_welcome(caller):
	"""Starting page."""
	text = dedent(
		"""\
		$head(Character Creation)

		Thank you for helping to test Nexus! You can stop character creation at any time by entering $h(q) or $h(quit) - you won't lose any of your progress, so you can come back later.

		Not all of the character creation process is complete, so don't worry if it seems like something is missing.
	"""
	)
	options = {"desc": "Let's begin!", "goto": "menunode_pronouns"}
	return text, options


#########################################################
#                Setting Gender
#########################################################


def menunode_pronouns(caller, **kwargs):
	# set resume point
	caller.new_char.db.chargen_step = "menunode_pronouns"

	text = dedent("""
		$head(Your Pronouns)

		Some aspects of the game, such as your description, will automatically use third-person pronouns for you.
		Choose which pronouns should be used - and don't worry if you're not sure, you can change them any time in the game.

		Pick your pronouns:
	""")
	helptext = "Custom pronouns are not supported, but additional options may be added in the future."
	options = [
		{"desc": "he/him", "goto": (_set_pronouns, {"gender": "male"})},
		{"desc": "she/her", "goto": (_set_pronouns, {"gender": "female"})},
		{"desc": "they/them", "goto": (_set_pronouns, {"gender": "plural"})},
#		{"desc": "it/it", "goto": (_set_pronouns, {"gender": "neutral"})},
	]
	return (text, helptext), options

def _set_pronouns(caller, raw_string, gender="plural", **kwargs):
	caller.new_char.gender = gender
	return "menunode_info_arch_base"


#########################################################
#				 Archetype Choices
#########################################################

def menunode_info_arch_base(caller):
	"""Base node for the informational choices."""
	# this is a base node for a decision, so we want to save the character's progress here
	caller.new_char.db.chargen_step = "menunode_info_arch_base"
	gen.reset_special(caller.new_char)

	text = dedent(
		"""\
		$head(Choosing an Archetype)

		[lore redacted]
	"""
	)
	options = []
	# Build your options from your info dict so you don't need to update this to add new options
	for arch_key, arch_data in sorted(ARCHETYPE_INFO.items()):
		options.append(
			{
				"desc": f"Learn about $h({arch_data[0]}) abilities",
				"goto": ("menunode_info_arch", {"selected_class": arch_key}),
			}
		)
	return text, options


# putting your kwarg in the menu declaration helps keep track of what variables the node needs
def menunode_info_arch(caller, raw_string, selected_class=None, **kwargs):
	"""Informational overview of a particular class"""

	# sometimes weird bugs happen - it's best to check for them rather than let the game break
	if not selected_class:
		# reset back to the previous step
		caller.new_char.db.chargen_step = "menunode_welcome"
		# print error to player and quit the menu
		return "Something went wrong. Please $h(quit) character creation and try again."

	# Since you have all the info in a nice dict, you can just grab it to display here
	desc, text = ARCHETYPE_INFO[selected_class]
	helptext = "If you want option-specific help, you can define it in your info dict and reference it."
	options = []

	# set an option for players to choose this class
	options.append(
		{
			"desc": f"Choose this archetype",
			"goto": (_set_archetype, {"selected_class": selected_class}),
		}
	)

	# once again build your options from the same info dict
	for arch_key, arch_data in sorted(ARCHETYPE_INFO.items()):
		# make sure you don't print the currently displayed page as an option
		if arch_key != selected_class:
			options.append(
				{
					"desc": f"Learn about $h({arch_data[0]}) abilities",
					"goto": ("menunode_info_arch", {"selected_class": arch_key}),
				}
			)
	return (text, helptext), options


def _set_archetype(caller, raw_string, selected_class=None, **kwargs):
	# a class should always be selected here
	if not selected_class:
		# go back to the base node for this decision
		return "menunode_info_arch_base"

	chara = caller.new_char

	if chara.tags.has("generating"):
		return ("menunode_too_fast", {'selected_class': selected_class} | kwargs)
	
	reset_archetype(chara, selected_class)
	if selected_class == "vampire":
		gen.set_character_feature(chara, "ear", value="pointed", chargen=True)
		# gen.set_character_feature(chara, "fangs", value="pointed", location="mouth", chargen=True)

	# move on to the next step!
	node_name = f"menunode_{selected_class}_customize"
	return node_name

def menunode_too_fast(caller, raw_string, **kwargs):
	text = ''
	if not kwargs.get("continue"):
		dial = " Please hold, your character is still being prepared..."
	
	else:
		dial = choice(['','',' Thank you for your patience.',' Please hold, your character is still being prepared...'])

	text += "(chill jazz music plays){}".format(dial)
	option = {'desc': 'Wait', "goto": (_set_archetype, kwargs | {'continue': True})}

	return text, option

def menunode_sorcerer_customize(caller, **kwargs):
	chara = caller.new_char
	chara.db.chargen_step = "menunode_sorcerer_customize"

	element = None
	if magic := chara.effects.get(name='innate magic'):
		element = magic.element
	if familiar := chara.db.familiar:
		familiar = familiar.deserialize()
	else:
		chara.db.familiar = familiar = {}

	# TODO: split this out into a helper func so i can use it in the familiar customization nodes
	fam_sdesc = []
	if familiar.get("personality"):
		fam_sdesc.append(familiar.get("personality"))
	if familiar.get('form'):
		fam_sdesc.append(familiar.get("form"))
	if familiar.get('key'):
		fam_name = f" named {familiar.get('key')}"
	else:
		fam_name = ''

	ele_str = ""
	fam_str = ""
	if element:
		ele_str = f"You've selected |{magic.color}{element}|n."
	if familiar:
		fam_str = f"Your familiar is {numbered_name(' '.join(fam_sdesc),1)}{fam_name}."

	text = dedent(f"""\
		Your soul-bonded familiar is an elemental entity. Familiars have one preferred form they typically stick with, as well as their elemental affinity.
		
		{ele_str} {fam_str}
	""")
	text = strip_extra_spaces(text)

	options = []
	options.append({"desc": "Choose your familiar's element", "goto": "menunode_choose_element"})
	options.append({"desc": "Customize your familiar's appearance", "goto": "menunode_customize_familiar"})
	options.append(
		{"key": ("(Back)", "back", "b"), "desc": "Choose a different archetype", "goto": "menunode_info_arch_base", })
	if element and familiar:
		options.append({"key": ("(Continue)", "continue", "c"), "desc": "Confirm and continue", "goto": "menunode_build", })
	return text, options

def menunode_choose_element(caller, **kwargs):
	chara = caller.new_char
	element = None
	if magic := chara.effects.get(name='innate magic'):
		element = magic.element

	text = "Choose an element:"

	options = []
	for key in chargen.ELEMENT_OPTS.keys():
		options.append({"desc": key, "goto": (_set_element, {"element": key, "next_node": "menunode_sorcerer_customize"})})
	if element:
		options.append({"key": ("(Back)", "back", "b"), "desc": "Don't change your element", "goto": "menunode_sorcerer_customize", })

	return text, options

def menunode_customize_familiar(caller, **kwargs):
	text = "Your familiar is your companion for life. What should it look like?"
	# TODO: display what it looks like so far
	options = []
	for key in chargen.FAMILIAR_OPTS.keys():
		options.append({ "desc": f"Choose your familiar's {key}.", "goto": ("menunode_familiar_opts", {"opt_key": key})})
	options.append({ "desc": f"Name your familiar.", "goto": "menunode_familiar_name"})
	options.append({"key": ("(Back)", "back", "b"), "desc": "Go back", "goto": "menunode_sorcerer_customize", })
	return text, options

def menunode_familiar_opts(caller, **kwargs):
	if not (opt_key := kwargs.get("opt_key")):
		return menunode_customize_familiar(caller, **kwargs)
	
	text = f"Choose your familiar's {opt_key}:"
	# TODO: highlight the one you already have

	options = []
	for option in chargen.FAMILIAR_OPTS.get(opt_key):
		options.append({"desc": option, "goto": (_set_familiar_opt, {"opt_key": opt_key, "value": option})})
	# TODO: recognize the currently selected choice, and add the option to keep it

	return text, options

def _set_familiar_opt(caller, raw_string, opt_key, value, **kwargs):
	caller.new_char.db.familiar[opt_key] = value
	return "menunode_customize_familiar"

def menunode_familiar_name(caller, **kwargs):
	text = "Enter your familiar's name:"
	options = {"key": "_default", "goto": _set_familiar_name}
	return text, options

def _set_familiar_name(caller, raw_string, **kwargs):
	new_name = caller.new_char.normalize_name(raw_string.strip())
	caller.new_char.db.familiar["key"] = new_name
	return "menunode_customize_familiar"


def menunode_vampire_customize(caller, **kwargs):
	chara = caller.new_char
	chara.db.chargen_step = "menunode_vampire_customize"
	element = None
	if magic := chara.effects.get(name='innate magic'):
		element = magic.element

	if not element:
		prompt = "Choose an element"
	else:
		prompt = f"You've selected |{magic.color}{element}|n and will have {chara.features.get('eye')}."\
		         f"\n\nChoose another or confirm:"
		        #  f"Your starting spell type is $h({chara.archetype.spell_list[0]}).\n\nChoose another or confirm:"

	text = dedent("""\
		As a vampire, you can choose the element of your spirit. This will affect your future abilities, as well as the color of your eyes and of your magic.
		
		(NOTE: more information will be provided later.)

		{prompt}
	""").format(prompt=prompt)
	
	options = []
	for key in chargen.ELEMENT_OPTS.keys():
		options.append({"desc": key, "goto": (_set_element, {"element": key, "next_node": "menunode_vampire_customize"})})
	if element:
		options.append( { "key": ("(Continue)", "continue", "c"), "desc": "Confirm and continue", "goto": "menunode_build", }	)
	options.append( { "key": ("(Back)", "back", "b"), "desc": "Choose a different archetype", "goto": "menunode_info_arch_base", }	)
	
	return text, options


def _set_element(caller, raw_string, element=None, next_node="menunode_build", **kwargs):
	if not element or element not in chargen.ELEMENT_OPTS:
		caller.msg("Something went wrong, please try again.")
		caller.new_char.db.chargen_step = "menunode_welcome"
		return
	chara = caller.new_char

	if magic := chara.effects.get(name='innate magic'):
		chara.effects.delete(magic)

	chara.effects.add('systems.archetypes.base.MagicAbility', element=element)
	
	return next_node


def menunode_werewolf_customize(caller, **kwargs):
	chara = caller.new_char
	chara.db.chargen_step = "menunode_werewolf_customize"
	
	if not (werefeatures := chara.ndb.werefeatures):
		chara.ndb.werefeatures = { "format": "{fur} fur, {claws} claws, {fangs} fangs", "fur": "N/A", "claws": "N/A", "fangs": "N/A", }
		werefeatures = chara.ndb.werefeatures
	
	text = dedent(f"""\
		$h(Bestial Features)
		
		As a werewolf or shifter, you can customize your shifted features! Your fur will be the same as your natural hair color, but there are several other things you can choose.
		
		Your current choices:
			{werefeatures['format'].format(**werefeatures)}
	""")
	
	options = []
	for feature in chargen.WEREWOLF_FEATURE_OPTS.keys():
		options.append({"desc": feature, "goto": ("menunode_werewolf_feature", {"feature": feature})})
	options.append({"key": ("(Randomize)","random","r","randomize"), "goto": (_randomize_werewolf, {"calling_node": "menunode_werewolf_customize"})})
	if "N/A" not in werefeatures.values():
		options.append( { "key": ("(Continue)", "continue", "c"), "desc": "Confirm and continue", "goto": _apply_werewolf_features, }	)
	options.append( { "key": ("(Back)", "back", "b"), "desc": "Choose a different archetype", "goto": "menunode_info_arch", }	)

	return text, options

def menunode_werewolf_feature(caller, raw_string, feature=None, **kwargs):
	if not feature:
		return "menunode_werewolf_features"
	chara = caller.new_char

	if not (werefeatures := chara.ndb.werefeatures):
		return "menunode_werewolf_features"
		
	value = werefeatures.get(feature, 'N/A')

	text = f"You currently have {value} {feature}."

	options = []
	for opt in chargen.WEREWOLF_FEATURE_OPTS.get(feature,[]):
		options.append({"desc": opt, "goto": (_set_werewolf_feature, {"feature": feature, "value": opt})})
	if len(options):
		choose_from = list(options)
		options.append({"key": ("(Randomize)", "randomize", "random", "r"), "desc": "Choose a random option", "goto": (_random_choice, {"option_list": choose_from})})
	if value != "N/A":
		options.append( { "key": ("(Back)", "back", "b"), "desc": f"Don't change {feature}", "goto": "menunode_werewolf_customize", } )
	
	return text, options
		

def _set_werewolf_feature(caller, raw_string, feature=None, value=None, **kwargs):
	if not feature:
		return "menunode_werewolf_customize"
	if not value:
		return ("menunode_werewolf_feature", {"feature": feature})

	caller.new_char.ndb.werefeatures[feature] = value
	return "menunode_werewolf_customize"

def _apply_werewolf_features(caller, raw_string, **kwargs):
	chara = caller.new_char
	if not (werefeatures := chara.ndb.werefeatures):
		return "menunode_werewolf_customize"
	
	archetype = chara.archetype

	full = archetype.forms.get("full", {})
	part = archetype.forms.get("partial", {})

	for key, val in werefeatures.items():
		if key == "format":
			continue
		elif key == "fur":
			full[key] = { "format": "{adj} {color}", "adj": val, "unique": True, "shifted": True }
			part[key] = { "format": "{adj} {color}", "adj": val, "unique": True, "shifted": True }
		else:
			full[key] = { "value": val, "unique": True, "shifted": True }
			part[key] = { "value": val, "unique": True, "shifted": True }

	archetype.forms['full'] = full
	archetype.forms['partial'] = part
	archetype.save()

	return "menunode_build"

#########################################################
#				Physical Appearance
#########################################################

def menunode_build(caller, **kwargs):
	"""Base node for categorized options."""
	# this is a new decision step, so save your resume point here
	chara = caller.new_char
	chara.db.chargen_step = "menunode_build"
	chara.sdesc.update()

	text = dedent(
		"""\
		$head(Your Appearance, Part One)

		Your character's basic physical characteristics, such as height, cannot be disguised or otherwise altered later on.
		However, they also don't affect your character's stats, abilities, or other game mechanics besides appearance.
		
		You are currently {build}.
		""".format(build=INFLECT.an(chara.build))
	)

	helptext = "Your character's physical appearance has no mechanical effect other than aesthetics, so go wild!"
	options = []

	# just like for informational categories, build the options off of a dictionary to make it
	# easier to manage
	for category in chargen.BUILD_OPTS.keys():
		options.append(
			{
				"desc": f"Choose your $h({category})",
				"goto": ("menunode_build_options", {"category": category}),
			}
		)

	# since this node goes in and out of sub-nodes, you need an option to proceed to the next step
	options.append(
		{
			"key": ("(Next)", "next", "n", "c", "confirm", "continue"),
			"desc": "Confirm and continue.",
			"goto": chara.ndb.prev_node or "menunode_features",
		}
	)
	options.append({"key": ("(Randomize)","random","r","randomize"), "goto": (_randomize_features, {"build": True, "calling_node": "menunode_build"})})
	# once past the first decision, it's also a good idea to include a "back to previous step"
	# option
	options.append( { "key": ("(Back)", "back", "b"), "desc": "Go back", "goto": chara.ndb.prev_node or "menunode_info_arch_base", }	)
	return (text, helptext), options


def menunode_build_options(caller, raw_string, category=None, **kwargs):
	"""Choosing an option within the categories."""
	if not category:
		# this shouldn't have happened, so quit and retry
		return "Something went wrong. Please $h(quit) character creation and try again."

	# for mechanics-related choices, you can combine this with the
	# informational options approach to give specific info
	text = f"Choose your $h({category}):"
	helptext = f"This will define your {category}."

	options = []
	# build the list of options from the right category of your dictionary
	for option in chargen.BUILD_OPTS[category]:
		options.append(
			{"desc": option, "goto": (_set_build_opt, {"category": category, "value": option})}
		)
	if len(options):
		choose_from = list(options)
		options.append({"key": ("(Randomize)", "randomize", "random", "r"), "desc": "Choose a random option", "goto": (_random_choice, {"option_list": choose_from})})
	# always include a "back" option in case they aren't ready to pick yet
	options.append(
		{
			"key": ("(Back)", "back", "b"),
			"desc": f"Don't change {category}",
			"goto": "menunode_build",
		}
	)
	return (text, helptext), options


def _set_build_opt(caller, raw_string, category, value, **kwargs):
	"""Set the option for a category"""

	caller.new_char.features.set('build', **{category: value})

	# go back to the base node for the categories choice to pick another
	return "menunode_build"


def menunode_features(caller, **kwargs):
	"""Root menu for appearance details."""
	# set resume point
	chara = caller.new_char
	chara.db.chargen_step = "menunode_features"
	chara.update_features()
	
	arch = chara.archetype
	arch_key = getattr(arch,'key', None)

	text = """
$head(Your Appearance, Part Two)

You are {build}.

You have {features}.

Choose a feature to customize:
""".format(
            build = chara.build,
            features = chara.features.view
          )

	helptext = fill("The different physical features you define here will be combined "
				"into your character's permanent base description. Some of these features can be customized"
				"later on in-game, such as with hair dye and colored contacts.")

	options = []
	feature_list = list(chara.features.all)
	feature_dict = defaultdict(list)
	for feature in feature_list:
		if (arch_key == "vampire") and "eye" in feature:
			continue
		if type(feature) is tuple:
			if feature[0] not in chargen.FEATURE_OPTS:
				continue
			for_chargen = chara.features.get(feature[0], option='chargen')
			if for_chargen:
				if is_iter(for_chargen):
					if any(for_chargen):
						continue
				else:
					continue
			feature_dict[feature[0]].append(feature[1])
		elif chara.features.get(feature, option='chargen'):
			continue
		elif feature in chargen.FEATURE_OPTS:
			feature_dict[feature] = []
	
	for fkey, subtypes in sorted(feature_dict.items(), key=lambda tup:tup[0]):
		# TODO: use inflect to pluralize properly
		options.append(
			{
				"desc": f"Customize your $h({fkey}{'s' if len(subtypes) > 1 else ''}).",
    		"goto": (_pass_to_feature, { "feature": fkey, "subtypes": subtypes })
			}
		)

	options.append({"key": ("(Randomize)","random","r","randomize"), "desc": "Redo all your features randomly", "goto": (_randomize_features, {"calling_node": "menunode_features"})})
	options.append({"key": ("(Continue)", "continue", "c"), "desc": "Confirm and continue", "goto": chara.ndb.prev_node or "menunode_sdesc"})
	options.append({"key": ("(Back)", "back", "b"), "desc": "Go back", "goto": chara.ndb.prev_node or "menunode_build"})
	return (text, helptext), options

def _pass_to_feature(caller, raw_string, feature=None, subtypes=[], **kwargs):
	if not feature:
		return "menunode_features"
		
	feature_opts = caller.new_char.features.options(feature)
	if not feature_opts:
		return ( "menunode_feature", { "feature": feature, "subtypes": subtypes } )

	return ( "menunode_sub_feature", { "feature": feature, "feature_opts": feature_opts, "subtypes": subtypes } )

def menunode_sub_feature(caller, raw_string, feature=None, feature_opts=None, **kwargs):
	"""Selection an aspect of a feature to describe."""
	chara = caller.new_char
	if not feature or not feature_opts:
		# something went terribly wrong
		chara.db.chargen_step = "menunode_welcome"
		logger.log_err(f"Unset values in menunode_sub_feature. feature: {feature} feature_opts: {feature_opts}")
		return "Something went wrong. Please $h(quit) character creation and try again."

	if type(feature) is tuple:
		feature_desc = chara.features.get(feature[0], match={"subtype": feature[1]})
		feature_str = f"{feature[1]} {feature[0]}"
	else:
		feature_desc = chara.features.get(feature)
		feature_str = feature

	text = f"""
You have {feature_desc}.

Which part of your {feature_str} do you want to customize?
"""

	helptext = fill("Choose one of the options below.")
	options = []
	for option in feature_opts:
		choices = chargen.FEATURE_OPTS[feature][option]
		if len(choices) == 1 and choices[0] == '':
			continue
		options.append({"desc": f"Customize your {feature_str} |c{option}|n.", "goto": ("menunode_feature", { "feature": feature, "option": option })})
	options.append({"key": ("(Back)", "back", "b"), "desc": "Customize a different feature", "goto": "menunode_features"})
	return (text, helptext), options


def menunode_feature(caller, raw_string, feature=None, option='', **kwargs):
	"""Setting a physical feature's description."""
	if not feature:
		# something went terribly wrong
		caller.new_char.db.chargen_step = "menunode_welcome"
		logger.log_err(f"FEATURE not set in menunode_feature")
		return "Something went wrong. Please $h(quit) character creation and try again."

	subtypes = kwargs.get('subtypes',[])
	subtype = kwargs.get('subtype','')
	if subtype:
		feature_str = f"{subtype} {feature}"
	else:
		feature_str = feature + ('s' if len(subtypes) > 1 else '')
	feature_key = feature

	if option:
		opt_str = ' '+option
		desc_str = f"{feature_str} {option}"
		option_values = chargen.FEATURE_OPTS[feature_key][option]
	else:
		opt_str = ''
		option = "value"
		desc_str = f"{feature_str}"
		option_values = chargen.FEATURE_OPTS[feature_key]

	text = f"Customize your $h({desc_str}):"
	helptext = fill("Choose an option.")
	options = []
	for value in sorted(option_values, key=lambda k: strip_ansi(k)):
		if value == "":
			options.append({"desc": f"no descriptor{opt_str}", "goto": (_set_feature, { "feature": feature, "option": option, "value": value, 'subtype': subtype})})
		else:
			options.append({"desc": f"{value}{opt_str}", "goto": (_set_feature, { "feature": feature, "option": option, "value": value, 'subtype': subtype})})
	if len(subtypes) > 1:
		for s in subtypes:
			options.append({"desc": f"Customize just your {s} {feature}", "goto": ("menunode_feature", { "feature": feature, "option": option, "value": value, 'subtype': subtype})})
	if len(options):
		choose_from = list(options)
		options.append({"key": ("(Randomize)", "randomize", "random", "r"), "desc": "Choose a random option", "goto": (_random_choice, {"option_list": choose_from})})
	options.append({"key": ("(Back)", "back", "b"), "desc": "", "goto": "menunode_features"})
	return (text, helptext), options

def _set_feature(caller, raw_string, feature=None, option=None, value=None, **kwargs):
	if not feature:
		return "menunode_features"
	if not option:
		return ("menunode_sub_feature", { "feature": feature })
	if not value and value != "":
		return ("menunode_feature", {"feature": feature, "option": option})

	new_kwargs = {option: value}
	feature_name = feature
	if subtype := kwargs.get('subtype'):
		match = {"subtype": subtype}
	else:
		match = {}
	
	gen.set_character_feature(caller.new_char, feature_name, match=match, **new_kwargs)
#	caller.new_char.features.set(feature_name, match=match, **new_kwargs)
	caller.new_char.update_features()
	if option == "value":
		return "menunode_features"
	else:
		return _pass_to_feature(caller, raw_string, feature=feature)


#########################################################
#				  Character Short desc
#########################################################


def menunode_sdesc(caller, raw_string, **kwargs):
	"""Enter a character description."""
	chara = caller.new_char

	# set resume point
	chara.db.chargen_step = "menunode_sdesc"

	opts_list = []

	raw_feats = [ feat for feat in chara.features.all ]
	feats = []
	for feat in raw_feats:
		if type(feat) is tuple:
			feat = feat[0]
		if feat not in feats:
			feats.append(feat)
	for fkey in feats:
		if opts := chara.features.options(fkey):
			opts_list.extend( [ f"{fkey} {opt}" for opt in opts if chara.features.get(fkey, option=opt)] )
		else:
			opts_list.append(fkey)

	sdesc_list = kwargs.get("sdesc", [ key[1:-1] for key in chara.sdesc.slist ] or ['build persona'])

	text = dedent("""\
		$head(Short Description)

		Your short description is shown in place of your name to characters who
		don't know you, as a quick view of what your character looks like.
		
		Your current short description: {sdesc}

		Choose two of your character's features listed below in the same order you
		want them to be listed.
	""").format(sdesc = chara.sdesc.get(strip=True))

#	text.format(sdesc = sdesc)

	helptext = fill("Choosing an already-selected option will deselect it, allowing you to choose something else.")

	options = []
	count = len(sdesc_list)
	for option in opts_list:
		opt_desc = option
		if option.startswith('build '):
			if option not in ('build height', 'build bodytype'):
				continue
			opt_desc = option.split(' ', maxsplit=1)[1]
		if option in sdesc_list:
			prior = sdesc_list.index(option) + 1
			opt_desc = f"$h({opt_desc}) ({prior})"
			add = False
		elif count < 3:
			add = True
		else:
			continue
		options.append({"desc": opt_desc, "goto": ( _set_sdesc, {"sdesc": sdesc_list, "option": option, "add": add})})
	if count == 3:
		options.append({"key": ("(Continue)", "continue", "c"), "desc": "Finalize your character", "goto": "menunode_confirm_visual"})

	options.append({"key": ("(Back)", "back", "b"), "desc": "Redo your features", "goto": "menunode_features"})

	return (text, helptext), options


def _set_sdesc(caller, raw_string, sdesc=["persona"], **kwargs):
#	logger.log_msg("{} {}".format(sdesc, kwargs))
	if option := kwargs.get("option"):
		if kwargs.get("add",True):
			start = option.split(maxsplit=1)[0]
			if start != 'build':
				sdesc = [item for item in sdesc if not item.startswith(start)]
			sdesc.insert(-1,option)
		else:
			sdesc.remove(option)
		sdesc_str = caller.new_char.sdesc.add(sdesc)

	return ("menunode_sdesc", {"sdesc":sdesc})

def menunode_confirm_visual(caller, raw_string, **kwargs):
	chara = caller.new_char
	# set resume point
	chara.db.chargen_step = "menunode_confirm_visual"
	chara.ndb.prev_node = "menunode_confirm_visual"
	if chara.can_shift:
		chara.do_shift("part")
	
	text = "$head(Your Character)\n\n"
	text += chara.get_display_desc(chara)
	text += "\n\nYou'll appear to others as $h({}).".format(INFLECT.an(chara.sdesc.get(strip=True)))
	text += "\n\nConfirm appearance and continue?"

	if chara.can_shift:
		chara.do_shift("off")

	helptext = "If you're not happy with part of your description here, you can go back and change that step."

	options = []
	options.append( { "desc": "Change your physical build", "goto": "menunode_build" } )
	options.append( { "desc": "Change your features", "goto": "menunode_features" } )
	options.append( { "desc": "Change your short description", "goto": "menunode_sdesc" } )
	options.append( { "key": ("Start Over", "restart", "so", "start"), "desc": "Choose a different archetype", "goto": "menunode_info_arch_base" } )
	# TODO: add initial skills and direct to them from here
	options.append( { "key": ("Continue", "c", "confirm"), "desc": "Confirm and continue.", "goto": "menunode_choose_name" } )

	return text, options


#########################################################
#				Choosing a Name
#########################################################


def menunode_choose_name(caller, raw_string, **kwargs):
	"""Name selection"""
	char = caller.new_char

	# another decision, so save the resume point
	char.db.chargen_step = "menunode_choose_name"

	# check if an error message was passed to the node. if so, you'll want to include it
	# into your "name prompt" at the end of the node text.
	if error := kwargs.get("error"):
		prompt_text = f"{error} Enter a different name:"
	else:
		# there was no error, so just ask them to enter a name.
		prompt_text = "Enter your name:"

	# this will print every time the player is prompted to choose a name,
	# including the prompt text defined above
	text = dedent(
		f"""\
		$head(Choosing a Name)

		This is the last step!

		Other people won't be able to see your character's name, just your short description. However, you'll be seeing it a lot, and it'll show up in all of your logs. Choose something you like!

		{prompt_text}
		"""
	)

	helptext = "You'll have a chance to change your mind before confirming."
	# since this is a free-text field, we just have the one
	options = {"key": "_default", "goto": _check_charname}
	return (text, helptext), options


def _check_charname(caller, raw_string, **kwargs):
	"""Check and confirm name choice"""
	# strip any extraneous whitespace from the raw text
	# if you want to do any other validation on the name, e.g. no punctuation allowed, this
	# is the place!
	charname = raw_string.strip()

	# aside from validation, the built-in normalization function from the caller's Account does
	# some useful cleanup on the input, just in case they try something sneaky
	charname = caller.account.normalize_username(charname)
	if charname in (obj.key for obj in caller.account.characters.all() if obj != caller.new_char):
		return "menunode_choose_name", { "error": "You already have a character by that name." }

	caller.new_char.db.charname = charname
	# continue on to the confirmation node
	return "menunode_confirm_name"


def menunode_confirm_name(caller, raw_string, **kwargs):
	"""Confirm the name choice"""
	char = caller.new_char

	# since we reserved the name by assigning it, you can reference the character key
	# if you have any extra validation or normalization that changed the player's input
	# this also serves to show the player exactly what name they'll get
	text = f"Your new character will be named $h({char.db.charname}). Is this right?"
	# let players change their mind and go back to the name choice, if they want
	options = [
		{"key": ("Yes", "y"), "desc": "Confirm and finish", "goto": "menunode_end"},
		{"key": ("No", "n"), "desc": "Choose something else", "goto": "menunode_choose_name"},
	]

	return text, options


#########################################################
#					 The End
#########################################################


def menunode_end(caller, raw_string):
	"""End-of-chargen cleanup."""
	chara = caller.new_char

	# since everything is finished and confirmed, we actually create the starting objects now
	# TODO: these outfits will vary by persona
	gen.create_starting_outfit(chara, 'default')

	if fam_data := chara.db.familiar:
		fam_data = fam_data.deserialize()
		# TODO: ?????
		chara.do_familiar(update=fam_data)
	chara.attributes.remove('familiar')

	# some extra stoof
	gen.create_starter_phone(chara)
	card = spawn("BASIC_CASH_CARD")[0]
	card.location = chara
	card.attributes.add('value', 1000, category='money')
	# finalize the name
	chara.key = chara.db.charname
	del chara.db.charname
	# clear in-progress status
	del chara.db.chargen_step
	text = dedent(
		"""
		Congratulations!

		You have completed character creation. Enjoy the game!
	"""
	)
	return text, None


# aliases
menunode_human_customize = menunode_build
menunode_wisper_customize = menunode_build
