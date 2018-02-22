from django.core.cache import cache

THEME_CACHE_KEY_PREFIX = "django_themes__"


def theme_cache_key(user, mode):
    user_key = user
    if hasattr(user, 'pk'):
        user_key = user.pk
    return "-".join(map(str,[THEME_CACHE_KEY_PREFIX, mode, user_key]))


def add_theme_to_preview(user, theme):
    key = theme_cache_key(user, "previewing")
    themes_pks = get_previewing_themes(user)
    themes_pks = list(set(themes_pks + theme.pk))
    cache.set(key,themes_pks, 500)


def get_previewing_themes(user):
    key = theme_cache_key(user, "previewing")
    return list(cache.get(key) or [])


def set_themes_to_preview(user, themes):
    key = theme_cache_key(user, "previewing")
    themes_pks = [
        # If its a theme object get the PK, if its already a number, return that
        # This will fail spectacularly if a dev gives bad input
        getattr(theme, "pk", None) or int(theme)
        for theme in themes
    ]
    cache.set(key,themes_pks, 500)

def delete_preview_cache(user):
    key = theme_cache_key(user, "previewing")
    cache.delete(key)

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return (str(num), unit+suffix)
        num /= 1024.0
    return  (str(num), 'Yi'+suffix)
