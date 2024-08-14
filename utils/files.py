import os
from evennia.utils import logger
from twisted.internet.threads import deferToThread

def write(msg, filename="output.log"):
	"""
	Arbitrary file logger using threads.
	Args:
		msg (str): String to append to logfile.
		filename (str, optional): Defaults to 'game.log'. All logs
			will appear in the logs directory. Differs from core Evennia
			file logger by not preppending timestamps.
	"""

	def callback(filepath, msg):
		"""Writing to file and flushing result"""
		msg = f"\n{msg.strip()}"
		with open(filepath, "a") as file:
			file.write(msg)

	def errback(failure):
		"""Catching errors to normal log"""
		logger.log_trace()

	# save to server/logs/ directory
	lines = msg.split('\n')
	for line in lines:
		deferToThread(callback, filename, line).addErrback(errback)