from utils.strmanip import numbered_name


def menunode_login(caller, raw_string, **kwargs):
	"""Connect to your ATM account"""
	# TODO: connect this to the banking system with a PIN and stuff
	text = "Thank you for banking with Free Money.\n\nPlease enter your card into the machine."

	options = []
	for obj in caller.contents:
		if obj.behaviors.can_do('pay_in'):
			options.append( {
				'desc': obj.get_display_name(caller, article=False),
				'goto': ("menunode_choose", {'receiver': obj})
			})
	
	if not options:
		options = {"key": ("Cancel", 'c'), "desc": "(You don't have a card...)", "goto": "menunode_end"}
	return text, options

def menunode_choose(caller, raw_string, receiver, **kwargs):
	caller.ndb._evmenu.receiver = receiver
	text = "Card confirmed.\n\nPlease choose an option below."

	options = (
		{"desc": "Withdraw funds", "goto": "menunode_withdraw"},
		{"desc": "Check card status", "goto": "menunode_status"},
		{"desc": "Cancel", "goto": "menunode_end"},
	)
	return text, options

def menunode_status(caller, raw_string, **kwargs):
	if value := caller.ndb._evmenu.receiver.db.value:
		currency = caller.ndb._evmenu.receiver.db.currency or 'dollar'
		# TODO: make a money util for better currency rendering
		text = f"Your card has {numbered_name(currency, value)} on it."

	else:
		text = "This card has no value."

	text += "\n\nPlease choose an option below."
	options = (
		{"desc": "Withdraw funds", "goto": "menunode_withdraw"},
		{"desc": "Change card", "goto": "menunode_login"},
		{"desc": "Cancel", "goto": "menunode_end"},
	)
	return text, options

def menunode_withdraw(caller, raw_string, **kwargs):
	text = "Please enter how much you would like to withdraw."

	option = { "key": "_default", "goto": _withdraw_funds }
	return text, option

def _withdraw_funds(caller, raw_string, **kwargs):
	try:
		amount = float(raw_string.strip())
	except ValueError:
		return "menunode_error"
	
	if caller.ndb._evmenu.atm.do_pay_out(amount, caller.ndb._evmenu.receiver):
		return "menunode_end"
	else:
		return "menunode_error"

def menunode_success(caller, raw_string, **kwargs):
	text = "Transaction successful.\n\nPlease choose an option below."

	options = (
		{"desc": "Withdraw funds", "goto": "menunode_withdraw"},
		{"desc": "Check card status", "goto": "menunode_status"},
		{"desc": "Cancel", "goto": "menunode_end"},
	)
	return text, options


def menunode_error(caller, raw_string, **kwargs):
	return "Your transaction could not be processed. Please try again later."

def menunode_end(caller, raw_string, **kwargs):
	return "Thank you for using Free Money. Please tell all of your friends about how great we are."
