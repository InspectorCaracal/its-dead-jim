from collections import Counter, defaultdict
from random import choice, shuffle
from evennia.utils.create import create_object
from evennia.utils.utils import is_iter

from core.scripts import Script
from systems.crafting.automate import generate_new_object
from utils.timing import delay_iter


class ShopManager(Script):
	"""a script for tracking shop management stuff"""

	def at_script_creation(self):
		super().at_script_creation()

		# STRUCTURE: prototype_key: shelf_tag
		self.db.stocking_rules = {}
		# STRUCTURE: bar code ID: (prototype_key, materials, price, quantity)
		# TODO: create a method that generates the unique ID from the key/material data
		self.db.stock_quotas = {}
	
	def check_inventory(self, *rooms):
		"""returns a list of what expected inventory needs to be ordered/replaced"""
		expected_stock = self.db.stock_quotas.deserialize()
		if not expected_stock:
			return {}
		restock = { i: val[3] for i, val in enumerate(expected_stock) }
		store_rooms = [room for room in rooms if room.tags.has('shop_storage')]
		rooms = [room for room in rooms if room not in store_rooms]
		shop_stock = [item for room in store_rooms for item in room.get_all_contents()]
		if tagged_shelves := self.get_shop_shelves(*rooms):
			for shelf, _ in tagged_shelves:
				shop_stock.extend(shelf.contents)
				in_stock = Counter(item.tags.get(category="from_prototype") for item in shelf.contents)
				for key, count in in_stock.items():
					if key in restock:
						restock[key] -= count
		
		restock = {key: (count,) + (expected_stock[key][1:]) for key, count in restock.items() if count > 0}
		return restock

	def get_shop_shelves(self, *rooms):
		# get all possible shelves
		tagged_shelves = []
		for room in rooms:
			shelves = room.decor.all() + [p for d in room.decor.all() for p in d.parts.all()]
			# get all the actually tagged shelves
			for shelf in shelves:
				if tags := shelf.tags.get(category="shop_shelf", return_list=True):
					tagged_shelves.append((shelf, tags))
		
		return tagged_shelves

	def sort_stock(self, rooms, *objs):
		"""this is terrible!"""
		rules = self.db.stocking_rules.deserialize()
		if not is_iter(rooms):
			rooms = [rooms]
		
		if not (tagged_shelves := self.get_shop_shelves(*rooms)):
			return {}

		stock_to = defaultdict(list)
		protos_to_shelf = defaultdict(set)
		# build a dict of what shelves already have what stuff stocked on it
		for shelf, tags in tagged_shelves:
			protos = set(item.tags.get(category="from_prototype") for item in shelf.contents)
			for proto in protos:
				protos_to_shelf[proto].add(shelf)

		for obj in objs:
			proto = obj.tags.get(category="from_prototype")
			# check if there's already a shelf for this prototype
			shelf_options = protos_to_shelf.get(proto, [])
			# if not, check if there's rules for it and filter by those
			print(shelf_options)
			if not shelf_options:
				print('a')
				if opts := rules.get('proto', []):
					shelf_options = [ shelf for shelf, tags in tagged_shelves if any(t for t in tags if t in opts) ]
				print('b')
				if shelf_options:
					filtered = [ shelf for shelf in shelf_options if any(item.tags.has(proto, category="from_prototype") for item in shelf.contents) ]
					if filtered:
						shelf_options = filtered
				else:
					print('qq')
					# last ditch option, just use all the shelves as options
					shelf_options = [s for s, _ in tagged_shelves]
			print(shelf_options)
			shelf = choice(list(shelf_options))
			# assign this shelf
			stock_to[shelf].append(obj)
			# also update the protos_to_shelf dict
			protos_to_shelf[proto].add(shelf)
		
		# we're finally done
		return stock_to


class ShopRestocker(Script):
	"""
	Placeholder system for refreshing a shop's stock, intended to be attached to the shop's store room.
	Can be added to the main shop room for single-room shops
	
	TODO: Later on, this system needs to account for things like traffic and suppliers.
	"""
	def at_script_creation(self):
		super().at_script_creation()
		self.key = "delivery system"
		self.interval = 600
		self.db.count = 0
	
	def at_repeat(self, **kwargs):
		self.db.count += 1
		if not (manager := self.obj.db.store_manager):
			return
		to_tag = []
		for obj in self.obj.contents_get(content_type="object"):
			if obj.parts.search('price tag'):
				continue
			else:
				to_tag.append(obj)
			if len(to_tag) > 10:
				break

		prices = { key: val[1] for key, val in manager.db.stock_quotas.items() }
		# tag the first 10 items
		for obj in to_tag:
			proto = obj.tags.get(category='from_prototype')
			if price := prices.get(proto):
				price_tag = create_object(key='price tag', attributes=[('price', (price))])
				obj.parts.attach(price_tag)

		if self.db.count % 10:
			return
		rooms = self.db.rooms or [self.obj]
		if restock := manager.check_inventory(*rooms):
			# spawn some of the stuff in here and drop it
			recipes = []
			for key in restock.keys():
				recipes.extend([key]*restock[key][0])
			# TODO: set up the stock so i can specify materials in the listings
			gener = generate_new_object(recipes, {}, self.obj)
			# i don't think this need to be persistent
			delay_iter(gener, 0.2)

