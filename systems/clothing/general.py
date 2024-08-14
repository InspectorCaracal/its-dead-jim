def cover_parts(*args):
	"""
	Generate a list of coverage tags
	
	Args:
		part names to cover, or tuples of (part, subtype)
	
	Returns:
		list of correctly formatted coverage tags
	"""
	taglist = []
	cat = "parts_coverage"
	for arg in args:
		if type(arg) is tuple:
			# tags have to be strings, so we represent it as a csl
			arg = ",".join(arg)
		taglist.append( (arg, cat) )
	return taglist