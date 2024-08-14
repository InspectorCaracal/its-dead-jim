from db.models import Scene

class ScenesHandler:
	"""
	Manages scene creation and access for a particular player (goes on the character)
	"""
	def __init__(self, obj):
		self.obj = obj
	
	@property
	def recording(self):
		return Scene.objects.any_active_by(self.obj.account)

	@property
	def paused(self):
		return Scene.objects.any_paused_by(self.obj.account)

	def get_active(self):
		if self.obj.account:
			if scenes := list(Scene.objects.all_active_by(self.obj.account)):
				return scenes[0]

	def add_line(self, message, from_obj):
		"""Logs the line to an actively-recording scene"""
		if scene := self.get_active():
			scene.add_line(message, from_obj)

	def start(self):
		"""
		Resume an existing scene or start a new one
		
		Returns:
			True if recording has started, else False
		"""
		if self.recording:
			return False
		if self.paused:
			paused = list(Scene.objects.all_paused_by(self.obj.account))
			scene = paused[0]
			scene.status = "RECORDING"
			return True
		else:
			Scene.objects.create(self.obj.account, '')
			return True

	def stop(self, final=True):
		"""
		Stops an actively recording scene
		
		Returns:
			True if recording has ended, else False
		"""
		if not self.recording:
			return False

		scene = self.get_active()
		scene.status = "DRAFT" if final else "PAUSED"
		return True

	def pause(self):
		"""
		Pauses an actively recording scene
		
		Returns:
			True if recording has paused, else False
		"""
		return self.stop(final=False)
