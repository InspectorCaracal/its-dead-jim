from base_systems.effects.base import Effect


class ShopClerkEffect(Effect):
	duration = 30

	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		if register := kwargs.get("register"):
			self.owner.db.cash_register = register
		if backroom := kwargs.get('employee_room'):
			self.owner.db.employee_room = backroom
		self.owner.behaviors.add("ShopClerkBehavior")
		# TODO: add triggers for specific methods
		self.owner.react.add("on_object_enter", "self.do_receive_object")
		self.owner.react.add("customer_done", "self.do_work")
		# TODO: maybe add a greet to arrival, or that might be a diff effect
	
	def at_delete(self, *args, **kwargs):
		self.owner.behaviors.remove("ShopClerkBehavior")
		del self.owner.db.employee_room
		del self.owner.db.cash_register
		super().at_delete(*args, **kwargs)

	def at_tick(self, *args, **kwargs):
		self.owner.do_work()


class HelpingCustomerEffect(Effect):
	def at_create(self, *args, **kwargs):
		super().at_create(*args, **kwargs)
		self.owner.db.now_helping = kwargs.get('source')
		self.owner.behaviors.add("CheckoutClerkBehavior")
		self.owner.react.add("on_object_enter", "self.do_receive_object")
		self.owner.react.add("finalize_sale", "self.do_bag_items")
		self.owner.react.add("departure", "self.do_customer_leave")
	
	def at_delete(self, *args, **kwargs):
		self.owner.behaviors.remove("CheckoutClerkBehavior")
		del self.owner.db.now_helping
		super().at_delete(*args, **kwargs)
		self.owner.on_customer_done(*list(self.sources.keys()))

	def at_add(self, *args, **kwargs):
		if not all([self.owner.db.cash_register, kwargs.get('source')]):
			self.delete()
		elif not self.sources:
			customer = kwargs.get('source')
			# TODO: hook this into personality later
			speech = f"Hello! Please hand me the things you'd like to buy."
			emote = self.owner.at_pre_say(speech, target=customer)
			self.owner.emote(emote, include=customer)
			customer.on_spoken_to(self.owner, speech)
			super().at_add(*args, **kwargs)