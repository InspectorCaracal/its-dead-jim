"""
Serializers in the Django Rest Framework are similar to Forms in normal django.
They're used for transmitting and validating data, both going to clients and
coming to the server. However, where forms often contained presentation logic,
such as specifying widgets to use for selection, serializers typically leave
those decisions in the hands of clients, and are more focused on converting
data from the server to JSON (serialization) for a response, and validating
and converting JSON data sent from clients to our enpoints into python objects,
often django model instances, that we can use (deserialization).

"""

from rest_framework import serializers

from evennia.web.api.serializers import TypeclassSerializerMixin
from evennia.objects.objects import DefaultObject

from evennia.utils import logger
from evennia.utils.text2html import parse_html


class StyledObjectDBSerializer(serializers.ModelSerializer):
	styled_name = serializers.SerializerMethodField()

	class Meta:
		model = DefaultObject
		fields = ["id", "db_key", "styled_name"]

	@staticmethod
	def get_styled_name(obj):
		namestr = obj.sdesc.get()
		return parse_html(namestr)

class GroupedContentsSerializer(serializers.ModelSerializer):
	characters = serializers.SerializerMethodField()
	objects = serializers.SerializerMethodField()
	exits = serializers.SerializerMethodField()

	class Meta:
		model = DefaultObject
		fields = ["id", "db_key", "styled_name"]

	@staticmethod
	def get_characters(obj):

		namestr = obj.sdesc.get()
		return parse_html(namestr)


class InventorySerializer(TypeclassSerializerMixin, serializers.ModelSerializer):

	worn = serializers.SerializerMethodField()
	carried = serializers.SerializerMethodField()

	class Meta:
		model = DefaultObject
		fields = [
			"id",
			"worn",
			"carried",
		]
#		] + TypeclassSerializerMixin.shared_fields
		read_only_fields = ["id"]

	@staticmethod
	def get_worn(obj):
		"""
		Args:
			obj: Object being serialized

		Returns:
			List of data from SimpleObjectDBSerializer
		"""
		worn = obj.clothing.all
		return StyledObjectDBSerializer(worn, many=True).data

	@staticmethod
	def get_carried(obj):
		"""
		Args:
			obj: Object being serialized

		Returns:
			List of data from SimpleObjectDBSerializer
		"""
		carried = [ ob for ob in obj.contents if ob not in obj.clothing.all ]
		return StyledObjectDBSerializer(carried, many=True).data

