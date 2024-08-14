from evennia.utils import iter_to_str

from core.commands import Command
from utils.strmanip import get_band


class CmdHealth(Command):
	key = "health"

	def func(self):
		# TODO: add the ability to assess other people's health
		# TODO: make it skill checked for detail
		damaged = []
		for p in self.caller.parts.all():
			status = []
			pct = p.stats.integrity.percent(formatting=None)
			if pct < 98.0:
				status.append(get_band("damage", pct))
			tags = p.tags.get(category='health', return_list=True)
			if tags:
				status.append(iter_to_str(tags))
			if status:
				damaged.append(f"Your {p.sdesc.get(strip=True)} is {iter_to_str(status)}.")
		
		if damaged:
			self.msg(("\n".join(damaged), {'type':'look'}))
		else:
			self.msg("You are in perfect health.")


