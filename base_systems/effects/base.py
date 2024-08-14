import time
from evennia.utils import logger, delay


class Effect:
	name = "effect"
	handler = None
	last_tick = 0
	duration = 0

	@property
	def owner(self):
		return self.handler.obj

	@property
	def stacks(self):
		return sum([stacks for source, stacks in self.sources.items()])

	def __init__(self, handler, *args, **kwargs):
		self.sources = {}

		for key, val in kwargs.items():
			if (attr := getattr(self, key, None)) and callable(attr):
				# don't override methods
				continue
			if key in ("source", "stacks"):
				# we don't want to add these as data
				continue
			setattr(self, key, val)

		if self.duration:
			# this is a ticking effect, resume
			for source in self.sources.keys():
				delay(1, self.tick, source)

		# this allows us to save changes
		self.handler = handler

	def save(self):
		# tell our handler to persist our data
		self.handler.save(self)

	def add(self, *args, **kwargs):
		start_ticking = False
		if self.duration and kwargs.get('source') not in self.sources.keys():
			start_ticking = True
		self.at_add(*args, **kwargs)
		self.save()
		if start_ticking:
			self.tick(*args, **kwargs)

	def remove(self, *args, **kwargs):
		if not kwargs.get('source') and kwargs.get('stacks') == 'all':
			kwargs['source'] = 'all'
		if kwargs.get('stacks') == 'all':
			kwargs['stacks'] = self.stacks
		if kwargs.get('source') == 'all':
			del kwargs['source']
			for source in self.sources:
				stacks = self.sources[source]
				self.at_remove(*args, source=source, **kwargs)
				kwargs['stacks'] -= stacks
				if kwargs['stacks'] <= 0:
					break
		else:
			self.at_remove(*args, **kwargs)
		if self.stacks <= 0:
			self.handler.delete(self, *args, **kwargs)
		else:
			self.save()

	def tick(self, source=None, *args, **kwargs):
		if not self.duration:
			return
		now = time.time()
		since_last = now - self.last_tick
		if since_last >= self.duration:
			if source not in self.sources.keys():
				# this source no longer exists, stop ticking it
				return
			self.at_tick(source, *args, **kwargs)
			# schedule next tick
			if self.duration:
				self.last_tick = now
				delay(self.duration, self.tick, source)
				self.save()
		else:
			# it's too soon, schedule for when it should be
			delay(self.duration-since_last, self.tick, source)

	# you can override these methods!
	def at_remove(self, *args, **kwargs):
		"""
		Reduces the number of stacks and removes the source, if present.
		"""
		# if no source is specified, it's None
		source = kwargs.get("source", None)
		stacks = kwargs.get("stacks", 1)

		# remove the number of stacks from this source
		if source in self.sources:
			self.sources[source] -= stacks

			# if there are no more stacks from that source, remove it
			if self.sources[source] <= 0:
				del self.sources[source]

	def at_add(self, *args, **kwargs):
		"""
		Increase the number of stacks by 1
		"""
		# if no source is specified, it's None
		source = kwargs.get("source", None)
		stacks = kwargs.get("stacks", 1)

		if source in self.sources:
			self.sources[source] += stacks
		else:
			self.sources[source] = stacks

	def at_delete(self, *args, **kwargs):
		"""
		Code to be executed just before this effect is completely deleted.
		"""
		pass

	def at_create(self, *args, **kwargs):
		"""
		Code to be executed immediately after this effect is created.
		"""
		pass

	def at_tick(self, *args, **kwargs):
		"""
		Code to be executed when the effect "ticks", i.e. the internal timer loops.
		"""
		pass


class TagEffect(Effect):
	"""
	Effects that apply or remove status tags when created or deleted.
	"""
	def at_create(self, status, source=None, category=None, **kwargs):
		super().at_create(status, source=source, category=category, **kwargs)
		self.name = f"{status} {category}"
		self.status = status
		self.handler.obj.tags.add(status, category=category)

	def at_delete(self, *args, **kwargs):
		super().at_delete(*args, **kwargs)
		self.handler.obj.tags.remove(self.status, category=self.category)

class StatBuffEffect(Effect):
	bonus = 1
	stat = None

	def at_add(self, *args, **kwargs):
		super().at_add(*args, **kwargs)
		if self.stat:
			obj = self.handler.obj
			obj.stats[self.stat].mod += kwargs.get('stacks', 1)

	def at_remove(self, *args, **kwargs):
		super().at_remove(*args, **kwargs)
		if self.stat:
			obj = self.handler.obj
			obj.stats[self.stat].mod -= kwargs.get('stacks', 1)



class AreaEffect(Effect):
	pulse = None # the effect to apply
	duration = 5
	block = None

	def at_tick(self, source, *args, **kwargs):
		super().at_tick(source, *args, **kwargs)

		def do_pulse(target):
			for obj in target.contents:
				obj.effects.add(self.pulse, source=self.handler.obj)
				if self.block:
					if type(self.block) is tuple:
						tagname, tagcat = self.block
						if obj.tags.has(tagname, category=tagcat):
							continue
					elif not obj.tags.has(self.block):
						continue
				do_pulse(obj)

		if self.pulse:
			do_pulse(self.handler.obj)



