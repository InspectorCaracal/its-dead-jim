"""
Partial-match cmdparser that will select the best matching available commands to a given input string.
"""

import re
from django.conf import settings
from evennia.utils import logger

from os.path import commonprefix

_CMD_IGNORE_PREFIXES = settings.CMD_IGNORE_PREFIXES
_RE_SPLIT = re.compile(r'[^a-zA-Z0-9]')


def create_match(cmdname, string, raw_cmdname, cmd_obj):
	"""
	Builds a command match by splitting the incoming string and
	evaluating the quality of the match.

	Args:
		cmdname (str): Name of command to check for.
		string (str): The string to match against.
		cmdobj (str): The full Command instance.
		raw_cmdname (str, optional): If CMD_IGNORE_PREFIX is set and the cmdname starts with
			one of the prefixes to ignore, this contains the raw, unstripped cmdname,
			otherwise it matches cmdname.

	Returns:
		match (tuple): This is on the form (cmdname, args, cmdobj, incmd, overlap, raw_cmdname)

	Notes:
		The returned tuple's data in more detail, by index:
		0: matched command string
		1: arguments
		2: the command object
		3: the incoming command string used
		4: the length of overlapping characters between 0 and 3
		5: the raw command string (which is only different from index 0 if optional prefixes have been stripped)
	"""
	overlap = commonprefix([string.lower(), cmdname])
	search_str = string[len(overlap):]

	if i := _RE_SPLIT.search(search_str):
		i = i.span()[0]
		incmd = overlap + search_str[:i].lower()
		args = search_str[i:]
	else:
		incmd = string.lower()
		args = ''
	return (cmdname, args, cmd_obj, incmd, len(overlap), raw_cmdname)


def build_matches(raw_string, cmdset, include_prefixes=False):
	"""
	Build match tuples by matching raw_string against available commands.

	Args:
		raw_string (str): Input string that can look in any way; the only assumption is
			that the sought command's name/alias must be *first* in the string.
		cmdset: a list of valid Commands to pick from.
		include_prefixes (bool): If set, include prefixes like @, ! etc (specified in settings)
			in the match, otherwise strip them before matching.

	Returns:
		matches (list) A list of match tuples created by `create_match`.

	"""
	matches = []
	stripped_string = raw_string.lstrip(_CMD_IGNORE_PREFIXES) if len(raw_string) > 1 else raw_string

	#	matchlen = 0
	try:
		if include_prefixes:
			# use the cmdname as-is
			for cmd in cmdset:
				keys = [cmd.key] + cmd.aliases
				new_matches = [create_match(cmdname, raw_string, cmdname, cmd) for cmdname in keys if cmdname]
				matches.extend([match for match in new_matches if match[4] and match[3] in match[0]])

		else:
			# strip prefixes set in settings
			for cmd in cmdset:
				new_matches = []
				for raw_cmdname in [cmd.key] + cmd.aliases:
					cmdname = (
						raw_cmdname.lstrip(_CMD_IGNORE_PREFIXES)
						if len(raw_cmdname) > 1
						else raw_cmdname
					)
					new_matches.append(create_match(cmdname, stripped_string, raw_cmdname, cmd))

				matches.extend([match for match in new_matches if match[4] and match[3] in match[0]])

	except Exception:
		logger.log_trace("cmdhandler error. raw_input:%s" % raw_string)
	return matches


def cmdparser(raw_string, cmdset, caller, **kwargs):
	"""
	This function is called by the cmdhandler once it has
	gathered and merged all valid cmdsets valid for this particular parsing.

	Args:
		raw_string (str): The unparsed text entered by the caller.
		cmdset (CmdSet): The merged, currently valid cmdset
		caller (Session, Account or Object): The caller triggering this parsing.

	Returns:
		matches (list): This is a list of match-tuples as returned by `create_match`.
			If no matches were found, this is an empty list.
	"""
	if not raw_string:
		return []

	# only check for commands we are actually allowed to call.
	cmdset = [cmd for cmd in cmdset if cmd.access(caller, "cmd")]

	# find matches, using the fuzziest matching first
	matches = build_matches(raw_string, cmdset, include_prefixes=False)

	if not len(matches):
		# there are no commands that match at all
		return matches

	max_score = max([mat[4] for mat in matches])

	if len(matches) > 1 and _CMD_IGNORE_PREFIXES:
		# check for a disambiguating prefix
		trimmed = build_matches(raw_string, cmdset, include_prefixes=True)
		if len(trimmed):
			trimmed_score = max([mat[4] for mat in trimmed])
			if trimmed_score >= max_score:
				matches = trimmed
				max_score = trimmed_score

	if len(matches) > 1:
		# check for exact matches
		trimmed = [match for match in matches if len(match[0]) == match[4]]
		if trimmed:
			matches = trimmed

	if len(matches) > 1:
		# find the best non-exact matches
		matches = [mat for mat in matches if mat[4] == max_score]

	if len(matches) > 1:
		# check command for attached object against name
		obj_cmds = [mat for mat in matches if mat[2]]
		if obj_cmds:
			obj_cmds = [mat for mat in obj_cmds if mat[2].obj and
			            any(item in mat[2].obj.sdesc.get(strip=True).split() for item in mat[1].split())]
	
			if obj_cmds:
				matches = obj_cmds

	if len(matches) > 1:
		trimmed = []
		used = []
		# TODO: this results in multimatching the same command; do it better
		for match in matches:
			if (match[0], type(match[2])) not in used:
				trimmed.append(match)
				used.append((match[0], type(match[2])))
		if trimmed:
			matches = trimmed

	return matches
