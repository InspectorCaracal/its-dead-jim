from evennia.utils import logger, iter_to_str
from core.ic.behaviors import Behavior, NoSuchBehavior, behavior

def _check_if_usable(*objs):
	"""Checks if an electronic device is usable"""
	# check if object itself is disabled
	for obj in objs:
		if any(obj.tags.has(['disabled', 'overloaded'], category='status', return_list=True)):
			return False

	bases = {obj.baseobj for obj in objs}
	if len(bases) > 1:
		raise ValueError('Can only check parts of the same base object at once, but bases differ.')
	# oh my god is this hacky
	for b in bases:
		base = b
	# check if base is powered on
	psu = base.baseobj.parts.search('power_source', part=True)
	if not psu:
		# there's nothing
		return False
	psu = psu[0]
	if any(psu.tags.has(['disabled', 'overloaded'], category='status', return_list=True)):
		return False
	if not psu.tags.has("powered on", category="status"):
		return False
	return True

@behavior
class PowerOnOff(Behavior):
	priority = 10

	def power(obj, doer, state, **kwargs):
		"""Turn an object on or off"""
		obj = obj.baseobj
		# find the central processor
		psu = obj.baseobj.parts.search('power_source', part=True)
		if not psu:
			# there's nothing
			return
		psu = psu[0]
		if any(psu.tags.has(['disabled', 'overloaded'], category='status', return_list=True)):
			status = obj.tags.get(category="status", return_list=True)
			doer.msg(f"{obj.get_display_name(doer)} is {iter_to_str(status)}.")
			return

		powered_on = psu.tags.has("powered on", category="status")
		if powered_on == state:
			# no change
			return False
		if state:
			# turn on
			psu.tags.add("powered on", category="status")
			try:
				obj.do_startup()
			except NoSuchBehavior:
				pass
		else:
			# turn off
			if powered_on:
				psu.tags.remove('powered on', category="status")

		# successfully done
		return True

@behavior
class DataReadWrite(Behavior):
	priority = 10

	# TODO: how should `read_data` work

	# TODO: add read/write speeds
	# gotta have that high-pressure racing the clock to copy critical data

	def write_data(obj, data_obj, **kwargs):
		"""add data, return True if successful else False"""
		if not _check_if_usable(obj):
			return False
		
		drive = kwargs.get('behavior_source', obj)
		# TODO: calculate free space here
		data_obj.location = drive

		# successfully done
		return True

	def copy_data(obj, data_obj, target, **kwargs):
		"""copy data from this object"""
		# find the central processor
		if not _check_if_usable(obj):
			return False
		
		if not target.can_write_data():
			return False
		
		drive = kwargs.get('behavior_source', obj)
		# TODO: calculate free space here
		if data_obj not in drive.contents:
			return False
		
		data_copy = data_obj.copy()
		data_copy.location = None

		if not target.do_write_data(data_copy):
			data_copy.delete()
			return False
		else:
			# succeeded
			return True


@behavior
class AppDevice(Behavior):
	priority = 10

	def use(obj, doer, *args, **kwargs):
		# find the central processor
		cpu = obj.baseobj.parts.search('cpu', part=True)
		if not cpu:
			# there's nothing
			return
		cpu = cpu[0]
		if not _check_if_usable(cpu):
			return
		if not args:
			args = ['menu']
		if app_key := cpu.db.active_app:
			app = cpu.apps.get(app_key)
			app.use(doer, *args, **kwargs)
		else:
			cpu.apps.use(doer, *args, **kwargs)


@behavior
class ElecDisplay(Behavior):
	priority = 1

	def screen_render(obj, doer, **kwargs):
		# this needs both a working display screen and an active cpu
		screen = obj.baseobj.parts.search('display_screen', part=True)
		if not screen:
			# there's nothing
			doer.msg('no screen')
			return
		cpu = obj.baseobj.parts.search('cpu', part=True)
		if not cpu:
			# there's nothing
			doer.msg('no cpu')
			return ''

		screen = screen[0]
		cpu = cpu[0]
		if not _check_if_usable(cpu, screen):
			return
		if not hasattr(cpu, 'apps'):
			return ''
		
		appkey = kwargs.pop('appkey', cpu.db.active_app)

		return cpu.apps.display(appkey=appkey, **kwargs)

	# TODO: maybe turn the screen on and off?

@behavior
class ElecSpeaker(Behavior):
	priority = 1

	def make_sound(obj, message, **kwargs):
		base = obj.baseobj
		emote = kwargs.pop('emote', True)
		# find the speakers
		speaker = kwargs.get('behavior_source', obj)
		if not speaker:
			# there's nothing
			return
		if not _check_if_usable(speaker):
			return
		if not kwargs.get('volume'):
			kwargs['volume'] = speaker.db.volume or 1
		if emote:
			base.emote(message, **kwargs)
		else:
			base.location.msg(message, **kwargs)

@behavior
class ElecMicrophone(Behavior):
	priority = 1

	def parse_audio(obj, source, message, **kwargs):
		"""Receive an audio message input"""
		logger.log_msg(f"parsing audio {message} from {source}")
		obj = obj.baseobj
		# this needs both a working microphone and an active cpu
		mic = kwargs.get('behavior_source')
		if not mic:
			# there's nothing
			return
		cpu = obj.parts.search('cpu', part=True)
		if not cpu:
			# there's nothing
			return
		cpu = cpu[0]
		if not _check_if_usable(cpu) or not _check_if_usable(mic):
			return

		if app_key := kwargs.get('app_key'):
			app = cpu.apps.get(app_key)
		elif app_key := cpu.db.active_app:
			app = cpu.apps.get(app_key)
		else:
			app = cpu.apps
		if not app:
			app = cpu.apps
		logger.log_msg(app)
		if not hasattr(app, 'listen') or not callable(app.listen):
			app = cpu.apps
		app.listen(source, message, **kwargs)

@behavior
class PhoneCalls(Behavior):
	priority = 1

	def call(ours, theirs, app_key="Phone", **kwargs):
		"""Receive an audio message input"""
		ours = ours.baseobj
		# get cpu first
		cpu = ours.parts.search('cpu', part=True)
		if not cpu:
			# there's nothing
			return

		cpu = cpu[0]
		if not _check_if_usable(cpu):
			return

		if not hasattr(cpu, 'apps'):
			return
		
		if not (app := cpu.apps.get(app_key)):
			return
		if not cpu.db.active_app:
			cpu.db.active_app = app_key
		if kwargs.get('ring'):
			# receiving a call
			app.receive_call(theirs, **kwargs)
			return True
		elif kwargs.get('hangup'):
			# ending a call
			app.end_call(**kwargs)
			return True
		elif kwargs.get('audio'):
			kwargs['speaker'] = kwargs.pop('from_obj', None)
			logger.log_msg('sending audio')
			app.msg(theirs, **kwargs)
		else:
			# making a call
			return app.begin_call(theirs, **kwargs)
