import string

from collections import Counter
from django.conf import settings

from evennia.commands.cmdset import CmdSet
from evennia.utils.utils import iter_to_str

from core.commands import Command
from utils.strmanip import numbered_name

# Maximum character length of 'wear style' strings, or None to disable.
_WORNSTRING_MAX_LENGTH = 50
if hasattr(settings, "CLOTHING_WORNSTRING_MAX_LENGTH"):
	_WORNSTRING_MAX_LENGTH = settings.CLOTHING_WORNSTRING_MAX_LENGTH

# TODO: convert these to Actions
class CmdWear(Command):
	"""
	Puts on an item of clothing you are holding.

	Usage:
		wear <obj>[ wear style]

	Examples:
		wear shirt
		wear scarf wrapped loosely about your shoulders

	All the clothes you are wearing are appended to your description.
	If you provide a 'wear style' after the command, the message you
	provide will be displayed after the clothing's name.
	"""

	key = "wear"
	nofound_msg = "You don't have any {sterm}."
	help_category = "Clothing"

	def _filter_targets(self, targets, **kwargs):
		return [ ob for ob in targets if ob not in self.caller.clothing.all ]

	def func(self):
		"""
		This performs the actual command.
		"""
		caller = self.caller
		
		if not self.args:
			if _WORNSTRING_MAX_LENGTH:
				caller.msg("Usage: wear <obj>[ wear style]")
			else:
				caller.msg("Usage: wear <obj>")
			return

		target = self.args.strip()
		obj, wearstyle = yield from self.find_targets(target, candidates=caller.contents, numbered=False, tail=True)
		if not obj:
			return

		if obj in caller.clothing.all and not wearstyle:
			caller.msg("You're already wearing that.")
			return

		if wearstyle and _WORNSTRING_MAX_LENGTH:
			# If length of wearstyle exceeds limit
			if len(wearstyle) > _WORNSTRING_MAX_LENGTH:
				caller.msg(
					"Please keep your wear style message to less than {} characters.".format(_WORNSTRING_MAX_LENGTH)
				)
				return

		if caller.clothing.can_add(obj):
			msg = caller.clothing.add(obj, style=wearstyle)
			if msg:
				caller.emote(msg)


class CmdRemove(Command):
	"""
	Takes off an item of clothing.

	Usage:
		 take off <obj>

	Removes an item of clothing you are wearing. You can't remove clothes
	that are being covered by something else.
	"""

	key = "take off"
	aliases = ("remove",)
	nofound_msg = "You aren't wearing any {sterm}."
	help_category = "Clothing"

	def _filter_targets(self, targets, **kwargs):
		return [ ob for ob in targets if ob in self.caller.clothing.all ]

	def func(self):
		"""
		This performs the actual command.
		"""
		caller = self.caller

		if not self.args:
			caller.msg("Usage: take off <object>")
			return

		candidates = caller.clothing.all
		targets = [ item.strip() for item in self.args.strip().split(',') ]
		remove_objs, tail = yield from self.find_targets(targets[-1], candidates, tail=True)
		targets = targets[:-1]
		for term in targets:
			obj_list = yield from self.find_targets(term, candidates, nofound="You aren't wearing any {sterm}.")
			if obj_list:
				remove_objs += obj_list

		if not remove_objs:
			return

		if removable := caller.clothing.can_remove(remove_objs):
			msg = caller.clothing.remove(removable)
			if msg:
				if tail:
					if tail[0] not in string.punctuation:
						tail = f",{tail}"
				caller.emote(f"{msg}{tail}")

class CmdCover(Command):
	"""
	Covers a worn item of clothing with another you're holding or wearing.

	Usage:
		cover <obj> with <obj>

	When you cover a clothing item, it is hidden and no longer appears in
	your description until it's uncovered or the item covering it is removed.
	You can't remove an item of clothing if it's covered.

	You can optionally change your wear-style for the object doing the covering.

	Example:
		cover necklace with scarf wrapped loosely around your neck
	"""

	key = "cover"
	help_category = "clothing"
	rhs_split = (" with ",)

	def func(self):
		"""
		This performs the actual command.
		"""

		caller = self.caller
		if not self.argslist[1] or not self.argslist[0]:
			self.caller.msg("Usage: cover <worn clothing> with <clothing object>")
			return

		cover_with, tail = yield from self.find_targets(self.argslist[1], candidates=caller.contents, numbered=False, tail=True, nofound="You don't have any {sterm}.")
		if not cover_with:
			return
		if cover_with not in caller.clothing.all:
			if not caller.clothing.can_add(cover_with):
				caller.msg(f"You can't wear {cover_with.get_display_name(caller)}.")
				return

		# Put on or adjust the item to cover with if it's not on already
		caller.clothing.add(cover_with, quiet=True, style=(tail or None) )

		to_cover = []
		for arg in self.argslist[0].split(','):
			objs = yield from self.find_targets(arg, candidates=caller.clothing.all, nofound="You aren't wearing any {sterm}.")
			if not objs:
				return
			else:
				to_cover += objs

		covered = []
		for obj in to_cover:
			if caller.clothing.can_cover(obj, cover_with):
				obj.db.covered_by = cover_with
			covered.append(obj)

		if not covered:
			caller.msg("You can't cover those things.")
			return

		covered_names = Counter([obj.get_display_name(caller) for obj in covered])
		covered_names = iter_to_str([numbered_name(*item) for item in covered_names.items()])
		message = "covers {covered} with {cover_with}."
		message = message.format( covered = covered_names, cover_with = numbered_name(cover_with.get_display_name(caller),1))
		caller.emote(message)


class CmdUncover(Command):
	"""
	Reveals a worn item of clothing that's currently covered up.

	Usage:
		uncover <obj>

	When you uncover an item of clothing, you allow it to appear in your
	description without having to take off the garment that's currently
	covering it. You can't uncover an item of clothing if the item covering
	it is also covered by something else.
	"""

	key = "uncover"
	help_category = "clothing"
	nofound_msg = "You aren't wearing any {sterm}."

	def func(self):
		"""
		This performs the actual command.
		"""
		caller = self.caller
		if not self.args:
			caller.msg("Usage: uncover <worn clothing object>")
			return
		search_list = self.args.strip().split(',')
		to_uncover = []
		for term in search_list:
			obj_list = yield from self.find_targets(term, caller.clothing.all)
			if obj_list:
				to_uncover += obj_list

		if len(to_uncover) == 1:
			self.uncover(to_uncover[0])
			return

		uncovered = []
		for obj in to_uncover:
			if self.uncover(obj, quiet=True):
				uncovered.append(obj)

		if not uncovered:
			caller.msg("You can't uncover those.")
			return

		names = Counter([obj.get_display_name(caller) for obj in uncovered])
		names = iter_to_str([numbered_name(*item) for item in names.items()])
		message = f"uncovers {names}."
		caller.emote(message)

	def uncover(self, obj, quiet=False):
		caller = self.caller

		if not (covering := obj.db.covered_by):
			caller.msg(f"Your {obj.get_display_name(caller)} isn't covered by anything.")
			return False

		if covering.db.covered_by:
			caller.msg(f"Your {obj.get_display_name(caller)} is under too many layers to uncover.")
			return False

		if not quiet:
			caller.emote(f"uncovers $gp(their) {obj.get_display_name(caller)}.")

		obj.attributes.remove("covered_by")
		return True


class ClothedCharacterCmdSet(CmdSet):
	"""
	Command set for managing worn clothing
	"""

	def at_cmdset_creation(self):
		"""
		Populates the cmdset
		"""
		super().at_cmdset_creation()
		#
		# any commands you add below will overload the default ones.
		#
		self.add(CmdWear())
		self.add(CmdRemove())
		# self.add(CmdCover())
		# self.add(CmdUncover())
