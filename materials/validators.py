from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Название не ALLOWED_HOSTS, чтобы не путать с настройкой Django
ALLOWED_YOUTUBE_HOSTS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'youtu.be',
}


def validate_youtube_url(value):
    """
    Разрешает ссылки только на YouTube.
    Хост сравнивается целиком с белым списком, поэтому адреса вида
    youtube.com.example.com или youtube.com@evil.com не проходят.
    """
    if not value:
        return value  # пустые ссылки разрешены (blank=True)

    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()

    if parsed.scheme not in ('http', 'https') or host not in ALLOWED_YOUTUBE_HOSTS:
        raise ValidationError(
            _('Ссылка должна вести только на youtube.com или youtu.be.'),
            code='invalid_youtube_url',
        )
    return value
