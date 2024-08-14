import time
from evennia import CmdSet
from evennia import TICKER_HANDLER as tickerhandler
from evennia.utils import logger

from base_systems.maps.building import get_by_id
from base_systems.maps.pathing import get_exit_for_path, get_path_in_direction

from core.commands import Command
from core.ic.behaviors import Behavior

# TODO: convert these to Actions, probably?
class CmdDrive(Command):
	key = "drive"
	help_category = "Vehicles"

	def at_pre_cmd(self):
		if super().at_pre_cmd():
			return True
		self.vehicle = None
		for obj in self.caller.holding().values():
			if obj.tags.has('steering', category='part') and obj.baseobj != obj:
				vehicle = obj.baseobj
				try:
					if vehicle.do_drive():
						self.vehicle = vehicle
						break
					else:
						self.msg(f"You cannot drive {vehicle.get_display_name(self.caller, article=True)} anywhere.")
						return True
				except AttributeError:
					pass
				
		if not self.vehicle:
			self.msg("You don't have a vehicle to drive.")
			return True

	def func(self):
		caller = self.caller
		vehicle = self.vehicle

		if self.args:
			# TODO: account for turning radius
			vehicle.db.direction = self.args
		
		if direction := vehicle.db.direction:
			self.msg(f"You drive the {vehicle.get_display_name(caller)} {direction}.")
			self.vehicle.start()
			

class CmdAccel(Command):
	key = "accelerate"
	aliases = ('throttle',)
	help_category = "Vehicles"

	def at_pre_cmd(self):
		if super().at_pre_cmd():
			return True
		self.vehicle = None
		for obj in self.caller.holding().values():
			if obj.tags.has('throttle', category='part') and obj.baseobj != obj:
				vehicle = obj.baseobj
				try:
					if vehicle.do_drive():
						self.vehicle = vehicle
						break
					else:
						self.msg(f"You cannot drive {vehicle.get_display_name(self.caller, article=True)} anywhere.")
						return True
				except AttributeError:
					pass
		
		if not self.vehicle:
			self.msg("You don't have a vehicle to drive.")
			return True

	def func(self):
		if self.args:
			try:
				pct = int(self.args)
			except ValueError:
				pct = 50
		else:
			pct = 50
		
		change = self.vehicle.set_throttle(pct)
		if not change:
			self.msg("You don't do anything.")
		elif change > 0:
			self.msg("You start speeding up.")
		else:
			self.msg("You ease off the acceleration.")

class CmdBrake(Command):
	key = "brake"
	help_category = "Vehicles"

	def at_pre_cmd(self):
		if super().at_pre_cmd():
			return True
		self.vehicle = None
		for obj in self.caller.holding().values():
			if obj.tags.has('brake', category='part') and obj.baseobj != obj:
				vehicle = obj.baseobj
				try:
					if vehicle.do_drive():
						self.vehicle = vehicle
						break
					else:
						self.msg(f"You cannot drive {vehicle.get_display_name(self.caller, article=True)} anywhere.")
						return True
				except AttributeError:
					pass
		
		if not self.vehicle:
			self.msg("You don't have a vehicle to drive.")
			return True

	def func(self):
		mapping = { "hard": 100, "soft": 25, "": 50 }
		if not (pct := mapping.get(self.args)):
			try:
				pct = int(self.args)
			except ValueError:
				pct = 50
		
		self.vehicle.set_brake(pct)
	
class DrivingCmdSet(CmdSet):
	key = "Driving CmdSet"

	def at_cmdset_creation(self):
		self.add(CmdDrive)
		self.add(CmdAccel)
		self.add(CmdBrake)


class Driveable(Behavior):
	priority = 10

	def drive(obj):
		if not all(
			obj.parts.search("engine", part=True),
			obj.parts.search("steering", part=True),
			obj.parts.search("engine_throttle", part=True),
		):
			return False
		# required parts in craftables is just a boolean exists/doesn't check, so this is right
		if len(obj.parts.search("wheel", part=True)) < (obj.db.req_wheels or 0):
			return False
		return True

	def start(obj):
		# start the move ticker
		obj.db.last_step = time.time()
		tickerhandler.add(5, obj.do_move_tick)
	
	def stop(obj):
		# stop the move ticker
		tickerhandler.remove(5, obj.do_move_tick)

	def set_throttle(obj, value):
		if not (throttle := obj.parts.search("engine_throttle", part=True)):
			return 0
		throttle = throttle[0]
		current = throttle.db.pct or 0
		if current == value:
			return 0
		if 0 <= value <= 100:
			throttle.db.pct = value
			if value > current:
				return 1
			else:
				return -1
	
	def set_brake(self, obj, value):
		# at the moment this is not used so it's not finished
		if not (brake := obj.parts.search("brake", part=True)):
			return 0
		brake = brake[0]
		current = brake.db.pct or 0

	def _get_speed(obj):
		if not (throttle := obj.parts.search("engine_throttle", part=True)):
			return 0
		if not (engine := obj.parts.search("engine", part=True)):
			return 0
		if not obj.can_drive:
			obj.db.speed = 0
			return 0
		
		now = time.time()
		last_step = obj.db.last_step or now
		max_power = engine.stats.power.value
		percent = throttle.db.pct or 0
		speed = obj.db.speed or 0
		drag_coeff = 1/(obj.size*10)
		# TODO: include wheel/tire size
		# TODO: include gearing

		power = max_power * percent/100.0
		drag = drag_coeff * speed**2
		accel = (power - drag)/(obj.size/2)  #self.weight

		logger.log_msg(f"({power} - {drag})/({obj.size}/2) = {accel}")

		new_speed = speed + accel*(now - last_step)
		obj.db.speed = max(new_speed, 0)
		return new_speed
	
	def move_tick(obj):
		crash = False
		if path := obj.db.drive_path:
			target_id, route, crash = path
			logger.log_msg(path)
			target = get_by_id(target_id)
			route = route[1:-1]
			for room_id in route:
				if room_id == obj.location.id or room_id == target_id:
					continue
				# TODO: include direction of travel
				room = get_by_id(room_id)
				obj.emote("drives through", receivers=room.contents)
			# TODO: check traversal checks on the exit
			if route and (ex := get_exit_for_path(route[-1], target_id)):
				direction = ex.direction
			else:
				direction = obj.db.direction
		else:
			target = None
			direction = obj.db.direction
		if crash:
			obj.db.speed = 0
			del obj.db.drive_path
		else:
			speed = Driveable._get_speed(obj)
			if not speed:
				obj.stop()
				return
			logger.log_msg(direction)
			if new_path := get_path_in_direction(target or obj.location, direction, speed//10):
				obj.db.direction = direction
				obj.db.drive_path = new_path
				# TODO: message next move to driver
		obj.db.last_step = time.time()
		if target != obj.location:
			obj.move_to(target, move_type="crash" if crash else "cross")
		if not obj.db.speed:
			obj.stop()
	