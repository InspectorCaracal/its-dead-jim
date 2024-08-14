"""
Object

The Object is the "naked" base class for things in the game world.

Note that the default Character, Room and Exit does not inherit from
this Object, but from their respective default implementations in the
evennia library. If you want to use this class as a parent to change
the other types, you can do so by adding this as a multiple
inheritance.

"""
from collections import Counter, defaultdict
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import lazy_property, iter_to_str
from core.ic.features import FeatureHandler

import switchboard
import data.damages

from core.ic.base import BaseObject
from utils.colors import strip_ansi
from utils.strmanip import get_band, numbered_name, strip_extra_spaces


class Thing(BaseObject):
	size = AttributeProperty(default=1)

	@lazy_property
	def materials(self):
		return FeatureHandler(self, feature_attr="materials")

	@property
	def free_space(self):
		content_sizes = [obj.size for obj in self.contents]
		max_size = self.size * switchboard.CAPACITY_RATIO

		return max_size - sum(content_sizes)

	def at_object_creation(self):
		super().at_object_creation()
		# the amount of damage this object can take
		self.stats.add("integrity", "Integrity", trait_type="counter",base=10, min=-5, max=10)
		# the amount of damage this object does when it hits something else
		self.stats.add("dmg", "Damage", trait_type="static", base=1)
		# how easily this thing falls over
		self.stats.add("stab", "Stability", trait_type="static", base=0)

	def at_post_puppet(self, **kwargs):
		self.msg(f"You become {self.get_display_name(self)}.")
		if self.location.access(self, "view"):
			message = self.at_look(self.location)
			if isinstance(message, tuple):
				message = (message[0], message[1] | {"target": "location", "clear": True})
			else:
				message = (message, {"target": "location", "clear": True})
			self.msg(message)
		
	def get_display_name(self, looker, article=False, process=True, **kwargs):
		"""
		Displays the name of the object in a viewer-aware manner.
		"""
		suffix = ''
		if kwargs.pop("contents", True) and (self.get_lock(looker, 'viewcon')):
			contents = self._filter_visible(self.contents)
			if len(contents) > 3:
				suffix = f" with several things"
			elif contents:
				content_names = Counter([obj.get_display_name(looker, **kwargs) for obj in contents])
				content_str = iter_to_str([numbered_name(*item) for item in content_names.items()])
				suffix = f" with {content_str}"

		base = self.baseobj

		if base == self:
			sdesc = super().get_display_name(looker, article=article, process=process, **kwargs)

		else:
			try:
				# get the sdesc looker should see, with formatting
				parent = base.get_display_name(looker, process=process, **kwargs)
				kwargs.pop('ref',None)
				sdesc = looker.get_sdesc(self, article=False, process=process, **kwargs)
			except AttributeError as e:
				# use own sdesc as a fallback
				if looker == base:
					parent = base.key
				else:
					parent = base.sdesc.get()
					if article:
						parent = numbered_name(parent,1)
				if looker == self:
					# process your key as recog since you recognize yourself
					sdesc = self.key
				else:
					sdesc = self.sdesc.get()

			sdesc = f"{parent}'s {sdesc}"

		sdesc += suffix
		return self.get_posed_sdesc(sdesc, looker=looker, **kwargs) if kwargs.get("pose", False) else sdesc


	def get_status(self, third=False, **kwargs):
		msg = []
		if pose := self.get_pose(fallback=False):
			msg.append(pose)
		if damage := self.damage_status(third=third):
			msg.append(damage)
		
		return " ".join(msg)

	def damage_status(self, third=False, **kwargs):
		"""Return an assessment of the total health status"""
		text = []
		sentences = kwargs.get('sentences',True)
		integ = self.stats.integrity
		# TODO: add back in portions
		if integ.value != integ.max:
			band = "damage"
			verb = "is"
			# TODO: integ.percent(formatting=None) < 98
			status = get_band(band, integ.percent(formatting=None))
			if status:
				if sentences:
					text.append(f"$Gp(It) $pconj(is) {status}.")
				else:
					text.append(status)
		tags = self.tags.get(category='status', return_list=True) + self.tags.get(category='health', return_list=True)
		if tags:
			if sentences:
				text.append(f"$Gp(It) $pconj(is) {iter_to_str(tags)}.")
			else:
				text += tags
		if sentences:
			return " ".join(text)
		else:
			return iter_to_str(text)

	def get_display_footer(self, looker, **kwargs):
		footer = super().get_display_footer(looker)
		integ = self.stats.integrity
		if integ.value == integ.max:
			text = ''
		else:
			text = self.damage_status(third=True)
			# if self.tags.has("consumable"):
			# 	text = f"$Gp(It) $pconj(is) {integ.percent()} gone."
			# else:
			# 	text = f"$Gp(It) $pconj(is) {integ.percent()} damaged."
		return text if not footer else f"{footer}\n{text}".rstrip()

	def get_all_contents(self):
		"""Returns a list of all objects contained by this thing and its parts"""
		contents = self.contents
		for obj in self.parts.all():
			contents += obj.contents
		
		return contents

	def get_extra_info(self, looker, **kwargs):
		if self != self.baseobj:
			return f" (part of {self.baseobj.get_display_name(looker, **kwargs)})"
		return super().get_extra_info(looker, **kwargs)

	def at_damage(self, damage, source=None, destructive=False, quiet=False, **kwargs):
		self.on_defense(damage, source=source)
		integ = self.stats.integrity
		if integ.value <= 0 and not destructive:
			return
		# TODO: add damage reduction
		integ.current -= damage
		if integ.value <= 0:
			if not destructive:
				integ.current = 0
				self.tags.add("disabled")
			elif not self.tags.has("indestructible"):
				if not quiet:
					self.emote("is destroyed")
				self.delete()
				return
		# TODO: change damage to be a dictionary of damage types and amounts
		if dtype := kwargs.get('damage_type'):
			if damage_effects := self.tags.get(return_list=True, category="damage_effects"):
				key = damage_effects[0].upper().strip() + "_DAMAGES"
				if damage_dict := getattr(data.damages, key, None):
					if effect := damage_dict.get(dtype):
						pct_done = 100*damage / integ.max
						effect = [ e for p, e in effect.items() if pct_done >= p ]
						if effect:
							self.effects.add(effect[-1], stacks=damage)
							if not kwargs.get('notify',True):
								self.baseobj.update_features()
		self.on_damaged(damage, source=source)
		if not quiet:
			base_msg = f"takes damage; $gp(it's) {self.damage_status(third=True, sentences=False)}"
			if source and hasattr(source,'msg'):
				# TODO: add descriptors for % left
				source.msg(f"{self.get_display_name(source, ref='t')} {base_msg}.", from_obj=self)
			
			if self.baseobj != self:
				self.baseobj.msg(f"Your {self.sdesc.get()} {base_msg}.", from_obj=self)
			self.msg(f"You take damage; you're {self.damage_status(third=True, sentences=False)}.", from_obj=self)
		
		if self != self.baseobj and kwargs.get('notify',True):
			if hasattr(self.baseobj, 'at_part_damaged'):
				self.baseobj.at_part_damaged(damage, part=self, source=source)

	def at_pre_object_receive(self, obj, source_location, **kwargs):
		"""
		Do a simple capacity check before receiving an object.
		"""
		# if not self.tags.has('container', category="systems"):
		# 	return False
		# FIXME: this needs to be redone to potentially provide error feedback to players
		obj_size = obj.size
		if obj_size < self.size:
			return obj_size < self.free_space
		else:
			return False

	def at_pre_get(self, getter, **kwargs):
		up = super().at_pre_get(getter, **kwargs)
		if self.location:
			return up and self.location.access(getter, "getfrom")
		return up		

	def at_pre_use(self, user, *args, **kwargs):
		if self.tags.has("disabled"):
			user.msg("It doesn't seem to be working.")
			return False
		return True

	def use(self, user, *args, **kwargs):
		if self.at_pre_use(user, *args, **kwargs):
			self.at_use(user, *args, **kwargs)

	def at_use(self, user, *args, **kwargs):
		self.on_use(user, *args, **kwargs)

	def at_crafted(self, *args, **kwargs):
		# TODO: make this a trigger instead
		pass

	def generate_desc(self):
		parts_list = self.parts.all()
		# no attached parts, check if any are needed
		if len(parts_list) <= 0 and self.db.self_destruct:
			self.delete()
			return

		quality = self.db.quality
		quality = quality[1] if quality else ""

		#		self.materials.reset()
		#		mat_str = self.materials.view
		# TODO: use the new rgb pigment system
		mat_list = []
		for mat in self.materials.all:
			if not (feat := self.materials.get(mat)):
				continue
			if cqual := self.materials.get(mat, as_data=True).get('color_quality'):
				if cqual <= 1:
					feat = f"patchy {feat}"
			mat_list.append(feat)
		mat_str = iter_to_str(mat_list)
		formats = self.db.format or {}
		desc = "{quality} {prefix} " + formats.get("desc", "{piece}")

		base_prefix = self.db._sdesc_prefix or ""
		plural_prefix = ""

		if base_piece := self.db.piece:
			if base_prefix:
				plural_piece = base_piece
				plural_prefix = switchboard.INFLECT.plural(f"{base_prefix} {base_piece}")[:(-1 * len(base_piece))]
			else:
				plural_piece = switchboard.INFLECT.plural(base_piece)
		else:
			base_piece = self.key
			plural_piece = switchboard.INFLECT.plural(base_piece)

		plural_desc = desc.format(
			quality=quality,
			prefix=plural_prefix,
			material=mat_str,
			piece=plural_piece,
		)
		desc = desc.format(
			quality=quality,
			prefix=base_prefix,
			material=mat_str,
			piece=base_piece,
		)
		desc = numbered_name(desc, 1)
		#		desc = desc[0].upper() + desc[1:]

		pieces = set()
		piece_descs = []

		name_include = list(self.db.name_include or [])
		name_exclude = list(self.db.name_exclude or [])

		materials_dict = self.materials.get("all", as_data=True)

		# get the colors and materials of the object
		colors = set()
		matnames = set()
		name_pieces = defaultdict(list)
		for key, value in materials_dict:
			# if key in ["format", "prefix", "article"]:
			# 	continue
			if value.get('invisible'):
				continue
			matnames.add(key)
			color = value.get("color", '')
			if color:
				cqual = value.get("color_quality",0)
				try:
					cqual = int(cqual)
				except ValueError:
					continue
				if cqual < 5:
					color = strip_ansi(color)
				if cqual <= 1:
					color = f"patchy {color}"
				colors.add(color)

		for part in parts_list:
			part_materials = part.materials.get("all", as_data=True)
			for mat_key, mat_values in part_materials:
				if mat_values.get('invisible'):
					continue
				matnames.add(mat_key)
				color = mat_values.get("color", '')
				if color:
					cqual = mat_values.get("color_quality", 0)
					try:
						cqual = int(cqual)
					except ValueError:
						continue
					if cqual < 5:
						color = strip_ansi(color)
					if cqual <= 1:
						color = f"patchy {color}"
					colors.add(color)

			part_mat_str = part.materials.view
			if part_mat_str == mat_str:
				part_mat_str = ''

			piece = part.db.piece or part.tags.get(category="craft_material")
			key = (
			part.db.format.get("desc") if part.db.format else part.key, part.db._sdesc_prefix or "", piece, part_mat_str)
			pieces.add(piece)
			piece_descs.append(key)
			if name_include or name_exclude:
				if not any(part.tags.has(name_exclude, category="craft_material", return_list=True)):
					name_pieces['all'].append(part.key)
					if any(part.tags.has(name_exclude, category="craft_material", return_list=True)):
						name_pieces['short'].append(part.key)

		addons = []
		plural_addons = []
		piece_counts = Counter(piece_descs)
		for key, value in piece_counts.items():
			part_desc, prefix, piece, part_mats = key
			piece_desc = "{} {}".format(prefix, part_desc.format(prefix=prefix, piece=piece, material=part_mats))
			plural_piece_desc = switchboard.INFLECT.plural(piece_desc)
			piece_desc = numbered_name(piece_desc, value)
			addons.append(piece_desc)
			plural_addons.append(plural_piece_desc)

		if required := self.db.req_pieces:
			addons += ["no {}".format(switchboard.INFLECT.plural(piece)) for piece in required if piece not in pieces]

		if len(addons) > 0:
			addons = iter_to_str(addons)
			desc = f"{desc}, with {addons}"
			plural_addons = iter_to_str(plural_addons)
			plural_desc = f"{plural_desc} with {plural_addons}"

		desc = strip_extra_spaces(desc)
		plural_desc = strip_extra_spaces(plural_desc)

		if formats.get("desc"): # ????
			self.db.desc = desc[0].upper() + desc[1:] + "."
			self.db.plural_desc = plural_desc + "."
		else:
			self.db.desc = ""
			self.db.plural_desc = ""

		if len(colors):
			materials = list(colors)
			if len(materials) > 1:
				colorized = [mat for mat in materials if mat[0] == '|']
				for col in colorized:
					if strip_ansi(col) in materials:
						materials.remove(strip_ansi(col))
			material = "multicolored" if len(materials) > 3 else iter_to_str(materials)
		else:
			if name_include or name_exclude:
				if not len(name_pieces['all']):
					material = "empty"
				else:
					materials = Counter(name_pieces['all'])
					if len(materials.keys()) > 3:
						materials = Counter(name_pieces['short'])
					material = iter_to_str(sorted(materials.keys()))

			else:
				materials = list(matnames)
				material = "multicolored" if len(materials) > 3 else iter_to_str(materials)

		old_name = self.key
		name = formats.get("name", '{piece}').format(
			material=material,
			prefix=base_prefix,
			piece=base_piece,
		)
		# logger.log_msg(name)
		self.key = strip_extra_spaces(name)
		self.at_rename(old_name, self.key)
		if self.baseobj != self:
			try:
				self.location.generate_desc()
			except AttributeError:
				pass
	
	def basetype_setup(self):
		super().basetype_setup()
		self.locks.add("get:not holds()")
