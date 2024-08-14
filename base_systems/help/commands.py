from evennia.commands.default.help import CmdHelp as BaseCmdHelp
from evennia.utils.utils import pad, format_grid

class CmdHelp(BaseCmdHelp):
	def format_help_entry(self, aliases=None, **kwargs):
		return super().format_help_entry(aliases=None, **kwargs)

	def format_help_index(
		self, cmd_help_dict=None, db_help_dict=None, title_lone_category=False, click_topics=True
	):
		"""Output a category-ordered g for displaying the main help, grouped by
		category.

		Args:
			cmd_help_dict (dict): A dict `{"category": [topic, topic, ...]}` for
				command-based help.
			db_help_dict (dict): A dict `{"category": [topic, topic], ...]}` for
				database-based help.
			title_lone_category (bool, optional): If a lone category should
				be titled with the category name or not. While pointless in a
				general index, the title should probably show when explicitly
				listing the category itself.
			click_topics (bool, optional): If help-topics are clickable or not
				(for webclient or telnet clients with MXP support).
		Returns:
			str: The help index organized into a grid.

		Notes:
			The input are the pre-loaded help files for commands and database-helpfiles
			respectively. You can override this method to return a custom display of the list of
			commands and topics.

		"""

		def _group_by_category(help_dict):
			grid = []
			verbatim_elements = []

			if len(help_dict) == 1 and not title_lone_category:
				# don't list categories if there is only one
				for category in help_dict:
					# gather and sort the entries from the help dictionary
					entries = sorted(set(help_dict.get(category, [])))

					# make the help topics clickable
					if click_topics:
						entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]

					# add the entries to the grid
					grid.extend(entries)
			else:
				# list the categories
				for category in sorted(set(list(help_dict.keys()))):
					category_str = f"--- {category.title()} ---"
					grid.append(
						self.index_category_clr
						+ category_str
						+ "-" * (width - len(category_str))
						+ self.index_topic_clr
					)
					verbatim_elements.append(len(grid) - 1)

					# gather and sort the entries from the help dictionary
					entries = sorted(set(help_dict.get(category, [])))

					# make the help topics clickable
					if click_topics:
						entries = [f"|lchelp {entry}|lt{entry}|le" for entry in entries]

					# add the entries to the grid
					grid.extend(entries)

			return grid, verbatim_elements

		help_index = ""
		width = self.client_width()
		grid = []
		verbatim_elements = []
		cmd_grid, db_grid = "", ""

		if any(cmd_help_dict.values()):
			# get the command-help entries by-category
			sep1 = (
				self.index_type_separator_clr
				+ pad("Commands", width=width, fillchar="-")
				+ self.index_topic_clr
			)
			grid, verbatim_elements = _group_by_category(cmd_help_dict)
			gridrows = format_grid(
				grid,
				width,
				sep="  ",
				verbatim_elements=verbatim_elements,
				line_prefix=self.index_topic_clr,
			)
			cmd_grid = "\n".join(gridrows) if gridrows else ""

		if any(db_help_dict.values()):
			# get db-based help entries by-category
			sep2 = (
				self.index_type_separator_clr
				+ pad("Game & World", width=width, fillchar="-")
				+ self.index_topic_clr
			)
			grid, verbatim_elements = _group_by_category(db_help_dict)
			gridrows = format_grid(
				grid,
				width,
				sep="  ",
				verbatim_elements=verbatim_elements,
				line_prefix=self.index_topic_clr,
			)
			db_grid = "\n".join(gridrows) if gridrows else ""

		# only show the main separators if there are actually both cmd and db-based help
		if cmd_grid and db_grid:
			help_index = f"{sep1}\n{cmd_grid}\n{sep2}\n{db_grid}"
		else:
			help_index = f"{cmd_grid}{db_grid}"

		return help_index