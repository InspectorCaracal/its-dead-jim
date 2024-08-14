"""
See core contrib for docs
"""
import re
import string
from re import escape as re_escape
from collections import defaultdict
from string import punctuation

from django.conf import settings
from evennia.objects.models import ObjectDB
from evennia.utils import interactive, logger
from evennia.utils.utils import lazy_property, is_iter, make_iter, variable_from_module, string_partial_matching, string_suggestions
from evennia.utils.dbserialize import deserialize

from utils.strmanip import numbered_name, strip_extra_spaces
from utils.colors import strip_ansi

_VOICE_PARTS = ["quality", "style", "voice"]

# ------------------------------------------------------------
# Emote parser
# ------------------------------------------------------------

# Settings

# The prefix is the (single-character) symbol used to find the start
# of a object reference, e.g `@tall` or `@tall man`
_PREFIX = "@"
# deprecated
_NUM_SEP = "-"

_EMOTE_NOMATCH_ERROR = """|RNo match for |r{ref}|R.|n"""

_RE_FLAGS = re.MULTILINE + re.IGNORECASE + re.UNICODE
#_RE_PREFIX = re.compile(r"^%s" % _PREFIX, re.UNICODE)

_RE_OBJ_REF_START = re.compile(rf"{_PREFIX}(\w+)", _RE_FLAGS)

_RE_LEFT_BRACKETS = re.compile(r"\{+", _RE_FLAGS)
_RE_RIGHT_BRACKETS = re.compile(r"\}+", _RE_FLAGS)
# Reference markers are used internally when distributing the emote to
# all that can see it. They are never seen by players and are on the form {#dbref<char>}
# with the <char> indicating case of the original reference query (like ^ for uppercase)
_RE_REF = re.compile(r"\{+\#([0-9]+[\^\~tv]{0,1})\}+")

# This regex is used to quickly reference one self in an emote.
_RE_SELF_REF = re.compile(r"(@me)[^a-zA-Z]+", _RE_FLAGS)
_RE_POSS_SELF_REF = re.compile(r"(@my)[^a-zA-Z]+", _RE_FLAGS)

# reference markers for language
_RE_REF_LANG = re.compile(r"\{+\##([0-9]+)\}+")
# language says in the emote are on the form "..." or langname"..." (no spaces).
# this regex returns in groups (langname, say), where langname can be empty.
_RE_LANGUAGE = re.compile(r'(\w+)?(".*?")')


class EmoteError(Exception):
	pass

class LanguageError(Exception):
	pass


# emoting mechanisms
def _get_case_ref(string):
    """
    Helper function which parses capitalization and
    returns the appropriate case-ref character for emotes.
    """
    # default to retaining the original case
    case = "~"
    # internal flags for the case used for the original /query
    # - t for titled input (like /Name)
    # - ^ for all upercase input (like /NAME)
    # - v for lower-case input (like /name)
    # - ~ for mixed case input (like /nAmE)
    if string.istitle():
        case = "t"
    elif string.isupper():
        case = "^"
    elif string.islower():
        case = "v"

    return case

def _do_multimatch(caller, target, lst):
	match_opts = []
	for i, obj in enumerate(lst):
		name = obj.key

		string = " {index} {name}{extra}".format(
			index=i + 1,
			name=obj.get_display_name(caller) if hasattr(obj, "get_display_name") else name,
			extra=obj.get_extra_info(caller) if hasattr(obj, "get_extra_info") else '',
		)
		match_opts.append(string)
	caller.msg("Which $h({target}) do you mean?\n{options}".format(target=target, options="\n".join(match_opts)))
	option = yield("Enter a number (or $h(c) to cancel)")
	if option.lower().strip() == 'c':
		caller.msg("Action cancelled.")
		return None
	try:
		option = int(option)
	except ValueError:
		option = -1

	if 0 < option <= len(lst):
		return lst[option - 1]
	else:
		caller.msg("Invalid option, cancelling.")
		return None

def parse_language(speaker, emote):
	"""
	Parse the emote for language. This is
	used with a plugin for handling languages.

	Args:
		speaker (Object): The object speaking.
		emote (str): An emote possibly containing
			language references.

	Returns:
		(emote, mapping) (tuple): A tuple where the
			`emote` is the emote string with all says
			(including quotes) replaced with reference
			markers on the form {##n} where n is a running
			number. The `mapping` is a dictionary between
			the markers and a tuple (langname, saytext), where
			langname can be None.
	Raises:
		evennia.contrib.rpg.rpsystem.LanguageError: If an invalid language was
		specified.

	Notes:
		Note that no errors are raised if the wrong language identifier
		is given.
		This data, together with the identity of the speaker, is
		intended to be used by the "listener" later, since with this
		information the language skill of the speaker can be offset to
		the language skill of the listener to determine how much
		information is actually conveyed.

	"""
	# escape mapping syntax on the form {##id} if it exists already in emote,
	# if so it is replaced with just "id".
	emote = _RE_REF_LANG.sub(r"\1", emote)

	errors = []
	mapping = {}
	for imatch, say_match in enumerate(reversed(list(_RE_LANGUAGE.finditer(emote)))):
		# process matches backwards to be able to replace
		# in-place without messing up indexes for future matches
		# note that saytext includes surrounding "...".
		langname, saytext = say_match.groups()
		istart, iend = say_match.start(), say_match.end()
		# the key is simply the running match in the emote
		key = "##%i" % imatch
		# replace say with ref markers in emote
		emote = emote[:istart] + "{%s}" % key + emote[iend:]
		mapping[key] = (langname, saytext)

	if errors:
		# catch errors and report
		raise LanguageError("\n".join(errors))

	# at this point all says have been replaced with {##nn} markers
	# and mapping maps 1:1 to this.
	return emote, mapping


def parse_sdesc_markers(caller, candidates, emote, case_sensitive=True, **kwargs):
	"""
	Replaces user-friendly @ markers to embedded object references for formatting.

	Args:
		caller (Object): The object sending the emote. This object's
			recog data will be considered in the parsing.
		candidates (iterable): A list of objects valid for referencing
			in the emote.
		emote (str): The string (like an emote) we want to analyze for keywords.
		case_sensitive (bool, optional); If set, the case of /refs matter, so that
			/tall will come out as 'tall man' while /Tall will become 'Tall man'.
			This allows for more grammatically correct emotes at the cost of being
			a little more to learn for players. If disabled, the original sdesc case
			is always kept and are inserted as-is.

	Returns:
		(str, dict) - the modified emote string and a mapping dict of ref keys to objects

	Raises:
		EmoteException: For various ref-matching errors.

	Notes:
		The parser analyzes and should understand the following _PREFIX-tagged structures in the emote:
		- self-reference (@me)
		- recogs (any part of it) stored on emoter, matching obj in `candidates`.
		- sdesc (any part of it) from any obj in `candidates`.
		- says, "..." are handled by the language parser

	"""
	# build a list of candidates with all possible referrable names
	# include 'me' keyword for self-ref
	candidate_map = []
	for obj in candidates:
		if obj == caller:
			candidate_map.append( (obj, obj.key) )
			continue
		# check if sender has any recogs for obj and add
		if hasattr(caller, "recog"):
			if recog := caller.recog.get(obj):
				candidate_map.append((obj, recog))
		# check if obj has an sdesc and add
		if hasattr(obj, "sdesc"):
			candidate_map.append((obj, obj.sdesc.get(strip=True)))
		# if no sdesc, include key plus aliases instead
		else:
			candidate_map.extend( [(obj, obj.key)] + [(obj, alias) for alias in obj.aliases.all()] )

	# escape mapping syntax on the form {#id} if it exists already in emote,
	# if so it is replaced with just "id".
	emote = _RE_REF.sub(r"\1", emote)
	# escape loose { } brackets since this will clash with formatting
	emote = _RE_LEFT_BRACKETS.sub("{{", emote)
	emote = _RE_RIGHT_BRACKETS.sub("}}", emote)

	mapping = {}
	errors = []
	obj = None
	nmatches = 0
	# first, find and replace any self-refs
	if caller:
		has_me = _RE_SELF_REF.search(emote)
		for i, my_match in enumerate(list(_RE_POSS_SELF_REF.finditer(emote))):
			matched = my_match.group().rstrip(punctuation).rstrip()
			mcase = _get_case_ref(matched.lstrip(_PREFIX)) if case_sensitive else "~"
			# replaced with ref
			if i == 0 and not has_me:
				repmatch = matched.replace('y','e').replace('Y', 'E')
			else:
				# TODO: make $gp case sensitive instead, change case on args
				repmatch = "$Gp(their)" if mcase=='t' else '$gp(their)'
			emote = emote.replace(matched,repmatch,1)

		for self_match in list(_RE_SELF_REF.finditer(emote)):
			matched = self_match.group().rstrip(punctuation).rstrip()
			mcase = _get_case_ref(matched.lstrip(_PREFIX)) if case_sensitive else "~"
			key = f"#{caller.id}{mcase}"
			# replaced with ref
			emote = emote.replace(matched,f"{{{key}}}")
			mapping[key] = caller

	# we now loop over all references and analyze them
	for marker_match in reversed(list(_RE_OBJ_REF_START.finditer(emote))):
		# we scan backwards so we can replace in-situ without messing
		# up later occurrences. Given a marker match, query from
		# start index forward for all candidates.

		match_index = marker_match.start()
		# split the emote string at the reference marker, to process everything after it
		head = emote[:match_index]
		tail = emote[match_index+1:]
		
		# to find the longest match, we start from the marker and lengthen the 
		# match query one word at a time.
		rquery = r''
		bestmatches = []
		# preserve punctuation when splitting
		tail = re.split(r'(\W)', tail)
		iend = 0
		for i, item in enumerate(tail):
			# don't add non-word characters to the search query
			if not item.isalpha():
				continue
			# rquery = "".join([r"\b(" + re.escape(word) + r").*" for word in word_list])
			rquery += r"(\b" + re.escape(item) + "|" + re.escape(item) + r"\b).*"
			# match candidates against the current set of words
			matches = ((re.search(rquery, text, _RE_FLAGS), obj, text) for obj, text in candidate_map)
			matches = [(obj, match.group()) for match, obj, text in matches if match]
			if len(matches) == 0:
				# no matches at this length, keep previous iteration as best
				break
			# since this is the longest match so far, set latest match set as best matches
			bestmatches = matches
			# save current index as end point of matched text
			iend = i

		# save search string
		matched_text = "".join(tail[:iend+1])
		# recombine remainder of emote back into a string
		tail = "".join(tail[iend+1:])

		objlist = list(set([match[0] for match in bestmatches]))
		nmatches = len(objlist)

		if nmatches > 1:
			# query player for correct match, or use the first match as a fallback
			if caller.is_connected:
				obj = yield from _do_multimatch(caller, matched_text, objlist)
			else:
				obj = objlist[0]
			if not obj:
				errors.append("Emote cancelled.")
			else:
				nmatches = 1
		elif nmatches == 1:
			obj = objlist[0]
		elif nmatches == 0:
			_, cand_words = zip(*candidate_map)
			suggestions = string_suggestions(matched_text, cand_words)
			if suggestions and caller.is_connected:
				objlist = [ tup[0] for tup in candidate_map if tup[1] in suggestions ]
				obj = yield from _do_multimatch(caller, matched_text, objlist)
				if not obj:
					errors.append("Emote cancelled.")
			else:
				obj = None
				errors.append(_EMOTE_NOMATCH_ERROR.format(ref=marker_match.group()))

		if obj:
			# a unique match - parse into intermediary representation
			case = _get_case_ref(matched_text) if case_sensitive else "~"  # retain original case of sdesc
			key = f"#{obj.id}{case}"
			# recombine emote with matched text replaced by ref
			emote = f"{head}{{{key}}}{tail}"
			mapping[key] = obj
		else:
			if not errors:
				errors.append("|REmote failed.|n")
			break

	if errors:
		# make sure to not let errors through.
		if caller:
			caller.msg("\n".join(errors))
		return None, None

	# at this point all references have been replaced with {#xxx} markers and the mapping contains
	# a 1:1 mapping between those inline markers and objects.
	return emote, mapping


@interactive
def send(sender, message, receivers=None, include=None, volume=1, **kwargs):

	send_to = receivers or sender.baseobj.location.contents
	include = make_iter(include) if include else []

	base_emote, obj_mapping = yield from parse_sdesc_markers(sender, send_to+include, message)
	if not base_emote:
		return

	skey = f"#{str(sender.id)}"
#	skeyt = f"#{str(sender.id)}t"

	# print(base_emote)

	# TODO: prevent players from speaking if they don't pass .can_speak
	try:
		base_emote, language_mapping = parse_language(sender, base_emote)
	except (EmoteError, LanguageError) as err:
		# handle all error messages, don't hide actual coding errors
		sender.msg(str(err))
		return

	lockey = "{{#x}}"

	def _do_emote(location, _message, v, first=False):
		_receive = location.contents
		if first:
			_receive.append(location)
			process_emote(sender, _receive, _message, obj_mapping, language_mapping, **kwargs)
		else:
			process_emote(sender, _receive, _message, obj_mapping, language_mapping, **kwargs)
		v -= 1
		if v > 0:
			soundproofing = location.attributes.get('soundproofing',0)
			if v > soundproofing and location.location:
				obj_mapping["#x"] = location.location
				_do_emote(location.location, f"From {lockey}, {skey} "+base_emote, v-soundproofing)

	if receivers:
		process_emote(sender, send_to, base_emote, obj_mapping, language_mapping, **kwargs)
	else:
		_do_emote(sender.baseobj.location, base_emote, volume)

def process_emote(
		caller, receivers, emote, obj_mapping, language_mapping, include=None, exclude=[],
		outkwargs=None, case_sensitive=True, anonymous_add="first", **kwargs
	):
	"""
	Takes an emote string and sends it to all recipients in a viewer-aware manner.

	Args:
		sender (Object): The one sending the emote.
		receivers (iterable): Receivers of the emote. These
			will also form the basis for which sdescs are
			'valid' to use in the emote.
		emote (str): The raw emote string as input by emoter.

	Keyword args:
		include (list) - objects to include as candidates who will not receive the emote
		exclude (list) - objects to exclude from receiving the emote (?? why do I have both of these)

		anonymous_add (str or None): Adds a self-reference if there is not already one present in the emote.
		  Valid options are:
			- None: Do not add a self-reference.
			- 'last': Add sender to the end of emote as [sender]
			- 'first': Prepend sender to start of emote as [Sender]
		case_sensitive (bool): Defaults to True. When False, names will be rendered with their default case.
		FIXME any: Other kwargs will be passed on into the receiver's process_sdesc and
			process_recog methods, and can thus be used to customize those.

	"""
	sender = caller
	if not include:
		include = []

	if not exclude:
		exclude = []

	# backwards compat until i finish refactoring
	if not outkwargs:
		outkwargs = {}
	outkwargs = kwargs | outkwargs

	if is_iter(emote) and len(emote) > 1:
		opts = emote[1]
		emote = emote[0]
		outkwargs = opts | outkwargs

	# FIXME
	outkwargs = { 'type': 'emote', 'target': 'emote' } | outkwargs

	# make sure to catch all possible self-refs
	if sender:
		skey = f"#{sender.id}"
		self_refs = [f"{skey}{ref}" for ref in ('t','^','v','~','')]
		if not any(tag in self_refs for tag in obj_mapping):
			match anonymous_add:
				case "first":
					skey += 't'
					# don't put a space after the self-ref if it's a possessive emote
					emote = f"{{{skey}}}{emote}" if emote.startswith("'") else f"{{{skey}}} {emote}"
				case None:
					pass
				case _:
					emote = f"{emote} [{{{skey}}}]"
		obj_mapping[skey] = sender

	# we escape the object mappings since we'll do the language ones first
	emote = _RE_REF.sub(r"{{#\1}}", emote)

	# broadcast emote to everyone
	for receiver in receivers:
		if receiver in exclude:
			continue
		# first handle the language mapping, which always produce different keys ##nn
		if hasattr(receiver, "process_language") and callable(receiver.process_language):
			receiver_lang_mapping = {
				key: receiver.process_language(saytext, sender, langname)
				for key, (langname, saytext) in language_mapping.items()
			}
		else:
			receiver_lang_mapping = {
				key: saytext for key, (langname, saytext) in language_mapping.items()
			}
		# map the language {##num} markers. This will convert the escaped sdesc markers on
		# the form {{#num}} to {#num} markers ready to sdesc-map in the next step.
		sendemote = emote.format(**receiver_lang_mapping)

		# map the ref keys to sdescs
		receiver_sdesc_mapping = dict(
			(
				ref,
				obj.get_display_name(receiver, ref=ref, from_obj=sender, # why does get_display_name get `from_obj` ???
					noid=True, article=True, link=True, strip=True, contents=False
				),
			)
			for ref, obj in obj_mapping.items()
		)

		# do the template replacement of the sdesc/recog {#num} markers
		receiver.msg(text=(sendemote.format(**receiver_sdesc_mapping), outkwargs), from_obj=sender)


def ic_search(sender, candidates, search_term, partial=False, exact=False, **kwargs):
	"""
	Matches a list of candidates to a search term

	Args:
		sender (Object): The object sending the emote. This object's
			recog data will be considered in the parsing.
		candidates (iterable): A list of objects valid for referencing
			in the emote.
		search_term (str): The string (like an emote) we want to analyze for keywords.
		search_mode (bool, optional): If `True`, the "emote" is a query string
			we want to analyze. If so, the return value is changed.
		case_sensitive (bool, optional); If set, the case of /refs matter, so that
			/tall will come out as 'tall man' while /Tall will become 'Tall man'.
			This allows for more grammatically correct emotes at the cost of being
			a little more to learn for players. If disabled, the original sdesc case
			is always kept and are inserted as-is.

	Returns:
		obj_list: A list of matched objects
		(obj_list, extra):  A list of matched objects, and whatever tail of the search
			string was left over, if partial=True
	"""
	# this is hacky as shit
	if search_term.startswith(_PREFIX):
		search_term = search_term[1:]
	if search_term.lower().startswith("a "):
		search_term = search_term[2:]
	elif search_term.lower().startswith("an "):
		search_term = search_term[3:]

	# build a list of candidates with all possible referrable names
	# include 'me' keyword for self-ref
	candidate_map = []
	for obj in candidates:
		if obj == sender:
			candidate_map.append( (obj, obj.key) )
			continue
		# check if sender has any recogs for obj and add
		if hasattr(sender, "recog"):
			if recog := sender.recog.get(obj):
				candidate_map.append((obj, recog))
		# check if obj has an sdesc and add
		if hasattr(obj, "sdesc"):
			candidate_map.append((obj, obj.sdesc.get(sender, strip=True)))
		# if no sdesc, use key instead
		else:
			candidate_map.append( (obj, obj.key) )
		# add in aliases
		candidate_map.extend( [(obj, alias) for alias in obj.aliases.all()] )

	# check for exact matches first
	objlist = { obj for obj, name in candidate_map if name.lower().strip() == search_term.lower().strip() }
	if objlist or exact:
		objlist = list(objlist)
		return (objlist, '') if partial else objlist
	# to find the longest match, we start from the beginning and lengthen the 
	# match query one word at a time.
	bestmatches = []
	# preserve punctuation when splitting
	tail = re.split(r'(\W)', search_term)
	iend = 0
	rquery = r''
	for i, item in enumerate(tail):
		# don't add non-word characters to the search query
		if not item.isalpha():
			continue
		rquery += r"(\b" + re.escape(item) + "|" + re.escape(item) + r"\b).*"
		# match candidates against the current set of words
		matches = ((re.search(rquery, text, _RE_FLAGS), obj, text) for obj, text in candidate_map)
		matches = [(obj, match.group(), text) for match, obj, text in matches if match]
		if len(matches) == 0:
			# no matches at this length, keep previous iteration as best
			break
		# otherwise, since this is the longest match so far, set latest match set as best matches
		bestmatches = matches
		# save current index as end point of matched text
		iend = i

	objlist = list( { match[0] for match in bestmatches } )

	if partial:
		# recombine remainder of search back into a string
		tail = "".join(tail[iend+1:])
		return (objlist, tail)
	else:
		return objlist
