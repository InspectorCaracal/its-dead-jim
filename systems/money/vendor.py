
from base_systems.things.base import Thing
from systems.crafting.automate import craft
from systems.money.vendor_recipes import SNACK_MACHINE
from utils.menus import MenuTree


class VendingMachine(Thing):
	"""
	TODO: make this actually part of the system omg
	"""
	def at_object_creation(self):
		super().at_object_creation()
		if not self.db.currency:
			self.db.currency = "dollar"
		self.behaviors.add("WalletBehavior")
		self.behaviors.add("VendingBehavior")
		if not self.db.stock:
			self.db.stock = SNACK_MACHINE


class VendingMenu(MenuTree):
	"""
	aaaaaaa
	"""
	def menunode_start(self, caller, raw_string, **kwargs):
		text = "Choose an option"
		options = []
		for item in self.menu.stock:
			desc = f"{item['name']} (${item['price']:.2f})"
			options.append(
				{ 'desc': desc, 'goto': ("menunode_pay", {'item': item})}
			)
		
		return text, options
	
	def menunode_pay(self, caller, raw_string, item, **kwargs):
		text = "Enter your card"

		options = [
			{ 'desc': obj.get_display_name(caller), 'goto': (self._buy_item, {'item': item, 'card': obj}) }
			for obj in caller.contents if obj.can_pay_out
		]

		return text, options
	
	def _buy_item(self, caller, raw_string, item, card, **kwargs):
		price = item['price']
		# FIXME: it should verify the currency exchagne before paying?
		if not card.do_pay_out(price, self.menu.vendor, stock_recipe=item):
			caller.msg("You couldn't buy that.")
			return "menunode_end"
		return "menunode_start"
			
	def menunode_end(self, *args, **kwargs):
		return