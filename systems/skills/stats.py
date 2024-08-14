from core.commands import Command
from switchboard import STAT_VALUES
from utils.table import EvTable

class CmdStatSheet(Command):
	"""
	view a summary of your character

	Usage:
		stats
	"""
	key = "stats"
	help_category = "Character"

	def func(self):
		chara = self.caller

		header = f"$h({chara.name}) ({chara.sdesc.get()})\n{chara.get_status(third=True)}"
		# TODO: render this better
		arch = f"$head(Supernatural status): {chara.archetype.desc if chara.archetype else 'mundane'}"
		abilities = EvTable(border=None)
		ability_head = f"$head(Natural Ability)\n"
		for stat_key in sorted(chara.stats.all()):
			stat = chara.stats[stat_key]
			abilities.add_row(*[stat.name, STAT_VALUES[stat.base-1]])
		abilities = ability_head + str(abilities).strip()

		# TODO: show a short view of top skills and in-practice skills
		skills = EvTable(border=None)
		skills_head = f"$head(Skills)"
		for skill in sorted(chara.skills.all()):
			# TODO: use skill-display code from skills command
			skills.add_row(*[skill.name,skill.desc or str(skill.value)])
		if not (skills := str(skills).strip()):
			skills = " N\A"
		skills = skills_head + skills

		self.msg( ("\n\n".join([header, arch, abilities, skills]), {'type': 'menu'}) )
