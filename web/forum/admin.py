from django.contrib import admin

from web.forum.models import (Category, Board)

# Register your models here.


admin.site.register(Category)
admin.site.register(Board)
