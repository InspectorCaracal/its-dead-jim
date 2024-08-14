from utils.handlers import HandlerBase

class MemoryHandler(HandlerBase):
	def __init__(self, obj):
		super().__init__(obj, 'npc_memory', 'systems')
