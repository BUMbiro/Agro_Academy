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
    """PaymentViewSet: права, CRUD, фильтры, сортировка, валидация."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(
            email='test1@agroacademy.local',
            password='test12345',
        )
        cls.user2 = User.objects.create_user(
            email='test2@agroacademy.local',
            password='test12345',
        )
        cls.admin = User.objects.create_superuser(
            email='admin-test@agroacademy.local',
            password='test12345',
        )
        cls.course1 = Course.objects.create(title='Курс 1', owner=cls.user1)
        cls.course2 = Course.objects.create(title='Курс 2', owner=cls.user2)
        cls.lesson1 = Lesson.objects.create(course=cls.course1, title='Урок 1', owner=cls.user1)
        cls.lesson2 = Lesson.objects.create(course=cls.course2, title='Урок 2', owner=cls.user2)

        now = timezone.now()
        cls.payment1 = Payment.objects.create(
            user=cls.user1,
            course=cls.course1,
            amount='5000.00',
            payment_method=Payment.PaymentMethod.TRANSFER,
            status=Payment.Status.PAID,
        )
        cls.payment2 = Payment.objects.create(
            user=cls.user1,
            lesson=cls.lesson1,
            amount='1500.00',
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.Status.PAID,
        )
        cls.payment3 = Payment.objects.create(
            user=cls.user2,
            course=cls.course2,
            amount='3000.00',
            payment_method=Payment.PaymentMethod.TRANSFER,
            status=Payment.Status.PAID,
        )
        Payment.objects.filter(pk=cls.payment1.pk).update(payment_date=now - timedelta(days=2))
        Payment.objects.filter(pk=cls.payment2.pk).update(payment_date=now - timedelta(days=1))
        Payment.objects.filter(pk=cls.payment3.pk).update(payment_date=now)
        for payment in (cls.payment1, cls.payment2, cls.payment3):
            payment.refresh_from_db()

    def _payload(self, **extra):
        """Данные для ручного создания платежа (только админ)."""
        data = {
            'user': self.user1.id,
            'course': self.course1.id,
            'amount': '1000.00',
            'payment_method': 'cash',
        }
        data.update(extra)
        return data

    # --- Просмотр ---

    def test_list_payments_anonymous_unauthorized(self):
        """Аноним не видит список платежей (401)."""
        response = self.client.get(reverse('payment-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_payments_user_sees_only_own(self):
        """Пользователь видит только свои платежи."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('payment-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        ids = {p['id'] for p in response.data['results']}
        self.assertEqual(ids, {self.payment1.id, self.payment2.id})

    def test_list_payments_admin_sees_all(self):
        """Админ видит все платежи."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'))
        self.assertEqual(response.data['count'], 3)

    def test_retrieve_own_payment(self):
        """Детальная своего платежа (200)."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(reverse('payment-detail', args=[self.payment1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '5000.00')
        self.assertEqual(response.data['course_title'], 'Курс 1')

    def test_retrieve_foreign_payment_not_found(self):
        """Чужой платёж не виден (404, а не 403 — не раскрываем существование)."""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse('payment-detail', args=[self.payment1.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- Создание ---

    def test_create_payment_anonymous_forbidden(self):
        """Аноним не может создать платёж (401)."""
        response = self.client.post(reverse('payment-list'), self._payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_payment_authenticated_forbidden(self):
        """Обычный пользователь не может создать платёж (403)."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(reverse('payment-list'), self._payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_payment_admin_allowed_and_paid_by_default(self):
        """Админ создаёт ручной платёж, статус по умолчанию — paid."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('payment-list'), self._payload(amount='2500.00'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], Payment.Status.PAID)
        self.assertEqual(Payment.objects.count(), 4)

    def test_create_stripe_payment_manually_forbidden(self):
        """Способ оплаты stripe вручную задать нельзя — только через checkout."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('payment-list'), self._payload(payment_method='stripe'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payment_method', response.data)

    def test_create_payment_both_course_and_lesson_fails(self):
        """Нельзя указать и курс, и урок (400)."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('payment-list'), self._payload(lesson=self.lesson1.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_payment_neither_course_nor_lesson_fails(self):
        """Нельзя создать платёж без курса и без урока (400)."""
        self.client.force_authenticate(user=self.admin)
        data = {'user': self.user1.id, 'amount': '1000.00', 'payment_method': 'cash'}
        response = self.client.post(reverse('payment-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Изменение и удаление ---

    def test_update_payment_admin_allowed(self):
        """Админ обновляет платёж (200)."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse('payment-detail', args=[self.payment1.id]), {'amount': '5500.00'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment1.refresh_from_db()
        self.assertEqual(self.payment1.amount, 5500)

    def test_update_payment_authenticated_forbidden(self):
        """Обычный пользователь не может изменить платёж (403)."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.patch(reverse('payment-detail', args=[self.payment1.id]), {'amount': '5500.00'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_payment_admin_allowed(self):
        """Админ удаляет платёж (204)."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(reverse('payment-detail', args=[self.payment1.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Payment.objects.filter(pk=self.payment1.pk).exists())

    def test_delete_payment_authenticated_forbidden(self):
        """Обычный пользователь не может удалить платёж (403)."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(reverse('payment-detail', args=[self.payment1.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Payment.objects.filter(pk=self.payment1.pk).exists())

    # --- Фильтры и сортировка (от имени админа, чтобы видеть все платежи) ---

    def test_filter_by_course(self):
        """Фильтр ?course=<id>."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'course': self.course1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment1.id)

    def test_filter_by_lesson(self):
        """Фильтр ?lesson=<id>."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'lesson': self.lesson1.id})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment2.id)

    def test_filter_by_payment_method(self):
        """Фильтр ?payment_method=cash."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'payment_method': 'cash'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment2.id)

    def test_filter_by_user(self):
        """Фильтр ?user=<id>."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'user': self.user1.id})
        self.assertEqual(response.data['count'], 2)
        ids = {p['id'] for p in response.data['results']}
        self.assertEqual(ids, {self.payment1.id, self.payment2.id})

    def test_filter_by_status(self):
        """Фильтр ?status=paid."""
        Payment.objects.filter(pk=self.payment3.pk).update(status=Payment.Status.PENDING)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'status': Payment.Status.PAID})
        self.assertEqual(response.data['count'], 2)
        ids = {p['id'] for p in response.data['results']}
        self.assertEqual(ids, {self.payment1.id, self.payment2.id})

    def test_ordering_by_payment_date_asc(self):
        """Сортировка ?ordering=payment_date — по возрастанию."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'ordering': 'payment_date'})
        ids = [p['id'] for p in response.data['results']]
        self.assertEqual(ids, [self.payment1.id, self.payment2.id, self.payment3.id])

    def test_ordering_by_payment_date_desc(self):
        """Сортировка ?ordering=-payment_date — по убыванию."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('payment-list'), {'ordering': '-payment_date'})
        ids = [p['id'] for p in response.data['results']]
        self.assertEqual(ids, [self.payment3.id, self.payment2.id, self.payment1.id])


class UserViewSetTests(APITestCase):
    """Тесты для UserViewSet: CRUD, права, скрытие истории платежей."""

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

    def test_create_user_anonymous_allowed(self):
        """Аноним МОЖЕТ создать пользователя (регистрация) (201)."""
        url = reverse('user-list')
        data = {
            'email': 'new@agroacademy.local',
            'password': 'newpassword123',
            'phone': '+79990000000',
            'city': 'Астрахань',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new@agroacademy.local').exists())
        new_user = User.objects.get(email='new@agroacademy.local')
        self.assertTrue(new_user.check_password('newpassword123'))
        # Пароль не должен возвращаться в ответе
        self.assertNotIn('password', response.data)

    def test_create_user_with_existing_email_fails(self):
        """Повторная регистрация на тот же email — 400."""
        url = reverse('user-list')
        data = {'email': 'view1@agroacademy.local', 'password': 'newpassword123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_retrieve_user_with_payments(self):
        """Владелец видит свои payments и payments_count (200)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payments', response.data)
        self.assertIn('payments_count', response.data)
        self.assertEqual(response.data['email'], 'view1@agroacademy.local')

    def test_retrieve_foreign_user_hides_payments(self):
        """При просмотре чужого профиля payments скрыты (200)."""
        self.client.force_authenticate(user=self.user2)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('payments', response.data)
        self.assertNotIn('payments_count', response.data)

    def test_update_own_profile(self):
        """Владелец может обновить свой профиль (200)."""
        self.client.force_authenticate(user=self.user1)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.patch(url, {'city': 'Астрахань'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.city, 'Астрахань')

    def test_update_foreign_profile_forbidden(self):
        """Чужой профиль редактировать нельзя (403)."""
        self.client.force_authenticate(user=self.user2)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.patch(url, {'city': 'Взлом'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_user_anonymous_forbidden(self):
        """Аноним не может удалить пользователя (401)."""
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_destroy_user_authenticated_forbidden(self):
        """Обычный авторизованный не может удалить пользователя (403)."""
        self.client.force_authenticate(user=self.user2)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.filter(pk=self.user1.pk).exists())

    def test_destroy_user_admin_allowed(self):
        """Админ (is_staff) может удалить пользователя (204)."""
        admin = User.objects.create_superuser(
            email='admin-test@agroacademy.local',
            password='test12345',
        )
        self.client.force_authenticate(user=admin)
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.user1.pk).exists())


class UserPaymentsHistoryTests(APITestCase):
    """Тесты на историю платежей в UserSerializer."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email='history@agroacademy.local',
            password='test12345',
        )
        cls.course = Course.objects.create(title='Курс', owner=cls.user)
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
        """Владелец видит историю своих платежей."""
        self.client.force_authenticate(user=self.user)
        url = reverse('user-detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['payments_count'], 2)
        self.assertEqual(len(response.data['payments']), 2)
        amounts = {p['amount'] for p in response.data['payments']}
        self.assertEqual(amounts, {'1000.00', '2000.00'})

    def test_user_serializer_hides_payments_for_anonymous(self):
        """Аноним НЕ видит историю платежей."""
        url = reverse('user-detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('payments', response.data)
        self.assertNotIn('payments_count', response.data)

    def test_payments_have_status_field(self):
        """В истории платежей есть статус (нужен фронтенду и документации)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('user-detail', args=[self.user.id])
        response = self.client.get(url)
        for payment in response.data['payments']:
            self.assertIn('status', payment)
            self.assertIn('status_display', payment)
            self.assertIn('payment_method_display', payment)


class JWTAuthTests(APITestCase):
    """Тесты JWT: получение, обновление и использование токена."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='jwt@agroacademy.local', password='test12345')

    def _obtain(self, password='test12345'):
        return self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'jwt@agroacademy.local', 'password': password},
        )

    def test_obtain_token_pair(self):
        """По email и паролю выдаются access и refresh (200)."""
        response = self._obtain()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_obtain_token_wrong_password(self):
        """С неверным паролем токен не выдаётся (401)."""
        response = self._obtain(password='wrong-password')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        """По refresh выдаётся новый access (200)."""
        refresh = self._obtain().data['refresh']
        response = self.client.post(reverse('token_refresh'), {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_access_with_bearer_token(self):
        """С заголовком Bearer открывается защищённый эндпоинт (200)."""
        access = self._obtain().data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
