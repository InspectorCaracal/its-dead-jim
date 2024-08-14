import re
import math
from django.conf import settings
from evennia.utils.utils import display_len, crop, dedent

from data import bands
from .colors import strip_ansi

from switchboard import INFLECT

re_dspace = re.compile(r'(?<=\S) {2,}')
re_gaplines = re.compile(r'\n{2,}')
re_empty = re.compile(r'\n\s*\n')
re_colorful = re.compile(r'\|.+?\|n')
re_articles = re.compile(r'^(a|an|and|the)(\s+)', re.IGNORECASE)
re_wraplines = re.compile(r'(?<!\n)(\n)(?!\s)')

_NUMBER_WORDS = {
	"one":		1,
	"two":		2,
	"three":	  3,
	"four":	   4,
	"five":	   5,
	"six":		6,
	"seven":	  7,
	"eight":	  8,
	"nine":	   9,
	"ten":	   10,
	"eleven":	11,
	"twelve":	12,
	"thirteen":  13,
	"fourteen":  14,
	"fifteen":   15,
	"sixteen":   16,
	"seventeen": 17,
	"eighteen":  18,
	"nineteen":  19,
	"twenty":	20,
	"thirty":	30,
	"forty":	 40,
	"fifty":	 50,
	"sixty":	 60,
	"seventy":   70,
	"eighty":	80,
	"ninety":	90,
	"hundred":  100,
	"thousand": 1000,
	"million":  1000000,
	"billion":  1000000000,
	"trillion": 1000000000000,
}

def isare(count):
	return "is" if count == 1 else "are"


def strip_extra_spaces(text):
	text = re_dspace.sub(" ",text).strip()
	text = re_empty.sub("\n\n",text)
	text = re_gaplines.sub("\n\n",text)
	return text


def numbered_name(name, count, pair=False, pluralize=True, cap=False, prefix=True):
	name = re_articles.sub('', name)
	colorlist = re_colorful.findall(name)
	colorkeys = {}
	for colorword in colorlist:
		index = strip_ansi(colorword)+'@'
		colorkeys[index] = colorword
		name = name.replace(colorword, index)
	if count == 1 and prefix:
		name = INFLECT.an(name)
	else:
		if not count:
			num = "no"
		elif pair and count == 2 and not name.startswith("pair of"):
			num = "a pair of"
		else:
			num = INFLECT.number_to_words(count)
		if pluralize:
			name = INFLECT.plural_noun(name) or name
		if prefix:
			name = f"{num} {name}"

	if cap:
		name = name[0].upper() + name[1:]

	for index, colorword in colorkeys.items():
		name = name.replace(index, colorword)

	return name


def str_to_int(number):
	number = str(number)
	try:
		return int(number)
	except:
		pass

	if number in _NUMBER_WORDS:
		return _NUMBER_WORDS[number]

	# convert sound changes for generic ordinal numbers
	if number[-2:] == "th":
		# remove "th"
		number = number[:-2]
		if number[-1] == "f":
			# e.g. twelfth, fifth
			number = number[:-1] + "ve"
		elif number[-2:] == "ie":
			# e.g. twentieth, fortieth
			number = number[:-2] + "y"
		# custom case for ninth
		elif number[-3:] == "nin":
			number += "e"


	number = number.replace(" and "," ")
	# split number words by spaces, hyphens and commas, to accommodate multiple styles
	numbers = [ word.lower() for word in re.split(r'[-\s\,]',number) if word ]
	sums = []
	for word in numbers:
		# check if it's a known number-word
		if i := _NUMBER_WORDS.get(word):
			if not len(sums):
				# initialize the list with the current value
				sums = [i]
			else:
				# if the previous number was smaller, it's a multiplier
				# e.g. the "two" in "two hundred"
				if sums[-1] < i:
					sums[-1] = sums[-1]*i
				# otherwise, it's added on, like the "five" in "twenty five"
				else:
					sums.append(i)
		else:
			# invalid number-word, return None to error
			return None
	return sum(sums)


def justify(text, width=None, align="l", indent=0, fillchar=" "):
	"""
	Fully justify a text so that it fits inside `width`. When using
	full justification (default) this will be done by padding between
	words with extra whitespace where necessary. Paragraphs will
	be retained.
	Args:
		text (str): Text to justify.
		width (int, optional): The length of each line, in characters.
		align (str, optional): The alignment, 'l', 'c', 'r', 'f' or 'a'
			for left, center, right, full justification. The 'a' stands for
			'absolute' and means the text will be returned unmodified.
		indent (int, optional): Number of characters indentation of
			entire justified text block.
		fillchar (str): The character to use to fill. Defaults to empty space.
	Returns:
		justified (str): The justified and indented block of text.
	"""
	lb = "\n"

	def _process_line(line):
		"""
		helper function that distributes extra spaces between words. The number
		of gaps is nwords - 1 but must be at least 1 for single-word lines. We
		distribute odd spaces to one of the gaps.
		"""
		line_rest = width - (wlen + ngaps)

		gap = " "

		if line_rest > 0:
			if align == "l":
				if line[-1] == "\n\n":
					line[-1] = sp * (line_rest - 1) + "\n" + sp * width + "\n" + sp * width
				else:
					line[-1] += sp * line_rest
			elif align == "r":
				line[0] = sp * line_rest + line[0]
			elif align == "c":
				pad = sp * (line_rest // 2)
				line[0] = pad + line[0]
				if line[-1] == "\n\n":
					line[-1] += (
						pad + sp * (line_rest % 2 - 1) + "\n" + sp * width + "\n" + sp * width
					)
				else:
					line[-1] = line[-1] + pad + sp * (line_rest % 2)
			else:  # align 'f'
				gap += sp * (line_rest // max(1, ngaps))
				rest_gap = line_rest % max(1, ngaps)
				for i in range(rest_gap):
					line[i] += sp
		elif not any(line):
			return [sp * width]
		return gap.join(line)

	width = width if width is not None else settings.CLIENT_DEFAULT_WIDTH
	sp = fillchar

	if align == "a":
		# absolute mode - just crop or fill to width
		abs_lines = []
		for line in text.split("\n"):
			nlen = display_len(line)
			if display_len(line) < width:
				line += sp * (width - nlen)
			else:
				line = crop(line, width=width, suffix="")
			abs_lines.append(line)
		return lb.join(abs_lines)

	# all other aligns requires splitting into paragraphs and words

	# split into paragraphs and words
	paragraphs = text.split("\n")  # re.split("\n\s*?\n", text, re.MULTILINE)
	words = []
	for ip, paragraph in enumerate(paragraphs):
		if ip > 0:
			words.append((lb, 0))
		words.extend((word, display_len(word)) for word in paragraph.split())

	if not words:
		# Just whitespace!
		return sp * width

	ngaps = 0
	wlen = 0
	line = []
	lines = []

	while words:
		if not line:
			# start a new line
			word = words.pop(0)
			wlen = word[1]
			line.append(word[0])
		elif (words[0][1] + wlen + ngaps) >= width:
			# next word would exceed word length of line + smallest gaps
			lines.append(_process_line(line))
			ngaps, wlen, line = 0, 0, []
		else:
			# put a new word on the line
			word = words.pop(0)
			line.append(word[0])
			if word[1] == 0:
				# a new paragraph, process immediately
				lines.append(_process_line(line))
				ngaps, wlen, line = 0, 0, []
			else:
				wlen += word[1]
				ngaps += 1

	if line:  # catch any line left behind
		lines.append(_process_line(line))
	indentstring = sp * indent
	return lb.join([indentstring + line for line in lines])


def get_band(band_type, percent, invert=False):
	"""
	Maps a percentage (as an int 0-100) to a value in a given list
	of values.

	The first entry in the list is one to display if percent is 0.
	The following values form a linear spectrum of values to display
	across the remaining 1-100 range.

	For example, if there are 5 values in a list, the first one is
	displayed if the percentage is 0, the second if the percentage
	is 1-25, the third if the percentage is 26-50, etc.

	This default behavior is ideal for vitals where 100% is the ideal
	state, like health. For banded values where 0% is the ideal state,
	you can set the invert option to maintain a similar behavior.

	Args:
		list (list): The list of strings to choose from.
		percent (int): A value from 0-100, where 0% is the ideal state.
		invert (bool): True to flip the value range and consider 100% the
			ideal state instead.
	"""
	band_label = f"{band_type.upper()}_BANDS"
	if not (band_list := getattr(bands, band_label, None)):
		band_list = bands.DEFAULT_BANDS
	percent = min(max(percent, 0), 100)
	divisions = len(band_list) - 1
	if invert:
		percent = 100 - percent
	# mathfunc = math.floor if invert else math.ceil
	# band = mathfunc(percent / (100 / divisions))
	band = math.ceil(percent / (100 / divisions))
	return band_list[band]

def unwrap_paragraphs(text):
	text = dedent(text)
	paras = [ re_wraplines.sub(' ', line).strip() for line in re_gaplines.split(text) ]
	return "\n\n".join(paras)