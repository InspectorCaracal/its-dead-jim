from base_systems.prototypes import base_things
from data.money import cashnstuff

def _process_module(m):
	return [ dict(prot) | { "prototype_key": name.lower() } for name, prot in vars(m).items() if not name.startswith('_') and name != "MergeDict" ]

PROTOTYPE_LIST = _process_module(base_things) + _process_module(cashnstuff)# + another module