from evennia.utils import logger
from evennia.utils.dbserialize import deserialize
from copy import copy

class HandlerBase:
	def __init__(self, obj, db_attr, db_cat='systems', default_data={}):
		self.obj = obj
		self._db_attr = db_attr
		self._db_cat = db_cat
		self._data = copy(default_data)
		self._load()

	def _load(self):
		if data := self.obj.attributes.get(self._db_attr, category=self._db_cat):
			self._data = deserialize(data)

	def _save(self):
		try:
			self.obj.attributes.add(self._db_attr, self._data, category=self._db_cat)
		except Exception as e:
			logger.log_err(f"Could not save handler data for {type(self)} on {self.obj} (#{self.obj.pk})! Cached data may be corrupt; reloading from database.")
			logger.log_err(f"Cached data was: {self._data}")
			self._load()
