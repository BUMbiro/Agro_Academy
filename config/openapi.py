"""
Общие элементы OpenAPI-схемы: служебные сериализаторы и типовые ответы с ошибками.

Использование:
    responses={200: CourseSerializer, **error_responses(401, 403, 404)}
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiResponse
from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    """Стандартная ошибка DRF."""
    detail = serializers.CharField(help_text='Текст ошибки.')


class MessageSerializer(serializers.Serializer):
    """Информационное сообщение для пользователя."""
    message = serializers.CharField(help_text='Текст сообщения.')


def _detail(name, text):
    return [OpenApiExample(name, value={'detail': text}, response_only=True)]


_ERROR_RESPONSES = {
    400: OpenApiResponse(
        OpenApiTypes.OBJECT,
        description='Ошибка валидации. Ключ — имя поля (или `non_field_errors`), значение — список ошибок.',
        examples=[OpenApiExample(
            'Ошибка валидации',
            value={'title': ['Обязательное поле.']},
            response_only=True,
        )],
    ),
    401: OpenApiResponse(
        ErrorDetailSerializer,
        description='JWT-токен не передан, недействителен или истёк.',
        examples=_detail('Нет токена', 'Учетные данные не были предоставлены.'),
    ),
    403: OpenApiResponse(
        ErrorDetailSerializer,
        description='Недостаточно прав (не владелец / модератор / не админ).',
        examples=_detail('Нет прав', 'У вас недостаточно прав для выполнения данного действия.'),
    ),
    404: OpenApiResponse(
        ErrorDetailSerializer,
        description='Объект не найден (или недоступен текущему пользователю).',
        examples=_detail('Не найдено', 'Не найдено.'),
    ),
    429: OpenApiResponse(
        ErrorDetailSerializer,
        description='Превышен лимит запросов. Повторите позже.',
        examples=_detail('Лимит', 'Запрос был проигнорирован.'),
    ),
    502: OpenApiResponse(
        ErrorDetailSerializer,
        description='Stripe отклонил запрос (некорректные параметры продукта / цены / сессии).',
        examples=_detail('Ошибка Stripe', 'Stripe отклонил запрос (создание цены): Invalid currency.'),
    ),
    503: OpenApiResponse(
        ErrorDetailSerializer,
        description='Платёжный сервис недоступен или не настроен (нет STRIPE_SECRET_KEY).',
        examples=_detail('Stripe недоступен', 'Платёжный сервис временно недоступен. Повторите попытку позже.'),
    ),
}


def error_responses(*codes):
    """Возвращает словарь типовых ответов с ошибками для указанных HTTP-кодов."""
    return {code: _ERROR_RESPONSES[code] for code in codes}
