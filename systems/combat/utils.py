from random import choices
from evennia.utils import logger

def get_hit_location(target, min_size=1, **kwargs):
	if not (parts := target.parts.all()):
		return target
	
	parts = [ obj for obj in parts if hasattr(obj, 'at_damage') and not obj.tags.has('virtual_container', category='systems') and obj.size >= min_size ]
	if hasattr(target,'at_damage'):
		parts.append(target)
	
	weights = [ obj.size for obj in parts ]

	top = target.baseobj
	if top != target:
		# add other parts, but weighted less
		new_parts = [ obj for obj in top.parts.all() if obj not in parts and hasattr(obj, 'at_damage') and not obj.tags.has('virtual_container', category='systems') and obj.size >= min_size ]
		parts.extend(new_parts)
		weights.extend([ obj.size//3 for obj in new_parts ])

	picked = choices(parts, weights=weights)[0]

	return picked