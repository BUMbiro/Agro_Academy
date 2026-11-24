import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_youtube_url(value):
    """
    Валидатор, который разрешает ссылки только на YouTube.
    Поддерживает домены: youtube.com, www.youtube.com, youtu.be, m.youtube.com
    """
    if not value:
        return value  # Пустые ссылки разрешены (blank=True)

    # Регулярное выражение для проверки домена
    youtube_regex = (
        r'(https?://)?'  # Опциональный протокол
        r'(www\.|m\.)?'  # Опциональный www или m
        r'(youtube\.com|youtu\.be)'  # Домены
        r'(/.*)?'  # Любой путь после домена
    )

    if not re.match(youtube_regex, value):
        raise ValidationError(
            _('Ссылка должна вести только на YouTube (youtube.com или youtu.be).'),
            code='invalid_youtube_url'
        )
    return value
