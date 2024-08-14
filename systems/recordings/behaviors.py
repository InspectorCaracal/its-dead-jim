import string

from datetime import datetime
from evennia.utils.create import create_object

from core.ic.behaviors import Behavior, behavior
# NOTE: Should I have this be in switchboard? *can* I?
from base_systems.characters.base import PARSER
from utils.strmanip import numbered_name

_PHOTO_TEMPLATE = """
{desc}

{characters} {things}

{doors}
"""

@behavior
class CameraBehavior(Behavior):
	priority = 1

	def take_picture(obj, target, **kwargs):
		"""Take a picture of something"""
		if not obj.can_write_data:
			return

		desc = CameraBehavior._get_image_of(obj, target, **kwargs)

		filetype = kwargs.get('filetype', 'image/jpeg')

		desc, details = CameraBehavior._add_details_for(obj, target, desc, **kwargs)

		photo = create_object(
				key=datetime.now().isoformat(),
				typeclass="systems.electronics.software.digital_data.DataObject",
				attributes=[('desc', desc)] 
			)
		photo.filetype = filetype
		
		for d in details:
			d.partof = photo

		obj.do_write_data(photo)
		# TODO: make this configurable from the app/phone settings
		obj.do_make_sound("clicks")
		return photo

	def preview_picture(obj, target, **kwargs):
		return CameraBehavior._get_image_of(obj, target, **kwargs)

	def _add_details_for(obj, target, desc, **kwargs):
		"""create details for the provided description based on target's parts and contents"""
		base_size = getattr(target, 'size', 64)
		resolution = kwargs.get("resolution",4)
		details = {}

		def _make_detail(item):
			name = item.sdesc.get(strip=True)
			if name in details.keys():
				return
			det = create_object(typeclass='systems.crafting.design.DetailObject', key=name)
			details[name] = det
			desc = desc.replace(name, f"|lclook at {name}|lt|{name}|n|le")

		for ob in target.contents:
			if ob == obj.baseobj or ob == obj.baseobj.location:
				# we can't take a picture of ourself!
				continue
			if base_size/getattr(ob,'size',0.5) > resolution:
				continue
			_make_detail(ob)
		
		return desc, list(details.values())

	def _get_image_of(obj, target, **kwargs):
		"""get the descriptive image of the target"""
		output = []
		location = target.baseobj.location
		name = target.get_display_name(None, article=True, strip=True, link=False)
		header = f"A picture of {name}"
		if location:
			loc_desc = location.get_display_desc(None, glance=True, link=False, fallback=False)
			if loc_desc:
				loc_desc = loc_desc[0].lower() + loc_desc[1:]
			else:
				loc_desc = location.get_display_name(None, glance=True, link=False, fallback=False)
			header = f"{header}, set in {loc_desc}"
		if header[-1] not in string.punctuation:
			header += '.'
		output.append(f"$head({header})")

		body = target.return_appearance(None, template=_PHOTO_TEMPLATE, link=False, oob=False)
		output.append(body)

		output = "\n\n".join(output)
		output = PARSER.parse(output, caller=target, receiver=None)

		return output
		

@behavior
class VideoCamBehavior(Behavior):
	priority = 1

	def start_video(obj, target, **kwargs):
		"""Start or resume a video recording"""
		

	def pan_video(obj, target, **kwargs):
		"""Change the target of an active video"""
		

	def pause_video(obj, **kwargs):
		"""Pause a video"""
		

	def stop_video(obj, **kwargs):
		"""Stop recording a video"""
		

@behavior
class AudioRecordBehavior(Behavior):
	priority = 1

	def start_recording(obj, target, **kwargs):
		"""Start or resume a video recording"""
		

	def pause_recording(obj, **kwargs):
		"""Pause a video"""
	

	def stop_recording(obj, **kwargs):
		"""Stop recording a video"""
		
	