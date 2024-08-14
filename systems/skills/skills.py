from data.skills import SKILL_LEVELS, SKILL_TREE
from switchboard import MAX_SKILL, STAT_TO_SKILL_MOD, XP_COST


def add_skill_tree(char, skill_dict, parent=None):
	for key, tree in skill_dict.items():
		if subskills := tree.get("subskills"):
			children = subskills.keys()
		else:
			children = None
		char.skills.add(
				key, tree['name'],
				descs=tree.get('descs',SKILL_LEVELS),
				max=tree.get('cap', MAX_SKILL),
				stat=tree['stat'],
				parent=parent, children=children,
			)
		if subskills:
			add_skill_tree(char, tree["subskills"], parent=key)

def init_skills(char):
	add_skill_tree(char, SKILL_TREE)

def update_skill_tree(char, skill_dict, key_list=None, parent=None):
	if not key_list:
		key_list = list(char.skills.all())
	for key, tree in skill_dict.items():
		if subskills := tree.get("subskills"):
			children = subskills.keys()
		else:
			children = None
		if key not in key_list:
			char.skills.add(
					key, tree['name'],
					descs=tree.get('descs',SKILL_LEVELS),
					max=tree.get('cap', MAX_SKILL),
					stat=tree['stat'],
					parent=parent, children=children,
				)
		if subskills:
			update_skill_tree(char, tree["subskills"], key_list=key_list, parent=key)

def update_skills(char):
	update_skill_tree(char, SKILL_TREE)

def list_skills(char, skill_dict=None, level=0):
	skill_dict = SKILL_TREE if skill_dict is None else skill_dict
	prefix = "  " * level
	skills_list = []
	for key, dict in skill_dict.items():
		if skill := char.skills.get(key):
			skills_list.append((
				f"{prefix}{dict['name']}" if prefix else f"|u{dict['name']}|n",
		 		f"{prefix}{skill.desc}" if prefix else "",
				skill.mult
			))
			if "subskills" in dict.keys():
				skills_list += list_skills(char, dict["subskills"], level=level+1)
	return skills_list


class Skill:
	parent = None
	children = None

	def __init__(self, handler, name, key, **kwargs):
		self.handler = handler
		self.name = name
		self.key = key
		for key, val in kwargs.items():
			if callable(getattr(self, key, None)):
				continue
			setattr(self, key, val)
	
	def __str__(self):
		return self.name

	@property
	def base(self):
		return getattr(self, '_base', 0)
	@base.setter
	def base(self, value):
		self._base = max(min(getattr(self, 'cap', MAX_SKILL),value), 0)
		self.handler._save(key=self.key)

	@property
	def mod(self):
		return getattr(self, '_mod', 0)
	@mod.setter
	def mod(self, value):
		self._mod = value
		self.handler._save(key=self.key)

	@property
	def mult(self):
		return getattr(self, '_mult', 1)
	@mult.setter
	def mult(self, value):
		self._mult = value
		self.handler._save(key=self.key)

	@property
	def practice(self):
		return getattr(self, '_practice', 0)
	@practice.setter
	def practice(self, value):
		self._practice = value
		self.handler._save(key=self.key)
	
	@property
	def value(self):
		bonus = self.mod + self.get_stat_bonus()
		if self.parent and (parent := self.handler.get(self.parent)):
			bonus += parent.base / 2 + parent.get_stat_bonus()
		
		return (self.base + bonus)*self.mult

	def get_stat_bonus(self):
		"""Get the modifier for the owner's stat for this specific skill's stat"""
		bonus = 0
		if stat_key := getattr(self, 'stat', None):
			if stat := self.handler.obj.stats.get(stat_key):
				bonus = STAT_TO_SKILL_MOD(stat.value)
		return bonus

	def level_up(self, levels, cost=True):
		points = self.exp_to_level(self.base+levels)
		if points <= self.handler.obj.exp:
			self.handler.obj.exp -= points
			self.base += levels
			if self.parent and (parent := self.handler.get(self.parent)):
				parent.level_up(levels/2, cost=False)
		

	@property
	def desc(self):
		"""
		Retrieve descriptions of the current value, if available.
		Returns:
			str: The description describing the `value` value.
				If not found, returns the empty string.
		"""
		if not (descs := getattr(self, 'descs', None)):
			return ""
		value = self.base + self.get_stat_bonus()
		filtered = [ txt for bound, txt in descs.items() if bound <= value ]
		if not filtered:
			return ''
		# we want the highest item that passed
		return filtered[-1]

	def levels_to_desc(self, desc):
		"""
		Returns the number of levels required to get to the listed desc.

		If the desc is invalid or already passed, returns 0.
		"""
		if not (descs := getattr(self, 'descs', None)):
			# this has no descs
			return 0
		desc = desc.lower().strip()
		current_desc = self.desc.lower()
		if desc == 'next':
			# desc keys are floors, so we want to find the first key after ours
			desc_strs = list(descs.values())
			i = desc_strs.index(current_desc)
			if i == len(desc_strs)-1:
				# it's the last one
				return 0
			level = list(descs.keys())[i+1]
		else:
			# desc keys are floors, so we just need to get the desc's key
			level = 0
			for key, val in descs.items():
				if val.lower() == desc:
					level = key
					break

		# get the difference
		if level > self.base:
			return level - self.base
		else:
			return 0

	def exp_to_level(self, level='next'):
		if level == 'next':
			return (self.base+1)*XP_COST
		elif level <= self.base:
			return 0
		
		start = self.base+1
		points = sum(inc*XP_COST for inc in range(start, level))
		return points
