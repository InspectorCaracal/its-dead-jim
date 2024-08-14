"""
NPCs
"""
from evennia.utils import lazy_property

from systems.chargen.gen import create_person
from .base import Character
from .ai.memory import MemoryHandler

class BaseNPC(Character):
	"""
	Base typeclass for NPCs
	"""
	_content_types = ("character", "npc",)

	@lazy_property
	def memory(self):
		return MemoryHandler(self)

	def at_object_creation(self):
		super().at_object_creation()
		# TODO: add base behaviors and triggers

	def ask_permission(self, requester, message, **kwargs):
		"""
		Generic method to get confirmation for an action.
		"""
		message = f"{requester.get_display_name(self, ref='t', article=True)} is requesting:\n  {message}\n"
		self.msg(message)
		if threshold := kwargs.get("favor"):
			# TODO: check for opinion
			opinion = 0
			if threshold >= opinion:
				requester.grant_permission(True)
			else:
				requester.grant_permission(False)
		else:
			requester.grant_permission(True)
	

class HumanoidNPC(BaseNPC):
	def at_object_creation(self):
		super().at_object_creation()
		create_person(self)
		# TODO: have this randomly generated
		self.sdesc.add(['build height', 'build bodytype', "build persona"])

class Familiar(BaseNPC):
	@property
	def bonded(self):
		if not self.ndb._bonded:
			if b := self.attributes.get('bonded', category="systems"):
				self.ndb._bonded = b
		return self.ndb._bonded

#	def at_object_creation(self):
#		BaseObject.at_object_creation(self)

	def get_display_name(self, looker, article=False, process=True, **kwargs):
		visibility = self.is_visible(looker)
		if not looker:
			return ''

		if looker != self.bonded or looker != self:
			return super().get_display_name(looker, article=article, process=process, **kwargs)
		else:
			sdesc = self.key
		if process:
			color = self.bonded.archetype.color
			sdesc = f"|{color}{sdesc}|n"

		# add dbref if looker has control access and `noid` is not set
		if self.access(looker, access_type="control") and not kwargs.get("noid"):
			sdesc = f"{sdesc}(#{self.id})"

		return self.get_posed_sdesc(sdesc, looker=looker, **kwargs) if kwargs.get("pose") and visibility else sdesc

	def at_rename(self, old_name, new_name, **kwargs):
		super().at_rename(old_name, new_name, **kwargs)
		# NOTE: does this result in duplicate cmdsets? i need to check
		self.create_new_cmdset()
	
	def create_new_cmdset(self):
		from systems.archetypes.commands import CmdFamiliar, FamiliarCmdSet
		cmd = CmdFamiliar(aliases=(self.key.lower(),))
		# create a cmdset
		fam_cmdset = FamiliarCmdSet()
		# add command to cmdset
		fam_cmdset.add(cmd)
		self.bonded.cmdset.add(fam_cmdset)
