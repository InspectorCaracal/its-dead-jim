from evennia.utils import iter_to_str

class MetaDataHandler:
	def __init__(self, obj):
		self.obj = obj
		self.load()
	
	def load(self, attrs=['data', 'locks', 'verbs']):
		for attr_name in attrs:
			if value := self.obj.attributes.get(f"meta_{attr_name}", category="systems"):
				setattr(self, attr_name, value)
			else:
				setattr(self, attr_name, {})
	
	def save(self, attrs=['data', 'locks', 'verbs']):
		for attr_name in attrs:
			if value := getattr(self, attr_name, None):
				self.obj.attributes.add(f"meta_{attr_name}", value, category="systems")
	
	def add(self, field, quantity=None, verb=None, meta_type="meta", lockstring=None, **kwargs):
		to_save = ['data']
		if meta_type not in self.data:
			self.data[meta_type] = {}
		ref = self.data[meta_type]
		if quantity:
			original = ref.get(field,0)
			ref[field] = quantity+original
		elif ref.get(field):
			raise ValueError(f"{field} is a quantified value")
		else:
			ref[field] = quantity
		if lockstring:
			self.locks[meta_type] = lockstring
			to_save.append('locks')
		if verb and verb != self.verbs.get(meta_type):
			self.verbs[meta_type] = verb
			to_save.append('verbs')

		self.save(attrs=to_save)

	def display(self, viewer, **kwargs):
		if not viewer:
			return ''
		lines = []
		for meta, data in self.data.items():
			if lock := self.locks.get(meta):
				if not self.obj.locks.check_lockstring(viewer, lock, default=True, access_type='view'):
					continue
			verb = self.verbs.get(meta, "see")
			# TODO: make the quantity display as relative words
			items = [ f"{val} {key}" if val else key for key, val in data.items() ]
			text = f"You {verb} {iter_to_str(items)}."
			lines.append(text)
		return "\n".join(lines)
