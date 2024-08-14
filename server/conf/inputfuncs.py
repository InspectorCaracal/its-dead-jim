"""
Input functions

Input functions are always called from the client (they handle server
input, hence the name).

This module is loaded by being included in the
`settings.INPUT_FUNC_MODULES` tuple.

All *global functions* included in this module are considered
input-handler functions and can be called by the client to handle
input.

An input function must have the following call signature:

    cmdname(session, *args, **kwargs)

Where session will be the active session and *args, **kwargs are extra
incoming arguments and keyword properties.

A special command is the "default" command, which is will be called
when no other cmdname matches. It also receives the non-found cmdname
as argument.

    default(session, cmdname, *args, **kwargs)

"""

def auto_look(session, *args, **kwargs):
	appear = None
	if (obj := session.puppet) and obj.location:
		appear = obj.at_look(obj.location, look_in=False)
	elif session.account:
		appear = session.account.at_look()

	if not appear:
		return

	if type(appear) is tuple:
		session.msg( (appear[0], {"target": "look"} | appear[1]), options=None)
	else:
		session.msg((appear, {"target": "look"}), options=None)


def close_quit(session, *args, **kwargs):
	if session.ndb._evmenu:
		session.execute_cmd('q')
	elif session.puppet and session.puppet.ndb._evmenu:
		session.execute_cmd('q')


def get_channels(session, *args, **kwargs):
	if session.account:
		from core.channels import Channel
		for chan in Channel.objects.all():
			if chan.has_connection(session.account):
				session.msg(chaninfo=(chan.key))

# def default(session, cmdname, *args, **kwargs):
#     """
#     Handles commands without a matching inputhandler func.
#
#     Args:
#         session (Session): The active Session.
#         cmdname (str): The (unmatched) command name
#         args, kwargs (any): Arguments to function.
#
#     """
#     pass

