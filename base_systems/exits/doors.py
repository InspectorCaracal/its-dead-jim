from base_systems.exits.base import Exit


class DoorExit(Exit):
	"""
	An exit which is attached to a door object that can be opened, closed, and locked.
	"""
	_content_types = ('exit', 'door')

	@property
	def locked(self):
		"""Boolean indicating if the door is locked or not"""
		if not (door := self.db.door):
			# who took the door
			return False
		locks = door.parts.search('lock', part=True)
		if not locks:
			# there is no lock, so it can't be locked
			return False
		if any(lock.tags.has('locked') for lock in locks):
			return True
		return False
	
	@property
	def open(self):
		"""Boolean indicating if the door is open or not"""
		if not (door := self.db.door):
			# if the door is gone then we're open
			return True
		return door.tags.has('open', category='status') or not door.tags.has('closed', category='status')

	@property
	def visibility(self):
		if self.open:
			return super().visibility
		else:
			return False
	
	def at_object_creation(self):
		super().at_object_creation()
		self.db.leave_traverse = "{verbs} through {exit}"

	def get_display_desc(self, looker, **kwargs):
		# force the exit as not-see-throughable if it's closed
		transparent = self.open

		if door := self.db.door:
			desc = door.get_display_desc(looker, **kwargs)
			desc += "\n\n"
			transparent = transparent or door.tags.has('transparent')

		if not transparent:
			kwargs['visibility'] = False
			kwargs['look_in'] = False

		desc += super().get_display_desc(looker, **kwargs)

		return desc

	def at_pre_traverse(self, mover, target_loc, **kwargs):
		if not self.open and not self.can_unlock(mover):
			mover.msg(f"You cannot open {self.get_display_name(mover, article=True)}.")
			return False
		return super().at_pre_traverse(mover, target_loc, **kwargs)

	def can_unlock(self, doer, **kwargs):
		"""Boolean indicating whether `doer` can unlock this door"""
		if not (door := self.db.door):
			# there is no door
			return False

		if not (locks := door.parts.search('lock', part=True)):
			# there is no lock at all
			return False

		# TODO: implement lockpicking and lock-hacking
		for lock in locks:
			if lock.db.owner == doer:
				# auto-pass this lock
				continue
			if not (keys := lock.db.keyset):
				# there are no valid extra keys at all
				return False
			if not keys.intersection(set(doer.contents)):
				# they aren't carrying the right key
				return False
		
		# we passed all the locks! we can unlock it
		return True

	def toggle_locks(self, onoff):
		"""
		Toggles all the locks on this door either on or off

		Returns a list of all locks which had their status changed
		"""
		changed = []
		if not (door := self.db.door):
			# there is no door
			return []

		for lock in door.parts.search('lock', part=True):
			if lock.tags.has("locked") != onoff:
				changed.append(lock)
				if onoff:
					# we're locking it
					lock.tags.add('locked')
				else:
					# we're unlocking it
					lock.tags.remove('locked')
		
		return changed

	def at_open_close(self, doer, open=True, **kwargs):
		if not (door := self.db.door):
			doer.msg("The door seems to be gone.")
			return

		if self.locked:
			if not self.can_unlock(doer):
				return f"tries to {'open' if open else 'close'} @{self.sdesc.get(strip=True)}, but it's locked"
		
		if open:
			if door.tags.has('open', category='status'):
				# it's already open
				return None
			# we're opening it
			door.tags.remove('closed', category='status')
			door.tags.add('open')
		else:
			if door.tags.has('closed', category='status'):
				# it's already closed
				return None
			# we're closing it
			door.tags.remove('open', category='status')
			door.tags.add('closed', category='status')

		for ex in door.db.sides:
			if doer.location == ex.location and not kwargs.get('anonymous'):
				message = f"@{doer.sdesc.get(strip=True)} {'opens' if open else 'closes'} @me"
			else:
				message = f"{'opens' if open else 'closes'}"
			ex.emote(message)

		# we don't return a message since we did our own messaging
		return None

	def at_lock_unlock(self, doer, locking=True, **kwargs):
		if not self.can_unlock(doer):
			return None

		# TODO: reference the actual lock items somehow that are returned from this
		self.toggle_locks(locking)
		return f"{'locks' if locking else 'unlocks'} @{self.sdesc.get(strip=True)}"

	def install_door(self, obj, **kwargs):
		"""returns True if door installed, False if not"""
		other_side = [ex for ex in self.get_return_exit(return_all=True) if 'door' in ex._content_types]
		if obj.db.sides:
			return False
		obj.db.sides = []
		if other_side:
			other_side = other_side[0]
			if other_side.db.door:
				return False
			other_side.db.door = obj
			obj.db.sides.append(other_side)
		self.db.door = obj
		obj.db.sides.append(self)
		return True