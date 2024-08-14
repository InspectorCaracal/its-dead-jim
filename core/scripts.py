from evennia.scripts.scripts import DefaultScript

from base_systems.maps.building import get_by_uid
from utils.table import EvTable


class Script(DefaultScript):
	@property
	def uid(self):
		return self.attributes.get('uid', category="systems")

	@uid.setter
	def uid(self, value):
		if get_by_uid(value):
			raise KeyError(f"Object {value} already exists.")
		self.attributes.add('uid', value, category="systems")



# gross
from evennia.commands.default.building import ScriptEvMore as BaseScriptEvMore
from evennia.commands.default.building import CmdScripts as BaseCmdScripts
from evennia.scripts.models import ScriptDB
from evennia.utils import logger, create
class ScriptEvMore(BaseScriptEvMore):
	def page_formatter(self, scripts):
		"""Takes a page of scripts and formats the output
		into an EvTable."""

		if not scripts:
			return "<No scripts>"

		table = EvTable(
			"|wdbref|n",
			"|wobj|n",
			"|wkey|n",
			"|wintval|n",
			"|wnext|n",
			"|wrept|n",
			"|wtypeclass|n",
			"|wdesc|n",
			align="r",
			border="tablecols",
			width=self.width,
		)

		for script in scripts:
			nextrep = script.time_until_next_repeat()
			if nextrep is None:
				nextrep = script.db._paused_time
				nextrep = f"PAUSED {int(nextrep)}s" if nextrep else "--"
			else:
				nextrep = f"{nextrep}s"

			maxrepeat = script.repeats
			remaining = script.remaining_repeats() or 0
			if maxrepeat:
				rept = "%i/%i" % (maxrepeat - remaining, maxrepeat)
			else:
				rept = "-/-"

			table.add_row(
				f"#{script.id}",
				(
					f"{script.obj.key}({script.obj.dbref})"
					if (hasattr(script, "obj") and script.obj)
					else "<Global>"
				),
				script.key,
				script.interval if script.interval > 0 else "--",
				nextrep,
				rept,
				script.typeclass_path.rsplit(".", 1)[-1],
				# crop(script.desc, width=20),
			)

		return str(table)



class CmdScripts(BaseCmdScripts):
	def func(self):
		"""implement method"""

		caller = self.caller

		if not self.args:
			# show all scripts
			scripts = ScriptDB.objects.all().exclude(db_typeclass_path__in=self.hide_script_paths)
			if not scripts:
				caller.msg("No scripts found.")
				return
			ScriptEvMore(caller, scripts.order_by("id"), session=self.session)
			return

		# find script or object to operate on
		scripts, obj = None, None
		if self.rhs:
			obj_query = self.lhs
			script_query = self.rhs
		elif self.rhs is not None:
			# an empty "="
			obj_query = self.lhs
			script_query = None
		else:
			obj_query = None
			script_query = self.args

		scripts = self._search_script(script_query) if script_query else None
		objects = caller.search(obj_query, quiet=True) if obj_query else None
		obj = objects[0] if objects else None

		if not self.switches:
			# creation / view mode
			if obj:
				# we have an object
				if self.rhs:
					# creation mode
					if obj.scripts.add(self.rhs, autostart=True):
						caller.msg(
							f"Script |w{self.rhs}|n successfully added and "
							f"started on {obj.get_display_name(caller)}."
						)
					else:
						caller.msg(
							f"Script {self.rhs} could not be added and/or started "
							f"on {obj.get_display_name(caller)} (or it started and "
							"immediately shut down)."
						)
				else:
					# just show all scripts on object
					scripts = ScriptDB.objects.filter(db_obj=obj).exclude(
						db_typeclass_path__in=self.hide_script_paths
					)
					if scripts:
						ScriptEvMore(caller, scripts.order_by("id"), session=self.session)
					else:
						caller.msg(f"No scripts defined on {obj}")

			elif scripts:
				# show found script(s)
				ScriptEvMore(caller, scripts.order_by("id"), session=self.session)

			else:
				# create global script
				try:
					new_script = create.create_script(self.args)
				except ImportError:
					logger.log_trace()
					new_script = None

				if new_script:
					caller.msg(
						f"Global Script Created - {new_script.key} ({new_script.typeclass_path})"
					)
					ScriptEvMore(caller, [new_script], session=self.session)
				else:
					caller.msg(
						f"Global Script |rNOT|n Created |r(see log)|n - arguments: {self.args}"
					)

		elif scripts or obj:
			# modification switches - must operate on existing scripts

			if not scripts:
				scripts = ScriptDB.objects.filter(db_obj=obj).exclude(
					db_typeclass_path__in=self.hide_script_paths
				)

			if scripts.count() > 1:
				ret = yield (
					f"Multiple scripts found: {scripts}. Are you sure you want to "
					"operate on all of them? [Y]/N? "
				)
				if ret.lower() in ("n", "no"):
					caller.msg("Aborted.")
					return

			for script in scripts:
				script_key = script.key
				script_typeclass_path = script.typeclass_path
				scripttype = f"Script on {obj}" if obj else "Global Script"

				for switch in self.switches:
					verb = self.switch_mapping[switch]
					msgs = []
					try:
						getattr(script, switch)()
					except Exception:
						logger.log_trace()
						msgs.append(
							f"{scripttype} |rNOT|n {verb} |r(see log)|n - "
							f"{script_key} ({script_typeclass_path})|n"
						)
					else:
						msgs.append(f"{scripttype} {verb} - {script_key} ({script_typeclass_path})")
				caller.msg("\n".join(msgs))
				if "delete" not in self.switches:
					if script and script.pk:
						ScriptEvMore(caller, [script], session=self.session)
					else:
						caller.msg("Script was deleted automatically.")
		else:
			caller.msg("No scripts found.")