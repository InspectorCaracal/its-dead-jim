from evennia.prototypes import spawner

def spawn(*prototypes, caller=None, generate_desc=False, restart=True, **kwargs):
	spawner.spawn.__doc__
	statlist = []
	for prot in prototypes:
		# NOTE: this will break stored dicts if they are not copied before being passed in
		stat = None
		if isinstance(prot, dict):
			stat = prot.pop('stats', None)
			if 'prototype_key' not in prot and prot.get('recipe'):
				prot['prototype_key'] = prot['recipe']
		statlist.append(stat)
	result = spawner.spawn(*prototypes, caller=caller, **kwargs)
	if kwargs.get("only_validate"):
		return result
	# do my custom post-processing
	for i, obj in enumerate(result):
		if statlist[i]:
			for key, dat in statlist[i].items():
				obj.stats.add(key, **dat)
		if generate_desc:
			obj.generate_desc()
		if restart:
			obj.at_server_start()
		obj.behaviors.load()

	return result


# reimplementing spawn command with my spawn method

from evennia.prototypes import prototypes as protlib
from evennia.prototypes import menus as olc_menus

from evennia.utils import to_str, iter_to_str, interactive, logger
from evennia.commands.default.muxcommand import MuxCommand
from ast import literal_eval as _LITERAL_EVAL

class CmdSpawn(MuxCommand):
	"""
	spawn objects from prototype

	Usage:
	  spawn[/noloc] <prototype_key>
	  spawn[/noloc] <prototype_dict>

	  spawn/search [prototype_keykey][;tag[,tag]]
	  spawn/list [tag, tag, ...]
	  spawn/list modules	- list only module-based prototypes
	  spawn/show [<prototype_key>]
	  spawn/update <prototype_key>

	  spawn/save <prototype_dict>
	  spawn/edit [<prototype_key>]
	  olc	 - equivalent to spawn/edit

	Switches:
	  noloc - allow location to be None if not specified explicitly. Otherwise,
			  location will default to caller's current location.
	  search - search prototype by name or tags.
	  list - list available prototypes, optionally limit by tags.
	  show, examine - inspect prototype by key. If not given, acts like list.
	  raw - show the raw dict of the prototype as a one-line string for manual editing.
	  save - save a prototype to the database. It will be listable by /list.
	  delete - remove a prototype from database, if allowed to.
	  update - find existing objects with the same prototype_key and update
			   them with latest version of given prototype. If given with /save,
			   will auto-update all objects with the old version of the prototype
			   without asking first.
	  edit, menu, olc - create/manipulate prototype in a menu interface.

	Example:
	  spawn GOBLIN
	  spawn {"key":"goblin", "typeclass":"monster.Monster", "location":"#2"}
	  spawn/save {"key": "grunt", prototype: "goblin"};;mobs;edit:all()
	\f
	Dictionary keys:
	  |wprototype_parent  |n - name of parent prototype to use. Required if typeclass is
						not set. Can be a path or a list for multiple inheritance (inherits
						left to right). If set one of the parents must have a typeclass.
	  |wtypeclass  |n - string. Required if prototype_parent is not set.
	  |wkey		|n - string, the main object identifier
	  |wlocation   |n - this should be a valid object or #dbref
	  |whome	   |n - valid object or #dbref
	  |wdestination|n - only valid for exits (object or dbref)
	  |wpermissions|n - string or list of permission strings
	  |wlocks	  |n - a lock-string
	  |waliases	|n - string or list of strings.
	  |wndb_|n<name>  - value of a nattribute (ndb_ is stripped)

	  |wprototype_key|n   - name of this prototype. Unique. Used to store/retrieve from db
							and update existing prototyped objects if desired.
	  |wprototype_desc|n  - desc of this prototype. Used in listings
	  |wprototype_locks|n - locks of this prototype. Limits who may use prototype
	  |wprototype_tags|n  - tags of this prototype. Used to find prototype

	  any other keywords are interpreted as Attributes and their values.

	The available prototypes are defined globally in modules set in
	settings.PROTOTYPE_MODULES. If spawn is used without arguments it
	displays a list of available prototypes.

	"""

	key = "@spawn"
	aliases = ["@olc"]
	switch_options = (
		"noloc",
		"search",
		"list",
		"show",
		"raw",
		"examine",
		"save",
		"delete",
		"menu",
		"olc",
		"update",
		"edit",
	)
	locks = "cmd:perm(spawn) or perm(Builder)"
	help_category = "Building"

	def _search_prototype(self, prototype_key, quiet=False):
		"""
		Search for prototype and handle no/multi-match and access.

		Returns a single found prototype or None - in the
		case, the caller has already been informed of the
		search error we need not do any further action.

		"""
		prototypes = protlib.search_prototype(prototype_key)
		nprots = len(prototypes)

		# handle the search result
		err = None
		if not prototypes:
			err = f"No prototype named '{prototype_key}' was found."
		elif nprots > 1:
			err = "Found {} prototypes matching '{}':\n  {}".format(
				nprots,
				prototype_key,
				", ".join(proto.get("prototype_key", "") for proto in prototypes),
			)
		else:
			# we have a single prototype, check access
			prototype = prototypes[0]
			if not self.caller.locks.check_lockstring(
				self.caller, prototype.get("prototype_locks", ""), access_type="spawn", default=True
			):
				err = "You don't have access to use this prototype."

		if err:
			# return None on any error
			if not quiet:
				self.caller.msg(err)
			return
		return prototype

	def _parse_prototype(self, inp, expect=dict):
		"""
		Parse a prototype dict or key from the input and convert it safely
		into a dict if appropriate.

		Args:
			inp (str): The input from user.
			expect (type, optional):
		Returns:
			prototype (dict, str or None): The parsed prototype. If None, the error
				was already reported.

		"""
		eval_err = None
		try:
			prototype = _LITERAL_EVAL(inp)
		except (SyntaxError, ValueError) as err:
			# treat as string
			eval_err = err
			prototype = to_str(inp)
		finally:
			# it's possible that the input was a prototype-key, in which case
			# it's okay for the LITERAL_EVAL to fail. Only if the result does not
			# match the expected type do we have a problem.
			if not isinstance(prototype, expect):
				if eval_err:
					string = (
						f"{inp}\n{eval_err}\n|RCritical Python syntax error in argument. Only"
						" primitive Python structures are allowed. \nMake sure to use correct"
						" Python syntax. Remember especially to put quotes around all strings"
						" inside lists and dicts.|n For more advanced uses, embed funcparser"
						" callables ($funcs) in the strings."
					)
				else:
					string = f"Expected {expect}, got {type(prototype)}."
				self.caller.msg(string)
				return

		if expect == dict:
			# an actual prototype. We need to make sure it's safe, so don't allow exec.
			if "exec" in prototype and not self.caller.check_permstring("Developer"):
				self.caller.msg(
					"Spawn aborted: You are not allowed to use the 'exec' prototype key."
				)
				return
			try:
				# we homogenize the prototype first, to be more lenient with free-form
				protlib.validate_prototype(protlib.homogenize_prototype(prototype))
			except RuntimeError as err:
				self.caller.msg(str(err))
				return
		return prototype

	def _get_prototype_detail(self, query=None, prototypes=None):
		"""
		Display the detailed specs of one or more prototypes.

		Args:
			query (str, optional): If this is given and `prototypes` is not, search for
				the prototype(s) by this query. This may be a partial query which
				may lead to multiple matches, all being displayed.
			prototypes (list, optional): If given, ignore `query` and only show these
				prototype-details.
		Returns:
			display (str, None): A formatted string of one or more prototype details.
				If None, the caller was already informed of the error.


		"""
		if not prototypes:
			# we need to query. Note that if query is None, all prototypes will
			# be returned.
			prototypes = protlib.search_prototype(key=query)
		if prototypes:
			return "\n".join(protlib.prototype_to_str(prot) for prot in prototypes)
		elif query:
			self.caller.msg(f"No prototype named '{query}' was found.")
		else:
			self.caller.msg("No prototypes found.")

	def _list_prototypes(self, key=None, tags=None):
		"""Display prototypes as a list, optionally limited by key/tags."""
		protlib.list_prototypes(self.caller, key=key, tags=tags, session=self.session)

	@interactive
	def _update_existing_objects(self, caller, prototype_key, quiet=False):
		"""
		Update existing objects (if any) with this prototype-key to the latest
		prototype version.

		Args:
			caller (Object): This is necessary for @interactive to work.
			prototype_key (str): The prototype to update.
			quiet (bool, optional): If set, don't report to user if no
				old objects were found to update.
		Returns:
			n_updated (int): Number of updated objects.

		"""
		prototype = self._search_prototype(prototype_key)
		if not prototype:
			return

		existing_objects = protlib.search_objects_with_prototype(prototype_key)
		if not existing_objects:
			if not quiet:
				caller.msg("No existing objects found with an older version of this prototype.")
			return

		if existing_objects:
			n_existing = len(existing_objects)
			slow = " (note that this may be slow)" if n_existing > 10 else ""
			string = (
				f"There are {n_existing} existing object(s) with an older version "
				f"of prototype '{prototype_key}'. Should it be re-applied to them{slow}? [Y]/N"
			)
			answer = yield (string)
			if answer.lower() in ["n", "no"]:
				caller.msg(
					"|rNo update was done of existing objects. "
					"Use spawn/update <key> to apply later as needed.|n"
				)
				return
			try:
				n_updated = spawner.batch_update_objects_with_prototype(
					prototype,
					objects=existing_objects,
					caller=caller,
				)
			except Exception:
				logger.log_trace()
			caller.msg(f"{n_updated} objects were updated.")
		return

	def _parse_key_desc_tags(self, argstring, desc=True):
		"""
		Parse ;-separated input list.
		"""
		key, desc, tags = "", "", []
		if ";" in argstring:
			parts = [part.strip().lower() for part in argstring.split(";")]
			if len(parts) > 1 and desc:
				key = parts[0]
				desc = parts[1]
				tags = parts[2:]
			else:
				key = parts[0]
				tags = parts[1:]
		else:
			key = argstring.strip().lower()
		return key, desc, tags

	def func(self):
		"""Implements the spawner"""

		caller = self.caller
		noloc = "noloc" in self.switches

		# run the menu/olc
		if (
			self.cmdstring == "olc"
			or "menu" in self.switches
			or "olc" in self.switches
			or "edit" in self.switches
		):
			# OLC menu mode
			prototype = None
			if self.lhs:
				prototype_key = self.lhs
				prototype = self._search_prototype(prototype_key)
				if not prototype:
					return
			olc_menus.start_olc(caller, session=self.session, prototype=prototype)
			return

		if "search" in self.switches:
			# query for a key match. The arg is a search query or nothing.

			if not self.args:
				# an empty search returns the full list
				self._list_prototypes()
				return

			# search for key;tag combinations
			key, _, tags = self._parse_key_desc_tags(self.args, desc=False)
			self._list_prototypes(key, tags)
			return

		if "raw" in self.switches:
			# query for key match and return the prototype as a safe one-liner string.
			if not self.args:
				caller.msg("You need to specify a prototype-key to get the raw data for.")
			prototype = self._search_prototype(self.args)
			if not prototype:
				return
			caller.msg(str(prototype))
			return

		if "show" in self.switches or "examine" in self.switches:
			# show a specific prot detail. The argument is a search query or empty.
			if not self.args:
				# we don't show the list of all details, that's too spammy.
				caller.msg("You need to specify a prototype-key to show.")
				return

			detail_string = self._get_prototype_detail(self.args)
			if not detail_string:
				return
			caller.msg(detail_string)
			return

		if "list" in self.switches:
			# for list, all optional arguments are tags.
			tags = self.lhslist
			err = self._list_prototypes(tags=tags)
			if err:
				caller.msg(
					"No prototypes found with prototype-tag(s): {}".format(
						iter_to_str(tags, "or")
					)
				)
			return

		if "save" in self.switches:
			# store a prototype to the database store
			if not self.args:
				caller.msg(
					"Usage: spawn/save [<key>[;desc[;tag,tag[,...][;lockstring]]]] ="
					" <prototype_dict>"
				)
				return
			if self.rhs:
				# input on the form key = prototype
				prototype_key, prototype_desc, prototype_tags = self._parse_key_desc_tags(self.lhs)
				prototype_key = None if not prototype_key else prototype_key
				prototype_desc = None if not prototype_desc else prototype_desc
				prototype_tags = None if not prototype_tags else prototype_tags
				prototype_input = self.rhs.strip()
			else:
				prototype_key = prototype_desc = None
				prototype_tags = None
				prototype_input = self.lhs.strip()

			# handle parsing
			prototype = self._parse_prototype(prototype_input)
			if not prototype:
				return

			prot_prototype_key = prototype.get("prototype_key")

			if not (prototype_key or prot_prototype_key):
				caller.msg(
					"A prototype_key must be given, either as `prototype_key = <prototype>` "
					"or as a key 'prototype_key' inside the prototype structure."
				)
				return

			if prototype_key is None:
				prototype_key = prot_prototype_key

			if prot_prototype_key != prototype_key:
				caller.msg("(Replacing `prototype_key` in prototype with given key.)")
				prototype["prototype_key"] = prototype_key

			if prototype_desc is not None and prot_prototype_key != prototype_desc:
				caller.msg("(Replacing `prototype_desc` in prototype with given desc.)")
				prototype["prototype_desc"] = prototype_desc
			if prototype_tags is not None and prototype.get("prototype_tags") != prototype_tags:
				caller.msg("(Replacing `prototype_tags` in prototype with given tag(s))")
				prototype["prototype_tags"] = prototype_tags

			string = ""
			# check for existing prototype (exact match)
			old_prototype = self._search_prototype(prototype_key, quiet=True)

			diff = spawner.prototype_diff(old_prototype, prototype, homogenize=True)
			diffstr = spawner.format_diff(diff)
			new_prototype_detail = self._get_prototype_detail(prototypes=[prototype])

			if old_prototype:
				if not diffstr:
					string = f"|yAlready existing Prototype:|n\n{new_prototype_detail}\n"
					question = (
						"\nThere seems to be no changes. Do you still want to (re)save? [Y]/N"
					)
				else:
					string = (
						f'|yExisting prototype "{prototype_key}" found. Change:|n\n{diffstr}\n'
						f"|yNew changed prototype:|n\n{new_prototype_detail}"
					)
					question = (
						"\n|yDo you want to apply the change to the existing prototype?|n [Y]/N"
					)
			else:
				string = f"|yCreating new prototype:|n\n{new_prototype_detail}"
				question = "\nDo you want to continue saving? [Y]/N"

			answer = yield (string + question)
			if answer.lower() in ["n", "no"]:
				caller.msg("|rSave cancelled.|n")
				return

			# all seems ok. Try to save.
			try:
				prot = protlib.save_prototype(prototype)
				if not prot:
					caller.msg("|rError saving:|R {}.|n".format(prototype_key))
					return
			except protlib.PermissionError as err:
				caller.msg("|rError saving:|R {}|n".format(err))
				return
			caller.msg("|gSaved prototype:|n {}".format(prototype_key))

			# check if we want to update existing objects

			self._update_existing_objects(self.caller, prototype_key, quiet=True)
			return

		if not self.args:
			# all switches beyond this point gets a common non-arg return
			ncount = len(protlib.search_prototype())
			caller.msg(
				"Usage: spawn <prototype-key> or {{key: value, ...}}"
				f"\n ({ncount} existing prototypes. Use /list to inspect)"
			)
			return

		if "delete" in self.switches:
			# remove db-based prototype
			prototype_detail = self._get_prototype_detail(self.args)
			if not prototype_detail:
				return

			string = f"|rDeleting prototype:|n\n{prototype_detail}"
			question = "\nDo you want to continue deleting? [Y]/N"
			answer = yield (string + question)
			if answer.lower() in ["n", "no"]:
				caller.msg("|rDeletion cancelled.|n")
				return

			try:
				success = protlib.delete_prototype(self.args)
			except protlib.PermissionError as err:
				retmsg = f"|rError deleting:|R {err}|n"
			else:
				retmsg = (
					"Deletion successful"
					if success
					else "Deletion failed (does the prototype exist?)"
				)
			caller.msg(retmsg)
			return

		if "update" in self.switches:
			# update existing prototypes
			prototype_key = self.args.strip().lower()
			self._update_existing_objects(self.caller, prototype_key)
			return

		# If we get to this point, we use not switches but are trying a
		# direct creation of an object from a given prototype or -key

		prototype = self._parse_prototype(
			self.args, expect=dict if self.args.strip().startswith("{") else str
		)
		if not prototype:
			# this will only let through dicts or strings
			return

		key = "<unnamed>"
		if isinstance(prototype, str):
			# A prototype key we are looking to apply
			prototype_key = prototype
			prototype = self._search_prototype(prototype_key)

			if not prototype:
				return

		# proceed to spawning
		try:
			for obj in spawn(prototype, caller=self.caller):
				self.caller.msg("Spawned %s." % obj.get_display_name(self.caller))
				if not prototype.get("location") and not noloc:
					# we don't hardcode the location in the prototype (unless the user
					# did so manually) - that would lead to it having to be 'removed' every
					# time we try to update objects with this prototype in the future.
					obj.location = caller.location
		except RuntimeError as err:
			caller.msg(err)