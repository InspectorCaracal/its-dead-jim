from evennia.utils.utils import crop, iter_to_str
from utils.strmanip import strip_extra_spaces
from utils.menus import MenuTree


class AppHandlerMenu(MenuTree):
	_node_format = "{header}\n\n{text}\n\n$foot({footer})"

	@property
	def _header(self):
		if hasattr(self, 'app'):
			return self.app.display()
	
	def _pre_node_process(self, caller, *args, **kwargs):
		if not hasattr(self, 'app'):
			self.app = caller.ndb.apps

	def menunode_main(self, caller, raw_string, *args, **kwargs):
		text = ""
		options = (
			{ "key": ("Open App", "open", 'o'), "goto": "menunode_choose_open" },
			{ "key": ("Install App", "install", 'i'), "goto": "menunode_choose_install" },
			{ "key": ("Close", "c"), "goto": "menunode_close" },
		)
		return text, options

	def menunode_choose_open(self, caller, raw_string, *args, **kwargs):
		text = "Open which app?"
		options = []
		for key in self.app.app_data.keys():
			options.append( {"desc": key, "goto": ("menunode_open_app",{"appkey": key})} )
		options.append({ "key": ("Back", "b"), "goto": "menunode_main" })

		return text, options

	def menunode_choose_install(self, caller, raw_string, *args, **kwargs):
		text = "Search app store for:"
		options =(
			{ "key": "_default", "goto": "menunode_install_confirm" },
		)
		return text, options

	def menunode_install_confirm(self, caller, raw_string, *args, **kwargs):
		results = self.app.search_app(raw_string.strip().lower(), installed=False)
		text = "Install:"
		options = [ { "desc": key, "goto": ("menunode_install_app", {"appkey": key})} for key in results ]
		options.append({ "key": ("Go back", "back", "b"), "desc": "Don't install anything", "goto": "menunode_main" })

		return text, options

	def menunode_install_app(self, caller, raw_string, appkey, **kwargs):
		if self.app.install_app(appkey):
			text = f'{appkey} installed successfully.'
		else:
			text = f'Could not install {appkey}.'
		
		option = { "key": ("Back to main screen", "back", "b"), "goto": "menunode_main" }
		return text, option

	def menunode_open_app(self, caller, raw_string, appkey, *args, **kwargs):
		self.app.obj.active_app = appkey
		caller.ndb._evmenu.cmd_on_exit = self._open_app
		return None

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		return None

	def _open_app(self, caller, menu):
		app = caller.ndb.apps
		appkey = app.obj.active_app
		if new_app := app.get(appkey):
			new_app.use(caller.puppet, "menu")


class AppMenuBase(MenuTree):
	def _pre_menu(self, caller, *args, **kwargs):
		if not hasattr(self, 'menu'):
			self.menu = caller.ndb._evmenu

		self.menu.cmd_on_exit = self._return_to_main

	def _pre_node_process(self, caller, *args, **kwargs):
		if not hasattr(self, 'app'):
			self.app = caller.ndb.app
		if not hasattr(self, 'menu'):
			self.menu = caller.ndb._evmenu

	def _return_to_main(self, caller, menu):
		main_menu = self.app.handler
		main_menu.use(caller.puppet, "menu")


class PhoneAppMenu(AppMenuBase):
	_header = "Phone"

	def menunode_main(self, caller, raw_string, error='', **kwargs):
		text = "Enter a phone number to call, or choose an option below."
		# TODO: recent calls list

		if error:
			text = f"{error}\n\n{text}"

		options = (
			{ "key": "_default", "goto": self._dial },
			{ "key": ("Contacts", "con"), "goto": "menunode_contact_list" },
			{ "key": ("Info", "i"), "goto": "menunode_phone_info" },
			{ "key": ("Close", "cl"), "goto": "menunode_close" },
		)
		return text, options

	def menunode_contact_list(self, caller, raw_string, *args, **kwargs):
		text = "This isn't implemented yet."
		options = {"key": ("Back", 'b'), "desc": "Return to phone menu.", "goto": "menunode_main"}
		return text, options

	def menunode_phone_info(self, caller, raw_string, *args, **kwargs):
		number = self.app.get_number()
		text = f"Your phone number is: $h({number or 'N/A'})"
		options = {"key": ("Back", 'b'), "desc": "Return to phone menu.", "goto": "menunode_main"}
		return text, options

	def _dial(self, caller, raw_string, *args, **kwargs):
		number = "".join(n for n in raw_string if n.isdecimal)
		if len(number) != 7:
			return ("menunode_main", {"error": "Invalid number."})
		else:
			self.app.begin_call(number)
			return "menunode_calling"

	def menunode_calling(self, caller, raw_string, *args, **kwargs):
		if self.app.calling:
			text = f"Call with {self.app.calling.db.number}"
			options = (
				{"key": "_default", "goto": self._talk_on_phone},
				{"key": ("Hang Up","hangup","h"), "goto": self._end_call}
			)
		else:
			text = "Call ended."
			options = {"key": "_default", "desc": "Return to menu.", "goto": "menunode_main"}
			
		return text, options

	def menunode_ringing(self, caller, raw_string, *args, **kwargs):
		if self.app.ringing:
			text = f"Incoming call from {self.app.self.app.display_contact(self.app.ringing.db.number)}"
			options = (
				{"key": ("Pick Up","answer","p"), "goto": self._take_call},
				{"key": ("Hang Up","hangup","h"), "goto": self._end_call}
			)
		else:
			text = "Call ended."
			options = {"key": "_default", "desc": "Return to menu.", "goto": "menunode_main"}
			
		return text, options

	def _talk_on_phone(self, caller, raw_string, *args, **kwargs):
		if not self.app.calling:
			return "menunode_main"
		caller.puppet.execute_cmd(f"say to {self.app.handler.obj.baseobj}: {raw_string.strip()}")
	#	app.listen(self, caller.puppet, raw_string.strip())
		return "menunode_calling"

	def _end_call(self, caller, raw_string, *args, **kwargs):
		if self.app.calling:
			self.app.end_call()
		return "menunode_main"

	def _take_call(self, caller, raw_string, *args, **kwargs):
		if self.app.ringing:
			self.app.begin_call(self.app.ringing.db.number, pickup=True)
		return "menunode_calling"

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		self.app.close()
		return None

class MessagingAppMenu(AppMenuBase):
	_header = "Messages"

	def menunode_main(self, caller, raw_string, error='', **kwargs):
		# TODO: add a way to paginate through
		convos = self.app.conversation_list()

		options = []
		number = self.app.get_number()
		for receivers, sender, message in convos:
			display = ",".join(self.app.display_contact(r) for r in receivers if str(r) != str(number))
			display = crop(display, 20, "...")
			message = crop(message, 50)
			sender = self.app.display_contact(sender) if str(sender) != str(number) else "You"
			options.append( { "desc": f"{display}\n    {sender}: {message}", "goto": ("menunode_messages", {"convo": receivers}) } )
		options.append({"key": ("Start new chat", "new", "start"), "goto": "menunode_new_convo"})
		return '', options

	def menunode_new_convo(self, caller, raw_string, **kwargs):
		text = "Enter a list of contacts:"

		# TODO: make it so you can add from your contact list

		option = { 'key': "_default", "goto": self._start_new_convo }
		return text, option

	def _start_new_convo(self, caller, raw_string, **kwargs):
		contacts = tuple(c.strip() for c in raw_string.strip().split(','))

		convo_key = self.app.add_convo(contacts)
		if not convo_key:
			return "menunode_main"

		return ("menunode_messages", {'convo': convo_key})

	def menunode_messages(self, caller, raw_string, convo, **kwargs):
		number = self.app.get_number()

		display_names = { str(r): self.app.display_contact(r) for r in convo}
		display_names[str(number)] = "You"

		# TODO: render conversation names nicely
		text = f" ({','.join(r for n, r in display_names.items() if str(n) != str(number))})\n\n"

		message_list = self.app.get(convo)
		if message_list is None:
			return self.menunode_main(caller, raw_string, error='Invalid conversation.', **kwargs)
		
		unread = False
		print_me = []
		# TODO: pagination
		for line in message_list[-10:]:
			timestamp, sender, message, read = line
			# TODO: render contact name and time
			item = f"{display_names.get(str(sender), sender)}: {message}"
			if not read:
				item = f"|w{item}|n"
				if not unread:
					unread = True
					item = "-"*20 +'\n' + item
			print_me.append(item)
			self.app.mark_read(convo, line)

		if print_me:
			text += "\n".join(print_me)
		else:
			text += " (No messages)"

		options = (
			{"key": ("Back", 'b'), "desc": "Return to phone menu.", "goto": "menunode_main"},
			{"key": "_default", "goto": (self._send_message, {'convo': convo})}
		)
		return text, options

	def _send_message(self, caller, raw_string, convo, **kwargs):
		app = caller.ndb.app

		app.send_message(convo, raw_string)

		return ("menunode_messages", {'convo': convo})

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		self.app.close()
		return None

class ContactsAppMenu(AppMenuBase):
	_header = "Contacts"

	def menunode_main(self, caller, raw_string, error='', page=0, **kwargs):
		options = []
		if page > 0:
			options.append(
				{"key": ("Previous 10", "prev", "back"), "goto": ("menunode_new_convo", {"page": max(page-10,0)})}
			)
		contacts = self.app.contact_list()
		for contact in contacts[page:page+10]:
			options.append(
				{"desc": contact, "goto": ("menunode_edit_contact", {"contact_name": contact})}
			)

		if page+10 < len(contacts):
			options.append(
				{"key": ("Next 10", "next"), "goto": ("menunode_new_convo", {"page": page+10})}
			)

		options += (
			{"key": ("Add new contact", "new"), "goto": "menunode_new_contact"},
			{"key": ("Return to main menu", "main"), "goto": "menunode_close"}
			)
		return '', options

	def menunode_new_contact(self, caller, raw_string, **kwargs):
		text = "Enter the contact name:"

		option = { 'key': "_default", "goto": self._add_new_contact }
		return text, option

	def _add_new_contact(self, caller, raw_string, **kwargs):
		contact_name = raw_string.strip()

		if not self.app.add_contact(contact_name):
			return ("menunode_main", {"error": "There was an error adding the contact."})

		return ("menunode_edit_contact", {"contact_name": contact_name})

	def menunode_edit_contact(self, caller, raw_string, contact_name, **kwargs):
		contact = self.app.get_contact(contact_name)

		text = contact_name
		text += "\n\nChoose an entry to edit, or enter a new number to add."

		options = []

		for number, label in contact.items():
			options.append({
				"desc": f"{label}: {number}",
				"goto": ("menunode_edit_number", {"contact_name": contact_name, "number": number, "label": label})
			})
		options.append({"key": ("Back to contacts", "back", "b"), "goto": "menunode_main"})
		options.append({"key": "_default", "goto": (self._add_new_number, {"contact_name": contact_name}) })

		return text, options

	def _add_new_number(self, caller, raw_string, contact_name, **kwargs):
		number = raw_string.strip()
		return ("menunode_enter_change", {'contact_name':contact_name, 'number':number, 'change': "label"})


	def menunode_edit_number(self, caller, raw_string, contact_name, number, label, **kwargs):
		text = contact_name

		text += f"\n\nEditing $h({label}: {number})"

		options = [
			{"desc": f"Edit label ({label})", "goto": ("menunode_enter_change", {"contact_name": contact_name, "number": number, "change": "label"})},
			{"desc": f"Edit number ({number})", "goto": ("menunode_enter_change", {"contact_name": contact_name, "number": number, "change": "number"})},
		]
		return text, options


	def menunode_enter_change(self, caller, raw_string, contact_name, number, change, **kwargs):
		text = contact_name

		text += f"\n\nEnter the new {change}:"
		option = {"key": "_default", "goto": (self._set_contact_data, {"contact_name": contact_name, "number": number, "change": change})}
		return text, option

	def _set_contact_data(self, caller, raw_string, contact_name, number, change, **kwargs):
		contact = self.app.get_contact(contact_name)

		if change == "label":
			label = raw_string.strip()
			new_number = int(number)
		elif change == "number":
			label = contact[int(number)]
			new_number = int(raw_string.strip())
			# we need to remove the old number to "change" it
			self.app.del_contact(contact_name, number=number)
		else:
			# whoops!
			return "menunode_main"
		
		if self.app.add_contact(contact_name, number=number, label=label):
			return ("menunode_edit_contact", {"contact_name": contact_name})
		else:
			return "menunode_main"

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		self.app.close()
		return None

class CameraAppMenu(AppMenuBase):
	_header = "Camera"

	def menunode_main(self, caller, raw_string, error='', **kwargs):
		text = ''
		if error:
			text = error + "\n"
		
		if 'target' not in kwargs:
			baseloc = caller.puppet.location
			kwargs['target'] = baseloc
		
		text += self.menu.camera.baseobj.do_preview_picture(kwargs['target'])

		options = (
			{ "key": "_default", "goto": (self._camera_action, kwargs) },
			{ "key": "Take picture", "goto": (self._camera_action, kwargs) },
			{ "key": ("Close", "cl"), "goto": "menunode_close" },
		)
		return text, options

	def _camera_action(self, caller, raw_string, **kwargs):
		inp = raw_string.strip().lower()
		if inp.startswith('l') or inp.startswith('tar'):
			_, *args = inp.split()
			target_str = " ".join(args)
			if results := caller.puppet.search(target_str, quiet=True):
				# FIXME: this needs to use full Command.find_targets logic
				kwargs['target'] = results[0]
		elif any(word in inp for word in ('pic', 'photo', 'take', 'snap', 'shutter') ):
			if not self.menu.camera.baseobj.do_take_picture(kwargs['target']):
				kwargs['error'] = "Couldn't take picture."
			else:
				kwargs['error'] = '(photo taken)'
			
		return ("menunode_main", kwargs)

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		self.app.close()
		return None

class GalleryAppMenu(AppMenuBase):
	_header = "Gallery"

	def menunode_main(self, caller, raw_string, error='', **kwargs):

		images = []
		for drive in self.menu.drives:
			images += [d for d in drive.contents if d.metatype == "image"]

		options = []
		for img in images:
			options.append( { "desc": img.get_display_name(caller), "goto": ("menunode_view_image", {"image": img}) } )
		options.append({ "key": ("Close", "cl", 'c'), "goto": "menunode_close" })
		return '', options

	def menunode_view_image(self, caller, raw_string, image, detail=None, **kwargs):
		if detail:
			text = detail.get_display_desc(caller)
		else:
			text = image.get_display_desc(caller)

		options = (
			{"key": ("Back", 'b'), "desc": "Return to phone menu.", "goto": "menunode_main"},
			{"key": "_default", "goto": (self._look_at_image, {'image': image})},
			{ "key": ("Close", "cl", 'c'), "goto": "menunode_close" },
		)
		return text, options

	def _look_at_image(self, caller, raw_string, image, **kwargs):
		inp = raw_string.strip().lower()
		if inp.startswith('l'):
			_, *args = inp.split()
			target_str = " ".join(args)
			if target_str and (results := image.parts.search(target_str)):
				# FIXME: this sucks
				return ("menunode_view_image", {'image': image, 'detail': results[0]} | kwargs)
			else:
				# looking at the full picture
				return ("menunode_view_image", {'image': image} | kwargs)

		# FIXME: this should give an "invalid option" response
		return ("menunode_main", kwargs)

	def menunode_close(self, caller, raw_string, *args, **kwargs):
		self.app.close()
		return None