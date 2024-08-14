from base_systems.things.base import Thing
# TODO: port in the Bank scripts system

# for initial pre-alpha testing, it just prints money instead of hook up to a bank account
# by "print money" i mean you put in a cash card and it recharges it by N dollars
class ATMObject(Thing):
	def at_object_creation(self):
		super().at_object_creation()
		self.db.value = 0
		if self.size == 1:
			self.size = 8
		self.behaviors.add("BankingBehavior")


