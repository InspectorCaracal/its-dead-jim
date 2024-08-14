import uuid
from base_systems.things.base import Thing


class CashCard(Thing):
	"""
	A special kind of object which can store an arbitrary amount of data.

	Has a unique ID, which can potentially be tracked
	"""
	def at_object_creation(self):
		super().at_object_creation()
		self.locks.add("call:holds()")
		self.db.uuid = uuid.uuid4().bytes
		if not self.attributes.has('value', category='money'):
			self.attributes.add('value', 0, category='money')
		if not self.attributes.has('currency', category='money'):
			self.attributes.add('currency', 'dollar', category='money')
		self.behaviors.add("WalletBehavior")


def use(obj, user, target=None, **kwargs):
	"""Allows you to just use a card on a checkout device or ATM to pay without entering numbers"""
	# note: total is negative if payment, positive if received
	if not target:
		return False
	try:
		total, currency = target.db.get_total
	except ValueError:
		return False
	success = False
	if total > 0:
		# we're getting money
		if obj.do_pay_in(total, currency, obj):
			user.msg(f"You transfer {total} {currency} onto your {obj.get_display_name(user, article=False)}.")
			success = True
	elif total < 0:
		# we're paying money
		if obj.do_pay_out(total, target, **kwargs):
			user.msg(f"You pay {total} {currency} from your {obj.get_display_name(user, article=False)}.")
			success = True

	return success