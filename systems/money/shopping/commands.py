from core.commands import Command
from evennia import CmdSet

from utils.timing import delay

class CmdCheckout(Command):
	"""
	checkout

	Queue up to check out at the register.
	"""
	key = "checkout"
	aliases = ("check out",)

	def func(self):
		register = self.obj
		if queue := register.attributes.get('checkout_queue', []):
			if self.caller in queue:
				self.msg("You are already waiting in line.")
				return
			else:
				queue.append(self.caller)
		else:
			register.db.checkout_queue = [self.caller]
		
		self.caller.emote(f"goes over to @{register.sdesc.get(strip=True)}")

		location = self.caller.location
		for obj in location.contents_get(content_type="npc"):
			if obj.db.cash_register == register and not obj.db.now_helping:
				delay(1, obj.do_work)
				break



class RegisterCmdSet(CmdSet):
	key = "Register CmdSet"

	def at_cmdset_creation(self):
		super().at_cmdset_creation()
		self.add(CmdCheckout)