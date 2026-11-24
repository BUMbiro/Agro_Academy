from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson, Subscription
from materials.serializers import CourseSerializer

User = get_user_model()


class CourseAPITests(APITestCase):
    """Тесты для CourseViewSet (базовые)."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(
            title='Тестовый курс',
            description='Описание',
            owner=self.user
        )

    def test_get_course_list_anonymous(self):
        """Аноним может смотреть список курсов (200)."""
        url = reverse('course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_get_course_detail_anonymous(self):
        """Аноним может смотреть детальную курса (200)."""
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Тестовый курс')

    def test_create_course_anonymous_forbidden(self):
        """Аноним не может создать курс (401)."""
        url = reverse('course-list')
        data = {'title': 'Новый курс', 'description': 'Описание'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_course_authenticated(self):
        """Авторизованный может создать курс (201)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-list')
        data = {'title': 'Новый курс', 'description': 'Описание'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)
        new_course = Course.objects.get(title='Новый курс')
        self.assertEqual(new_course.owner, self.user)

    def test_create_course_with_invalid_link(self):
        """Создание курса со ссылкой на сторонний ресурс (400)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-list')
        data = {
            'title': 'Курс с левой ссылкой',
            'video_url': 'https://www.vimeo.com/123456'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_update_course_authenticated(self):
        """Владелец может обновить свой курс (200)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.patch(url, {'title': 'Обновлённый курс'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Обновлённый курс')

    def test_delete_course_authenticated(self):
        """Владелец может удалить свой курс (204)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())


class CourseSerializerTests(APITestCase):
    """Тесты для CourseSerializer: lessons_count и вложенные lessons."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='ser@agro.ru', password='test12345')
        cls.course = Course.objects.create(title='Курс с уроками', owner=cls.user)
        cls.lesson1 = Lesson.objects.create(course=cls.course, title='Урок 1', owner=cls.user)
        cls.lesson2 = Lesson.objects.create(course=cls.course, title='Урок 2', owner=cls.user)

    def test_lessons_count_field(self):
        """SerializerMethodField lessons_count возвращает корректное число."""
        data = CourseSerializer(self.course).data
        self.assertEqual(data['lessons_count'], 2)

    def test_lessons_field_contains_nested_data(self):
        """Вложенный LessonSerializer отдаёт список уроков курса."""
        data = CourseSerializer(self.course).data
        self.assertEqual(len(data['lessons']), 2)
        titles = {lesson['title'] for lesson in data['lessons']}
        self.assertEqual(titles, {'Урок 1', 'Урок 2'})

    def test_course_without_lessons(self):
        """Курс без уроков: lessons_count=0, lessons=[]."""
        empty_course = Course.objects.create(title='Пустой курс', owner=self.user)
        data = CourseSerializer(empty_course).data
        self.assertEqual(data['lessons_count'], 0)
        self.assertEqual(data['lessons'], [])


class LessonAPITests(APITestCase):
    """Тесты для Generic-классов Lesson (базовые)."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс', description='Описание', owner=self.user)
        self.lesson = Lesson.objects.create(
            course=self.course,
            title='Урок 1',
            description='Описание урока',
            video_url='https://youtube.com/watch?v=test_video_id',
            owner=self.user
        )

    def test_get_lesson_list_anonymous(self):
        """Аноним может смотреть список уроков (200)."""
        url = reverse('lesson-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_lesson_detail_anonymous(self):
        """Аноним может смотреть детальную урока (200)."""
        url = reverse('lesson-detail', args=[self.lesson.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Урок 1')

    def test_create_lesson_authenticated(self):
        """Авторизованный может создать урок (201)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-create')
        data = {
            'course': self.course.id,
            'title': 'Урок 2',
            'description': 'Описание',
            'video_url': 'https://youtube.com/watch?v=another_test_id',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)
        new_lesson = Lesson.objects.get(title='Урок 2')
        self.assertEqual(new_lesson.owner, self.user)

    def test_create_lesson_anonymous_forbidden(self):
        """Аноним не может создать урок (401)."""
        url = reverse('lesson-create')
        data = {'course': self.course.id, 'title': 'Урок 2'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_lesson_authenticated(self):
        """Владелец может обновить свой урок (200)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-update', args=[self.lesson.id])
        response = self.client.patch(url, {'title': 'Обновлённый урок'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Обновлённый урок')

    def test_delete_lesson_authenticated(self):
        """Владелец может удалить свой урок (204)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-delete', args=[self.lesson.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())


class ModeratorAndOwnerPermissionsTests(APITestCase):
    """Тесты прав доступа для модераторов и владельцев."""

    def setUp(self):
        self.moderator_group, _ = Group.objects.get_or_create(name='Moderator')
        self.owner = User.objects.create_user(email='owner@agro.ru', password='test12345')
        self.other_user = User.objects.create_user(email='other@agro.ru', password='test12345')
        self.moderator = User.objects.create_user(email='moder@agro.ru', password='test12345')
        self.moderator.groups.add(self.moderator_group)
        self.course = Course.objects.create(title='Курс владельца', owner=self.owner)
        self.lesson = Lesson.objects.create(course=self.course, title='Урок владельца', owner=self.owner)

    def test_moderator_can_update_any_course(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.patch(url, {'title': 'Курс отредактирован модератором'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_can_update_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('lesson-update', args=[self.lesson.id])
        response = self.client.patch(url, {'title': 'Урок отредактирован модератором'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_cannot_create_course(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('course-list')
        data = {'title': 'Новый курс'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_create_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('lesson-create')
        data = {'course': self.course.id, 'title': 'Новый урок'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_course(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        url = reverse('lesson-delete', args=[self.lesson.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_own_course(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.patch(url, {'title': 'Свой курс'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_delete_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse('lesson-delete', args=[self.lesson.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_other_user_cannot_update_foreign_course(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.patch(url, {'title': 'Попытка взлома'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_delete_foreign_lesson(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse('lesson-delete', args=[self.lesson.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_delete_foreign_course(self):
        """Другой пользователь не может удалить чужой курс (403)."""
        self.client.force_authenticate(user=self.other_user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class YouTubeValidatorTests(APITestCase):
    """Тесты валидации ссылок на YouTube."""

    def setUp(self):
        self.user = User.objects.create_user(email='validator@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс для валидации', owner=self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_lesson_with_valid_youtube_link(self):
        """Создание урока с корректной ссылкой на YouTube (201)."""
        url = reverse('lesson-create')
        data = {
            'course': self.course.id,
            'title': 'Урок с YouTube',
            'video_url': 'https://www.youtube.com/watch?v=test_video_id'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_with_youtu_be_short_link(self):
        """Создание урока с короткой ссылкой youtu.be (201)."""
        url = reverse('lesson-create')
        data = {
            'course': self.course.id,
            'title': 'Урок с короткой ссылкой',
            'video_url': 'https://youtu.be/test_video_id'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_with_invalid_link(self):
        """Создание урока со ссылкой на сторонний ресурс (400)."""
        url = reverse('lesson-create')
        data = {
            'course': self.course.id,
            'title': 'Урок с левой ссылкой',
            'video_url': 'https://www.vimeo.com/123456'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_update_lesson_with_invalid_link(self):
        """Обновление урока со ссылкой на сторонний ресурс (400)."""
        lesson = Lesson.objects.create(
            course=self.course, title='Урок', owner=self.user,
            video_url='https://youtube.com/watch?v=test_video_id'
        )
        url = reverse('lesson-update', args=[lesson.id])
        response = self.client.patch(url, {'video_url': 'https://rutube.ru/video/123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)


class SubscriptionTests(APITestCase):
    """Тесты функционала подписки на обновления курса."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner_sub@agro.ru', password='test12345')
        self.student = User.objects.create_user(email='student_sub@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс для подписки', owner=self.owner)

    def test_subscribe_to_course(self):
        """Пользователь может подписаться на курс (201)."""
        self.client.force_authenticate(user=self.student)
        url = reverse('course-subscribe', args=[self.course.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscription.objects.filter(user=self.student, course=self.course).exists())

    def test_subscribe_twice_returns_200(self):
        """Повторная подписка не создаёт дубль (200)."""
        Subscription.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)
        url = reverse('course-subscribe', args=[self.course.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Subscription.objects.filter(user=self.student, course=self.course).count(), 1)

    def test_unsubscribe_from_course(self):
        """Пользователь может отписаться от курса (204)."""
        Subscription.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)
        url = reverse('course-subscribe', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subscription.objects.filter(user=self.student, course=self.course).exists())

    def test_unsubscribe_when_not_subscribed_returns_400(self):
        """Попытка отписаться без подписки возвращает 400."""
        self.client.force_authenticate(user=self.student)
        url = reverse('course-subscribe', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_is_subscribed_field_true(self):
        """В детальной курса поле is_subscribed=True для подписанного пользователя."""
        Subscription.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_subscribed'])

    def test_is_subscribed_field_false(self):
        """В детальной курса поле is_subscribed=False для неподписанного пользователя."""
        self.client.force_authenticate(user=self.student)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_subscribed'])

    def test_is_subscribed_field_false_for_anonymous(self):
        """Для анонима is_subscribed всегда False."""
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_subscribed'])


class LessonValidationTests(APITestCase):
    """Тесты валидации создания урока в чужом курсе."""

    def setUp(self):
        self.user = User.objects.create_user(email='creator@agro.ru', password='test12345')
        self.other_user = User.objects.create_user(email='other_creator@agro.ru', password='test12345')
        self.foreign_course = Course.objects.create(title='Чужой курс', owner=self.other_user)

    def test_create_lesson_in_foreign_course(self):
        """Пользователь не может добавить урок в чужой курс (400)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-create')
        data = {
            'course': self.foreign_course.id,
            'title': 'Незаконный урок',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)
