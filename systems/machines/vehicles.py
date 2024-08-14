import time
from evennia import TICKER_HANDLER as tickerhandler
from evennia.utils import logger

from base_systems.maps.building import get_by_id

from base_systems.things.base import Thing
from base_systems.maps.pathing import get_path_in_direction, get_exit_for_path

# TODO: all the speed settings should be in NDB that are preserved and reloaded on a warm reload but cleared on a cold start

class DrivableThing(Thing):

	@property
	def engine(self):
		if engine := self.parts.search("engine", part=True):
			if len(engine) > 1:
				# ???
				engine = engine[:1]
			return engine[0]
		return None
	
	@property
	def throttle(self):
		if accel := self.parts.search("engine_throttle", part=True):
			if len(accel) > 1:
				# ???
				accel = accel[:1]
			return accel[0]
		return None

	@property
	def steering(self):
		if steering := self.parts.search("steering", part=True):
			if len(steering) > 1:
				# ???
				steering = steering[:1]
			return steering[0]
		return None

	@property
	def brake(self):
		if brake := self.parts.search("brake", part=True):
			if len(brake) > 1:
				# ???
				brake = brake[:1]
			return brake[0]
		return None

	@property
	def can_drive(self):
		if not all( (self.throttle, self.engine, self.steering) ):
			return False
		# TODO: check the actual syntax for required parts in craftables
		if len(self.parts.search("wheel", part=True)) < (self.db.req_wheels or 0):
			return False

		return True

	def start(self):
		# start the move ticker
		self.db.last_step = time.time()
		tickerhandler.add(5, self.move_tick)
	
	def stop(self):
		# stop the move ticker
		tickerhandler.remove(5, self.move_tick)

	def set_throttle(self, value):
		if not (throttle := self.throttle):
			return 0
		current = throttle.db.pct or 0
		if current == value:
			return 0
		if 0 <= value <= 100:
			throttle.db.pct = value
			if value > current:
				return 1
			else:
				return -1

	def get_speed(self):
		if not self.can_drive:
			self.db.speed = 0
			return 0
		
		now = time.time()
		last_step = self.db.last_step or now
		max_power = self.engine.stats.power.value
		percent = self.throttle.db.pct or 0
		speed = self.db.speed or 0
		drag_coeff = 1/(self.size*10)
		# TODO: include wheel/tire size
		# TODO: include gearing

		power = max_power * percent/100.0
		drag = drag_coeff * speed**2
		accel = (power - drag)/(self.size/2)  #self.weight

		logger.log_msg(f"({power} - {drag})/({self.size}/2) = {accel}")

		new_speed = speed + accel*(now - last_step)
		self.db.speed = max(new_speed, 0)
		return new_speed
	
	def move_tick(self):
		crash = False
		if path := self.db.drive_path:
			target_id, route, crash = path
			logger.log_msg(path)
			target = get_by_id(target_id)
			route = route[1:-1]
			for room_id in route:
				if room_id == self.location.id or room_id == target_id:
					continue
				# TODO: include direction of travel
				room = get_by_id(room_id)
				self.emote("drives through", receivers=room.contents)
			# TODO: check traversal checks on the exit
			if route and (ex := get_exit_for_path(route[-1], target_id)):
				direction = ex.direction
			else:
				direction = self.db.direction
		else:
			target = None
			direction = self.db.direction
		if crash:
			self.db.speed = 0
			del self.db.drive_path
		else:
			speed = self.get_speed()
			if not speed:
				self.stop()
				return
			logger.log_msg(direction)
			if new_path := get_path_in_direction(target or self.location, direction, speed//10):
				self.db.direction = direction
				self.db.drive_path = new_path
				# TODO: message next move to driver
		self.db.last_step = time.time()
		if target != self.location:
			self.move_to(target, move_type="crash" if crash else "cross")
		if not self.db.speed:
			self.stop()
	
	def at_pre_move(self, destination, **kwargs):
		if not super().at_pre_move(destination, **kwargs):
			return False
		if posed := self.location.posing.get(self):
			_, posed = posed
			self.ndb.riding = posed
		return True
	
	def at_post_move(self, source_location, **kwargs):
		super().at_post_move(source_location, **kwargs)
		if riders := self.ndb.riding:
			for rider in riders:
				if rider.location == source_location:
					rider.location = self.location
					self.location.posing.add(rider, self, "riding")
					rider.msg(rider.at_look(self.location), options=None)
