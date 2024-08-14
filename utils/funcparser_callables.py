from evennia.utils.verb_conjugation.conjugate import verb_tense, verb_present, verb_past
from evennia.utils.verb_conjugation.pronouns import pronoun_to_viewpoints
from evennia.utils import inherits_from, logger
from evennia.utils.funcparser import ParsingError

from utils.colors import strip_ansi
from switchboard import INFLECT

def _get_recv_account(receiver):
	"""
	Helper function to figure out if a receiving entity has, or is, an
	account, and returns either the account or None.
	"""
	if inherits_from(receiver, "evennia.accounts.accounts.DefaultAccount"):
		return receiver
	if getattr(receiver, "has_account", False):
		return receiver.account
	try:
		return receiver.get_account()
	except AttributeError:
		return None

def verb_actor_stance_components(verb, plural=False):
	"""
	Figure out actor stance components of a verb.
	Args:
		verb (str): The verb to analyze
		plural (bool): Whether to force 3rd person to plural form 
	Returns:
		tuple: The 2nd person (you) and 3rd person forms of the verb,
			in the same tense as the ingoing verb.
	"""
	tense = verb_tense(verb)
	them = "*" if plural else "3"
	them_suff = "" if plural else "s"
		
	if "participle" in tense or "plural" in tense:
		return (verb, verb)
	if tense == "infinitive" or "present" in tense:
		you_str = verb_present(verb, person="2") or verb
		them_str = verb_present(verb, person=them) or verb + them_suff
	else:
		you_str = verb_past(verb, person="2") or verb
		them_str = verb_past(verb, person=them) or verb + them_suff
	return (you_str, them_str)

def _colorize_text(message, style, receiver, **kwargs):
	"""
	Applies a style from the receiver's options to the input message
	"""
	if not (account := _get_recv_account(receiver)):
		return message
	# TODO: reimplement account color settings
	#	if not (color := account.gameoptions.get("colors", option=style)):
	color = style
	return "".join((color, message.replace('|n', color), '|n'))

def funcparser_color_hilight(*args, caller=None, receiver=None, **kwargs):
	"""
	Usage: $h(string)
	"""
	message = ", ".join(args)
	if not args or not receiver:
		return message
	style = "|y"
	# style = 'hilight'
	return _colorize_text(message, style, receiver, **kwargs)
	
def funcparser_color_header(*args, caller=None, receiver=None, **kwargs):
	"""
	Usage: $head(string)
	"""
	message = ", ".join(args)
	if not message or not receiver:
		return message
	style = "|w"
	# style = 'header'
	return _colorize_text(message, style, receiver, **kwargs)

def funcparser_color_footer(*args, caller=None, receiver=None, **kwargs):
	"""
	Usage: $foot(string)
	"""
	message = ", ".join(args)
	if not args or not receiver:
		return message
	style = "|X"
	# style = 'footer'
	return _colorize_text(message, style, receiver, **kwargs)

def funcparser_callable_article_plural_caps(*args, **kwargs):
	"""
	Adds a capital to the article
	"""
	return funcparser_callable_article_plural(*args, init_caps=True, **kwargs)
	
def funcparser_callable_article_plural(*args, **kwargs):
	"""
	Usage: $an(word, [number])
	
	Returns: (string) the parsed string
	"""
	if not args:
		return ""
	num = 1
	if len(args) > 1:
		try:
			num = int(args[1])
		except ValueError:
			pass
	
	if num > 1:
		prefix = INFLECT.number_to_words(num, threshold=12)
		word = INFLECT.plural(args[0])
		string = "{} {}".format(prefix, word)
	else:
		string = INFLECT.an(args[0])

	if kwargs.get("init_cap",False):
		string = string[0].upper() + string[1:]
	
	return string


def funcparser_pronoun_third_caps(*args, caller=None, **kwargs):
	return funcparser_pronoun_third(*args, caller=caller, capitalize=True, **kwargs)

def funcparser_pronoun_third(*args, caller=None, receiver=None, capitalize=False, **kwargs):
	pronoun = args[0]
	if not pronoun:
		return ""

	sub_dicts = {
		"they": {
				"male": "he", "female": "she", "neutral": "it",
			},
		"them": {
				"male": "him", "female": "her", "neutral": "it",
			},
		"their": {
				"male": "his", "female": "her", "neutral": "its",
			},
		"theirs": {
				"male": "his", "female": "hers", "neutral": "its",
			},
		"themself": {
				"male": "himself", "female": "herself", "neutral": "itself",
			},
		}

	if hasattr(caller, "gender"):
		if callable(caller.gender):
			gender = caller.gender()
		else:
			gender = caller.gender
	else:
		gender = "plural"
	
	if pronoun not in sub_dicts:
		for key, val in sub_dicts.items():
			if pronoun in val.values():
				pronoun = key
				break

	try:
		gendered = pronoun if gender == "plural" else sub_dicts[pronoun][gender]
	except KeyError:
		gendered = pronoun

	if capitalize:
		gendered = gendered.capitalize()

	return gendered

def funcparser_callable_conjugate(*args, caller=None, receiver=None, **kwargs):
	"""
	Usage: $pconj(word, [options])
	A gender-sensitive version of the built-in $conj()

		Keyword Args:
		caller (Object): The object who represents 'you' in the string.
		receiver (Object): The recipient of the string.
	Returns:
		str: The parsed string.
	Raises:
		ParsingError: If `you` and `recipient` were not both supplied.
	Notes:
		Note that the verb will not be capitalized. It also
		assumes that the active party (You) is the one performing the verb.
		This automatic conjugation will fail if the active part is another person
		than 'you'. The caller/receiver must be passed to the parser directly.
	Examples:
		This is often used in combination with the $pron/Pron() callables.
		- `With a grin, $pron(you) $pconj(jump)`
		You will see "With a grin, you jump."
		Others will see "With a grin, she jumps." OR "With a grin, they jump."

	"""
	if not args:
		return ""
	if not caller:
		raise ParsingError("No caller/receiver supplied to $pconj callable")

	if hasattr(caller, "gender"):
		if callable(caller.gender):
			plural = (caller.gender() == "plural")
		else:
			plural = (caller.gender == "plural")

	else:
		plural = False

	second_person_str, third_person_str = verb_actor_stance_components(args[0],plural=plural)
	return second_person_str if caller == receiver else third_person_str


FUNCPARSER_CALLABLES = {
	"pconj": funcparser_callable_conjugate,
	"an": funcparser_callable_article_plural,
	"An": funcparser_callable_article_plural_caps,
	"h": funcparser_color_hilight,
	"head": funcparser_color_header,
	"foot": funcparser_color_footer,
	"gp": funcparser_pronoun_third,
	"Gp": funcparser_pronoun_third_caps,
}
