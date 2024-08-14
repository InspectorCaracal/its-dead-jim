from string import punctuation
from random import choice, choices
import time
from class_registry import ClassRegistry, AutoRegister
from abc import abstractmethod

from evennia import search_object, GLOBAL_SCRIPTS
from evennia.utils import delay, is_iter, iter_to_str, logger

from core.ic.behaviors import NoSuchBehavior
from utils.menus import FormatEvMenu

APP_REGISTRY = ClassRegistry('key', unique=True)

class AppHandler:
	status = ''

	def __init__(self, obj):
		self.obj = obj
		self.load()

	def load(self):
		app_data = {}
		if db_data := self.obj.attributes.get("app_data", category="software"):
			db_data = db_data.deserialize()
			for key, val in db_data.items():
				app_data[key] = APP_REGISTRY.get(key, self, **val)
		
		self.app_data = app_data

	def save(self):
		app_data = {}
		for key, item in self.app_data.items():
			data = dict(vars(item))
			data.pop('handler')
			app_data[key] = data
		self.obj.attributes.add("app_data", app_data, category="software")

	def display(self, appkey=None, **kwargs):
		screen = 'Your Background Here'
		if app := self.get(appkey):
			screen = f"It currently has {appkey} open."
			if hasattr(app, 'display'):
				if display := app.display(**kwargs):
					screen += "\n\n"+display
			if app.output:
				screen += f"\n\n{app.output}"
		elif self.status:
			screen = f'"{self.status}"'
		return screen

	def msg(self, message, **kwargs):
		if kwargs.pop('sound', False):
			try:
				self.obj.baseobj.do_make_sound(message, **kwargs)
			except NoSuchBehavior:
				pass
		elif kwargs.pop("emote", False):
			self.obj.baseobj.emote(message, **kwargs)
		else:
			self.obj.baseobj.msg(message, **kwargs)
			self.obj.baseobj.location.msg(message, **kwargs)

	def listen(self, speaker, input, **kwargs):
		if not input:
			return
		input = input.lower().strip(punctuation)
		words = input.split()
		action = words[0]
		args = words[1:] if len(words) > 1 else []
		self.use(speaker, action, *args, **kwargs)

	def install_app(self, app_key, *args, **kwargs):
		# TODO: implement better error handling
		if self.get(app_key):
			# already installed
			return False
		if app_key not in APP_REGISTRY.keys():
			# invalid app
			return False
		new_app = APP_REGISTRY.get(app_key, self, *args, **kwargs)
		if new_app.at_install():
			self.app_data[app_key] = new_app
			self.save()
			return True
		else:
			# somehow installation failed
			return False
	
	def delete_app(self, app_key):
		if self.app_data.get(app_key):
			del self.app_data[app_key]
			self.save()
			return True
		# TODO: better handling of no match vs multimatch
		return False
	
	def search_app(self, search_terms, keys=False, installed=True):
		term_list = search_terms if is_iter(search_terms) else [search_terms]
		if not installed:
			results = [app_key for app_key in APP_REGISTRY.keys() if any(term in app_key.lower() for term in term_list)]
			results = [key for key in results if key not in self.app_data]
		else:
			results = [key if keys else app for key, app in self.app_data.items() if any(term in key.lower() for term in term_list)]
		return results

	def get(self, app_key):
		return self.app_data.get(app_key)
	
	def use(self, user, action, *args, **kwargs):
		self.status = ''
		match action:
			case 'menu':
				session = user.sessions.all()[0]
				session.ndb.apps = self
				FormatEvMenu(session, 'systems.electronics.software.menus.AppHandlerMenu', startnode="menunode_main")
			case 'install':
				results = self.search_app(args, installed=False)
				match len(results):
					case 0:
						self.status = f"No apps matching {' '.join(args)}"
						self.msg('beeps unhappily', sound=True)
					case 1:
						if self.install_app(results[0]):
							self.msg("dings!", sound=True)
						else:
							self.status = f"Could not install {results[0]}"
							self.msg('beeps unhappily', sound=True)
			case 'uninstall' | 'delete':
				results = self.search_app(args, keys=True)
				match len(results):
					case 0:
						self.status = f"No apps matching {' '.join(args)}"
						self.msg('beeps unhappily', sound=True)
					case 1:
						if self.delete_app(results[0]):
							self.status = f"{results[0]} successfully uninstalled."
							self.msg("dings!", sound=True)
						else:
							self.status = f"Could not uninstall {results[0]}"
							self.msg('beeps unhappily', sound=True)
			case 'open':
				results = self.search_app(" ".join(args))
				if len(results) == 1:
					self.obj.db.active_app = results[0].key
					self.msg("dings!", sound=True)
				else:
					self.msg("beeps unhappily", sound=True)
			case 'close':
				if args[0].strip() == 'app':
					self.obj.db.active_app = ''
					self.msg("dings!", sound=True)
				else:
					results = self.search_app(" ".join(args))
					if len(results) == 1:
						if self.obj.db.active_app == results[0].key:
							self.obj.db.active_app = ''
							self.msg("dings!", sound=True)
			case _:
				try:
					attr = getattr(self.obj.baseobj, f"do_{action}")
				except AttributeError:
					self.msg('beeps?', sound=True)
				else:
					attr(*args, user=user)


class BaseApp(metaclass=AutoRegister(APP_REGISTRY)):
	key = "base_app"
	output = ''

	# TODO: add possibly-customizable app display info

	def __init__(self, handler, **kwargs):
		self.handler = handler
		for key, val in kwargs.items():
			if attr := getattr(self, key, None) and callable(attr):
				continue
			setattr(self, key, val)

	@abstractmethod
	def at_install(self, *args, **kwargs):
		raise NotImplementedError()

	def use(self, *args, **kwargs):
		raise NotImplementedError()

	def settings(self, *args, **kwargs):
		raise NotImplementedError()

	def display(self, *args, **kwargs):
		raise NotImplementedError()

	def msg(self, message, **kwargs):
		self.handler.msg(message, **kwargs)

	def close(self):
		if self.handler.obj.db.active_app == self.key:
			self.handler.obj.db.active_app = ''
			return True

from base_systems.maps import pathing
from data.maps import LANDMARKS

class NaviApp(BaseApp):
	key = "NaviMate"

	landmarks = None
	active = False
	route = None
	last_check = None
	weight = None
	up_next = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.tick()
	
	def at_install(self, *args, **kwargs):
		self.landmarks = {}
		for key, id in LANDMARKS.items():
			room = search_object(id, exact=True, use_dbref=True)
			self.landmarks[key] = room
		return True

	def msg(self, message, **kwargs):
		message = f'@Me says, "{message}"'
		kwargs['emote'] = True
		super().msg(message, **kwargs)

	def listen(self, speaker, input, **kwargs):
		if not input:
			return
		input = input.lower().strip(punctuation)
		words = input.split()
		action = words[0]
		args = " ".join(words[1:]) if len(words) > 1 else ''
		if self.use(speaker, action, args=args) is None:
			return self.handler.listen(speaker, input, **kwargs)

	def use(self, user, action, **kwargs):
		if action == "navigate":
			destination = kwargs.pop('args', '').strip()
			location, _ = pathing.get_room_and_dir(user)
			if not (location and destination):
				self.msg("I can't navigate that.")
				return False
			if destination.startswith("to "):
				destination = destination[3:]
			return self.navigate(location, destination, **kwargs)
		elif action == "register":
			self.msg("I'm sorry, registering new landmarks has not yet been implemented. Thank you for using NaviMate.")
			return False
		elif action == "cancel" and self.route:
			self.msg("Cancelling navigation.")
			self.stop()
			return True
		elif action == 'menu':
			session = user.sessions.all()[0]
			session.ndb.app = self
			FormatEvMenu(session, 'systems.electronics.software.menus.navimate', startnode="menunode_main" if not self.active else "menunode_navmap")
			return True
	
	def navigate(self, location, destination, weight='road', **kwargs):
		# location is a room 
		# destination is a string
		if not self.landmarks:
			self.msg("No landmarks recorded.")
			return False
		# landmarks is a dict of nick:room
		results = [obj for key, obj in self.landmarks.items() if destination.lower() in key.lower()]
		if not results:
			results = self.handler.obj.search(destination, candidates=self.landmarks, quiet=True)
		if not results:
			# TODO: use string suggestions
			self.msg("No matching destination found.")
			return False
		target = choice(results)
		if self.route:
			self.msg("Cancelling previous route.")
		self.msg(f"Calculating route...")
		self.weight = weight
		self.calculate_route(location.id, target.id)
		self.start()
		return True

	def view_route(self):
		if not self.route:
			return ''
		if not (start := self.last_check):
			start = 0
		route = []
		last_dir = 0
		for i, rid in enumerate(self.route.keys()):
			if start == i:
				route.append(f"Go {self.route[i]}.")
				last_dir == i
			elif start < i:
				if self.route[i] != self.route[i-1]:
					route.append(f"After 0.{i-last_dir:.2f} miles, make a {self.route[i]}.")
					last_dir = i
		return "\n".join(route)

	def calculate_route(self, start, end):
		self.last_check = None
		if not (flat_route := pathing.path_to_target(start, end, weight=self.weight)):
			self.msg("Error calculating route. Cancelling...")
			self.stop()
			return
		self.route = {}
		obj = self.handler.obj
		for i in range(len(flat_route)-1):
			if exi := pathing.get_exit_for_path(flat_route[i],flat_route[i+1]):
				direction = exi.direction
				self.route[flat_route[i]] = direction
			else:
				self.msg("Error calculating route. Cancelling...")
				self.stop()
				return
		self.route[flat_route[-1]] = None
		self.handler.save()
	
	def check_route(self):
		location, direction = pathing.get_room_and_dir(self.handler.obj)
		id = location.id
		route_ids = list(self.route.keys())
		if id == self.last_check:
			return
		self.last_check = id

		if id not in route_ids:
			self.msg("Recalculating route...")
			self.stop()
			self.calculate_route(id, route_ids[-1])
			delay(2,self.start)
			return
		destination = list(self.route.keys())[-1]
		if id == destination:
			self.msg("You have arrived.")
			self.stop()
			return

		message = ''
		index = route_ids.index(id)
		next_dir = self.route[id]
		id_range = route_ids[index+1:min(index+4, len(route_ids))]

		turn = pathing.cardinal_to_relative(direction, next_dir)
		if not turn:
			message = f"Go {next_dir}."
		elif turn != "straight":
			message = f"Make a {turn}."
		elif index > 1 and self.route[route_ids[index-1]] != direction:
			id_range = route_ids[index+1:]

		i=0
		for rid in id_range:
			if rid == self.up_next:
				break
			i+=1
			if self.route[rid] != next_dir:
				# TODO: figure out how i want rooms scale to distances
				distance = 0.1*i
				if message:
					message += " "
				if self.route[rid]:
					turn = pathing.cardinal_to_relative(next_dir, self.route[rid])
					message += f"In {distance:.1f} miles, make a {turn}."
				else:
					message += f"In {distance:.1f} miles, you will arrive at your destination."
				self.up_next = rid
				break
		if message:
			self.msg(message)

	def tick(self):
		if self.active:
			self.check_route()
			delay(1,self.tick)

	def start(self):
		self.active = True
		self.handler.save()
		delay(1,self.tick)

	def stop(self):
		self.route = None
		self.active = False
		self.last_check = None
		self.up_next = None
		self.handler.save()

class PhoneCalls(BaseApp):
	key = "Phone"
	calling = None
	ringing = False

	def _get_simchip(self):
		"""returns the simcard object, or None"""
		phone = self.handler.obj.baseobj
		sim = phone.parts.search('simcard', part=True)
		if not sim:
			return None
		else:
			return sim[0]

	def get_number(self, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		return sim.db.number

	def display_contact(self, number, **kwargs):
		number = str(number)
		if app_obj := self.handler.search_app("contacts"):
			app_obj = app_obj[0]
			return app_obj.get_display_name(number)
		else:
			return number

	def at_install(self, *args, **kwargs):
		if not (sim := self._get_simchip()):
			return False
		if not sim.db.number:
			new_number = GLOBAL_SCRIPTS.phonebook.assign_number(sim)
			sim.db.number = new_number
			success = True
		else:
			success = GLOBAL_SCRIPTS.phonebook.add_record(sim.db.number, sim)
		if success:
			sim.behaviors.add('PhoneCalls')
			sim.baseobj.behaviors.merge(sim)
		return success

	def listen(self, speaker, input, **kwargs):
		if self.calling:
			self.calling.baseobj.do_call(input, from_obj=speaker, app_key=self.key, audio=True, **kwargs)
			return True
		else:
			# match input.lower().split():
			# 	case ["call", contact]:
			# 		self.begin_call(contact)

			return self.handler.listen(speaker, input, **kwargs)

	def msg(self, message, speaker=None, **kwargs):
		if not speaker:
			super().msg(message, **kwargs)
			return

		if not (sref := speaker.sdesc.get(strip=True)):
			sref = speaker.name
		message = f'From @me, @{sref} says, "{message}"'
		kwargs['emote'] = True
		self.handler.msg(message, include=[speaker], **kwargs)
	
	def receive_call(self, phone, **kwargs):
		if ring := kwargs.get('ring'):
			self.ringing = phone
		if self.ringing:
			self.msg("rings...", sound=True, emote=True)
			delay(5, self.receive_call, phone)
	
	def begin_call(self, number, pickup=False, **kwargs):
		mycard = self._get_simchip()
		if self.calling:
			# already on a call
			return False
		elif pickup:
			# they called us
			self.calling = self.ringing
			self.ringing = False
			return True
		if type(number) is int:
			number = str(number)
		if type(number) is str:
			if not number.isnumeric():
				if contact_list := self.handler.get('Contacts'):
					number = contact_list.get_default_number_for(number)
			card = GLOBAL_SCRIPTS.phonebook.get_by_number(number)
		else:
			card = number
		if card == mycard:
			self.msg("That's your phone number.")
			return False
		if card:
			phone = card.baseobj
			try:
				if phone.do_call(mycard, self.key, ring=True):
					self.calling = card
					self.msg("Calling...")
					logger.log_msg("am i getting HERE now")
					return True
			except NoSuchBehavior:
				pass
		self.msg("That number is not available.")
		return False
	
	def end_call(self, **kwargs):
		if not kwargs.get("hangup"):
			# we're initiating the call end
			try:
				self.calling.baseobj.do_call(self._get_simchip(), hangup=True)
			except NoSuchBehavior:
				pass
		self.msg("Call ended.")
		self.calling = None
		self.ringing = None

	def use(self, user, action, **kwargs):
		if action == "menu":
			session = user.sessions.all()[0]
			session.ndb.app = self
			startnode = "menunode_main"
			if self.calling:
				startnode = "menunode_calling"
			elif self.ringing:
				startnode = "menunode_ringing"
			FormatEvMenu(session, 'systems.electronics.software.menus.PhoneAppMenu', startnode=startnode)
			return True

	def display(self, *args, **kwargs):
		if not self.ringing and not self.calling:
			return

		if self.ringing:
			number = self.ringing.db.number
			message = "Incoming call from {contact}"
		elif self.calling:
			number = self.calling.db.number
			message = "Call with {contact}"

		contact = self.display_contact(number)
		return message.format(contact=contact)

class ContactList(BaseApp):
	key = "Contacts"

	def _get_simchip(self):
		"""returns the simcard object, or None"""
		phone = self.handler.obj.baseobj
		sim = phone.parts.search('simcard', part=True)
		if not sim:
			return None
		else:
			return sim[0]

	def get_number(self, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		return sim.db.number

	def at_install(self, *args, **kwargs):
		if not (sim := self._get_simchip()):
			return False
		if not sim.attributes.has('contacts'):
			sim.db.contacts = {}
		return True

	def contact_list(self, *args, **kwargs):
		if not (sim := self._get_simchip()):
			return []
		if contacts := sim.db.contacts:
			return list(contacts.keys())
		return []

	def get_display_name(self, number, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		
		try:
			contacts = sim.db.contacts.deserialize()
		except:
			# in case we have no contacts
			return None
		
		matches = [ contact_name for contact_name, data in contacts.items() for n, label in data.items() if str(n) == str(number) ]
		if matches:
			return matches[0]
		else:
			return str(number)

	def get_contact(self, contact_name, *args, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		# TODO: add case insensitivity
		try:
			contact_list = sim.db.contacts.deserialize()
		except:
			return None

		contact = contact_list.get(contact_name)

		if not contact:
			matches = [ key for key, data in contact_list.items() if key.lower() == contact_name.lower() ]
			if matches:
				contact = contact_list.get(matches[0])

		return contact
	
	def get_default_number_for(self, contact_name, *args, **kwargs):
		# TODO: allow people to actually set a default number instead of just first
		if contact := self.get_contact(contact_name):
			return list(contact.keys())[0]


	def add_contact(self, contact_name, number=None, label='Cell', **kwargs):
		if not (sim := self._get_simchip()):
			return False
		try:
			contact = sim.db.contacts.get(contact_name)
		except:
			return False
		
		if not contact:
			if number:
				sim.db.contacts[contact_name] = {number: label}
			else:
				sim.db.contacts[contact_name] = {}
	
		elif number:
			number = int(number)
			sim.db.contacts[number] = label

		return True

	def del_contact(self, contact_name, number=None, **kwargs):
		if not (sim := self._get_simchip()):
			return False
		if contact_name in sim.attributes.get('contacts', {}):
			if number:
				del sim.db.contacts[contact_name][int(number)]
			else:
				del sim.db.contacts[contact_name]
			return True
		else:
			return False

	def use(self, user, action, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		if action == "menu":
			session = user.sessions.all()[0]
			session.ndb.app = self
			startnode = "menunode_main"
			FormatEvMenu(session, 'systems.electronics.software.menus.ContactsAppMenu', startnode=startnode)
			return True

class TextMessages(BaseApp):
	key = "Messages"

	unread_count = 0

	def _get_simchip(self):
		"""returns the simcard object, or None"""
		phone = self.handler.obj.baseobj
		sim = phone.parts.search('simcard', part=True)
		if not sim:
			return None
		else:
			return sim[0]

	def display_contact(self, number, **kwargs):
		number = str(number)
		if app_obj := self.handler.get("Contacts"):
			return app_obj.get_display_name(number)
		else:
			return number

	def get_number(self, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		return sim.db.number

	def at_install(self, *args, **kwargs):
		if not (sim := self._get_simchip()):
			return False
		if not sim.db.number:
			new_number = GLOBAL_SCRIPTS.phonebook.assign_number(sim)
			sim.db.number = new_number
			success = True
		else:
			success = GLOBAL_SCRIPTS.phonebook.add_record(sim.db.number, sim)
		
		if success and not sim.attributes.has('conversations'):
			sim.db.conversations = {}

		return success

	def receive_message(self, sender, receivers, message, **kwargs):
		logger.log_msg(f"receiving message from {sender}")
		if not (sim := self._get_simchip()):
			return

		self._add_to_conversation(sim, receivers, sender, message)

		self.unread_count += 1
		self.handler.status = f"You have {self.unread_count} new messages."
		self.msg("vibrates twice", emote=True)

	def send_message(self, receivers, message, **kwargs):
		logger.log_msg("sending message")
		if not (sim := self._get_simchip()):
			return
		
		if not (number := sim.db.number):
			return

		# receivers is a list of numbers
		receivers = list(sorted(int(n) for n in receivers))

		logger.log_msg(f"sending to receivers {receivers}")

		self._add_to_conversation(sim, receivers, number, message, read=True)

		for r in receivers:
			logger.log_msg(f"it's {r}'s turn")
			card = GLOBAL_SCRIPTS.phonebook.get_by_number(r)
			logger.log_msg(f"got {card} from phone book")
			if not card:
				continue
			if card == sim:
				logger.log_msg("oh, it's me")
				continue
			phone = card.baseobj
			cpu = phone.parts.search("cpu", part=True)
			if cpu:
				cpu = cpu[0]
			else:
				continue
			try:
				logger.log_msg(f"attempting to find message app on {phone} for {r}")
				their_app = cpu.apps.get('Messages')
				logger.log_msg("got it")
			except AttributeError as e:
				logger.log_msg(f"oh no {str(e)}")
				continue
			logger.log_msg(f"sending message to {their_app}")
			their_app.receive_message(number, receivers, message)

	def _add_to_conversation(self, sim, receivers, sender, message, read=False):
		# receivers is a list of numbers
		receivers = tuple(sorted(int(n) for n in receivers))

		try:
			conversations = sim.db.conversations.deserialize()
		except:
			conversations = {}

		timestamp = time.time()
		item = (timestamp, sender, message, read)
		if receivers in conversations:
			conversations[receivers].append(item)
		else:
			conversations[receivers] = [item]
		
		conversations = { receivers: conversations } | conversations

		sim.db.conversations = conversations

	def mark_read(self, convo, item):
		if not (sim := self._get_simchip()):
			return

		try:
			i = sim.db.conversations[convo].index(item)
		except:
			return
		
		sim.db.conversations[convo][i] = (item[0], item[1],item[2], True)

	def conversation_list(self, start=0, chunk=10):
		if not (sim := self._get_simchip()):
			return []
		number = sim.db.number

		convos = list(sim.attributes.get('conversations', {}).items())[start:start+chunk]

		result = []
		for receivers, messages in convos:
			if messages:
				timestamp, sender, message, _ = messages[-1]
				# TODO: include the rendered time and sender
				result.append((receivers, sender, message))
		
		return result

	def get(self, convo_key, **kwargs):
		if not (sim := self._get_simchip()):
			return None

		if sim.attributes.has('conversations'):
			return sim.db.conversations.get(convo_key)

	def add_convo(self, contacts, **kwargs):
		if not (sim := self._get_simchip()):
			return None
		
		if not (number := sim.db.number):
			return
		
		if app_obj := self.handler.get("Contacts"):
			contacts = [ app_obj.get_default_number_for(c) for c in contacts ]

		receivers = tuple(sorted(int(n) for n in contacts) + [number])

		if not sim.attributes.has('conversations'):
			sim.db.conversations = { receivers: [] }
			return receivers

		elif receivers not in sim.db.conversations:
			sim.db.conversations[receivers] = []
		
		return receivers


	def use(self, user, action, **kwargs):
		if action == "menu":
			session = user.sessions.all()[0]
			session.ndb.app = self
			startnode = "menunode_main"
			FormatEvMenu(session, 'systems.electronics.software.menus.MessagingAppMenu', startnode=startnode)
			return True

	def display(self, *args, **kwargs):
		return f"You have {self.unread_count} new messages."

class DigiCamera(BaseApp):
	key = "Camera"

	def _get_camera(self):
		"""returns the camera object, or None"""
		phone = self.handler.obj.baseobj
		sim = phone.parts.search('camera', part=True)
		if not sim:
			return None
		else:
			return sim[0]
	
	def display(self, *args, **kwargs):
		return "The camera is on."

	def at_install(self, *args, **kwargs):
		return True

	def use(self, user, action, **kwargs):
		if not (cam := self._get_camera()):
			return None
		if action == "menu":
			session = user.sessions.all()[0]
			session.ndb.app = self
			startnode = "menunode_main"
			FormatEvMenu(session, 'systems.electronics.software.menus.CameraAppMenu', startnode=startnode, auto_look=False, camera=cam)
			return True


class Gallery(BaseApp):
	key = "Gallery"

	def _get_storage(self):
		"""returns any data storage objects"""
		phone = self.handler.obj.baseobj
		return phone.parts.search('datadrive', part=True)
	
	def at_install(self, *args, **kwargs):
		return True
	
	def display(self, *args, **kwargs):
		return "The Gallery is open."

	def use(self, user, action, **kwargs):
		if not (drives := self._get_storage()):
			return None
		if action == "menu":
			session = user.sessions.all()[0]
			session.ndb.app = self
			startnode = "menunode_main"
			FormatEvMenu(session, 'systems.electronics.software.menus.GalleryAppMenu', startnode=startnode, auto_look=False, drives=drives)
			return True
