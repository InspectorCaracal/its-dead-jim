from evennia.utils import logger

from base_systems.actions.base import Action, InterruptAction
from base_systems.exits.base import ExitAction
from base_systems.things.actions import DropAction, GiveAction, PutAction
from utils.strmanip import numbered_name
from utils.timing import delay


class RestockAction(Action):
	move = "restock"

	def __init__(self, actor, **kwargs):
		self.actor = actor # ????
		super().__init__(actor, **kwargs)
	
	def _get_exit_to(self, destination):
		# TODO: this is going to need a better solution to account for potentially having to travel through multiple rooms
		exits = [ex for ex in self.actor.location.contents_get(content_type="exit") if ex.destination == destination]
		if exits:
			return exits[0]
	
	def do(self, *unstocked, **kwargs):
		unstocked = self.actor.contents
		if not unstocked:
			for obj in self.actor.location.contents_get(content_type='object'):
				if not obj.parts.search('price tag'):
					continue
				if not self.actor.at_pre_object_receive(obj, obj.location):
					break
				unstocked.append(obj)
		if unstocked:
			unstocked = unstocked[:10] #FIXME
			for obj in unstocked:
				obj.location = self.actor
			if manager_script := self.actor.location.db.store_manager:
				rooms = self.actor.location
				if backroom := self.actor.db.employee_room:
					print(f"room {backroom}")
					# TODO: this likely needs to be changed eventually
					if scr := backroom.scripts.get('delivery system'):
						rooms = scr[0].db.rooms or rooms
				restock_data = manager_script.sort_stock(rooms, *unstocked)
				if restock_data:
#				if restock_data := manager_script.sort_stock(self.actor.location, *unstocked):
					shelf = list(restock_data.keys())[0]
					if shelf.baseobj.location != self.actor.location:
						if ex := self._get_exit_to(shelf.baseobj.location):
							try:
								action = ExitAction(actor=self.actor, exit_obj=ex)
								self.actor.actions.add(action)
							except InterruptAction:
								return self.end()
					items = restock_data[shelf]
					try:
						action = PutAction(self.actor, targets=items, destination=shelf)
					except InterruptAction:
						return self.end()
					self.delay(10, end=True)
					self.actor.actions.add(action)
					return
			else:
				# FIXME: THIS IS TEMPORARY FOR DEBUGGING
				try:
					action = DropAction(self.actor, targets=unstocked)
				except InterruptAction:
					return self.end()
				self.delay(10, end=True)
				self.actor.actions.add(action)
		else:
			if self.actor.location != self.actor.db.employee_room:
				if ex := self._get_exit_to(self.actor.db.employee_room):
					try:
						action = ExitAction(actor=self.actor, exit_obj=ex)
						self.actor.actions.add(action)
						action = RestockAction(self.actor)
						self.actor.actions.add(action)
					except InterruptAction:
						pass

		return self.end()

	def status(self):
		return "You are restocking."
	

class AttendCustomerAction(Action):
	move = "work"


class ReadOffTotal(Action):
	move = "work"

	def __init__(self, actor, register, customer, **kwargs):
		self.actor = actor
		self.register = register
		self.customer = customer
		super().__init__(**kwargs)
	
	def start(self, *args, **kwargs):
		if not (self.register and self.customer):
			self.fail()
		if self.customer.location != self.actor.location:
			self.fail()
		
		super().start(*args, **kwargs)
	
	def do(self, *args, **kwargs):
		total, currency = self.register.do_total(self.actor)
		
		speech = f"Your current total is {numbered_name(currency, total)}."
		emote = self.actor.at_pre_say(speech, target=self.customer)
		self.actor.emote(emote, include=self.customer)
		self.customer.on_spoken_to(self.actor, speech)
		self.end()
	
	def fail(self, *args, **kwargs):
		self.actor.effects.remove("systems.money.shopping.effects.HelpingCustomerEffect", stacks="all")
		self.end()


class BagItems(Action):
	move = "bag"
	duration = 2

	def __init__(self, actor, customer, sold_items, **kwargs):
		self.actor = actor
		self.sold_items = sold_items
		self.customer = customer
		self.remaining_items = sold_items
		self.bags = []
		super().__init__(**kwargs)
	
	def do(self, *args, **kwargs):
		if not self.bag_spawner:
			logger.log_warn(f"no bag spawner provided to {self.actor}")
			return self.end()
		# spawn bags as needed and fill
		bagged = []
		if bag := self.bag_spawner.do_spawn(count=1):
			self.bags.append(bag)
			while bag_me := self.remaining_items.pop(0, None):
				if not bag.at_pre_object_receive(bag_me):
					break
				if not bag_me.move_to(bag, quiet=True, muffle_hooks=True):
					break
				bagged.append(bag_me)
			if not bag.contents:
				# something went horribly wrong
				self.remaining_items.extend(bagged)
				return self.end()

			if not self.remaining_items:
				# we done
				return self.end()

			self.delay(self.duration, end=False)
		
		else:
			return self.end()


	def end(self, *args, **kwargs):
		self.remaining_items += self.bags
		if self.remaining_items:
			# hand over the items
			speech = "Thank you, here are your items. Have a nice day!"
			emote = self.actor.at_pre_say(speech, target=self.customer)
			self.actor.emote(emote, include=self.customer)
			self.customer.on_spoken_to(self.actor, speech)
			try:
				action = GiveAction(self.actor, self.remaining_items, receiver=self.customer)
			except InterruptAction:
				action = DropAction(self.actor, self.remaining_items)
			self.actor.actions.add(action)
		self.actor.effects.remove("systems.money.shopping.effects.HelpingCustomerEffect", source=self.customer)
		super().end()