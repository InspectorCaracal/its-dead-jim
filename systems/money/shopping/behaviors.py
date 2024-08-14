from copy import copy
from evennia.utils.utils import calledby

from base_systems.actions.base import InterruptAction
from base_systems.things.actions import DropAction, GiveAction, UseAction
from core.ic.behaviors import Behavior, behavior
from utils.timing import delay

from . import actions

@behavior
class ShopClerkBehavior(Behavior):
	priority = 5

	def work(obj, *args, **kwargs):
		if obj.actions.current or obj.effects.has("systems.money.shopping.effects.HelpingCustomerEffect"):
			return
		if register := obj.db.cash_register:
			# check queue
			if queue := register.db.checkout_queue:
				queue = queue.deserialize()
				while queue:
					next_customer = queue.pop(0)
					if next_customer.location == register.location:
						break
				register.db.checkout_queue = queue
				# TODO: make an effects registry too
				obj.effects.add("systems.money.shopping.effects.HelpingCustomerEffect", source=next_customer)
				return
		# no customers to help, try to restock
		try:
			action = actions.RestockAction(obj)
		except InterruptAction:
			return
		obj.actions.add(action)


@behavior
class CheckoutClerkBehavior(Behavior):
	"""behavior for an NPC cashier checking out a customer"""
	priority = 10

	def receive_object(obj, received, source, **kwargs):
		print('aaaaa')
		if not (customer := obj.db.now_helping):
			obj.effects.remove("systems.money.shopping.effects.HelpingCustomerEffect", stacks="all")
		if source and source != customer:
			try:
				action = GiveAction(obj, [received], receiver=source)
				obj.actions.add(action)
			except InterruptAction:
				pass
			return
			
		if kwargs.get('move_type') == "give":
			# it was given to us by source
			if not (cash_register := obj.db.cash_register):
				# we can't check them out
				# TODO: give the object back
				return
			# TODO: differentiate between a card to pay with and something to scan
			if received.can_pay_out:
				obj.do_ring_up(customer, cash_register, received)
			else:
				obj.do_scan_item(received, cash_register)
	
	def scan_item(obj, item, cash_register):
		try:
			action = UseAction(obj, [cash_register], use_on=[item])
		except InterruptAction:
			return
		obj.actions.add(action)
		if getattr(obj, "_task", None):
			obj._task.cancel()
		obj._task = delay(5, obj.do_give_total)
	
	def give_total(obj, **kwargs):
		if not obj.actions.queue and (customer := obj.db.now_helping):
			try:
				action = actions.ReadOffTotal(obj, obj.db.cash_register, customer)
			except InterruptAction:
				return
			obj.actions.add(action)

	def customer_leave(obj, leaver, *args, **kwargs):
		if leaver == obj.db.now_helping:
			del obj.db.now_helping
			if obj.actions.queue:
				obj.actions.clear()
			# TODO: this should clearly be in an action...
			if getattr(obj, "_task", None):
				obj._task.cancel()
			obj.effects.remove("systems.money.shopping.effects.HelpingCustomerEffect", stacks="all")
			obj.on_customer_done(leaver)

	def ring_up(obj, customer, cash_register, cash_card):
		print('ring up')

		if getattr(obj, "_task", None):
			obj._task.cancel()

		total, _ = cash_register.do_total(obj)
		if total <= 0:
			try:
				action = GiveAction(obj, [cash_card], receiver=customer)
				obj.actions.add(action)
			except InterruptAction:
				obj.emote(f"shrugs and keeps @{cash_card.sdesc.get()}")
			return

		try:
			action = UseAction(obj, [cash_register], use_on=[cash_card])
		except InterruptAction:
			obj.emote(f"looks dubiously at @{cash_card.sdesc.get()}")
			return
		obj.actions.add(action)

	def bag_items(obj, customer, cash_card, sold_items, **kwargs):
		try:
			action = GiveAction(obj, [cash_card], receiver=customer)
			obj.actions.add(action)
		except InterruptAction:
			obj.emote(f"shrugs and keeps @{cash_card.sdesc.get()}")

		register = obj.db.cash_register
		try:
			action = actions.BagItems(obj, customer, sold_items, bag_spawner=register.db.bags)
			obj.actions.add(action)
		except InterruptAction:
			action = DropAction(obj, sold_items)
			obj.actions.add(action)
			obj.effects.remove("systems.money.shopping.effects.HelpingCustomerEffect", source=customer)

@behavior
class CheckoutRegisterBehavior(Behavior):
	"""behavior for a cash register object to scan totals"""
	priority = 5

	def use(obj, actor, targets=None, **kwargs):
		print("using the register")
		if len(targets) == 1:
			if targets[0].can_pay_out:
				return obj.do_finalize_sale(actor, targets[0])

		if scanned := obj.attributes.get('scanned', category='shopping', default={}):
			scanned = scanned.deserialize()
		if not targets:
			return
		for target in targets:
			if pricetag := target.parts.search('price tag'):
				pricetag = pricetag[0]
				if price := pricetag.db.price:
					# TODO: cross-check price currency with register currency
					scanned[target] = price[0]
		obj.attributes.add('scanned', scanned, category='shopping')
		if len(targets) > 1:
			actor.emote("scans the items")
		else:
			actor.emote(f"scans @{targets[0].sdesc.get(strip=True)}", include=targets)
		
	
	def total(obj, actor, **kwargs):
		currency = obj.attributes.get('currency', 'dollar', category='money')
		if scanned := obj.attributes.get('scanned', category='shopping', default={}):
			scanned = scanned.deserialize()
			total = sum(list(scanned.values()))
		else:
			total = 0
		return (total, currency)
	
	def get_sale_items(obj, actor, **kwargs):
		scanned = obj.attributes.get('scanned', category='shopping', default={})
		return list(scanned.keys())
	
	def finalize_sale(obj, actor, cash_card, **kwargs):
		if not (customer := actor.db.now_helping):
			return
		total = obj.do_total(actor)
		if cash_card.do_pay_out(total[0], obj):
			# successful purchase!
			sold = obj.do_get_sale_items(actor)
			actor.on_finalize_sale(customer, cash_card, sold)
			obj.do_end_sale()

		else:
			speech = "It seems you can't pay with this."
			emote = actor.at_pre_say(speech, target=customer)
			actor.emote(emote, include=customer)
			customer.on_spoken_to(actor, speech)
			try:
				action = GiveAction(actor, [cash_card], receiver=customer)
				actor.actions.add(action)
			except InterruptAction:
				actor.emote(f"shrugs and keeps @{cash_card.sdesc.get()}")
			return

	def end_sale(obj, *args, **kwargs):
		obj.attributes.remove('scanned', category='shopping')

	def unqueue(obj, queuer, *args, **kwargs):
		if queuer in obj.attributes.get('checkout_queue', []):
			obj.db.checkout_queue.remove(queuer)