from math import ceil
from evennia import CmdSet

from core.commands import Command
from data.skills import SKILL_TREE
from utils.table import EvColumn, EvTable

from .skills import list_skills
from .stats import CmdStatSheet

class CmdSkillList(Command):
	"""
	View your skill tree.

	Usage:
		skills
		skills <parent skill>

	View your character's current skill levels over the skill tree.
	If a parent skill is specified, only view the levels for that skill
	and its sub-skills.
	"""

	key = "skills"
	help_category = "Character"

	def func(self):
		caller = self.caller
		skills_list = []

		if not self.args:
			skills_list = list_skills(caller)
			header = "All Skills"
		else:
			skills = caller.skills.search(self.args)
			if not skills:
				self.msg(f"You don't know any skills like '{self.args}'.")
				return
			# you can only view trees from parent skills
			skills = [skill for skill in skills if not skill.parent]
			if not skills:
				self.msg(f"That is not a valid skill group.")
				return
			elif len(skills) > 1:
				self.multimatch_msg(self.args, skills)
				index = yield ("Enter a number (or $h(c) to cancel):")
				skill = self.process_multimatch(index, skills)
				if not skill:
					return
			else:
				skill = skills[0]

			for skill_dict in SKILL_TREE.values():
				if skill_dict['name'] == skill.name:
					header = skill.name
					skills_list = list_skills(caller, skill_dict=skill_dict['subskills'], level=1)
					break
			
			if not skills_list:
				caller.msg(f"Can't find a skill tree for {skill.name}.")
				return

		def buff_lvl(skill_name, skill_value, multiplier):
			lvl = 10 *(multiplier - 1)
			if lvl <= 0:
				lvl = 0
			elif lvl <= 2:
				lvl = 1
			elif lvl <= 4:
				lvl = 2
			else:
				lvl = 3
			lvl_colors = [ "{}", "|w{}|n", "|c{}|n", "|g{}|n" ]

			return (lvl_colors[lvl].format(skill_name), lvl_colors[lvl].format(skill_value + "+"*lvl))

		skill_names, skill_values = zip(*[buff_lvl(*skill) for skill in skills_list])

		cols_list = []
		if len(skills_list) > 10:
			if len(skills_list) < 20:
				cols_list.append(EvColumn(*skill_names[:10]))
				cols_list.append(EvColumn(*skill_values[:10]))
				cols_list.append(EvColumn(*["|"]*10))
				cols_list.append(EvColumn(*skill_names[10:]))
				cols_list.append(EvColumn(*skill_values[10:]))

			else:
				split = ceil(len(skills_list )/2)
				cols_list.append(EvColumn(*skill_names[:split]))
				cols_list.append(EvColumn(*skill_values[:split]))
				cols_list.append(EvColumn(*["|"]*split))
				cols_list.append(EvColumn(*skill_names[split:]))
				cols_list.append(EvColumn(*skill_values[split:]))

		else:
			cols_list.append(EvColumn(*skill_names))
			cols_list.append(EvColumn(*skill_values))

		skill_table = EvTable(table = cols_list, border="none")
		caller.msg((f"$head({header})\n{str(skill_table)}", {'type': 'menu'}))


class CmdRaiseSkill(Command):
	"""
	Convert your earned experience into skill proficiency.

	Usage:
		improve <skill name> [to <tier>]
	
	Example:
		improve tailoring
		improve evasion to expert

	"""
	key = "improve"
	splitters = ('to',)
	help_category = "Character"

	def func(self):
		match len(self.argslist):
			case 0:
				self.list_improvable()
				return
			case 1:
				skillkey = self.args
				desc = None
				levels = 1
			case _:
				skillkey = self.argslist[0]
				desc = self.argslist[1]
				levels = 0
		
		skills = self.caller.skills.search(skillkey)
		if not skills:
			self.msg(f"You don't know any skills like '{skillkey}'.")
			return
		if len(skills) == 1:
			skill = skills[0]
		else:
			# filter out parent skills just in case
			skills = [skill for skill in skills if not skill.children]
			if not skills:
				self.msg(f"That is not a valid improvable skill.")
				return
			elif len(skills) > 1:
				self.multimatch_msg(skillkey, skills)
				index = yield ("Enter a number (or $h(c) to cancel):")
				skill = self.process_multimatch(index, skills)
				if not skill:
					return
			else:
				skill = skills[0]
		
		if skill.children:
			# list improvable skill group
			self.list_improvable(skillgroup=skill)
			return
		
		if desc:
			levels = skill.levels_to_desc(desc)
		
		if not levels:
			message = f"You cannot improve your {skill.name.lower()}"
			if desc:
				if desc == 'next':
					message += " to a higher tier"
				else:
					message += f" to {desc.lower()}"
			message += "."
			self.msg(message)
			return

		old_desc = skill.desc
		if skill.level_up(levels):
			new_desc = skill.desc
			tier_msg = '' if new_desc == old_desc else f" and are now $h({new_desc.lower()})"
			f"You improve your {skill.name.lower()}{tier_msg}."
			self.msg()
		else:
			self.msg(f"Could not improve {skill.name.lower()} at this time.")
	

	def list_improvable(self, skillgroup=None):
		"""lists skills that can be improved. if skillgroup, lists only improvable child skills"""
		if skillgroup:
			keys = skillgroup.children
		else:
			keys = self.caller.skills.all()
		
		improvable = []
		pool = self.caller.exp
		if pool <= 0:
			self.msg("You cannot currently improve any skills.")
			return

		for key in keys:
			skill = self.caller.skills.get(key)
			if skill.children:
				continue
			# FIXME: this currently duplicates the exp cost calculation
			if (skill.base+1)*5 <= pool:
				improvable.append(f"{skill.name} ({skill.desc})")
		
		if improvable:
			message = "You can improve the following skills:\n\n "
			cols_list = []
			if len(improvable) > 10:
				if len(improvable) < 20:
					cols_list.append(EvColumn(*improvable[:10]))
					cols_list.append(EvColumn(*["|"]*10))
					cols_list.append(EvColumn(*improvable[10:]))

				else:
					split = ceil(len(improvable)/2)
					cols_list.append(EvColumn(*improvable[:split]))
					cols_list.append(EvColumn(*["|"]*split))
					cols_list.append(EvColumn(*improvable[split:]))

			else:
				cols_list.append(EvColumn(*improvable))

			message += str(EvTable(table = cols_list, border="none"))
			message = (message, {"type":"menu"})
		else:
			message = "You cannot currently improve any skills."
		
		self.msg(message)

class SkillCmdSet(CmdSet):
	key = "Skill CmdSet"

	def at_cmdset_creation(self):
		super().at_cmdset_creation()
		self.add(CmdSkillList)
		self.add(CmdRaiseSkill)
		self.add(CmdStatSheet)