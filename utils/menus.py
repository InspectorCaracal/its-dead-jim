from math import ceil
from inspect import getfullargspec, getmembers

from evennia.commands.cmdset import CmdSet
from evennia.utils.utils import m_len, display_len, mod_import, variable_from_module
from evennia.utils import logger
from evennia.utils.evmenu import EvMenu, CmdEvMenuNode
from evennia.utils.funcparser import FuncParser, ACTOR_STANCE_CALLABLES

from utils.funcparser_callables import FUNCPARSER_CALLABLES as LOCAL_FUNCPARSER_CALLABLES
parser = FuncParser(ACTOR_STANCE_CALLABLES | LOCAL_FUNCPARSER_CALLABLES)

from django.conf import settings
_MAX_TEXT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

from utils.colors import strip_ansi
from utils import table

class EvMenuCmdSet(CmdSet):
	"""
	The Menu cmdset replaces the current cmdset.

	"""

	key = "menu_cmdset"
	priority = 1
	mergetype = "Replace"
	no_objs = True
	no_exits = True
	no_channels = False
	menu = None

	def at_cmdset_creation(self):
		"""
		Called when creating the set.
		"""
		cmd = CmdEvMenuNode()
		if self.menu:
			cmd._update_aliases(self.menu)
		self.add(cmd)

class FormatEvMenu(EvMenu):
	"""
	Adds funcparser to evmenu formatting
	"""
	node_border_char = ''

	def __init__(self, *args, **kwargs):
		startnode_input = kwargs.get('startnode_input', '')
		if type(startnode_input) is str:
			startnode_kwargs = {}
		else:
			startnode_input, startnode_kwargs = startnode_input
		
		startnode_kwargs['start'] = True
		kwargs['startnode_input'] = (startnode_input, startnode_kwargs,)
		super().__init__(*args, **kwargs)
			
	def _parse_menudata(self, menudata):
		if isinstance(menudata, dict):
			# This is assumed to be a pre-loaded menu tree.
			return menudata
		elif type(menudata) is str:
			# a python path of a module or class
	 		# TODO: find a way to implement this that doesn't create error logs
			menu = mod_import(menudata)
			if not menu:
				try:
					menu_module, menu_class = menudata.rsplit('.', maxsplit=1)
				except: # TODO: find right exception for this
					# it's busted
					raise ValueError(f"Invalid menu path '{menudata}'")
				menu = variable_from_module(menu_module, variable=menu_class)
			if callable(menu):
				menu = menu()
		else:
			# we assume it's already a loaded module or class
			menu = menudata

		# check if the menu has its own custom tree definition
		if menutree := getattr(menu, '_menutree',None):
			if callable(menutree):
				return menutree()
			else:
				return menutree
		return {
			key: func
			for key, func in getmembers(menu)
			if callable(func) and not key.startswith("_")
		}

	def nodetext_formatter(self, nodetext):
		string = parser.parse(nodetext, caller=self.caller, receiver=self.caller)
		return super().nodetext_formatter(string)
	
	def helptext_formatter(self, helptext):
		string = parser.parse(helptext, caller=self.caller, receiver=self.caller)
		return super().helptext_formatter(string)
	
	def options_formatter(self, optionlist):
		"""
		Formats the option block.

		Args:
			optionlist (list): List of (key, description) tuples for every
				option related to this node.

		Returns:
			options (str): The formatted option display.

		"""
		if not optionlist:
			return ""

		# column separation distance
		colsep = 4

		nlist = len(optionlist)

		# get the widest option line in the table.
		table_width_max = -1
		row_list = []
		for key, desc in optionlist:
			if desc:
				desc_string = parser.parse(f": {desc}", caller=self.caller, receiver=self.caller)
			else:
				desc_string = ""
			if key or desc:
				table_width_max = max(
					table_width_max,
					(max(len(strip_ansi(p)) for p in key.split("\n"))
					+ max(len(strip_ansi(p)) for p in desc_string.split("\n"))
					+ colsep),
				)
				raw_key = strip_ansi(key)
				if raw_key != key:
					# already decorations in key definition
					item = f" |lc{raw_key}|lt{key} {desc_string}|le"
				else:
					# add a default white color to key
					item = f" |lc{raw_key}|lt|w{key}|n {desc_string}|le"
				table_width_max = max(table_width_max, len(strip_ansi(item)))
				row_list.append(item)
		ncols = _MAX_TEXT_WIDTH // table_width_max	# number of ncols

		if ncols < 0:
			# no visible option at all
			return ""

		ncols = max(1, ncols)

		# minimum number of rows in a column
		min_rows = 4

		# split the items into columns
		split = max(min_rows, ceil(len(row_list)/ncols))
		max_end = len(row_list)
		cols_list = []
		for icol in range(ncols):
			start = icol*split
			end = min(start+split,max_end)
			cols_list.append(row_list[start:end])

		# return str(table.EvTable(table=cols_list, border="none"))

		# get display width for each column
		col_widths = [max([len(strip_ansi(row)) for row in col])+4 for col in cols_list if col]
		# initialist list of rowstrings to blank strings
		rows_list = ['']*max([len(col) for col in cols_list])

		# append each column to the rows, with padding
		for i, col in enumerate(cols_list):
			for j, row in enumerate(col):
				rows_list[j] += row
				if i < len(cols_list):
					# add spaces for padding the next column
					rows_list[j] += " "*(col_widths[i] - len(strip_ansi(row)))

		return "|tbs" + "\n".join(rows_list) + "|tbe"

	def node_formatter(self, nodetext, optionstext):
		"""
		Formats the entirety of the node.
		Args:
			nodetext (str): The node text as returned by `self.nodetext_formatter`.
			optionstext (str): The options display as returned by `self.options_formatter`.
			caller (Object, Account or None, optional): The caller of the node.
		Returns:
			node (str): The formatted node to display.
		"""
		sep = self.node_border_char

		if self._session:
			screen_width = self._session.protocol_flags.get("SCREENWIDTH", {0: _MAX_TEXT_WIDTH})[0]
		else:
			screen_width = _MAX_TEXT_WIDTH

		nodetext_width_max = max(display_len(line) for line in nodetext.split("\n"))
		options_width_max = max(display_len(line) for line in optionstext.split("\n"))
		total_width = min(screen_width, max(options_width_max, nodetext_width_max))
		separator1 = (sep * total_width + "\n") if nodetext_width_max else ""
		separator2 = "\n" + sep * total_width + "\n"
		return separator1 + "|n" + nodetext + "|n" + separator2 + "|n" + optionstext


class MenuTree(object):
	_node_format = "$head({header})\n\n{text}\n\n$foot({footer})"

	def _menutree(self):
		return {
			key: (lambda c, *x, func=value, **y: self._node_wrapper(func, c, *x, **y)) 
			if not key.startswith("_") else value for key, value in getmembers(self)
		}

	def _pre_menu(self, caller, *args, **kwargs):
		"""
		Runs before the very first menu node is run.
		"""
		self.menu = caller.ndb._evmenu


	def _pre_node_process(self, *args, **kwargs):
		"""
		Runs before a node function is executed with the same args and kwargs.
		This allows you to update or set any class properties to access within the node. 
		"""

	def _post_node_process(self, *args, **kwargs):
		"""
		Runs after a node function is executed with the same args and kwargs.
		This occurs after the header, footer, and additional options are applied.
		"""

	def _post_menu(self, *args, **kwargs):
		"""
		Runs after an "end node" i.e. one that has no options, to do any end-of-menu logic.

		NOTE: This does NOT trigger when using `quit` to exit!
		"""

	def _node_wrapper(self, func, *args, **kwargs):
		"""Wrap menu nodes in extra functions to avoid boilerplate"""
		if not callable(func):
			# should raise an actual menu error here
			raise ValueError("menutree used an invalid node name")

		# add dummy raw string
		if len(args) == 1:
			args = list(args)
			args.append('')

		# optional running of an initial hook
		# not the best implementation, but it works okay
		if kwargs.get('start'):
			kwargs.pop('start')
			self._pre_menu(*args, **kwargs)

		self._pre_node_process(*args, **kwargs)
		if res := func(*args, **kwargs):
			text_and_help, *options = res

			# append headers/footers to node text
			header = getattr(self, '_header', '')
			if callable(header):
				header = header(*args, **kwargs)
			footer = getattr(self, '_footer', '')
			if callable(footer):
				footer = footer(*args, **kwargs)
			if type(text_and_help) is str:
				text_and_help = self._node_format.format(header=header, footer=footer, text=text_and_help)
			else:
				text, *helptext = text_and_help
				text = self._node_format.format(header=header, footer=footer, text=text)
				text_and_help = tuple(text, *helptext)

			# append header/footer options to option text
			firsts = getattr(self, '_prefix_options', [])
			if callable(firsts):
				firsts = firsts(*args, **kwargs)
			lasts = getattr(self, '_suffix_options', [])
			if callable(lasts):
				lasts = lasts(*args, **kwargs)

			options = options[0] if len(options) else None
			if options:
				# only auto-add options if there is at least one - otherwise we will never have an end node
				if type(options) is dict:
					options = [options]
				else:
					options = list(options)
				options = firsts + options + lasts

		else:
			text_and_help = ''
			options = []

		self._post_node_process(*args, **kwargs)

		if not options:
			# if no options, it's a final node - do any final cleanup
			self._post_menu(*args, **kwargs)

		return text_and_help, options