from utils.handlers import HandlerBase


class PersonalityHandler(HandlerBase):
	def __init__(self, obj):
		super().__init__(obj, 'npc_ai', 'systems')
	
