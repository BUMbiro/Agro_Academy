from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson, Subscription
from materials.serializers import CourseSerializer
from materials.validators import validate_youtube_url

User = get_user_model()


class CourseAPITests(APITestCase):
    """Базовые тесты CourseViewSet."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Тестовый курс', description='Описание', owner=self.user)

    def test_get_course_list_anonymous_unauthorized(self):
        """Аноним не может смотреть список курсов (401)."""
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_course_detail_anonymous_unauthorized(self):
        """Аноним не может смотреть детальную курса (401)."""
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_course_list_owner(self):
        """Владелец видит свои курсы в списке (200)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_get_course_detail_owner(self):
        """Владелец видит детальную своего курса (200)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Тестовый курс')

    def test_create_course_anonymous_forbidden(self):
        """Аноним не может создать курс (401)."""
        response = self.client.post(reverse('course-list'), {'title': 'Новый курс'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_course_authenticated(self):
        """Авторизованный может создать курс (201)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('course-list'), {'title': 'Новый курс', 'description': 'Описание'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(Course.objects.get(title='Новый курс').owner, self.user)

    def test_create_course_with_invalid_link(self):
        """Курс со ссылкой на сторонний ресурс (400)."""
        self.client.force_authenticate(user=self.user)
        data = {'title': 'Курс с левой ссылкой', 'video_url': 'https://www.vimeo.com/123456'}
        response = self.client.post(reverse('course-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_update_course_authenticated(self):
        """Владелец может обновить свой курс (200)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse('course-detail', args=[self.course.id]), {'title': 'Обновлённый курс'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Обновлённый курс')

    def test_delete_course_authenticated(self):
        """Владелец может удалить свой курс (204)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())


class CourseSerializerTests(APITestCase):
    """Тесты CourseSerializer: lessons_count, вложенные lessons, is_subscribed."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email='ser@agro.ru', password='test12345')
        cls.course = Course.objects.create(title='Курс с уроками', owner=cls.user)
        Lesson.objects.create(course=cls.course, title='Урок 1', owner=cls.user)
        Lesson.objects.create(course=cls.course, title='Урок 2', owner=cls.user)

    def test_lessons_count_field(self):
        self.assertEqual(CourseSerializer(self.course).data['lessons_count'], 2)

    def test_lessons_field_contains_nested_data(self):
        data = CourseSerializer(self.course).data
        self.assertEqual({lesson['title'] for lesson in data['lessons']}, {'Урок 1', 'Урок 2'})

    def test_course_without_lessons(self):
        empty_course = Course.objects.create(title='Пустой курс', owner=self.user)
        data = CourseSerializer(empty_course).data
        self.assertEqual(data['lessons_count'], 0)
        self.assertEqual(data['lessons'], [])

    def test_is_subscribed_false_without_request(self):
        """Без запроса в контексте (аноним) is_subscribed = False."""
        self.assertFalse(CourseSerializer(self.course).data['is_subscribed'])


class LessonAPITests(APITestCase):
    """Базовые тесты Generic-классов Lesson."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс', owner=self.user)
        self.lesson = Lesson.objects.create(
            course=self.course, title='Урок 1', owner=self.user,
            video_url='https://youtube.com/watch?v=test_video_id',
        )

    def test_get_lesson_list_anonymous_unauthorized(self):
        response = self.client.get(reverse('lesson-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_lesson_detail_anonymous_unauthorized(self):
        response = self.client.get(reverse('lesson-detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_lesson_list_owner(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('lesson-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_get_lesson_detail_owner(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('lesson-detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Урок 1')

    def test_create_lesson_authenticated(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'course': self.course.id,
            'title': 'Урок 2',
            'video_url': 'https://youtube.com/watch?v=another_test_id',
        }
        response = self.client.post(reverse('lesson-create'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.get(title='Урок 2').owner, self.user)

    def test_create_lesson_anonymous_forbidden(self):
        response = self.client.post(reverse('lesson-create'), {'course': self.course.id, 'title': 'Урок 2'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_lesson_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse('lesson-update', args=[self.lesson.id]), {'title': 'Обновлённый урок'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Обновлённый урок')

    def test_delete_lesson_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('lesson-delete', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())


class ModeratorAndOwnerPermissionsTests(APITestCase):
    """Права доступа: владелец, чужой пользователь, модератор."""

    def setUp(self):
        moderator_group, _ = Group.objects.get_or_create(name='Moderator')
        self.owner = User.objects.create_user(email='owner@agro.ru', password='test12345')
        self.other_user = User.objects.create_user(email='other@agro.ru', password='test12345')
        self.moderator = User.objects.create_user(email='moder@agro.ru', password='test12345')
        self.moderator.groups.add(moderator_group)
        self.course = Course.objects.create(title='Курс владельца', owner=self.owner)
        self.lesson = Lesson.objects.create(course=self.course, title='Урок владельца', owner=self.owner)

    # --- Модератор ---
    def test_moderator_can_update_any_course(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.patch(reverse('course-detail', args=[self.course.id]), {'title': 'Модератор'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_can_update_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.patch(reverse('lesson-update', args=[self.lesson.id]), {'title': 'Модератор'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_can_retrieve_any_course(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_can_retrieve_any_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(reverse('lesson-detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moderator_sees_all_courses_in_list(self):
        Course.objects.create(title='Курс другого', owner=self.other_user)
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.data['count'], 2)

    def test_moderator_sees_all_lessons_in_list(self):
        other_course = Course.objects.create(title='Курс другого', owner=self.other_user)
        Lesson.objects.create(course=other_course, title='Урок другого', owner=self.other_user)
        self.client.force_authenticate(user=self.moderator)
        response = self.client.get(reverse('lesson-list'))
        self.assertEqual(response.data['count'], 2)

    def test_moderator_cannot_create_course(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(reverse('course-list'), {'title': 'Новый курс'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_create_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.post(reverse('lesson-create'), {'course': self.course.id, 'title': 'Новый урок'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_course(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.delete(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_cannot_delete_lesson(self):
        self.client.force_authenticate(user=self.moderator)
        response = self.client.delete(reverse('lesson-delete', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Владелец ---
    def test_owner_can_update_own_course(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(reverse('course-detail', args=[self.course.id]), {'title': 'Свой курс'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_delete_own_lesson(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(reverse('lesson-delete', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_owner_sees_only_own_courses_in_list(self):
        Course.objects.create(title='Курс другого', owner=self.other_user)
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.course.id)

    # --- Чужой пользователь ---
    def test_other_user_cannot_retrieve_foreign_course(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_retrieve_foreign_lesson(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('lesson-detail', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_course_list_excludes_foreign(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('course-list'))
        self.assertEqual(response.data['count'], 0)

    def test_other_user_lesson_list_excludes_foreign(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse('lesson-list'))
        self.assertEqual(response.data['count'], 0)

    def test_other_user_cannot_update_foreign_course(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(reverse('course-detail', args=[self.course.id]), {'title': 'Взлом'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_delete_foreign_lesson(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(reverse('lesson-delete', args=[self.lesson.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_user_cannot_delete_foreign_course(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class YouTubeValidatorTests(APITestCase):
    """Валидация YouTube-ссылок через API."""

    def setUp(self):
        self.user = User.objects.create_user(email='validator@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс для валидации', owner=self.user)
        self.client.force_authenticate(user=self.user)

    def _create_lesson(self, video_url):
        data = {'course': self.course.id, 'title': 'Урок', 'video_url': video_url}
        return self.client.post(reverse('lesson-create'), data)

    def test_create_lesson_with_valid_youtube_link(self):
        response = self._create_lesson('https://www.youtube.com/watch?v=test_video_id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_with_youtu_be_short_link(self):
        response = self._create_lesson('https://youtu.be/test_video_id')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_lesson_with_invalid_link(self):
        response = self._create_lesson('https://www.vimeo.com/123456')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_create_lesson_with_fake_youtube_domain(self):
        """Домен, который начинается с youtube.com, но им не является (400)."""
        response = self._create_lesson('https://youtube.com.example.com/video')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_create_course_with_fake_youtube_domain(self):
        data = {'title': 'Курс', 'video_url': 'https://youtube.com.example.com/video'}
        response = self.client.post(reverse('course-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_update_lesson_with_invalid_link(self):
        lesson = Lesson.objects.create(
            course=self.course, title='Урок', owner=self.user,
            video_url='https://youtube.com/watch?v=test_video_id',
        )
        response = self.client.patch(reverse('lesson-update', args=[lesson.id]),
                                     {'video_url': 'https://rutube.ru/video/123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)


class YouTubeValidatorUnitTests(SimpleTestCase):
    """Юнит-тесты самой функции validate_youtube_url (без БД)."""

    def test_valid_urls(self):
        for url in [
            'https://youtube.com/watch?v=1',
            'https://www.youtube.com/watch?v=1',
            'http://m.youtube.com/watch?v=1',
            'https://youtu.be/abc',
            'https://WWW.YouTube.com/watch?v=1',
        ]:
            with self.subTest(url=url):
                self.assertEqual(validate_youtube_url(url), url)

    def test_invalid_urls(self):
        for url in [
            'https://youtube.com.example.com/video',
            'https://notyoutube.com/watch?v=1',
            'https://evil.com/youtube.com',
            'https://youtube.com@evil.com/video',
            'ftp://youtube.com/video',
        ]:
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    validate_youtube_url(url)

    def test_empty_value_allowed(self):
        self.assertEqual(validate_youtube_url(''), '')


class SubscriptionTests(APITestCase):
    """Подписка на обновления курса."""

    def setUp(self):
        self.owner = User.objects.create_user(email='owner_sub@agro.ru', password='test12345')
        self.student = User.objects.create_user(email='student_sub@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс для подписки', owner=self.owner)
        self.url = reverse('course-subscribe', args=[self.course.id])

    def test_subscribe_to_course(self):
        """Можно подписаться и на чужой курс (201)."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscription.objects.filter(user=self.student, course=self.course).exists())

    def test_subscribe_anonymous_unauthorized(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_subscribe_twice_returns_200(self):
        Subscription.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Subscription.objects.filter(user=self.student, course=self.course).count(), 1)

    def test_unsubscribe_from_course(self):
        Subscription.objects.create(user=self.student, course=self.course)
        self.client.force_authenticate(user=self.student)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subscription.objects.filter(user=self.student, course=self.course).exists())

    def test_unsubscribe_when_not_subscribed_returns_400(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_is_subscribed_true_in_detail(self):
        Subscription.objects.create(user=self.owner, course=self.course)
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_subscribed'])

    def test_is_subscribed_false_in_detail(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('course-detail', args=[self.course.id]))
        self.assertFalse(response.data['is_subscribed'])

    def test_is_subscribed_true_in_list(self):
        """В списке is_subscribed берётся из Prefetch (user_subscriptions)."""
        Subscription.objects.create(user=self.owner, course=self.course)
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('course-list'))
        self.assertTrue(response.data['results'][0]['is_subscribed'])


class LessonValidationTests(APITestCase):
    """Нельзя создать урок в чужом курсе."""

    def setUp(self):
        self.user = User.objects.create_user(email='creator@agro.ru', password='test12345')
        self.other_user = User.objects.create_user(email='other_creator@agro.ru', password='test12345')
        self.foreign_course = Course.objects.create(title='Чужой курс', owner=self.other_user)

    def test_create_lesson_in_foreign_course(self):
        self.client.force_authenticate(user=self.user)
        data = {'course': self.foreign_course.id, 'title': 'Незаконный урок'}
        response = self.client.post(reverse('lesson-create'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)
