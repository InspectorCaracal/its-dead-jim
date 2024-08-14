from evennia.utils import logger

_TASK_HANDLER = None

def delay(timedelay, callback, *args, **kwargs):
	"""
	Delay the calling of a callback (function).

	Args:
		timedelay (int or float): The delay in seconds.
		callback (callable): Will be called as `callback(*args, **kwargs)`
			after `timedelay` seconds.
		*args: Will be used as arguments to callback
	Keyword Args:
		persistent (bool, optional): If True the delay remains after a server restart.
			persistent is False by default.
		any (any): Will be used as keyword arguments to callback.

	Returns:
		task (TaskHandlerTask): An instance of a task.
			Refer to, evennia.scripts.taskhandler.TaskHandlerTask

	Notes:
		The task handler (`evennia.scripts.taskhandler.TASK_HANDLER`) will
		be called for persistent or non-persistent tasks.
		If persistent is set to True, the callback, its arguments
		and other keyword arguments will be saved (serialized) in the database,
		assuming they can be.  The callback will be executed even after
		a server restart/reload, taking into account the specified delay
		(and server down time).
		Keep in mind that persistent tasks arguments and callback should not
		use memory references.
		If persistent is set to True the delay function will return an int
		which is the task's id intended for use with TASK_HANDLER's do_task
		and remove methods.
		All persistent tasks whose time delays have passed will be called on server startup.

	"""
	global _TASK_HANDLER
	if _TASK_HANDLER is None:
		from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER

	task = _TASK_HANDLER.add(timedelay, callback, *args, **kwargs)
	task.get_deferred().addErrback(logger.log_trace)
	return task


def delay_iter(gener, duration=1):
	try:
		next(gener)
	except StopIteration:
		return
	delay(duration, delay_iter, gener)