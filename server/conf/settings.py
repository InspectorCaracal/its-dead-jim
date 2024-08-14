r"""
Evennia settings file.

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

SERVERNAME = "Nexus"
# backwards-compatability fallback
GAME_SLOGAN = "Welcome to the Future"
GAME_SLOGANS = (
    "Welcome to the Future",
    "not The Future we Need, but The Future we Deserve",
    "in Cyberpunk Future, Corporation Owns You",
    "sometimes, Crime Does Pay",
    "you can do Flips 'n Shit",
    "Action and Crafting, together like a PB&J",
    "be Kind to your Neighbors",
    "CyberPunk Robin Hood",
)

# character control limits
MULTISESSION_MODE = 2
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_SIMULTANEOUS_PUPPETS = 3
MAX_NR_CHARACTERS = 3

# Time-related settings
TIME_ZONE = "MST"
# Deactivate time zone in datetimes
USE_TZ = False

CHARGEN_MENU = "systems.chargen.menu"

# help system settings
FILE_HELP_ENTRY_MODULES = ["data.help.general"]
# turned off since it's breaking OOB
HELP_MORE_ENABLED = False

# Notes systems
INSTALLED_APPS += [
    "db",
]
TEMPLATES[0]['OPTIONS']['context_processors'].append("web.custom_context.extra_context")

# Additional content and scripts
PROTOTYPE_MODULES += [ 'data.prototypes' ]

GLOBAL_SCRIPTS = {
    "phonebook": {
        "typeclass": "systems.electronics.software.phonebook.PhoneBookScript",
        "desc": "The central compendium of all phone numbers.",
        "interval": 3600
    }
}

DEFAULT_CHANNELS = [
    {
        "key": "Newbie",
        "desc": "OOC channel to introduce yourself and ask questions",
        "locks": "control:perm(Admin);listen:all();send:all()",
    }
]

##########################################
# aaaaaaaaaaaaaaaaaaa

EXTRA_LAUNCHER_COMMANDS.update({'gamewipe': 'utils.gamewipe.wipe_gameworld'})


######################################
#### forum
########################################

# lol
import django
from django.utils.encoding import smart_str
django.utils.encoding.smart_text = smart_str

INSTALLED_APPS += [
    "web.forum",
    "widget_tweaks",
    "django.contrib.humanize",
    "tinymce",
    "django_gravatar",
]

TINYMCE_JS_URL = "/static/tinymce/tinymce.min.js"
TINYMCE_COMPRESSOR = False
TINYMCE_DEFAULT_CONFIG = {
#	'selector': '#texteditor',
	'browser_spellcheck': True,
	'theme': 'modern',
	'skin': 'nexus',
	'menubar': False,
    'statusbar': False,
	'plugins': 'directionality paste textcolor',
	'toolbar': 'undo redo | fontsizeselect forecolor bold italic underline strikethrough subscript superscript removeformat | alignleft aligncenter alignright alignjustify blockquote',
    # 'content_css': '/static/tinymce/.css',
}

# tags which are allowed
BLEACH_ALLOWED_TAGS = ['span', 'p', 'a', 'abbr', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul']
BLEACH_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'span': ['style'],
}
# remove all tags from input
#BLEACH_STRIP_TAGS = True

# remove comments, or allow them in
BLEACH_STRIP_COMMENTS = True

##########################################
#   wiki
##########################################

INSTALLED_APPS += [
    # 'django_nyt.apps.DjangoNytConfig',
    'mptt',
    'sorl.thumbnail',
    'wiki.apps.WikiConfig',
    'wiki.plugins.attachments.apps.AttachmentsConfig',
    # 'wiki.plugins.notifications.apps.NotificationsConfig',
    # 'wiki.plugins.images.apps.ImagesConfig',
    # 'wiki.plugins.macros.apps.MacrosConfig',
]

WIKI_ACCOUNT_HANDLING = False
WIKI_ACCOUNT_SIGNUP_ALLOWED = False
WIKI_ANONYMOUS_WRITE = False
WIKI_USE_BOOTSTRAP_SELECT_WIDGET = False

WIKI_MARKDOWN_KWARGS = {
    'extensions': [
        'wikilinks',
    ]
}
from utils import wiki_helpers

# Create new users
WIKI_CAN_ADMIN = wiki_helpers.is_superuser

# Change the owner and group for an article
WIKI_CAN_ASSIGN = wiki_helpers.is_staff

# Change the GROUP of an article, despite the name
WIKI_CAN_ASSIGN_OWNER = wiki_helpers.is_staff

# Change read/write permissions on an article
WIKI_CAN_CHANGE_PERMISSIONS = wiki_helpers.is_staff

# Mark an article as deleted
WIKI_CAN_DELETE = wiki_helpers.is_builder

# Lock or permanently delete an article
WIKI_CAN_MODERATE = wiki_helpers.is_staff

# Create or edit any pages
# TODO: make this a different check
WIKI_CAN_WRITE = wiki_helpers.is_builder

# Read any pages
WIKI_CAN_READ = lambda x, y: True

######################################################################
# Default command sets and commands
######################################################################

# COMMAND_DEFAULT_CLASS = "core.commands.Command"

CMDSET_UNLOGGEDIN = "core.default_cmdsets.UnloggedinCmdSet"
CMDSET_SESSION = "core.default_cmdsets.SessionCmdSet"
CMDSET_CHARACTER = "core.default_cmdsets.CharacterCmdSet"
CMDSET_ACCOUNT = "core.default_cmdsets.AccountCmdSet"

CMDSET_PATHS = ["contrib", "evennia", "evennia.contrib"]
CMDSET_FALLBACKS = {
    CMDSET_CHARACTER: "evennia.commands.default.cmdset_character.CharacterCmdSet",
    CMDSET_ACCOUNT: "evennia.commands.default.cmdset_account.AccountCmdSet",
    CMDSET_SESSION: "evennia.commands.default.cmdset_session.SessionCmdSet",
    CMDSET_UNLOGGEDIN: "evennia.commands.default.cmdset_unloggedin.UnloggedinCmdSet",
}

COMMAND_PARSER = "core.cmdparser.cmdparser"
######################################################################
# Typeclasses and other paths
######################################################################

TYPECLASS_PATHS = [
    "evennia",
    "evennia.contrib",
    "evennia.contrib.tutorial_examples",
    "base_systems",
    "systems"
    ]

#SERVER_SESSION_CLASS = "core.sessions.classes.ServerSession"
#SERVER_SESSION_HANDLER_CLASS  = "core.sessions.handler.ServerSessionHandler"
BASE_ACCOUNT_TYPECLASS = "core.accounts.Account"
BASE_CHANNEL_TYPECLASS = "core.channels.Channel"
BASE_SCRIPT_TYPECLASS  = "core.scripts.Script"
BASE_OBJECT_TYPECLASS  = "base_systems.things.base.Thing"
BASE_CHARACTER_TYPECLASS = "base_systems.characters.base.Character"
BASE_ROOM_TYPECLASS    = "base_systems.rooms.base.Room"
BASE_EXIT_TYPECLASS    = "base_systems.exits.base.Exit"

PLAYER_CHARACTER_TYPECLASS = "base_systems.characters.players.PlayerCharacter"

WEBSOCKET_PROTOCOL_CLASS = "server.portal.websocket.WebSocketClient"
TELNET_PROTOCOL_CLASS = "server.portal.telnet.TelnetProtocol"
SSL_PROTOCOL_CLASS = "server.portal.telnet.SSLProtocol"

TRAIT_CLASS_PATHS = ["systems.skills.traits.DescTrait"]


######################################################################
# Connection Wizard settings and data
######################################################################

try:
    from .connection_settings import *
except ImportError:
    pass

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
