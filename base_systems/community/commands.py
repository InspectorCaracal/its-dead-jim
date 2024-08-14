from evennia import CmdSet
from evennia.utils.utils import iter_to_str

from core.commands import Command
from db.models import Report

class CmdXcard(Command):
	"""
	xcard [<options>]

	Indicate an out-of-character issue with, or need to discuss, the current scene or in-character situation.
	
	If no options are provided, it defaults to "yellow".
	
	Available options:
		clear  - Remove your previous xcard as resolved.
		green  - The scene is fine, but you need to pause it for OOC reasons.
		yellow - There is an issue with an aspect of the scene that needs to be stopped or changed, but the scene can continue once amended.
		red    - There is a serious issue and the current roleplay scene needs to be stopped immediately.
    anon   - The xcard message will be anonymous.
		ooc    - You want to discuss the issue being xcarded over an OOC channel with the other players before continuing.

	Example usage:
		xcard ooc
		xcard anon green
	"""
	key = 'xcard'
	help_category = 'Roleplay'
	free = True

	def parse(self):
		super().parse()
		args = self.args.strip().split()
		if 'red' in args or 'r' in args:
			self.stoplight = 0
		elif 'yellow' in args or 'y' in args:
			self.stoplight = 1
		elif 'green' in args or 'g' in args:
			self.stoplight = 2
		elif 'clear' in args or 'c' in args:
			self.stoplight = -1
		else:
			# this is the default
			self.stoplight = 1
		self.anon = True if 'anon' in args else False
		self.ooc = True if 'ooc' in args else False
	
	def func(self):

		message = "$h(-X-) {player} needs the current situation to be {result}{replace}."
		action = []
		if self.stoplight == -1:
			if not (cdata := self.caller.db.xcard):
				self.msg("You don't have an active X-card to clear.")
				return
			card, anon, ooc = cdata
			player = "A player here" if anon else "@Me"
			pron = "their" if anon else "$gp(their)"
			message = f"$h(-X-) {player} considers {pron} issue resolved."
			del self.caller.db.xcard

		else:
			replace = ""
			if self.caller.db.xcard:
				replace = ", replacing a previous issue"
			self.caller.db.xcard = (self.stoplight, self.anon, self.ooc)
			if self.stoplight == 0:
				action.append("stopped immediately")
			elif self.stoplight == 1:
				action.append("redirected or rolled back")
			elif self.stoplight == 2:
				action.append("paused")
			
			if self.ooc:
				action.append("discussed OOC before continuing")
			
			if self.anon:
				player = "A player here"
			else:
				player = f"@Me's player"
			
			result = iter_to_str(action) if action else "redirected or rolled back"
			message = message.format(player=player, result=result, replace=replace)
			
		self.caller.emote(message, anonymous_add=None, action_type="ooc")

class CmdReport(Command):
	"""
	Report a bug, typo or a player

	Usage:
	  report <player> = <explanation>
	  bug <obj> = <description>
	  typo <obj> = <correction>

	For room bugs or typos, please use "here" while in the room as the object reference

	For player reports, please be as clear as possible.
	"""
	key = "report"
	aliases = ("bug", "typo")
	splitters = ('=',)
	help_category = "System"
	free = True
	
	def func(self):
		if not self.rhs:
			self.msg(f"Usage: {self.cmdstring} <obj or player> = <explanation>")
			return
		caller = self.caller

		if self.lhs.lower() == "here":
			target = caller.location

		else:
			search_str = self.lhs.strip()
			result = caller.search(search_str, quiet=True)
			if len(result) == 0:
				caller.msg(f"You can't see any $h{search_str}).")
				return
			elif len(result) > 1:
				caller.multimatch_msg(search_str, result)
				index = yield("Enter a number (or $h(c) to cancel):")
				target = caller.process_multimatch(index, result)
			else:
				target = result[0]
			if not target:
				return

		if target.is_typeclass('core.characters.typeclasses.Character'):
			kind = "report"
		else:
			kind = self.cmdstring

		Report.objects.create(caller, self.rhs, kind=kind, subject=target)

		self.msg("Report created.")


class CmdViewReports(Command):
	"""
	View a list of reports, or a single report

	Usage:
	  view report [<index>]
	"""
	key = "view report"
	switch_options = ("bug", "typo", "report")
	locks = "cmd:pperm(Admin)"
	help_category = "Admin"

	def func(self):
		caller = self.caller

		reports = list(Report.objects.all())
		args = self.args.strip()

		if args:
			# get a specific report
			if args.isnumeric():
				index = int(args)-1
				if index < len(reports):
					report = reports[index]
					message = f"Submitted by: {report.writer}\nRegarding: {report.subject}\nReport: {report.content}"

		else:
			message = []
			for i, report in enumerate(reports):
				message.append(f"{i+1}: {report.kind} {report.subject} by {report.writer}")
			message = "\n".join(message)
		caller.msg(message)
		return

class CommunityCmdSet(CmdSet):
	def at_cmdset_creation(self):
		super().at_cmdset_creation()
		self.add(CmdXcard)
		self.add(CmdReport)
