"""
This file defines global variables that will always be available in a view
context without having to repeatedly include it.
"""
from os.path import getmtime
from random import choice
from django.conf import settings

WEBSITE_CSS_VERSION  = round(getmtime("web/static/website/css/website.css"))

WEBCLIENT_CSS_VERSION = round(getmtime("web/static/webclient/css/webclient.css"))
WEBCLIENT_JS_VERSION  = round(getmtime("web/static/webclient/js/webclient.js"))

def extra_context(request):
    """
    Returns context stuff, which is automatically added to context of all views.
    """
    return {
        "css_version": WEBSITE_CSS_VERSION,
        "client_css_version": WEBCLIENT_CSS_VERSION,
        "client_js_version": WEBCLIENT_JS_VERSION,
        "pick_game_slogan": choice(settings.GAME_SLOGANS),
    }
