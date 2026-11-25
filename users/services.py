"""
Сервисный слой интеграции со Stripe.

Все обращения к Stripe собраны здесь. View не знает о SDK: функции возвращают
обычные словари (JSON-совместимые данные), а любые ошибки Stripe приводятся
к единому исключению StripeServiceError с HTTP-кодом для ответа.

Документация:
- Product:          https://docs.stripe.com/api/products/create
- Price:            https://docs.stripe.com/api/prices/create
- Checkout Session: https://docs.stripe.com/api/checkout/sessions/create
- Session Retrieve: https://docs.stripe.com/api/checkout/sessions/retrieve
"""
import logging
from datetime import datetime, timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings

from .models import Payment

logger = logging.getLogger(__name__)


class StripeServiceError(Exception):
    """Ошибка взаимодействия со Stripe, готовая к отдаче клиенту."""

    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_stripe_client():
    """Клиент Stripe (StripeClient — рекомендуемый способ начиная с SDK v8)."""
    if not settings.STRIPE_SECRET_KEY:
        raise StripeServiceError(
            'Онлайн-оплата не настроена: укажите STRIPE_SECRET_KEY в .env.',
            status_code=503,
        )
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def to_minor_units(amount):
    """Рубли → копейки (Stripe принимает сумму в минимальных единицах валюты).

    1500.00 → 150000, 99.99 → 9999. Decimal исключает ошибки float.
    """
    return int((Decimal(str(amount)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _from_timestamp(value):
    """Unix-время Stripe → aware datetime."""
    return datetime.fromtimestamp(value, tz=dt_timezone.utc) if value else None


def _request(operation, func, *args, **kwargs):
    """Вызов Stripe с переводом ошибок SDK в StripeServiceError."""
    try:
        return func(*args, **kwargs)
    except stripe.AuthenticationError as exc:
        logger.error('Stripe [%s]: неверный API-ключ: %s', operation, exc)
        raise StripeServiceError(
            'Платёжный сервис не принял API-ключ. Проверьте STRIPE_SECRET_KEY.', status_code=503,
        ) from exc
    except (stripe.APIConnectionError, stripe.RateLimitError) as exc:
        logger.warning('Stripe [%s]: сервис недоступен: %s', operation, exc)
        raise StripeServiceError(
            'Платёжный сервис временно недоступен. Повторите попытку позже.', status_code=503,
        ) from exc
    except stripe.InvalidRequestError as exc:
        logger.error('Stripe [%s]: некорректный запрос (param=%s): %s', operation, exc.param, exc)
        raise StripeServiceError(
            f'Stripe отклонил запрос ({operation}): {exc.user_message or exc}', status_code=502,
        ) from exc
    except stripe.StripeError as exc:
        logger.exception('Stripe [%s]: непредвиденная ошибка', operation)
        raise StripeServiceError(
            f'Ошибка платёжного сервиса ({operation}).', status_code=502,
        ) from exc


def create_stripe_product(name, description='', metadata=None):
    """Создаёт продукт в Stripe. Возвращает {'id', 'name'}."""
    params = {'name': name, 'metadata': metadata or {}}
    if description and description.strip():
        # Stripe не принимает пустую строку в description — передаём только если есть текст
        params['description'] = description.strip()

    product = _request('создание продукта', get_stripe_client().v1.products.create, params=params)
    return {'id': product.id, 'name': product.name}


def create_stripe_price(product_id, amount):
    """Создаёт цену для продукта. amount — в рублях, в Stripe уходит в копейках."""
    params = {
        'product': product_id,
        'unit_amount': to_minor_units(amount),
        'currency': settings.STRIPE_CURRENCY,
    }
    price = _request('создание цены', get_stripe_client().v1.prices.create, params=params)
    return {'id': price.id, 'unit_amount': price.unit_amount, 'currency': price.currency}


def create_stripe_session(price_id, success_url, cancel_url, client_reference_id=None, metadata=None):
    """Создаёт Checkout-сессию по ID цены. Возвращает ссылку на оплату и данные сессии."""
    params = {
        'mode': 'payment',  # разовая оплата (не подписка)
        'line_items': [{'price': price_id, 'quantity': 1}],
        'success_url': success_url,
        'cancel_url': cancel_url,
        'metadata': metadata or {},
    }
    if client_reference_id:
        params['client_reference_id'] = str(client_reference_id)

    session = _request('создание сессии', get_stripe_client().v1.checkout.sessions.create, params=params)
    return {
        'id': session.id,
        'url': session.url,
        'status': session.status,
        'payment_status': session.payment_status,
        'expires_at': _from_timestamp(session.expires_at),
    }


def retrieve_stripe_session(session_id):
    """Получает актуальные данные Checkout-сессии (статус оплаты)."""
    session = _request(
        'получение сессии', get_stripe_client().v1.checkout.sessions.retrieve, session_id,
    )
    return {
        'id': session.id,
        'url': session.url,
        'status': session.status,                  # open | complete | expired
        'payment_status': session.payment_status,  # paid | unpaid | no_payment_required
        'amount_total': session.amount_total,      # в копейках
        'currency': session.currency,
        'expires_at': _from_timestamp(session.expires_at),
    }


def start_checkout(user, product, success_url, cancel_url):
    """Полный сценарий: продукт → цена → сессия.

    product — экземпляр Course или Lesson (у обоих есть title, description, price).
    """
    kind = product._meta.model_name  # 'course' | 'lesson'
    if kind == 'lesson':
        name = f'Урок «{product.title}» (курс «{product.course.title}»)'
    else:
        name = f'Курс «{product.title}»'

    metadata = {'user_id': str(user.pk), f'{kind}_id': str(product.pk)}

    stripe_product = create_stripe_product(name=name, description=product.description, metadata=metadata)
    stripe_price = create_stripe_price(product_id=stripe_product['id'], amount=product.price)
    session = create_stripe_session(
        price_id=stripe_price['id'],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=user.pk,
        metadata=metadata,
    )
    return {
        'product_id': stripe_product['id'],
        'price_id': stripe_price['id'],
        'session_id': session['id'],
        'url': session['url'],
        'expires_at': session['expires_at'],
    }


def resolve_payment_status(session):
    """Статус сессии Stripe → статус платежа в нашей системе."""
    if session['payment_status'] in ('paid', 'no_payment_required'):
        return Payment.Status.PAID
    if session['status'] == 'expired':
        return Payment.Status.EXPIRED
    return Payment.Status.PENDING


def sync_payment_with_stripe(payment):
    """Запрашивает сессию в Stripe и синхронизирует статус платежа.

    Статус «Оплачен» финальный и не откатывается.
    """
    session = retrieve_stripe_session(payment.stripe_session_id)
    new_status = resolve_payment_status(session)
    if payment.status != Payment.Status.PAID and payment.status != new_status:
        payment.status = new_status
        payment.save(update_fields=['status'])
    return session
