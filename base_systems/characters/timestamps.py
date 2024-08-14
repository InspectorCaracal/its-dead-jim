import time
from evennia.utils import logger
from utils.handlers import HandlerBase

# TODO: add actual add/remove methods to this???

class TimestampHandler(HandlerBase):
	"""
	A handler class attached to characters to track various timestamps that are referenced
	when "logging in". For PCs, this is typically run in the post-puppet hook, while for NPCs
	it's called by their "waking up" routine, i.e. when the NPC becomes active and returns
	to their in-game activities.

	Timestamps are stored as a dict, where the key is a string of the method to run and
	the value is the timestamp to check. Handler methods can be referenced with python dot
	notation.

	The methods being called MUST be on the character, and MUST behave in the following way:
	
	- It will be passed exactly	one argument of the timestamp difference since last called.
	- It will return a boolean representing whether the timestamp should be updated.
	"""

	def __init__(self, obj):
		super().__init__(obj, "timestamps")
	
	def stamp(self, *functions, **kwargs):
		"""
		Sets the timestamp for the given function keys to the current time.
		"""
		now = time.time()
		for func in functions:
			self._data[func] = now
		self._save()
	
	def check(self):
		"""
		Compares the saved timestamp to the current one for all of the stored method keys,
		and executes them with the difference.
		"""
		now = time.time()
		updates = []

		for func, timestamp in self._data.items():
			callme = self.obj
			for chunk in func.split('.'):
				if not (attr := getattr(callme, chunk, None)):
					logger.log_err(f"{self.obj} (#{self.obj.id}) has timestamp key '{func}' but there is no such method.")
					break
				callme = attr
			if not callable(callme):
				logger.log_err(f"Invalid method '{func}' as timestamp key for {self.obj} (#{self.obj.id})")
				continue
			try:
				if callme(now-timestamp):
					# True return means update timestamp
					updates.append(func)
			except:
				logger.log_trace(f"Attempted to run timestamp func '{func}' on {self.obj} (#{self.obj.id}), but it failed.")
		
		# we've run all the methods, so now we stamp the ones that need to be updated
		self.stamp(*updates)
		