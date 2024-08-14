#from django.conf import settings
#from evennia.utils import logger

import re
from html import escape as html_escape
from math import ceil

from evennia.utils.ansi import strip_ansi as core_strip_ansi

from data.colors import COLOR_DATA

_RE_HEX = re.compile(r'\|#([0-9a-f]{6})', re.I)
_RE_HEX_BG = re.compile(r'\|\[#([0-9a-f]{6})', re.I)
_RE_XTERM = re.compile(r'\|([0-5][0-5][0-5]|\=[a-z])')
_RE_XTERM_BG = re.compile(r'\|\[([0-5][0-5][0-5]|\=[a-z])')
_GREYS = "abcdefghijklmnopqrstuvwxyz"
# "ansi" styles and hex
_RE_STYLES = re.compile(r'\|\[?([rRgGbBcCyYwWxXmMu\*\>\_n]|#[0-9a-f]{6})')

_RE_MXPLINK = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
_RE_MXPURL = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)
_RE_LINE = re.compile(r'^(-+|_+)$', re.MULTILINE)

_INDENT = 4

_ANSI_COLOR_MAP = {
	'r': 'red1', 'R': 'red2',
	'y': 'yellow1', 'Y': 'yellow2',
	'g': 'green1', 'G': 'green2',
	'c': 'cyan1', 'C': 'cyan2',
	'b': 'blue1', 'B': 'blue2',
	'm': 'magenta1', 'M': 'magenta2',
	'w': 'hi-text', 'W': 'low-text',
	'x': 'hi-bg', 'X': 'low-bg',
}

# strip all format flags including hex ones

def strip_ansi(message):
	message = message.replace("|tbs","").replace("|tbe","")
	message = core_strip_ansi(message)
	message = _RE_HEX.sub("", message)
	message = _RE_HEX_BG.sub("", message)
	return message

# translate hex tags to XTERM tags
def hex_to_xterm(message):
	"""
	Converts all hex tags to xterm-format tags.
	
	Args:
		message (str): the text to parse for tags

	Returns:
		str: the text with converted tags
	"""
	def split_hex(text):
		return ( int(text[i:i+2],16) for i in range(0,6,2) )
		
	def grey_int(num):
		return round( max((num-8),0)/10 )

	def hue_int(num):
		return round(max((num-45),0)/40)
	
	
	for match in reversed(list(_RE_HEX.finditer(message))):
		start, end = match.span()
		tag = match.group(1)
		r, g, b = split_hex(tag)

		if r == g and g == b:
			# greyscale
			i = grey_int(r)
			message = message[:start] + "|=" + _GREYS[i] + message[end:]
		
		else:
			xtag = "|{}{}{}".format( hue_int(r), hue_int(g), hue_int(b) )
			message = message[:start] + xtag + message[end:]

	for match in reversed(list(_RE_HEX_BG.finditer(message))):
		start, end = match.span()
		tag = match.group(1)
		r, g, b = split_hex(tag)

		if r == g and g == b:
			# greyscale
			i = grey_int(r)
			message = message[:start] + "|[=" + _GREYS[i] + message[end:]
		
		else:
			xtag = "|[{}{}{}".format( hue_int(r), hue_int(g), hue_int(b) )
			message = message[:start] + xtag + message[end:]

	return message

def xterm_to_hex(message):

	def hue_hex(text):
		return format( int(text)*40+25 ,'02x')
	
	def grey_hex(text):
		return format( _GREYS.index(text)*10+8 ,'02x')
	
	for match in reversed(list(_RE_XTERM.finditer(message))):
		start, end = match.span()
		tag = match.group(1)
		if tag[0] == '=':
			# greyscale
			hex = grey_hex(tag[1])
			message = message[:start] + "|#" + hex*3 + message[end:]

		else:
			r, g, b = tag
			htag = "|#{}{}{}".format( hue_hex(r), hue_hex(g), hue_hex(b) )
			message = message[:start] + htag + message[end:]

	for match in reversed(list(_RE_XTERM_BG.finditer(message))):
		start, end = match.span()
		tag = match.group(1)
		if tag[0] == '=':
			# greyscale
			hex = grey_hex(tag[1])
			message = message[:start] + "|[#" + hex*3 + message[end:]

		else:
			r, g, b = tag
			htag = "|[#{}{}{}".format( hue_hex(r), hue_hex(g), hue_hex(b) )
			message = message[:start] + htag + message[end:]

	return message

def rgb_to_hex(rgb):
	"""
	Converts a three-int RGB tuple to a hex string.
	"""
	hstr = "#"
	for p in rgb:
		hstr += format(int(p),'02x')
	return hstr

def hex_to_rgb(hex):
	"""
	Converts a three-int RGB tuple to a hex string.
	"""
	if hex.startswith('#'):
		hex = hex[1:]
	r = int(hex[:2],  16)
	g = int(hex[2:4], 16)
	b = int(hex[4:],  16)
	return (r,g,b)
	hstr = "#"

def ev_to_html(message):
	"""
	Parses evennia style tags into html
	Args:
		text (str): The string to process.
	Returns:
		text (str): Processed text.
	"""

	def sub_mxp_links(match):
		"""
		Helper method to be passed to re.sub,
		replaces MXP links with HTML code.
		"""
		cmd, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
		val = rf'<span class="mxplink" data-command="{cmd}">{text}</span>'
		return val

	def sub_mxp_urls(match):
		"""
		Helper method to be passed to re.sub,
		replaces MXP links with HTML code.
		"""
		url, text = [grp.replace('"', "\\&quot;") for grp in match.groups()]
		val = rf'<a href="{url}" target="_blank">{text}</a>'
		return val	

	message = message.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')
	message = _RE_MXPLINK.sub(sub_mxp_links, message)
	message = _RE_MXPURL.sub(sub_mxp_urls, message)
	message = message.replace("|tbs", "<pre>").replace("|tbe", "</pre>")
	message = xterm_to_hex(message)
	# escape escaped pipes
	message = message.replace("||","&#124;").replace("|/","\n")
	# replace ---- with hr element
	message = _RE_LINE.sub("<hr/>",message)
	message = message.replace("<hr/>\n","<hr/>")

	# split out the ANSI codes and clean out any empty items
	str_list = [substr for substr in message.split("|") if substr]
	output = []
	# initialize all the flags and classes
	color = ""
	bgcolor = ""
	classes = set()
	clean = True
	inverse = False

	# special handling in case the first item is formatted
	if not message.startswith("|"):
		output.append(str_list[0])
		str_list = str_list[1:]

	for substr in str_list:
		# it's a background color
		if substr.startswith('['):
			if substr[1] == '#':
				# hex color, use as-is
				bgcolor = substr[1:8]
				substr = substr[8:]
			elif ccode := _ANSI_COLOR_MAP.get(substr[1]):
				bgcolor = f"var(--{ccode})"
				substr = substr[2:]
		# check color codes
		elif substr.startswith('#'):
			# hex color, use as-is
			color = substr[:7]
			substr = substr[7:]
		elif ccode := _ANSI_COLOR_MAP.get(substr[0]):
			color = f"var(--{ccode})"
			substr = substr[1:]
		
		# check style codes
		elif substr[0] == "u":
			classes.add("underline")
			substr = substr[1:]
		elif substr[0] in ">-":
			output.append(" " * _INDENT)
			output.append(substr[1:])
			continue
		elif substr[0] == "_":
			output.append(" ")
			output.append(substr[1:])
			continue
		elif substr[0] == "*":
			inverse = True
			substr = substr[1:]

		# check if it's a reset
		elif substr.startswith('n'):
			if not clean:
				color = ""
				bgcolor = ""
				classes = set()
				clean = True
				inverse = False
				output.append("</span>")
			output.append(substr[1:])
			continue

		# it didn't match any codes, just add the pipe back in and keep going
		else:
			output.append("|"+substr)
			continue

		# add the styling
		if not clean:
			output.append("</span>")

		new_span = "<span"
		# stop! colortime
		if color or bgcolor:
			# special handling to invert colors
			if inverse:
				if not bgcolor:
					style = f'style="color: inherit;background-color: {color}"'
				elif not color:
					style = f'style="color: {bgcolor}"'
				else:
					style = f'style="color: {bgcolor};background-color: {color}"'
			else:
			# normal coloring
				style = 'style="'
				if color:
					style += f"color: {color};"
				if bgcolor:
					style += f"background-color: {bgcolor}"
				style += '"'
			new_span += " " + style
		
		# add classes
		if len(classes):
			class_str = 'class="{}"'.format( " ".join(list(classes)) )
			new_span += " " + class_str
		
		new_span += ">"
		output.append(new_span)
		clean=False
		output.append(substr)

	return "".join(output)

def add_colors(rgbA, rgbB):
	# adds one color to another already-colored thing
	pigmentA = (255-rgbA[0], 255-rgbA[1], 255-rgbA[2])
	pigmentB = (255-rgbB[0], 255-rgbB[1], 255-rgbB[2])
	
	cyan = round( max( (pigmentA[0]+pigmentB[0])/2, pigmentA[0] ) )
	mag  = round( max( (pigmentA[1]+pigmentB[1])/2, pigmentA[1] ) )
	yel  = round( max( (pigmentA[2]+pigmentB[2])/2, pigmentA[2] ) )

	return (255-cyan, 255-mag, 255-yel)

def blend_colors(rgbA, rgbB, numfirst=1, numsecond=1):
	# mixes two sets of pigments
	pigmentA = (255-rgbA[0], 255-rgbA[1], 255-rgbA[2])
	pigmentB = (255-rgbB[0], 255-rgbB[1], 255-rgbB[2])
	
	cyan = round( (pigmentA[0]*numfirst + pigmentB[0]*numsecond)/(numfirst+numsecond) )
	mag  = round( (pigmentA[1]*numfirst + pigmentB[1]*numsecond)/(numfirst+numsecond) )
	yel  = round( (pigmentA[2]*numfirst + pigmentB[2]*numsecond)/(numfirst+numsecond) )
	
	return (255-cyan, 255-mag, 255-yel)

def get_name_from_rgb(rgb, styled=False):
	key = None
	diff = sum(rgb)
	for comp in COLOR_DATA.keys():
		diffs = ( abs(comp[i]-rgb[i]) for i in range(3) )
		max_diff = max(diffs)
		if max_diff < diff:
			key = comp
			diff = max_diff
	
	if result := COLOR_DATA.get(key, None):
		if styled:
			hex = rgb_to_hex(rgb)
			return f"|{hex}{result}|n"
		else:
			return result
	# no match
	return None
