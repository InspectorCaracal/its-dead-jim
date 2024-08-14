# Custom methods to link wiki permissions to game perms
def is_superuser(article, user):
    """Return True if user is a superuser, False otherwise."""
    return not user.is_anonymous and user.is_superuser

def is_staff(article, user):
    """Return True if user is admin or higher, else False"""
    return not user.is_anonymous and user.permissions.check("Admin")

def is_builder(article, user):
    """Return True if user is a builder, False otherwise."""
    return not user.is_anonymous and user.permissions.check("Builder")

def is_player(article, user):
    """Return True if user is a player, False otherwise."""
    return not user.is_anonymous and user.permissions.check("Player")






