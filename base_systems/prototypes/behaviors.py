from copy import copy
from evennia.utils.utils import is_iter, make_iter


from core.ic.behaviors import Behavior, behavior
from base_systems.prototypes.spawning import spawn
from systems.crafting.automate import generate_new_object

@behavior
class Spawner(Behavior):
	def spawn(obj, data=None, count=1, **kwargs):
		"""
		main spawning logic - it takes data or references the `spawn_data` attribute on itself

		returns a list
		"""
		if not data:
			data = obj.db.spawn_data
		if maximum := obj.db.stock_limit:
			count = min(count, maximum)
		
		if not count:
			return []
		
		locations = None
		if container := data.get('container'):
			# TODO: add better support for more complex containers
			if result := spawn(*[container]*count):
				locations = result[:count]
			if locations and (design := container.get('design')):
				# we add the design here
				if result := spawn(design):
					design_obj = result[:count]
				if design_obj:
					for i in range(count):
						locations[i].parts.attach(design_obj[i])
		if not locations:
			# to account for both no container being set, and for the spawn going wrong
			locations = obj
		prior_contents = []
		recipes = copy(data.get('recipes', []))
		mats = copy(data.get('materials',[]))
		if is_iter(locations):
			# we make the recipes for each container
			for location in locations:
				prior_contents.extend(location.contents)
				for item in recipes:
					for _ in generate_new_object([item], mats, location):
						continue
		else:
			# we make N recipes for the one location
			location = locations
			prior_contents = location.contents
			for item in recipes:
				for _ in generate_new_object([item]*count, mats, location):
					continue
		
		if maximum:
			obj.db.stock_limit -= count
		# this is the goofiest hack lol
		new_contents = [o for loc in make_iter(locations) for o in loc.contents if o not in prior_contents]
		return list(new_contents)