from random import choice, randint
from evennia import AttributeProperty
from core.scripts import Script

class PhoneBookScript(Script):
	key = "phonebook"
	numbers = AttributeProperty(default=None)

	def at_script_creation(self, **kwargs):
		super().at_script_creation(**kwargs)
		self.numbers = {}
	
	def add_record(self, number, phone, **kwargs):
		# TODO: add some validation here or something
		if existing := self.numbers.get(number):
			return existing == phone
		else:
			self.numbers[number] = phone
			return True
	
	def del_record(self, number, phone, **kwargs):
		if self.numbers.get(number) == phone:
			# only clear if the number is actually attached to the given phone
			del self.numbers[number]
			return True
	
	def get_by_number(self, number, **kwargs):
		number = str(number)
		return self.numbers.get(number)
	
	def get_by_phone(self, phone, **kwargs):
		numbers = self.numbers.deserialize()
		if phones := [ n for n, p in numbers.items() if p == phone ]:
			return phones[0]
	
	def assign_number(self, phone, **kwargs):
		# generate random number
		check_me = choice(range(1000000,10000000))
		new_number = None
		# cap how many loops we can do
		for _ in range(500):
			if str(check_me) not in self.numbers:
				# it's free!
				new_number = check_me
				break
			# increment instead of rerolling, more efficient
			check_me += 1
			if check_me >= 10000000:
				# it's exceeded 7 digits, reroll
				check_me = choice(range(1000000,10000000))
		if new_number:
			# only assign phone if a number was successfully assigned
			new_number = str(new_number)
			self.numbers[new_number] = phone
		return new_number

	def at_repeat(self):
		"""
		Randomly spam call someone!
		"""
		self.clear_dead_lines()
		if randint(0,50) >= len(self.numbers.keys()):
			# no call
			return
		
		callme = choice(self.numbers.keys())
		# do the phone call here, once it's a thing

	def clear_dead_lines(self):
		records = self.numbers.deserialize()
		for key, val in self.numbers.items():
			if not val:
				del records[key]
		self.numbers = records