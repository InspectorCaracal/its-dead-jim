from base_systems.prototypes.spawning import spawn
from core.ic.behaviors import Behavior, NoSuchBehavior, behavior
from systems.crafting.automate import generate_new_object
from systems.money.vendor import VendingMenu
from utils.general import get_classpath
from utils.menus import FormatEvMenu

from copy import copy

@behavior
class VendingBehavior(Behavior):
	priority = 10

	def pay_in(obj, value, currency, payer, **kwargs):
		"""
		Receive `value` amount of money from another object

		Returns True if the money was accepted successfully, False otherwise
		"""
		if not (item := kwargs.get("stock_recipe")):
			return False
		container = dict(item['container'])
		our_currency = obj.attributes.get('currency', category='money')
		if currency != our_currency:
			# currency exchanges must be done through the payer
			try:
				value = payer.do_currency_exchange(value, to_currency=our_currency, from_currency=currency)
			except NoSuchBehavior:
				return False
		
		value += obj.attributes.get('value', default=0, category='money')
		obj.attributes.add('value', value, category='money')
		obj.emote('beeps')
		# TODO: move this into the spawner behavior
		container_obj = spawn(container)[0]
		if adds := item.get('design'):
			# we add the design here
			design = spawn(adds)[0]
			container_obj.parts.attach(design)
		# TODO: use material properties and stuff
#		filled = craft(recipe, mats,[])
		# quant = recipe.pop('quantity', 1)
		recipes = copy(item['recipes'])
		mats = copy(item['materials'])
		for item in recipes:
			for _ in generate_new_object([item], mats, container_obj):
				continue
		container_obj.emote(
			f"falls into the retrieval compartment of @{obj.sdesc.get(strip=True)}",
			include=[obj, container_obj], receivers=obj.location.contents
		)
		container_obj.location = obj
		return True

	def use(obj, user, **kwargs):
		if in_stock := obj.db.stock:
			in_stock = in_stock.deserialize()
			# FIXME: the "Union" cmdset merge I wanted to use doesn't work
			FormatEvMenu(user, get_classpath(VendingMenu), vendor=obj, stock=in_stock,
				startnode="menunode_start")#, cmdset_mergetype='Union', cmdset_priority=102)


@behavior
class WalletBehavior(Behavior):
	"""
	Adds pay-in and pay-out behaviors to the object.
	"""
	priority = 1

	def pay_in(obj, value, currency, payer, **kwargs):
		"""
		Receive `value` amount of money from another object

		Returns True if the money was accepted successfully, False otherwise
		"""
		our_currency = obj.attributes.get('currency', category='money')
		if currency != our_currency:
			# currency exchanges must be done through the payer
			try:
				value = payer.do_currency_exchange(value, to_currency=our_currency, from_currency=currency)
			except NoSuchBehavior:
				return False
		value += obj.attributes.get('value', default=0, category='money')
		obj.attributes.add('value', value, category='money')
		return True

	def pay_out(obj, value, recipient, **kwargs):
		"""
		Pay out `value` amount of money from ourselves to recipient

		Returns True if the transaction completed successfully, False otherwise
		"""
		print(f"paying out from {obj} to {recipient}")
		wallet = obj.attributes.get('value', category='money', default=0)
		if value > wallet:
			print("not enough money")
			return False
		try:
			print("paying in")
			success = recipient.do_pay_in(value, obj.attributes.get('currency', category='money'), obj, **kwargs)
			print(f"paying in result: {success}")
		except NoSuchBehavior:
			print("recipient cannot receive money")
			return False

		if success:
			obj.attributes.add('value', wallet - value, category='money')
			return True
		else:
			return False

@behavior
class BankingBehavior(WalletBehavior):
	def currency_exchange(obj, value, to_currency=None, from_currency=None):
		# TODO: handle currency stuff, including banking exchange rates
		return value

	def pay_out(obj, value, recipient, **kwargs):
		# TODO: link these to accounts
		obj.db.value = value
		return WalletBehavior.pay_out(obj, value, recipient, **kwargs)

	def use(obj, user, **kwargs):
		FormatEvMenu(user, 'systems.money.atm_menu', cmd_on_exit=None, startnode="menunode_login", atm=obj)
		return True