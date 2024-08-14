import re
from evennia.utils import create
from core.ic.behaviors import NoSuchBehavior

import switchboard
from utils.colors import strip_ansi

def _get_materials(caller, design_type):
	return list(obj for obj in caller.contents if obj.tags.has(design_type, category='crafting_tool'))

# TODO: make this use my nice menu class

def menunode_begin_drawing(caller, raw_string, **kwargs):
	obj = caller.ndb._evmenu.action.target
	material = caller.ndb._evmenu.material
	text = f"You are drawing on {obj.get_display_name(caller)}"
	if material:
		text += f" with {material.get_display_name(caller)}.\n\nWhat do you draw?"
		options = {'key': '_default', 'goto': _process_design}
	else:
		text += '.\n\nChoose something to draw with:'
		options = [
			{	'key': obj.get_display_name(caller), 'goto': (_choose_material, {'material': obj}) }
				for obj in _get_materials(caller, 'sketching')
			]
	if err := kwargs.get('error'):
		text = f"|r{err}|n\n\n{text}"

	return text, options

def _choose_material(caller, raw_string, material, **kwargs):
	if not material.access(caller, 'craftwith'):
		return ('menunode_begin_drawing', {'error': f'You cannot draw with {material.get_display_name(caller)}.'})
	else:
		caller.ndb._evmenu.material = material
		return kwargs.get('nodename','menunode_begin_drawing')

def _process_design(caller, raw_string, **kwargs):
	design = raw_string.strip()
	design = design.replace("|/","\n")
	design = strip_ansi(design)
	if len(design) > switchboard.MAX_DESIGN_LENGTH:
		error = "Your drawing is too long; please try again with a shorter description."
		return ('menunode_begin_drawing', {'error': error})

	material = caller.ndb._evmenu.material
	if mat_str := material.materials.view:
		drawn = f"\n  (drawn in {mat_str})"
	else:
		drawn = ''
	
	return ('menunode_confirm_drawing', {'design': design, 'drawn': drawn})

def menunode_confirm_drawing(caller, raw_string, design, drawn, **kwargs):
	text = f"Your drawing will look like this:\n{design}{drawn}"

	options = [
		{'desc': 'Confirm and continue', 'goto': (_set_design,  {'design': design, 'drawn': drawn})},
		{'desc': 'Start over', 'goto': 'menunode_begin_drawing'},
	]

	return text, options

def _set_design(caller, raw_string, design, drawn, **kwargs):
	obj = caller.ndb._evmenu.action.target
	if side := obj.tags.get(category='side_up'):
		key = side
	else:
		key = 'design'
	side = f'"{side}"' if side else ''
	design_obj = create.object('base_systems.meta.base.MetaThing', key=key,
			attributes=[('desc', design+drawn)],
			locks=f'view:has_side_up({side});search:has_side_up({side});get:false()',
			tags=[('external', 'attach_type'), ('design', 'part')],
		)
	design_obj.partof = obj	
#	obj.descs.add_design(design+drawn)
	caller.ndb._evmenu.action.xp += 1
	caller.ndb._evmenu.action.design = design_obj
	return 'menunode_choose_detail'

def menunode_choose_detail(caller, raw_string, **kwargs):
	obj = caller.ndb._evmenu.action.design
	text = f"Your current design:\n\n{strip_ansi(obj.descs.get(caller))}\n\n"
	if err := kwargs.get('error'):
		text = f"|r{err}|n\n\n{text}"

	# TODO: add a check on how many details you can add here, to display

	options = []
	if details := obj.parts.search('design_detail', part=True):
		options = [ {"desc": f"Edit $h({detail})", "goto": (_get_or_make_detail, {'detail': detail})} for detail in details ]

	if len(options) < caller.ndb._evmenu.action.max_details:
		text += '\n\nEnter an element you want to add more detail to (e.g. "evergreen tree"), or choose an existing detail below to work on.'
		options.append(	{"key": "_default", "goto": _get_or_make_detail} )
	else:
		text += "\n\nChoose a detail to work on:"

	helptext = "Details are highlighted sections of your drawing which can be looked at, and which have their own full description attached."
	options.append({"key": ("Stop drawing","stop"), "goto": "menunode_end"})

	return (text, helptext), options

def _get_or_make_detail(caller, raw_string, **kwargs):
	obj = caller.ndb._evmenu.action.design
	if not kwargs.get('detail'):
		key = raw_string.strip()
		matches = obj.parts.search(key)
		if matches:
			detail = matches[0]
		else:
			# we're making a new detail
			design = strip_ansi(obj.descs.get(caller))
			refind = re.compile(rf"\b({key})\b", re.I)
			results = refind.findall(design)
			if len(results) > 1:
				# caller.msg() # ???
				return ("menunode_choose_detail", {'error': "That element is too vague."})
			elif len(results) < 1:
				# caller.msg()
				return ("menunode_choose_detail", {'error': f"There is no {key} in your drawing."})
			else:
				key = results[0]
				detail = create.object('base_systems.meta.base.MetaThing', key=key,
						locks=obj.locks.get(),
						tags=[('design_detail', 'part')],
					)
				caller.msg(f"created {detail}, adding it to {obj}")
				detail.partof = obj
				caller.ndb._evmenu.action.xp += 1
		kwargs['detail'] = detail
	
	return ("menunode_choose_material", kwargs)

def menunode_choose_material(caller, raw_string, **kwargs):
	detail_obj = kwargs['detail']

	text = f"Choose a material for your $h({detail_obj.key})."

	if detail_obj.db.desc:
		text = f"The {detail_obj.key} currently looks like:\n{detail_obj.get_display_desc(caller)}\n\n{text}"

	materials = [ ob for ob in caller.location.contents + caller.contents if ob.tags.has('sketching', category='crafting_tool')]
	options = [ {"desc": mat.get_display_name(caller, article=False), "goto": ("menunode_create_detail", kwargs | {'material': mat})} for mat in materials ]

	options += [
		{"key": ("Choose a different detail","detail", "restart"), "goto": "menunode_choose_detail"},
		{"key": ("Stop drawing","stop"), "goto": "menunode_end"}
	]

	return text, options

def menunode_create_detail(caller, raw_string, **kwargs):
	text = f"You are detailing {kwargs['detail'].key} with {kwargs['material'].get_display_name(caller)}\n\nEnter the description for your detail:"
	if err := kwargs.pop('error', None):
		text = f"|r{err}|n\n\n{text}"

	helptext = "The detail's description should expand on the initial element of the drawing, and is limited to 240 characters."
	option = { "key": "_default", "goto": (_set_detail, kwargs) }

	return (text,helptext), option

def _set_detail(caller, raw_string, **kwargs):
	desc = raw_string.rstrip()
	desc = desc.replace("|/","\n")
	desc = strip_ansi(desc)
	if len(desc) > switchboard.MAX_DESIGN_LENGTH:
		return ("menunode_create_detail", kwargs | {'error': "Your description was too long."} )
	
	detail = kwargs['detail']
	mat = kwargs['material']
	detail.features.clear()
	# TODO: add a "draw" behavior to pull pigment materials and use up ink etc.
	try:
		if mat.do_color(detail):
			detail.db.desc = desc
			return "menunode_choose_detail"
		else:
			return ("menunode_choose_detail", {'error': f'There is not enough of your {mat} to draw anything.'})
	except NoSuchBehavior:
		detail.db.desc = desc
		return "menunode_choose_detail"


def menunode_end(caller, raw_string, **kwargs):
	return