"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks
sessions etc.

"""
from evennia.server.portal.telnet import TelnetProtocol as BaseTelnetProtocol

from utils.colors import hex_to_xterm

class TelnetProtocol(BaseTelnetProtocol):
	"""
	Each player connecting over telnet (ie using most traditional mud
	clients) gets a telnet protocol instance assigned to them.  All
	communication between game and player goes through here.

	"""

	def send_text(self, *args, **kwargs):
		"""
		Send text data. This is an in-band telnet operation.

		Args:
			text (str): The first argument is always the text string to send. No other arguments
				are considered.
		Keyword Args:
			options (dict): Send-option flags

			   - mxp: Enforce MXP link support.
			   - ansi: Enforce no ANSI colors.
			   - xterm256: Enforce xterm256 colors, regardless of TTYPE.
			   - noxterm256: Enforce no xterm256 color support, regardless of TTYPE.
			   - nocolor: Strip all Color, regardless of ansi/xterm256 setting.
			   - raw: Pass string through without any ansi processing
					(i.e. include Evennia ansi markers but do not
					convert them into ansi tokens)
			   - echo: Turn on/off line echo on the client. Turn
					off line echo for client, for example for password.
					Note that it must be actively turned back on again!

		"""
		text = args[0] if args else ""
		if text is None:
			return
		# filter custom hex codes back to xterm
		text = hex_to_xterm(text)
		# strip custom table flags
		text = text.replace("|tbs","").replace("|tbe","")

		args = (text, *args[1:]) if len(args) > 1 else (text,)

		# pass the modified text back up to be processed normally
		super().send_text(*args, **kwargs)


class SSLProtocol(TelnetProtocol):
	"""
	Communication is the same as telnet, except data transfer
	is done with encryption set up by the portal at start time.
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.protocol_key = "telnet/ssl"
