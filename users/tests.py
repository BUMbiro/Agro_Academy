from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson
from users.models import Payment

User = get_user_model()


class PaymentAPITests(APITestCase):
    """Тесты для PaymentViewSet: CRUD, фильтры, сортировка, права."""

    @classmethod
    def setUpTestData(cls):
        # Пользователи
        cls.user1 = User.objects.create_user(
            email='test1@agroacademy.local',
            password='test12345',
        )
        cls.user2 = User.objects.create_user(
            email='test2@agroacademy.local',
            password='test12345',
        )

        # Курсы и уроки
        cls.course1 = Course.objects.create(title='Курс 1')
        cls.course2 = Course.objects.create(title='Курс 2')
        cls.lesson1 = Lesson.objects.create(course=cls.course1, title='Урок 1')
        cls.lesson2 = Lesson.objects.create(course=cls.course2, title='Урок 2')

        # Платежи с разными датами, способами, курсами/уроками
        # ВАЖНО: payment_date — auto_now_add, поэтому задаём даты через update()
        now = timezone.now()
        cls.payment1 = Payment.objects.create(
            user=cls.user1,
            course=cls.course1,
            amount='5000.00',
            payment_method=Payment.PaymentMethod.TRANSFER,
        )
        cls.payment2 = Payment.objects.create(
            user=cls.user1,
            lesson=cls.lesson1,
            amount='1500.00',
            payment_method=Payment.PaymentMethod.CASH,
        )
        cls.payment3 = Payment.objects.create(
            user=cls.user2,
            course=cls.course2,
            amount='3000.00',
            payment_method=Payment.PaymentMethod.TRANSFER,
        )

        # Явно задаём даты: payment1 — самый старый, payment3 — самый новый
        Payment.objects.filter(pk=cls.payment1.pk).update(payment_date=now - timedelta(days=2))
        Payment.objects.filter(pk=cls.payment2.pk).update(payment_date=now - timedelta(days=1))
        Payment.objects.filter(pk=cls.payment3.pk).update(payment_date=now)

        # Обновляем объекты в памяти, чтобы тесты видели актуальные даты
        cls.payment1.refresh_from_db()
        cls.payment2.refresh_from_db()
        cls.payment3.refresh_from_db()

    # ------------------------------------------------------------
    # Права доступа
    # ------------------------------------------------------------

    def test_list_payments_anonymous(self):
        """Аноним может смотреть список платежей (200)."""
        url = reverse('payment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_create_payment_anonymous_forbidden(self):
        """Аноним не может создать платёж (403)."""
        url = reverse('payment-list')
        data = {
            'user': self.user1.id,
            'course': self.course1.id,
            'amount': '1000.00',
            'payment_method': 'cash',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def test_create_payment_authenticated(self):
        """Авторизованный может создать платёж (201)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('payment-list')
        data = {
            'user': self.user1.id,
            'course': self.course1.id,
            'amount': '2500.00',
            'payment_method': 'transfer',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 4)

    def test_retrieve_payment(self):
        """Детальная платежа (200)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('payment-detail', args=[self.payment1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '5000.00')

    def test_update_payment_authenticated(self):
        """Авторизованный может обновить платёж (200)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('payment-detail', args=[self.payment1.id])
        response = self.client.patch(url, {'amount': '5500.00'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment1.refresh_from_db()
        self.assertEqual(self.payment1.amount, 5500)

    def test_delete_payment_authenticated(self):
        """Авторизованный может удалить платёж (204)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('payment-detail', args=[self.payment1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Payment.objects.filter(pk=self.payment1.pk).exists())

    # ------------------------------------------------------------
    # Фильтры
    # ------------------------------------------------------------

    def test_filter_by_course(self):
        """Фильтр ?course=<id> возвращает только платежи по этому курсу."""
        url = reverse('payment-list')
        response = self.client.get(url, {'course': self.course1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment1.id)

    def test_filter_by_lesson(self):
        """Фильтр ?lesson=<id> возвращает только платежи по этому уроку."""
        url = reverse('payment-list')
        response = self.client.get(url, {'lesson': self.lesson1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment2.id)

    def test_filter_by_payment_method(self):
        """Фильтр ?payment_method=cash возвращает только наличные."""
        url = reverse('payment-list')
        response = self.client.get(url, {'payment_method': 'cash'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment2.id)

    # ------------------------------------------------------------
    # Сортировка
    # ------------------------------------------------------------

    def test_ordering_by_payment_date_asc(self):
        """Сортировка ?ordering=payment_date — от старых к новым."""
        url = reverse('payment-list')
        response = self.client.get(url, {'ordering': 'payment_date'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertEqual(ids, [self.payment1.id, self.payment2.id, self.payment3.id])

    def test_ordering_by_payment_date_desc(self):
        """Сортировка ?ordering=-payment_date — от новых к старым."""
        url = reverse('payment-list')
        response = self.client.get(url, {'ordering': '-payment_date'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [p['id'] for p in response.data['results']]
        self.assertEqual(ids, [self.payment3.id, self.payment2.id, self.payment1.id])


class UserViewSetTests(APITestCase):
    """Тесты для UserViewSet: CRUD пользователей."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email='view1@agroacademy.local',
            password='test12345',
        )
        cls.user2 = User.objects.create_user(
            email='view2@agroacademy.local',
            password='test12345',
        )

    def test_list_users_anonymous(self):
        """Аноним может смотреть список пользователей (200)."""
        url = reverse('user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_create_user_anonymous_forbidden(self):
        """Аноним не может создать пользователя (403)."""
        url = reverse('user-list')
        data = {
            'email': 'new@agroacademy.local',
            'phone': '+79990000000',
            'city': 'Астрахань',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user_with_payments(self):
        """Детальная пользователя содержит payments и payments_count."""
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payments', response.data)
        self.assertIn('payments_count', response.data)
        self.assertEqual(response.data['email'], 'view1@agroacademy.local')


class UserPaymentsHistoryTests(APITestCase):
    """Тесты на историю платежей в UserSerializer (доп. задание *)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='history@agroacademy.local',
            password='test12345',
        )
        cls.course = Course.objects.create(title='Курс')
        Payment.objects.create(
            user=cls.user,
            course=cls.course,
            amount='1000.00',
            payment_method=Payment.PaymentMethod.CASH,
        )
        Payment.objects.create(
            user=cls.user,
            course=cls.course,
            amount='2000.00',
            payment_method=Payment.PaymentMethod.TRANSFER,
        )

    def test_user_serializer_contains_payments(self):
        """UserSerializer отдаёт историю платежей и их количество."""
        url = reverse('user-detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['payments_count'], 2)
        self.assertEqual(len(response.data['payments']), 2)
        amounts = {p['amount'] for p in response.data['payments']}
        self.assertEqual(amounts, {'1000.00', '2000.00'})
