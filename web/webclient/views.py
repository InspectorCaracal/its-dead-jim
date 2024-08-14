"""
This contains a simple view for rendering the webclient
page and serve it eventual static content.

"""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.contrib.auth import login, authenticate

from evennia.accounts.models import AccountDB
from evennia.utils import logger


def channels(request):
    """
    Load the channels template.
    """

    # check if webclient should be enabled
    if not settings.WEBCLIENT_ENABLED:
        raise Http404

    # make sure to store the browser session's hash so the webclient can get to it!
    pagevars = {"browser_sessid": request.session.session_key}

    return render(request, "channels.html", pagevars)
