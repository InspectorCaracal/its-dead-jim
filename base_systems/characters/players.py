"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
import time
from collections import defaultdict
from evennia.utils import lazy_property, iter_to_str, logger, inherits_from, interactive
from evennia.typeclasses.attributes import AttributeProperty

from base_systems.characters.base import Character
from core.ic.sdescs import RecogHandler
import switchboard
from systems.chargen.gen import create_person
from systems.scenes.handlers import ScenesHandler
from utils.strmanip import get_band, numbered_name

class PlayerCharacter(Character):
	"""
	A Character which has additional support for player-facing systems.
	"""
	content_types = ("character", "player",)

	exp = AttributeProperty(0)

	def practice_buff(self, timediff):
		"""Process the practice data to update the in-practice buffs"""
		if timediff > 86400:
			# it's been long enough, process
			for skill in self.skills.all(keys=False):
				practice = getattr(skill, "practice", 0)
				level = skill.base
				req = level // 10 + 1
				if practice > req:
					skill.mult += 0.1
				elif practice < 1:
					skill.mult = max(skill.mult - 0.1, 0)
				skill.practice = 0
			return True

		else:
			return False

	@lazy_property
	def scenes(self):
		return ScenesHandler(self)

	@lazy_property
	def recog(self):
		return RecogHandler(self)
	
	def get_sdesc(self, obj, process=False, visible=True, strip=False, **kwargs):
		"""
		Single method to handle getting recogs with sdesc fallback in an
		aware manner, to allow separate processing of recogs from sdescs.
		Gets the sdesc or recog for obj from the view of self.

		Args:
			obj (Object): the object whose sdesc or recog is being gotten
		Keyword Args:
			process (bool): If True, the sdesc/recog is run through the
				appropriate process method for self - .process_sdesc or
				.process_recog
		"""
		own = False
		# always see own key
		if obj == self:
			recog = self.key
			sdesc = self.key
			own = True
		else:
			# first check if we have a recog for this object
			recog = self.recog.get(obj)
			# set sdesc to recog, using sdesc as a fallback, or the object's key if no sdesc
			if not recog:
				if hasattr(obj, "sdesc"):
					sdesc = obj.sdesc.get(viewer=self, strip=strip) or obj.name
					if not visible and hasattr(obj, 'vdesc'):
						sdesc = obj.vdesc.get(viewer=self, strip=strip) or sdesc
				else:
					sdesc = obj.name
					# sdesc = recog or (hasattr(obj, "vdesc") and obj.vdesc.get(viewer=self, strip=strip)) or obj.name

		old_sdesc = sdesc
		
		# if kwargs.get("from_obj") == obj:
		# 	sdesc = f"{sdesc}*"

		if kwargs.get('link'):
			sdesc = f"|lclook {old_sdesc.replace(',','')}|lt{sdesc}|le"

		if kwargs.get("article") and not recog:
			# if obj.belongs_to(self):
			# 	sdesc = f"your {sdesc}"
			# else:
				sdesc = numbered_name(sdesc,1)

		if process:
			# process the sdesc as a recog if a recog was found, else as an sdesc
			sdesc = (self.process_recog if recog else self.process_sdesc)(sdesc, obj, own=own, **kwargs)

		return sdesc

	def process_sdesc(self, sdesc, obj, **kwargs):
		"""
		Allows to customize how your sdesc is displayed (primarily by
		changing colors).

		Args:
			sdesc (str): The sdesc to display.
			obj (Object): The object to which the adjoining sdesc
				belongs. If this object is equal to yourself, then
				you are viewing yourself (and sdesc is your key).
				This is not used by default.

		Kwargs:
			ref (str): The reference marker found in string to replace.
				This is on the form #{num}{case}, like '#12^', where
				the number is a processing location in the string and the
				case symbol indicates the case of the original tag input
				- `t` - input was Titled, like /Tall
				- `^` - input was all uppercase, like /TALL
				- `v` - input was all lowercase, like /tall
				- `~` - input case should be kept, or was mixed-case

		Returns:
			sdesc (str): The processed sdesc ready
				for display.

		"""
		if not sdesc:
			return ""

		ref = kwargs.get("ref", "~")  # ~ to keep sdesc unchanged
		if "t" in ref:
			# we only want to capitalize the first letter if there are many words
			sdesc = sdesc.lower()
			sdesc = sdesc[0].upper() + sdesc[1:] if len(sdesc) > 1 else sdesc.upper()
		elif "^" in ref:
			sdesc = sdesc.upper()
		elif "v" in ref:
			sdesc = sdesc.lower()
		if self.account:
#			colorize = self.account.gameoptions.get('colors','character')
			colorize = '|C' if inherits_from(obj,Character) else '|w'
			return "{}{}{}".format(colorize,sdesc,"|n")
		else:
			return sdesc

	def process_recog(self, recog, obj, own=False, **kwargs):
		"""
		Allows to customize how a recog string is displayed.

		Args:
			recog (str): The recog string. It has already been
				translated from the original sdesc at this point.
			obj (Object): The object the recog:ed string belongs to.
				This is not used by default.
		Kwargs:
			ref (str): See process_sdesc.

		Returns:
			recog (str): The modified recog string.

		"""
		if not recog:
			return ""

		if self.account:
			if own:
				colorize = "|g"
#				colorize = self.account.gameoptions.get('colors','name')
			else:
				colorize = "|c"
#				colorize = self.account.gameoptions.get('colors','recog')
			return "{}{}{}".format(colorize,recog,"|n")
		else:
			return recog

	def at_pre_puppet(self, account, session=None, **kwargs):
		"""
		Return the character from storage in None location in `at_post_unpuppet`.
		Args:
			account (Account): This is the connecting account.
			session (Session): Session controlling the connection.

		"""
		# this line or something like it will be needed for things like rent calculations
		# gone_for = time.time() - (self.db.last_logout or 0.0)

		if (
			self.location is None
		):  # Make sure character's location is never None before being puppeted.
			# Return to last location (or home, which should always exist),
			self.location = self.home
			self.location.at_object_receive(
				self, None
			)  # and trigger the location's reception hook.
		if not self.location:
			account.msg(
				_("|r{obj} has no location and no home is set.|n").format(obj=self), session=session
			)  # Note to set home.
		if self.db.last_active:
			del self.db.last_active
		if self.db.last_logout:
			if (time.time() - self.db.last_logout) > switchboard.SESSION_GAP:
				self.timestamps.check()

	def at_post_unpuppet(self, account=None, session=None, **kwargs):
		"""
		Leave the character in place until the area has been emptied of players for the correct period of time
		
		Args:
			account (Account): The account object that just disconnected
				from this object.
			session (Session): Session controlling the connection that
				just disconnected.
		Keyword Args:
			reason (str): If given, adds a reason for the unpuppet. This
				is set when the user is auto-unpuppeted due to being link-dead.
			**kwargs (dict): Arbitrary, optional arguments for users
				overriding the call (unused by default).
		"""
		self.db.last_logout = time.time()

	def delete(self, full=True):
		super().delete(full=full)

	def at_object_delete(self):
		"""
		Additional PC-specific deletion logic.

		Notifies all players who have a character who remembers this PC that
		the character no longer exists, and removes the recog.
		"""
		if super().at_object_delete():
			accounts = defaultdict(list)
			for chara in PlayerCharacter.objects.all():
				if recog := chara.recog.get(self):
					if acct := chara.db.account:
						if acct == self.db.account:
							continue
						accounts[acct].append((chara, recog))
					chara.recog.remove(self)
			
			for acct, known in accounts.items():
				msg = "The character known as {} no longer exists.".format(
					iter_to_str([ f"{name} (to {chara.key})" for chara,name in known ])
				)
				# TODO: add account notifications
			return True
		else:
			# it failed so we should also fail
			return False


	def emote(self, *args, **kwargs):
		"""
		Add an extra message if there is a card here.
		"""
		super().emote(*args, **kwargs)

		if kwargs.get('action_type') != 'ooc':
			# not sure that's the right check but it's fine
			if self.location:
				xcards = self.location.get_xcards(self)
				if xcards:
					self.msg(("\n".join(xcards), {'target': 'emote', 'action_type': 'ooc'}), from_obj=self.location)
	
	def at_msg_receive(self, text=None, from_obj=None, **kwargs):
		"""log emotes to scene"""
		# FIXME
		# if type(text) is tuple:
		# 	if self.scenes.recording:
		# 		message, oob = text
		# 		# TODO: log room changes too
		# 		# this is hacky as shit
		# 		if oob.get('type') == 'emote' or (oob.get('target') == 'emote' and oob.get('type') != 'ooc'):
		# 			self.scenes.add_line(message, from_obj)
		
		return super().at_msg_receive(text=text, from_obj=from_obj, **kwargs)

	@interactive
	def ask_permission(caller, requester, message, **kwargs):
		"""
		Generic method to get confirmation for an action.
		"""
		if not caller.has_account:
			requester.grant_permission(False)
		message = f"{requester.get_display_name(caller, ref='t', article=True)} is requesting:\n  {message}\n|lcy|ltAccept|le/|lcn|ltDeny|le"
		response = yield(message)
		if response.lower() in ('y', 'yes', 'a', 'acc', 'accept'):
			requester.grant_permission(True)
		else:
			requester.grant_permission(False)
	
	def at_object_creation(self):
		super().at_object_creation()
		self.timestamps.stamp('practice_buff')
		create_person(self)