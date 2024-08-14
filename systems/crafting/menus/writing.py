import re
from evennia.utils import create
from core.ic.behaviors import NoSuchBehavior

import switchboard
from utils.colors import get_name_from_rgb, strip_ansi

def _get_materials(caller, design_type):
	return list(obj for obj in caller.contents if obj.tags.has(design_type, category='crafting_tool'))

# TODO: make this use my nice menu class

def menunode_begin_writing(caller, raw_string, **kwargs):
	obj = caller.ndb._evmenu.action.target
	material = caller.ndb._evmenu.material
	text = f"You are writing on {obj.get_display_name(caller)}"
	if material:
		text += f" with {material.get_display_name(caller)}.\n\nWhat do you write?"
		options = {'key': '_default', 'goto': _process_writing}
	else:
		text += '.\n\nChoose something to write with:'
		options = [
			{	'key': obj.get_display_name(caller), 'goto': (_choose_material, {'material': obj}) }
				for obj in _get_materials(caller, 'sketching')
			]
	if err := kwargs.get('error'):
		text = f"|r{err}|n\n\n{text}"

	return text, options

def _choose_material(caller, raw_string, material, **kwargs):
	if not material.access(caller, 'craftwith'):
		return ('menunode_begin_writing', {'error': f'You cannot write with {material.get_display_name(caller)}.'})
	else:
		caller.ndb._evmenu.material = material
		return kwargs.get('nodename','menunode_begin_writing')

def _process_writing(caller, raw_string, **kwargs):
	design = raw_string.strip()
	design = design.replace("|/","\n")
	design = strip_ansi(design)
	if prev := kwargs.get('continue_from'):
		design = f"{prev}\n{design}"
	if len(design) > switchboard.MAX_WRITING_LENGTH:
		error = "Your text is too long; please try again."
		return ('menunode_begin_writing', {'error': error})

	material = caller.ndb._evmenu.material
	if mat_str := material.materials.view:
		written = f"\n  (written in {mat_str})"
	else:
		written = ''
	
	return ('menunode_confirm_writing', {'design': design, 'written': written})

def menunode_confirm_writing(caller, raw_string, design, written, **kwargs):
	text = f"Your writing will look like this:\n{design}{written}\n\nContinue writing, or choose an option below:"

	options = [
		{'key': '_default', 'goto': (_process_writing, {'continue_from': design})},
		{'desc': 'Confirm and continue', 'goto': (_set_writing,  {'design': design, 'written': written})},
		{'desc': 'Start over', 'goto': 'menunode_begin_writing'},
	]

	return text, options

def _set_writing(caller, raw_string, design, written, **kwargs):
	handwriting = caller.ndb._evmenu.action.handwriting
	obj = caller.ndb._evmenu.action.target
	if side := obj.tags.get(category='side_up'):
		key = side
	else:
		key = 'text'
	if not side:
		side = ''
	text_obj = create.object('base_systems.meta.base.MetaThing', key=key,
			locks=f'view:has_side_up({side});search:has_side_up({side});get:false()',
			tags=[('external', 'attach_type'), ('text', 'part')],
		)

	# TODO: add support for things like invisible ink here
	detail = create.object('base_systems.meta.base.MetaThing', key=key,
			locks=f'read:all();get:false()', tags=[('detail', 'part')],
		)
	detail.partof = text_obj
	material = caller.ndb._evmenu.material
	detail.features.clear()
	# TODO: add a "write" behavior to pull pigment materials and use up ink etc.
	if material.can_color:
		if not material.do_color(detail):
			caller.ndb._evmenu.action.material = None
			return ("menunode_begin_writing", {'error': f'There is not enough of your {material} to write anything.'})
	detail.db.desc = design+written
	color = ''
	if mats := detail.features.all:
		mat = mats[0]
		color = detail.features.get(mat, as_data=True).get("pigment")
		color = get_name_from_rgb(color, styled=True) if color else ''
	text_obj.partof = obj

	return "menunode_end"


def menunode_end(caller, raw_string, **kwargs):
	return