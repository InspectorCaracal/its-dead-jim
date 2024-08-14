from django.conf import settings

def _do_wipe():
	from evennia.objects.models import ObjectDB
	from evennia.scripts.models import ScriptDB
	# TODO: scenes
	models = (ObjectDB, ScriptDB)

	# delete() to clean up foreign key attributes
	for model in models:
		print(f"Cleaning out {str(model)}....")
		model.objects.all().delete()

	# reset auto-increment IDs
	from django.db import connection
	cursor = connection.cursor()
	if connection.vendor == "sqlite":
		query_str = "UPDATE sqlite_sequence SET seq = 0 WHERE name == '{table}'"
	elif connection.vendor in ("mysql", "mariadb"):
		query_str = "ALTER TABLE {table} AUTO_INCREMENT = 0"
	for model in models:
		print(f"Resetting initial index for {str(model)}....")
		model_table = model._meta.db_table
		cursor.execute(query_str.format(table=model_table))
		# model_attr_table = f"{model_table}_db_attributes"
		# cursor.execute(query_str.format(table=model_attr_table))
		# model_tag_table = f"{model_table}_db_tags"
		# cursor.execute(query_str.format(table=model_tag_table))


ERROR_NO_SUPERUSER = """
	No superuser exists yet. The superuser is the 'owner' account on
	the Evennia server. Create a new superuser using the command

	   evennia createsuperuser

	Follow the prompts, then restart the server.
	"""

LIMBO_DESC = """
Welcome to your new |wEvennia|n-based game! Visit https://www.evennia.com if you need
help, want to contribute, report issues or just join the community.

As a privileged user, write |wbatchcommand tutorial_world.build|n to build
tutorial content. Once built, try |wintro|n for starting help and |wtutorial|n to
play the demo game.
"""


def _get_superuser_account():
	"""
	Get the superuser (created at the command line) and don't take no for an answer.

	Returns:
		Account: The first superuser (User #1).

	Raises:
		AccountDB.DoesNotExist: If the superuser couldn't be found.

	"""
	from evennia.accounts.models import AccountDB
	try:
		superuser = AccountDB.objects.get(id=1)
	except AccountDB.DoesNotExist:
		raise AccountDB.DoesNotExist(ERROR_NO_SUPERUSER)
	return superuser


def _reinit_objects():
	"""
	Re-creates the #1 account and Limbo room.

	"""
	import evennia
	evennia._init()

	print("Rebuild: Creating objects (Character #1 and Limbo room) ...")

	# Set the initial User's account object's username on the #1 object.
	# This object is pure django and only holds name, email and password.
	superuser = _get_superuser_account()
	from evennia.objects.models import ObjectDB
	from evennia.utils import create

	# Create an Account 'user profile' object to hold eventual
	# mud-specific settings for the AccountDB object.
	account_typeclass = settings.BASE_ACCOUNT_TYPECLASS

	# run all creation hooks on superuser (we must do so manually
	# since the manage.py command does not)
	superuser.swap_typeclass(account_typeclass, clean_attributes=True)
	superuser.basetype_setup()
	superuser.at_account_creation()
	superuser.locks.add(
		"examine:perm(Developer);edit:false();delete:false();boot:false();msg:all()"
	)
	# this is necessary for quelling to work correctly.
	superuser.permissions.add("Developer")

	# Limbo is the default "nowhere" starting room

	# Create the in-game god-character for account #1 and set
	# it to exist in Limbo.
	try:
		superuser_character = ObjectDB.objects.get(id=1)
	except ObjectDB.DoesNotExist:
		superuser_character, errors = superuser.create_character(
			key=superuser.username, nohome=True, description="I AM #1"
		)
		if errors:
			raise Exception(str(errors))

	superuser_character.locks.add(
		"examine:perm(Developer);edit:false();delete:false();boot:false();msg:all();puppet:false()"
	)
	superuser_character.permissions.add("Developer")
	superuser_character.save()

	superuser.attributes.add("_first_login", True)
	superuser.attributes.add("_last_puppet", superuser_character)

	room_typeclass = settings.BASE_ROOM_TYPECLASS
	try:
		limbo_obj = ObjectDB.objects.get(id=2)
	except ObjectDB.DoesNotExist:
		limbo_obj = create.create_object(room_typeclass, "Limbo", nohome=True)

	limbo_obj.db_typeclass_path = room_typeclass
	limbo_obj.db.desc = LIMBO_DESC.strip()
	limbo_obj.save()

	# Now that Limbo exists, try to set the user up in Limbo (unless
	# the creation hooks already fixed this).
	if not superuser_character.location:
		superuser_character.location = limbo_obj
	if not superuser_character.home:
		superuser_character.home = limbo_obj

def _rebuild_gameworld():
	"""
	Runs the most recent generated build file.
	"""


def wipe_gameworld():
	print("This will wipe the game.")
	_do_wipe()
	print("Wipe complete. Recreating initial objects...")
	_reinit_objects()
	print("This is where it would rebuild the game world.")
