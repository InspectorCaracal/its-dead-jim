"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path
from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns
from .views import index, errors, about, accounts, characters

# add patterns here
urlpatterns = [
    path("", index.EvenniaIndexView.as_view(), name="index"),
    path("about", about.AboutPageView.as_view(), name="about"),
    path("characters/", characters.CharacterListView.as_view(), name="character-list"),
    path("characters/manage/", errors.not_found, name="character-manage"),
    path(
        "characters/detail/<str:slug>/<int:pk>/",
        characters.CharacterDetailView.as_view(),
        name="player-character-detail",
    ),
    path("auth/register", accounts.AccountCreateView.as_view(), name="register"),
    # path("url-pattern", imported_python_view),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
