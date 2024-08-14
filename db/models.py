from django.db import models
from evennia.locks.lockhandler import LockHandler
from evennia.typeclasses.tags import Tag, TagHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.utils import crop, lazy_property
from evennia.utils.dbserialize import dbunserialize

from .managers import ReportManager, ArticleManager, SceneManager


class Note(SharedMemoryModel):
	"""
	An abstract base model that stores note-like objects.

	Notes have an author, subject, and text content, as well as a list of readers who
	have read the note.
	"""

	class Meta:
		abstract = True

	db_title = models.TextField("title", blank=True)
	db_content = models.TextField("content", blank=True)
	db_writer_accounts = models.ManyToManyField(
		"accounts.AccountDB",
		related_name="%(class)s_writer_accounts",
		blank=True,
		verbose_name="writer (account)",
		db_index=True,
	)
	db_writer_objects = models.ManyToManyField(
		"objects.ObjectDB",
		related_name="%(class)s_writer_objects",
		blank=True,
		verbose_name="writer (object)",
		db_index=True,
	)
	db_reader_accounts = models.ManyToManyField(
		"accounts.AccountDB",
		related_name="%(class)s_reader_accounts",
		blank=True,
		verbose_name="reader (account)",
		db_index=True,
	)
	db_reader_objects = models.ManyToManyField(
		"objects.ObjectDB",
		related_name="%(class)s_reader_objects",
		blank=True,
		verbose_name="reader (object)",
		db_index=True,
	)
	db_date_created = models.DateTimeField(
		"date created", editable=False, auto_now_add=True, db_index=True
	)
	db_tags = models.ManyToManyField(Tag, blank=True, help_text="Tags on this note.")
	db_lock_storage = models.TextField("locks", blank=True, help_text="Locks on this note.")

	@lazy_property
	def locks(self):
		return LockHandler(self)

	@lazy_property
	def tags(self):
		return TagHandler(self)

	@property
	def writers(self):
		"""Returns a list of all writers of this note, if any."""
		return list(self.db_writer_accounts.all()) + list(self.db_writer_objects.all())

	@property
	def writer(self):
		"""Returns the first writer on this Note, preferring accounts."""
		return writers[0] if (writers := self.writers) else None

	def add_writer(self, obj):
		"""Adds a writer to this note."""
		if not obj:
			return
		if hasattr(obj, "__dbclass__"):
			clsname = obj.__dbclass__.__name__
			if clsname == "ObjectDB":
				self.db_writer_objects.add(obj)
				return
			elif clsname == "AccountDB":
				self.db_writer_accounts.add(obj)
				return
		raise ValueError("Cannot add object as writer.")

	def remove_writer(self, obj):
		"""Removes a writer from this note."""
		if not obj:
			return
		if hasattr(obj, "__dbclass__"):
			clsname = obj.__dbclass__.__name__
			if clsname == "ObjectDB":
				self.db_writer_objects.remove(obj)
				return
			elif clsname == "AccountDB":
				self.db_writer_accounts.remove(obj)
				return
		raise ValueError("Cannot remove object from writers.")

	@property
	def readers(self):
		"""Returns a list of all readers of this note, if any."""
		return list(self.db_reader_accounts.all()) + list(self.db_reader_objects.all())

	def mark_read(self, obj):
		"""Marks this note read by a specific object or account."""
		if not obj:
			return
		if hasattr(obj, "__dbclass__"):
			clsname = obj.__dbclass__.__name__
			if clsname == "ObjectDB":
				self.db_reader_objects.add(obj)
				return
			elif clsname == "AccountDB":
				self.db_reader_accounts.add(obj)
				return
		raise ValueError("Cannot mark read for this object.")

	def mark_unread(self, obj):
		"""Marks this note unread by a specific object or account."""
		if not obj:
			return
		if hasattr(obj, "__dbclass__"):
			clsname = obj.__dbclass__.__name__
			if clsname == "ObjectDB":
				self.db_reader_objects.remove(obj)
				return
			elif clsname == "AccountDB":
				self.db_reader_accounts.remove(obj)
				return
		raise ValueError("Cannot mark unread for this object.")

	def is_read(self, obj):
		"""Returns True if this note has been read by a specific object or account."""
		return obj in self.writers or obj in self.readers

	def ic_time(self):
		"""Returns a WorldTime indicating when this note was created in-world."""
#		return WorldTime(self.db_date_created.timestamp())
		return None

	def access(self, accessing_obj, access_type="read", default=False):
		"""
		Checks lock access.

		Args:
			accessing_obj (Object or Account): The object trying to gain access.
			access_type (str, optional): The type of lock access to check.
			default (bool): Fallback to use if `access_type` lock is not defined.
		Returns:
			bool: If access was granted or not.
		"""
		return self.locks.check(accessing_obj, access_type=access_type, default=default)


class Report(Note):
	"""
	A model Msg representing a bug, typo, or other player-filed report.
	"""

	SUPPORTED_KINDS = ("bug", "typo", "report")

	class Meta:
		verbose_name = "Report"
		verbose_name_plural = "Reports"

	objects = ReportManager()

	db_subject = models.ForeignKey(
		"objects.ObjectDB",
		null=True,
		blank=True,
		related_name="%(class)s_subjects",
		on_delete=models.SET_NULL,
		help_text="The subject of this report.",
		db_index=True,
	)
	db_kind = models.CharField(max_length=30, blank=True, db_index=True)
	db_open = models.BooleanField(
		default=True, help_text="True if this report is open (pending action)."
	)

	@property
	def kind(self):
		"""Returns the kind of this report (bug, typo)."""
		return self.db_kind if self.db_kind in self.SUPPORTED_KINDS else None

	@kind.setter
	def kind(self, kind):
		"""Sets the kind of this report (bug, typo)."""
		if not kind:
			self.db_kind = ""
		elif kind in self.SUPPORTED_KINDS:
			self.db_kind = kind
		self.save()


class Article(Note):
	"""
	A model for representing news articles or board postings.
	"""

	class Meta:
		verbose_name = "Article"
		verbose_name_plural = "Articles"

	objects = ArticleManager()

	db_category = models.CharField(max_length=30, blank=True, db_index=True)



class SceneLinesHandler:
	lines = []
	
	def __init__(self, scene):
		self.scene = scene
		lines = scene.db_content
		self.lines = dbunserialize(lines)
	
	def serialize(self):
		return dbserialize(self.lines)

	def add(self, message, **kwargs):
		"""Add a new line or lines to the scene"""
		if type(message) is list:
			self.lines += message
		else:
			self.lines.append(message)
		self.save()
	
	def save(self):
		self.scene.db_content = self.serialize()
		self.scene.save()

	def find(self, search_term, **kwargs):
		"""returns the most recent matching line"""
		for i, line in reversed(list(enumerate(self.lines))):
			if search_term.lower() in line.lower():
				return i
	
	def get(self, index):
		"""gets the line at a specific index"""
		return self.lines[index]

	def crop(self, start_index, end_index=-1):
		"""cuts out the lines from start_index to end_index"""
		if end_index < 0:
			self.lines = self.lines[:start_index]

		elif start_index < end_index:
			# TODO: log this to admin logs
			cropped = self.lines[start_index:end_index]
			self.lines = self.lines[:start_index] + self.lines[end_index:]
		
		else:
			raise ValueError('start_index must be smaller than end_index')
		
		self.save()


class Scene(Note):
	"""
	A Note model representing a roleplay scene.
	"""

	Status = models.IntegerChoices('Status', 'RECORDING PAUSED DRAFT COMPLETED PUBLISHED')

	class Meta:
		verbose_name = "Scene"
		verbose_name_plural = "Scenes"

	objects = SceneManager()

	db_status = models.IntegerField(
		choices=Status.choices,
		default=Status.RECORDING,
		help_text="The current status of this scene.",
		db_index=True,
	)

	@property
	def status(self):
		"""Returns the status of this scene."""
		return self.db_status.name

	@lazy_property
	def lines(self):
		return SceneLinesHandler(self)

	@status.setter
	def status(self, status):
		"""Sets the status of this scene."""
		if not status:
			self.db_status = self.Status.RECORDING
		elif status in self.Status.names:
			self.db_status = self.Status[status].value
		self.save()

	def add_line(self, message, writer, **kwargs):
		"""Adds a new emote line to the scene log"""
		if writer and writer not in self.writers:
			self.add_writer(writer)
		self.lines.add(message)

	def retcon_from(self, line, **kwargs):
		"""
		Rolls back to a particular line in the scene, returning True if found or False if not
		"""
		if (index := self.lines.find(line)) is None:
			return False

		try:
			self.lines.crop(index)
		except ValueError:
			return False

		return True
