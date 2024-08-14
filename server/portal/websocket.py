"""
Webclient based on websockets.

This implements a webclient with WebSockets (http://en.wikipedia.org/wiki/WebSocket)
by use of the autobahn-python package's implementation (https://github.com/crossbario/autobahn-python).
It is used together with evennia/web/media/javascript/evennia_websocket_webclient.js.

All data coming into the webclient is in the form of valid JSON on the form

`["inputfunc_name", [args], {kwarg}]`

which represents an "inputfunc" to be called on the Evennia side with *args, **kwargs.
The most common inputfunc is "text", which takes just the text input
from the command line and interprets it as an Evennia Command: `["text", ["look"], {}]`

"""
import re
import json
import html
from django.conf import settings
from evennia.utils.utils import mod_import, class_from_module
from evennia.utils import logger
from autobahn.twisted.websocket import WebSocketServerProtocol
from autobahn.exception import Disconnected

from utils.colors import ev_to_html


_CLIENT_SESSIONS = mod_import(settings.SESSION_ENGINE).SessionStore
_UPSTREAM_IPS = settings.UPSTREAM_IPS

# Status Code 1000: Normal Closure
#   called when the connection was closed through JavaScript
CLOSE_NORMAL = WebSocketServerProtocol.CLOSE_STATUS_CODE_NORMAL

# Status Code 1001: Going Away
#   called when the browser is navigating away from the page
GOING_AWAY = WebSocketServerProtocol.CLOSE_STATUS_CODE_GOING_AWAY

_BASE_SESSION_CLASS = class_from_module(settings.BASE_SESSION_CLASS)

from evennia.server.portal.webclient import WebSocketClient as BaseWSClient

class WebSocketClient(BaseWSClient):
  """
  Implements the server-side of the Websocket connection.

  """

  # nonce value, used to prevent the webclient from erasing the
  # webclient_authenticated_uid value of csession on disconnect
  nonce = 0



  def disconnect(self, reason=None):
    """
    Generic hook for the engine to call in order to
    disconnect this protocol.

    Args:
      reason (str or None): Motivation for the disconnection.

    """
    csession = self.get_client_session()

    if csession:
      # if the nonce is different, webclient_authenticated_uid has been
      # set *before* this disconnect (disconnect called after a new client
      # connects, which occurs in some 'fast' browsers like Google Chrome
      # and Mobile Safari)
      if csession.get("webclient_authenticated_nonce", 0) == self.nonce:
        csession["webclient_authenticated_uid"] = None
        csession["webclient_authenticated_nonce"] = 0
        csession.save()
      self.logged_in = False

    self.sessionhandler.disconnect(self)
    # autobahn-python:
    # 1000 for a normal close, 1001 if the browser window is closed,
    # 3000-4999 for app. specific,
    # in case anyone wants to expose this functionality later.
    #
    # sendClose() under autobahn/websocket/interfaces.py
    self.sendClose(CLOSE_NORMAL, reason)

  def onClose(self, wasClean, code=None, reason=None):
    """
    This is executed when the connection is lost for whatever
    reason. it can also be called directly, from the disconnect
    method.

    Args:
      wasClean (bool): ``True`` if the WebSocket was closed cleanly.
      code (int or None): Close status as sent by the WebSocket peer.
      reason (str or None): Close reason as sent by the WebSocket peer.

    """
    if code == CLOSE_NORMAL or code == GOING_AWAY:
      self.disconnect(reason)
    else:
      self.websocket_close_code = code

  def onMessage(self, payload, isBinary):
    """
    Callback fired when a complete WebSocket message was received.

    Args:
      payload (bytes): The WebSocket message received.
      isBinary (bool): Flag indicating whether payload is binary or
               UTF-8 encoded text.

    """
    cmdarray = json.loads(str(payload, "utf-8"))
    if cmdarray:
      self.data_in(**{cmdarray[0]: [cmdarray[1], cmdarray[2]]})

  def send_text(self, *args, **kwargs):
    """
    Send text data. This will pre-process the text for
    color-replacement, conversion to html etc.

    Args:
      text (str): Text to send.

    Keyword Args:
      options (dict): Options-dict with the following keys understood:
        - raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
        - nocolor (bool): Clean out all color.
        - screenreader (bool): Use Screenreader mode.
        - send_prompt (bool): Send a prompt with parsed html

    """
    if args:
      args = list(args)
      text = args[0]
      if text is None:
        return
    else:
      return

    flags = self.protocol_flags

    options = kwargs.pop("options", {})
    prompt = options.get("send_prompt", False)

    cmd = "prompt" if prompt else "text"
    if options.get("raw",False):
      args[0] = html.escape(text)
    else:
      args[0] = ev_to_html(text)

    # send to client on required form [cmdname, args, kwargs]
    self.sendLine(json.dumps([cmd, args, kwargs]))
  
  def send_chaninfo(self, *args, **kwargs):
    if args:
      args = list(args)
      text = args[0]
      if text is None:
        return
    else:
      return

    flags = self.protocol_flags

    options = kwargs.pop("options", {})

    # send to client on required form [cmdname, args, kwargs]
    self.sendLine(json.dumps(["chaninfo", args, kwargs]))

  def data_in(self, **kwargs):
    if kwargs.get("ping"):
      # this is just a keepalive for the protocol...
      self.sendLine(json.dumps(["pong", "", ""]))
      return
    super().data_in(**kwargs)
