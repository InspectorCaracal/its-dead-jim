"""
Views are the functions that are called by different url endpoints. The Django
Rest Framework provides collections called 'ViewSets', which can generate a
number of views for the common CRUD operations.

"""
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from evennia.objects.objects import DefaultCharacter, DefaultExit, DefaultRoom
from evennia.web.api.views import ObjectDBViewSet

from . import serializers
from . import permissions

from evennia.utils import logger

class CharacterViewSet(ObjectDBViewSet):
	"""
	Characters are a type of Object commonly used as player avatars in-game.

	"""
	permission_classes = [permissions.CharacterPermission]
	queryset = DefaultCharacter.objects.all_family()

	@action(detail=True, methods=["get"])
	def inventory(self, request, pk=None):
		"""
		Retrieve just the inventory data for a character object
		"""
		obj = self.get_object()
		return Response( serializers.InventorySerializer(obj).data, status=status.HTTP_200_OK )


class RoomViewSet(ObjectDBViewSet):
	"""
	Rooms indicate discrete locations in-game.

	"""

	queryset = DefaultRoom.objects.all_family()

	def get_contents(self, request, pk=None):
		"""
		Retrieve visible contents, grouped by type
		"""
		obj = self.get_object()
		return Response( serializers.GroupedContentsSerializer(obj).data, status=status.HTTP_200_OK )
