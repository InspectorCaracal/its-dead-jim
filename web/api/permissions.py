"""
Sets up an api-access permission check using the in-game permission hierarchy.

"""


from rest_framework import permissions
from django.conf import settings
from evennia.locks.lockhandler import check_perm
from evennia.web.api.permissions import EvenniaPermission

class CharacterPermission(EvenniaPermission):
    # subclass this to change these permissions
    MINIMUM_LIST_PERMISSION = settings.REST_FRAMEWORK.get("DEFAULT_LIST_PERMISSION", "builder")
    MINIMUM_CREATE_PERMISSION = settings.REST_FRAMEWORK.get("DEFAULT_CREATE_PERMISSION", "builder")
    puppet_locks = settings.REST_FRAMEWORK.get("DEFAULT_PUPPET_LOCKS", ["puppet"])
    view_locks = settings.REST_FRAMEWORK.get("DEFAULT_VIEW_LOCKS", ["examine"])
    destroy_locks = settings.REST_FRAMEWORK.get("DEFAULT_DESTROY_LOCKS", ["delete"])
    update_locks = settings.REST_FRAMEWORK.get("DEFAULT_UPDATE_LOCKS", ["control", "edit"])

    def has_object_permission(self, request, view, obj):
        """
				Checks object-level permissions after has_permission
        """
        if view.action == "inventory":
            return self.check_locks(obj, request.user, self.puppet_locks)
        return super().has_object_permission(request, view, obj)
