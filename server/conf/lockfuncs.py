"""

Lockfuncs

Lock functions are functions available when defining lock strings,
which in turn limits access to various game systems.

All functions defined globally in this module are assumed to be
available for use in lockstrings to determine access. See the
Evennia documentation for more info on locks.

A lock function is always called with two arguments, accessing_obj and
accessed_obj, followed by any number of arguments. All possible
arguments should be handled with *args, **kwargs. The lock function
should handle all eventual tracebacks by logging the error and
returning False.

Lock functions in this module extend (and will overload same-named)
lock functions from evennia.locks.lockfuncs.

"""

# def myfalse(accessing_obj, accessed_obj, *args, **kwargs):
#    """
#    called in lockstring with myfalse().
#    A simple logger that always returns false. Prints to stdout
#    for simplicity, should use utils.logger for real operation.
#    """
#    print "%s tried to access %s. Access denied." % (accessing_obj, accessed_obj)
#    return False

def magesight(accessing_obj, accessed_obj, *args, **kwargs):
	try:
		return accessing_obj.archetype.sight
	except AttributeError:
		return False

def is_closed(accessing_obj, accessed_obj, *args, **kwargs):
	return accessed_obj.tags.has('closed', category='status') or not accessed_obj.tags.has('open', category='status')
closed = is_closed

def is_open(accessing_obj, accessed_obj, *args, **kwargs):
	return accessed_obj.tags.has('open', category='status') or not accessed_obj.tags.has('closed', category='status')

def is_posed_on(accessing_obj, accessed_obj, *args, **kwargs):
	"""Validate that the accessing object is in the correct position"""
	location = accessing_obj.location
	if not location:
		return False
	if pose := location.posing.get_posed_on(accessing_obj):
		return accessed_obj == pose
	else:
		return False

def obstacle_check(accessing_obj, accessed_obj, *args, **kwargs):
	"""Validate that the accessing object is in the correct position"""
	if not hasattr(accessed_obj, 'moves'):
		return True
	if not accessing_obj.location:
		return False
	if poses := accessing_obj.location.posing.get(accessing_obj):
		source = poses[0]
	else:
		source = accessing_obj.location
	return source in accessed_obj.moves.get_sources()

def has_side_up(accessing_obj, accessed_obj, side=None, *args, **kwargs):
	if not side:
		return True
#	if not (obj := accessed_obj.partof):
	obj = accessed_obj.baseobj
	return obj.tags.has(side, category='side_up')

def is_npc(accessing_obj, *args, **kwargs):
	return 'npc' in accessing_obj._content_types