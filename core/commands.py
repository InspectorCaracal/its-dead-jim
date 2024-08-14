"""
Commands

Commands describe the input the account can do to the game.

"""
import math
import time

from evennia.commands.command import Command as BaseCommand
from evennia.utils import logger, str2int, iter_to_str
from utils.table import EvTable
from utils.strmanip import INFLECT, unwrap_paragraphs

class Command(BaseCommand):
	"""
	Base command (you may see this if a child command had no help text defined)

	Note that the class's `__doc__` string is used by Evennia to create the
	automatic help entry for the command, so make sure to document consistently
	here. Without setting one, the parent's docstring will show (like now).

	"""
	free = False
	log = None
	disambiguator = 0
	prefixes=[]
	splitters = []
	err_msg = "Something went wrong...."
	nofound_msg = "You can't find {sterm}."
	search_range = 0

	def get_help(self, caller, cmdset):
		return unwrap_paragraphs(self.__doc__)

	def parse(self):
		super().parse()
		self.args = self.args.strip()
		self.argsdict = {}
		self.argslist = []

		def _split_me(tosplit, i):
			if not self.splitters:
				return [tosplit] if tosplit else []
			if i < len(self.splitters):
				return [ _split_me(item.strip(), i+1) for item in tosplit.split(self.splitters[i]) if item ]
			return tosplit

		if self.prefixes:		
			# first we identify prefixes and sort by order
			prefixes = [ (f" {pref} ", self.args.find(f" {pref} ")) for pref in self.prefixes ]
			# we want to go from the last one first
			prefixes.sort(key=lambda x:x[1], reverse=True)
			# now we chop up the args
			argdict = {}
			args = self.args

			for pref, n in prefixes:
				if n == -1:
					# we walked backwards so this means this and any additional prefixes weren't found
					break
				args, prefixed = args.split(pref, maxsplit=1)
				argdict[pref.strip()] = _split_me(prefixed, 0)

			argdict[None] = _split_me(args, 0)
			self.argsdict = argdict

		elif self.splitters:
			# just do the splitting
			self.argslist = _split_me(self.args, 0)

		# otherwise we'll only have the plain args so nothing else is needed

	def at_pre_cmd(self, **kwargs):
		"""
		Remember, returning TRUE means CANCEL
		"""
		if self.caller == self.account:
			return super().at_pre_cmd(**kwargs)
		self.caller.ndb.last_active = time.time()
		if self.caller.ndb.afk:
			self.caller.at_post_afk()
		if self.caller.tags.has("unconscious", category="status"):
			# make this draw randomly from a list
			self.caller.msg("You are blissfully unconscious.")
			return True
		if self.caller.tags.has("dead", category="status"):
			# make this draw randomly from a list
			self.caller.msg("You are a corpse.")
			return True
		if self.free:
			return False
		if text := self.caller.actions.status():
			if not getattr(self, 'action_override', False):
				self.caller.msg(text)
				return True

	def at_post_cmd(self, **kwargs):
		if self.log:
			# this command should log all uses
			fname = f"{self.log}.log"
			msg = f"Command entered by {self.caller} ({self.caller.id}): {self.raw_string}"
			logger.log_file(msg, filename=fname)

	#	def check_multimatch(self, search_term, candidates, **kwargs):

	def _filter_targets(self, targets: list, **kwargs):
		"""
		Filters out de-prioritized targets from the search results.

		Since different commands have different ideas of valid targets, this is split out
		to be more easily customized.
		"""
		return targets

	def _filter_candidates(self, candidates: list, **kwargs):
		"""
		Filters out invalid candidates from the search candidates.

		Since different commands have different ideas of valid targets, this is split out
		to be more easily customized.
		"""
		return candidates

	def _do_search(self, search_term: str, candidates: list, location, tail: bool, filter=None, **kwargs):
		tail_str = ''
		# FIXME: the kwargs for this are inconsistent, we need to refactor
		if filter:
			filter_cands = filter
		else:
			filter_cands = kwargs.get('filter_cands', self._filter_candidates)
		if tail:
			obj_list, tail_str = self.caller.search(search_term, candidates=candidates, location=location, quiet=True, partial=True, filter=filter_cands, **kwargs)
			if not search_term.endswith(tail_str):
				# PICNIC
				i = len(search_term) - len(tail_str)
				start = search_term.rfind(' ',0,i)
				tail_str = search_term[start:]
		else:
			obj_list = self.caller.search(search_term, candidates=candidates, location=location, quiet=True, filter=filter_cands, **kwargs)

		return (obj_list, tail_str)
	
	def _handle_result(self, obj_list: list, search_term: str, num: int, stack: bool, find_none: bool, **kwargs):
		"""Parse down the result object list to the right amount, or handle no-match"""
		if obj_list and not num:
			# return all matching objects
			return obj_list
		elif not obj_list or (not num or num > len(obj_list)):
			if find_none:
				return None
			else:
				errmsg = kwargs.get('nofound', self.nofound_msg)
				self.caller.msg(errmsg.format(sterm=f"$h({search_term})"))
				return False
		elif num == 1:
			if disambig := kwargs.get("disambiguator"):
				obj_list = self._collapse_ordinal(obj_list, disambig)
			elif stack:
				obj_list = self._collapse_stacks(obj_list)
			if len(obj_list) > 1:
				self.multimatch_msg(search_term, obj_list)
				index = yield("Enter a number (or $h(c) to cancel):")
				obj = self.process_multimatch(index, obj_list)
				if obj:
					obj_list = [obj]
				else:
					return False
		else:
			obj_list = obj_list[:num]
		
		return obj_list

	def find_targets(self, search_term: str, candidates: list=None, location=None,
		               numbered: bool=True, stack: bool=True, tail: bool=False, find_none: bool=False, **kwargs):
		"""
		Takes a target, possibly including a quantity, and returns
		a list of objects that match.
		"""
		if not search_term:
			return None if not tail else (None, '')
		tail_str = ''
		if search_term.lower().startswith('my '):
			search_term = search_term[3:]
			location = self.caller
		if numbered:
			num, name = self._parse_num(search_term)
		else:
			num = 1
			name = search_term

		kwargs['distance'] = kwargs.get('distance', self.search_range)

		# let's just implement the parts parsing here
		# TODO: we need to add back 'a of b' syntax at some point
		splitit = name.split("'s", maxsplit=1)
		if len(splitit) == 2:
			if splitit[0][-1].isalpha():
				obj_list, _ = self._do_search(splitit[0], candidates, location, False, **kwargs)
				# self.caller.search(splitit[0], candidates=candidates, location=location, quiet=True, partial=False)
				obj_list = yield from self._handle_result(obj_list, splitit[0], 1, False, False)
				# override kwargs to use this object as location, no candidates, and stacked
				if obj_list:
					location = obj_list[0]
					stack = True
					candidates = None
					name = splitit[1]
		obj_list, tail_str = self._do_search(name, candidates, location, tail, **kwargs)

		if len(obj_list) > 1:
			if custom_filter := kwargs.get('filter'):
				filtered = custom_filter(obj_list)
			else:
				filtered = self._filter_targets(obj_list)
			if filtered:
				obj_list = filtered

		obj_list = yield from self._handle_result(obj_list, name, num, stack, find_none, disambiguator=self.disambiguator, **kwargs)
		if not obj_list:
			return (obj_list, tail_str) if tail else obj_list

		result = obj_list[0] if (not numbered and obj_list) else obj_list
		return (result, tail_str) if tail else result


	def _collapse_stacks(self, obj_list: list):
		caller = self.caller
		obj_dict = {}
		for obj in obj_list:
			if obj.baseobj != obj:
				# stack based on parts instead of name
				obname = iter_to_str(sorted(obj.tags.get(category='part', return_list=True)))
			else:
				obname = obj.get_display_name(caller, noid=True)
			obname += obj.get_extra_info(caller)
			if obname in obj_dict:
				continue
			else:
				obj_dict[obname] = obj
		return list(obj_dict.values())

	def _collapse_ordinal(self, obj_list: list, position: int):
		"""
		return list of positionth items for each stack
		"""
		caller = self.caller
		obj_dict = {}
		return_list = []
		for obj in obj_list:
			name = "{}{}".format(obj.get_display_name(caller, noid=True), obj.get_extra_info(caller))
			if name in obj_dict:
				obj_dict[name].append(obj)
			else:
				obj_dict[name] = [obj]
		for key, objs in obj_dict.items():
			if len(objs) >= position:
				return_list.append(objs[position - 1])
		return return_list

	def _parse_num(self, search_term: str, **kwargs):
		split = search_term.split(' ', maxsplit=1)
		if len(split) <= 1:
			# it's not a number, use base search_term instead
			if single := INFLECT.singular_noun(search_term):
				return (None, single)
			else:
				# already singular
				return (1, search_term)

		num, name = split
		if num in ("all", "some"):
			num = None
		elif num in ('a', 'an', 'the'):
			num = 1
		else:
			# convert num to an integer
			try:
				num = str2int(num)
			except ValueError:
				# it's not a number, use base search_term instead
				if single := INFLECT.singular_noun(search_term):
					return (None, single)
				else:
					# already singular
					return (1, search_term)

		# we now have num and name - check plurality of name
		single = INFLECT.singular_noun(name)
		# this doesn't reliably work - i need to add a different method
		# if not single:
		# # the input was already singular
		# self.disambiguator = num
		# num = 1
		return (num, name) if not single else (num, single)

	def multimatch_msg(self, target, lst, match_cmd=False):
		match_opts = []
		for i, obj in enumerate(lst):
			if match_cmd:
				obj, name = obj
			elif hasattr(obj, 'name'):
				name = obj.name
			else:
				name = str(obj)

			string = " |lc{index}|lt{index} {name}|le{extra}".format(
				index=i + 1,
				name=obj.get_display_name(self.caller, link=False) if hasattr(obj, "get_display_name") else name,
				extra=obj.get_extra_info(self.caller) if hasattr(obj, "get_extra_info") else '',
			)
			match_opts.append(string)
		self.msg("Which $h({target}) do you mean?\n{options}".format(target=target, options="\n".join(match_opts)))

	def cmd_multimatch_msg(self, target, lst):
		"""deprecated"""
		self.multimatch_msg(target, lst, match_cmd=True)

	def process_multimatch(self, option, lst, free_text=False):
		if option.lower().strip() == 'c':
			self.msg("Action cancelled.")
			return None
		try:
			option = int(option)
		except ValueError:
			if free_text:
				return str(option)
			else:
				option = -1

		if 0 < option <= len(lst):
			return lst[option - 1]
		elif free_text:
			return str(option)
		else:
			self.msg("Invalid option, cancelling.")
			return None

	def styled_table(self, *args, **kwargs):
		"""
		Create an EvTable styled by on user preferences.

		Args:
			*args (str): Column headers. If not colored explicitly, these will get colors
				from user options.
		Keyword Args:
			any (str, int or dict): EvTable options, including, optionally a `table` dict
				detailing the contents of the table.
		Returns:
			table (EvTable): An initialized evtable entity, either complete (if using `table` kwarg)
				or incomplete and ready for use with `.add_row` or `.add_collumn`.

		"""
		border_color = self.account.options.get("border_color")
		column_color = self.account.options.get("column_names_color")

		colornames = ["|%s%s|n" % (column_color, col) for col in args]

		h_line_char = kwargs.pop("header_line_char", "~")
		header_line_char = f"|{border_color}{h_line_char}|n"
		c_char = kwargs.pop("corner_char", "+")
		corner_char = f"|{border_color}{c_char}|n"

		b_left_char = kwargs.pop("border_left_char", "||")
		border_left_char = f"|{border_color}{b_left_char}|n"

		b_right_char = kwargs.pop("border_right_char", "||")
		border_right_char = f"|{border_color}{b_right_char}|n"

		b_bottom_char = kwargs.pop("border_bottom_char", "-")
		border_bottom_char = f"|{border_color}{b_bottom_char}|n"

		b_top_char = kwargs.pop("border_top_char", "-")
		border_top_char = f"|{border_color}{b_top_char}|n"

		table = EvTable(
			*colornames,
			header_line_char=header_line_char,
			corner_char=corner_char,
			border_left_char=border_left_char,
			border_right_char=border_right_char,
			border_top_char=border_top_char,
			border_bottom_char=border_bottom_char,
			**kwargs,
		)
		return table

	def _render_decoration(
		self,
		header_text=None,
		fill_character=None,
		edge_character=None,
		mode="header",
		color_header=True,
		width=None,
	):
		"""
		Helper for formatting a string into a pretty display, for a header, separator or footer.

		Keyword Args:
			header_text (str): Text to include in header.
			fill_character (str): This single character will be used to fill the width of the
				display.
			edge_character (str): This character caps the edges of the display.
			mode(str): One of 'header', 'separator' or 'footer'.
			color_header (bool): If the header should be colorized based on user options.
			width (int): If not given, the client's width will be used if available.

		Returns:
			string (str): The decorated and formatted text.

		"""

		colors = dict()
		colors["border"] = self.account.options.get("border_color")
		colors["headertext"] = self.account.options.get(f"{mode}_text_color")
		colors["headerstar"] = self.account.options.get(f"{mode}_star_color")

		width = width or self.client_width()
		if edge_character:
			width -= 2

		if header_text:
			if color_header:
				header_text = "|n|{}{}|n".format(colors["headertext"], header_text)
			if mode == "header":
				begin_center = "|n|{}<|{}* |n".format(colors["border"], colors["headerstar"])
				end_center = "|n |{}*|{}>|n".format(colors["headerstar"], colors["border"])
				center_string = begin_center + header_text + end_center
			else:
				center_string = "|n |{}{} |n".format(colors["headertext"], header_text)
		else:
			center_string = ""

		fill_character = self.account.options.get(f"{mode}_fill")

		remain_fill = width - len(center_string)
		if remain_fill % 2 == 0:
			right_width = remain_fill / 2
			left_width = remain_fill / 2
		else:
			right_width = math.floor(remain_fill / 2)
			left_width = math.ceil(remain_fill / 2)

		right_fill = "|n|{}{}|n".format(colors["border"], fill_character * int(right_width))
		left_fill = "|n|{}{}|n".format(colors["border"], fill_character * int(left_width))

		if edge_character:
			edge_fill = "|n|{}{}|n".format(colors["border"], edge_character)
			main_string = center_string
			final_send = edge_fill + left_fill + main_string + right_fill + edge_fill
		else:
			final_send = left_fill + center_string + right_fill
		return final_send



