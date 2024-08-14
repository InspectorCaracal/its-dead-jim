"""
Managers for the notes app.
"""

from django.db.models import Q, Count
from evennia.typeclasses.managers import TypedObjectManager
from evennia.typeclasses.tags import Tag
from evennia.utils.utils import make_iter


def q_note_with_tag(tag, category):
	"""
	Gets a Q for Tag objects of the specified key for notes.
	"""
	tags = Tag.objects.filter(db_key=tag, db_category=category)
	return Q(db_tags__in=tags)


class NoteManager(TypedObjectManager):
	"""
	Base manager for note objects. As Note itself is an abstract model, this
	manager should also be considered abstract.
	"""

	default_locks = "read:all();write:all();delete:all()"

	def create(self, writer, content, tags=None, title=None, locks=None):
		"""
		Creates a new object for this manager's model.

		Args:
			writer (Object, Account, or list): One or more objects to make
				writers of this note. This first one is considered the primary
				author and gets edit writes if permitted by the Note subclass.
			content (str): The text of this note.
			tags (list): Optional list of tags to pass on to tags.batch_add.
			title (str): Optional title of this note.
			locks (str): Optional lock string to set.
		Returns:
			Note: The new note object.
		"""
		note = self.model(db_content=content, db_title=title or "")
		note.save()
		writers = make_iter(writer)
		for writer in writers:
			note.add_writer(writer)
		if tags:
			note.tags.batch_add(*tags)
		if locks:
			note.locks.add(locks)
		else:
			note.locks.add(locks or self.default_locks.format(id=writers[0].id if writers else 1))
		return note

	def get_object_model(self, obj):
		"""Returns the db model class name for an object, or None."""
		return obj.__dbclass__.__name__ if hasattr(obj, "__dbclass__") else None

	def all_by(self, obj):
		"""Returns a QuerySet of all notes written by a provided object or account."""
		model = self.get_object_model(obj)
		if model == "ObjectDB":
			return self.filter(db_writer_objects=obj)
		elif model == "AccountDB":
			return self.filter(db_writer_accounts=obj)
		raise ValueError("Invalid object type.")

	def all_read_by(self, obj):
		"""Returns a QuerySet of all notes read by a provided object or account."""
		model = self.get_object_model(obj)
		if model == "ObjectDB":
			return self.filter(db_reader_objects=obj)
		elif model == "AccountDB":
			return self.filter(db_reader_accounts=obj)
		raise ValueError("Invalid object type.")

	def all_unread_by(self, obj):
		"""
		Returns a QuerySet of all notes not read by a given object or account.
		"""
		model = self.get_object_model(obj)
		if model == "ObjectDB":
			return self.exclude(db_reader_objects=obj)
		elif model == "AccountDB":
			return self.exclude(db_reader_accounts=obj)
		raise ValueError("Invalid object type.")

	def any_unread_by(self, obj):
		"""Returns True if any note items are unread by a given object or account."""
		return self.all_unread_by(obj).exists()

	def all_tagged_with(self, *tags):
		"""Returns a QuerySet of all notes which have all of the given tags."""
		return self.filter(db_tags__db_key__in=tags).annotate(num_tags=Count('db_tags')).filter(num_tags=len(tags))


class ReportManager(NoteManager):
	"""Manager for Report objects."""

	default_locks = "read:perm(Builder);write:perm(Builder);delete:perm(Admin)"

	def create(self, writer, content, kind=None, subject=None, tags=None, title=None):
		"""
		Creates a new object for this manager's model.
		"""
		report = super().create(writer, content, tags=tags, title=title)
		if kind:
			report.kind = kind
		if subject:
			report.subject = subject
		report.save()
		return report

	def _q_open(self):
		return self.filter(db_open=True)

	def all_open(self):
		"""
		Returns a QuerySet of all reports currently open.
		"""
		return self.all() & self._q_open()

	def all_about(self, target, require_open=True):
		"""
		Returns a QuerySet of all reports about a particular target object.
		"""
		query = self.all() & self.filter(db_subject=target)
		if require_open:
			query = query & self._q_open()
		return query


class ArticleManager(NoteManager):
	"""
	Manager for Article objects.
	"""

	default_locks = "read:all();write:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"

	def create(self, writer, content, tags=None, title=None, locks=None, category=None):
		article = super().create(writer, content, tags=tags, title=title, locks=locks)
		if category:
			article.category = category
		article.save()
		return article

	def all_in_category(self, category):
		"""Returns a QuerySet of all Articles in a provided category."""
		return self.filter(db_category__iexact=category or "")

	def all_unread_by(self, obj, category=None):
		"""
		Returns a QuerySet of all articles in an optional given category that
		are unread by an object or account.
		"""
		query = super().all_unread_by(obj)
		if category:
			query = query & self.filter(db_category__iexact=category)
		return query

	def any_unread_by(self, obj, category=None):
		"""
		Returns True if any article in an optional category is unread by an
		object or account.
		"""
		return self.all_unread_by(obj, category).exists()


class SceneManager(NoteManager):
	"""
	Manager for Scene objects.
	"""

	default_locks = "read:id({id});write:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"

	def create(self, participants, content, tags=None, title=None, locks=None, status=None):
		scene = super().create(participants, content, tags=tags, title=title, locks=locks)
		if status:
			scene.status = status
		scene.save()
		return scene

	def all_public(self):
		"""Returns a QuerySet of all public Scenes."""
		return self.filter(db_status__exact=5)

	def all_public_by(self, obj):
		"""
		Returns a QuerySet of all Scenes including an object that are public.
		"""
		return self.all_by(obj) & self.all_public()

	def all_unread_by(self, obj, category=None):
		"""
		Returns a QuerySet of all articles in an optional given category that
		are unread by an object or account.
		"""
		query = super().all_unread_by(obj)
		if category:
			query = query & self.filter(db_category__iexact=category)
		return query

	def any_unread_by(self, obj, category=None):
		"""
		Returns True if any article in an optional category is unread by an
		object or account.
		"""
		return self.all_unread_by(obj, category).exists()

	def all_active(self):
		"""Returns a QuerySet of all actively recording scenes"""
		return self.filter(db_status__exact=1)
	
	def all_paused(self):
		return self.filter(db_status__exact=2)

	def all_active_by(self, obj):
		"""Returns a QuerySet of all active recording scenes including an object"""
		return self.all_by(obj) & self.all_active()
	
	def any_active_by(self, obj):
		return self.all_active_by(obj).exists()
	
	def all_paused_by(self, obj):
		"""Returns a QuerySet of all active recording scenes including an object"""
		return self.all_by(obj) & self.all_paused()
	
	def any_paused_by(self, obj):
		return self.all_active_by(obj).exists()