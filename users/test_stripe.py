from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import stripe
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson
from users.models import Payment
from users.services import (
    StripeServiceError,
    create_stripe_price,
    create_stripe_product,
    create_stripe_session,
    resolve_payment_status,
    start_checkout,
    to_minor_units,
)

User = get_user_model()


@override_settings(STRIPE_SECRET_KEY='sk_test_dummy', STRIPE_CURRENCY='rub')
class StripeServicesTests(SimpleTestCase):
    """Юнит-тесты сервисного слоя: Stripe замокан, сети нет."""

    def setUp(self):
        patcher = patch('users.services.get_stripe_client')
        self.client_mock = MagicMock()
        patcher.start().return_value = self.client_mock
        self.addCleanup(patcher.stop)

    def test_to_minor_units_converts_rubles_to_kopecks(self):
        self.assertEqual(to_minor_units(Decimal('1500.00')), 150000)
        self.assertEqual(to_minor_units(Decimal('99.99')), 9999)
        self.assertEqual(to_minor_units('0.5'), 50)

    def test_create_product_skips_empty_description(self):
        self.client_mock.v1.products.create.return_value = SimpleNamespace(id='prod_1', name='Курс')
        result = create_stripe_product(name='Курс', description='   ', metadata={'course_id': '1'})
        self.assertEqual(result, {'id': 'prod_1', 'name': 'Курс'})
        self.client_mock.v1.products.create.assert_called_once_with(
            params={'name': 'Курс', 'metadata': {'course_id': '1'}},
        )

    def test_create_price_sends_kopecks_and_product_id(self):
        self.client_mock.v1.prices.create.return_value = SimpleNamespace(
            id='price_1', unit_amount=150000, currency='rub',
        )
        result = create_stripe_price(product_id='prod_1', amount=Decimal('1500.00'))
        self.assertEqual(result['id'], 'price_1')
        self.client_mock.v1.prices.create.assert_called_once_with(
            params={'product': 'prod_1', 'unit_amount': 150000, 'currency': 'rub'},
        )

    def test_create_session_uses_price_id_and_returns_link(self):
        self.client_mock.v1.checkout.sessions.create.return_value = SimpleNamespace(
            id='cs_test_1',
            url='https://checkout.stripe.com/c/pay/cs_test_1',
            status='open',
            payment_status='unpaid',
            expires_at=1893456000,
        )
        result = create_stripe_session(
            price_id='price_1',
            success_url='https://ok',
            cancel_url='https://cancel',
            client_reference_id=7,
        )
        params = self.client_mock.v1.checkout.sessions.create.call_args.kwargs['params']
        self.assertEqual(params['line_items'], [{'price': 'price_1', 'quantity': 1}])
        self.assertEqual(params['mode'], 'payment')
        self.assertEqual(params['client_reference_id'], '7')
        self.assertEqual(result['url'], 'https://checkout.stripe.com/c/pay/cs_test_1')
        self.assertIsNotNone(result['expires_at'])

    def test_invalid_request_error_is_wrapped(self):
        self.client_mock.v1.prices.create.side_effect = stripe.InvalidRequestError(
            'Invalid currency: xyz', param='currency',
        )
        with self.assertRaises(StripeServiceError) as ctx:
            create_stripe_price(product_id='prod_1', amount=100)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn('Invalid currency', ctx.exception.message)

    def test_connection_error_returns_503(self):
        self.client_mock.v1.products.create.side_effect = stripe.APIConnectionError('Network down')
        with self.assertRaises(StripeServiceError) as ctx:
            create_stripe_product(name='Курс')
        self.assertEqual(ctx.exception.status_code, 503)

    def test_resolve_payment_status(self):
        self.assertEqual(
            resolve_payment_status({'status': 'complete', 'payment_status': 'paid'}), 'paid',
        )
        self.assertEqual(
            resolve_payment_status({'status': 'expired', 'payment_status': 'unpaid'}), 'expired',
        )
        self.assertEqual(
            resolve_payment_status({'status': 'open', 'payment_status': 'unpaid'}), 'pending',
        )


class StripeMissingKeyTests(SimpleTestCase):
    """Без STRIPE_SECRET_KEY сервис не падает, а отдаёт понятную ошибку 503."""

    @override_settings(STRIPE_SECRET_KEY='')
    def test_missing_key_raises_503(self):
        with self.assertRaises(StripeServiceError) as ctx:
            create_stripe_product(name='Курс')
        self.assertEqual(ctx.exception.status_code, 503)


class StartCheckoutTests(SimpleTestCase):
    """Сквозной сценарий сервиса: продукт → цена → сессия."""

    def test_start_checkout_creates_product_price_and_session(self):
        course = SimpleNamespace(
            pk=1,
            title='Агрономия',
            description='Описание',
            price=Decimal('1500.00'),
            _meta=SimpleNamespace(model_name='course'),
        )
        user = SimpleNamespace(pk=7)

        with patch(
            'users.services.create_stripe_product',
            return_value={'id': 'prod_1', 'name': 'Курс'},
        ) as product_mock, patch(
            'users.services.create_stripe_price',
            return_value={'id': 'price_1'},
        ) as price_mock, patch(
            'users.services.create_stripe_session',
            return_value={'id': 'cs_1', 'url': 'https://pay.test', 'expires_at': None},
        ) as session_mock:
            result = start_checkout(user, course, 'https://ok', 'https://cancel')

        self.assertEqual(result, {
            'product_id': 'prod_1',
            'price_id': 'price_1',
            'session_id': 'cs_1',
            'url': 'https://pay.test',
            'expires_at': None,
        })
        self.assertIn('Курс «Агрономия»', product_mock.call_args.kwargs['name'])
        self.assertEqual(
            product_mock.call_args.kwargs['metadata'],
            {'user_id': '7', 'course_id': '1'},
        )
        price_mock.assert_called_once_with(product_id='prod_1', amount=Decimal('1500.00'))
        self.assertEqual(session_mock.call_args.kwargs['price_id'], 'price_1')


def _checkout_result(session_id='cs_test_123'):
    return {
        'product_id': 'prod_test',
        'price_id': 'price_test',
        'session_id': session_id,
        'url': f'https://checkout.stripe.com/c/pay/{session_id}',
        'expires_at': timezone.now() + timedelta(hours=23),
    }


@override_settings(STRIPE_SUCCESS_URL='', STRIPE_CANCEL_URL='', STRIPE_MIN_AMOUNT=Decimal('50'))
class PaymentCheckoutAPITests(APITestCase):
    """POST /api/payments/checkout/."""

    def setUp(self):
        self.author = User.objects.create_user(email='author@agro.ru', password='test12345')
        self.buyer = User.objects.create_user(email='buyer@agro.ru', password='test12345')
        self.course = Course.objects.create(
            title='Агрономия', owner=self.author, price=Decimal('1500.00'),
        )
        self.lesson = Lesson.objects.create(
            course=self.course, title='Почвы', owner=self.author, price=Decimal('300.00'),
        )
        self.url = reverse('payment-checkout')

    @patch('users.views.start_checkout')
    def test_checkout_course_creates_payment_with_stripe_ids(self, mock_checkout):
        mock_checkout.return_value = _checkout_result()
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(self.url, {'course': self.course.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['payment_link'], 'https://checkout.stripe.com/c/pay/cs_test_123',
        )
        payment = Payment.objects.get(pk=response.data['id'])
        self.assertEqual(payment.user, self.buyer)
        self.assertEqual(payment.course, self.course)
        self.assertEqual(payment.amount, Decimal('1500.00'))  # сумма с сервера
        self.assertEqual(payment.payment_method, Payment.PaymentMethod.STRIPE)
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.stripe_product_id, 'prod_test')
        self.assertEqual(payment.stripe_price_id, 'price_test')
        self.assertEqual(payment.stripe_session_id, 'cs_test_123')

        kwargs = mock_checkout.call_args.kwargs
        self.assertEqual(kwargs['product'], self.course)
        self.assertIn('{CHECKOUT_SESSION_ID}', kwargs['success_url'])
        self.assertTrue(kwargs['cancel_url'].endswith(reverse('payment-cancel')))

    @patch('users.views.start_checkout')
    def test_checkout_lesson(self, mock_checkout):
        mock_checkout.return_value = _checkout_result('cs_lesson')
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'lesson': self.lesson.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Payment.objects.get(pk=response.data['id']).amount, Decimal('300.00'),
        )

    def test_checkout_anonymous_unauthorized(self):
        response = self.client.post(self.url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_checkout_requires_exactly_one_target(self):
        self.client.force_authenticate(user=self.buyer)
        self.assertEqual(
            self.client.post(self.url, {}).status_code, status.HTTP_400_BAD_REQUEST,
        )
        response = self.client.post(
            self.url, {'course': self.course.id, 'lesson': self.lesson.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_free_course_rejected(self):
        free = Course.objects.create(title='Бесплатный', owner=self.author)
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'course': free.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)

    def test_checkout_below_min_amount_rejected(self):
        cheap = Course.objects.create(title='Дёшево', owner=self.author, price=Decimal('10.00'))
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'course': cheap.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_own_course_rejected(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(self.url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_checkout_already_paid_rejected(self):
        Payment.objects.create(
            user=self.buyer, course=self.course, amount='1500.00',
            payment_method=Payment.PaymentMethod.STRIPE, status=Payment.Status.PAID,
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('users.views.start_checkout')
    def test_checkout_reuses_active_link(self, mock_checkout):
        existing = Payment.objects.create(
            user=self.buyer, course=self.course, amount='1500.00',
            payment_method=Payment.PaymentMethod.STRIPE, status=Payment.Status.PENDING,
            stripe_session_id='cs_old',
            payment_link='https://checkout.stripe.com/c/pay/cs_old',
            link_expires_at=timezone.now() + timedelta(hours=5),
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], existing.id)
        mock_checkout.assert_not_called()

    @patch('users.views.start_checkout')
    def test_checkout_stripe_error_does_not_create_payment(self, mock_checkout):
        mock_checkout.side_effect = StripeServiceError(
            'Платёжный сервис временно недоступен.', status_code=503,
        )
        self.client.force_authenticate(user=self.buyer)
        response = self.client.post(self.url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('detail', response.data)
        self.assertFalse(Payment.objects.exists())


class PaymentStatusAPITests(APITestCase):
    """Проверка статуса: GET /payments/<id>/status/ и success_url."""

    PAID_SESSION = {
        'id': 'cs_test_1', 'url': None, 'status': 'complete', 'payment_status': 'paid',
        'amount_total': 150000, 'currency': 'rub', 'expires_at': None,
    }

    def setUp(self):
        self.author = User.objects.create_user(email='author2@agro.ru', password='test12345')
        self.buyer = User.objects.create_user(email='buyer2@agro.ru', password='test12345')
        self.stranger = User.objects.create_user(email='stranger@agro.ru', password='test12345')
        self.course = Course.objects.create(
            title='Курс', owner=self.author, price=Decimal('1500.00'),
        )
        self.payment = Payment.objects.create(
            user=self.buyer, course=self.course, amount='1500.00',
            payment_method=Payment.PaymentMethod.STRIPE, status=Payment.Status.PENDING,
            stripe_session_id='cs_test_1',
            payment_link='https://checkout.stripe.com/c/pay/cs_test_1',
            link_expires_at=timezone.now() + timedelta(hours=23),
        )

    @patch('users.services.retrieve_stripe_session')
    def test_status_syncs_paid(self, mock_retrieve):
        mock_retrieve.return_value = self.PAID_SESSION
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(reverse('payment-status', args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Payment.Status.PAID)
        self.assertIsNone(response.data['payment_link'])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        mock_retrieve.assert_called_once_with('cs_test_1')

    @patch('users.services.retrieve_stripe_session')
    def test_status_syncs_expired(self, mock_retrieve):
        mock_retrieve.return_value = {
            **self.PAID_SESSION, 'status': 'expired', 'payment_status': 'unpaid',
        }
        self.client.force_authenticate(user=self.buyer)
        self.client.get(reverse('payment-status', args=[self.payment.id]))
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.EXPIRED)

    def test_status_foreign_payment_not_found(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('payment-status', args=[self.payment.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_status_manual_payment_bad_request(self):
        manual = Payment.objects.create(user=self.buyer, course=self.course, amount='100.00')
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(reverse('payment-status', args=[manual.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('users.services.retrieve_stripe_session')
    def test_success_url_syncs_without_auth(self, mock_retrieve):
        mock_retrieve.return_value = self.PAID_SESSION
        response = self.client.get(reverse('payment-success'), {'session_id': 'cs_test_1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Payment.Status.PAID)

    def test_success_url_without_session_id(self):
        response = self.client.get(reverse('payment-success'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_success_url_unknown_session(self):
        response = self.client.get(reverse('payment-success'), {'session_id': 'cs_unknown'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_url(self):
        response = self.client.get(reverse('payment-cancel'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
