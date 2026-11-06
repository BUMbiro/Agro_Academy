from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from materials.models import Course, Lesson
from materials.serializers import CourseSerializer

User = get_user_model()


class CourseAPITests(APITestCase):
    """Тесты для CourseViewSet."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Тестовый курс', description='Описание')

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
        """Аноним не может создать курс (403)."""
        url = reverse('course-list')
        data = {'title': 'Новый курс', 'description': 'Описание'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_course_authenticated(self):
        """Авторизованный может создать курс (201)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-list')
        data = {'title': 'Новый курс', 'description': 'Описание'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)

    def test_update_course_authenticated(self):
        """Авторизованный может обновить курс (200)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.patch(url, {'title': 'Обновлённый курс'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Обновлённый курс')

    def test_delete_course_authenticated(self):
        """Авторизованный может удалить курс (204)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())


class CourseSerializerTests(APITestCase):
    """Тесты для CourseSerializer: lessons_count и вложенные lessons (Задание 1 и 3)."""

    @classmethod
    def setUpTestData(cls):
        cls.course = Course.objects.create(title='Курс с уроками')
        cls.lesson1 = Lesson.objects.create(course=cls.course, title='Урок 1')
        cls.lesson2 = Lesson.objects.create(course=cls.course, title='Урок 2')

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
        empty_course = Course.objects.create(title='Пустой курс')
        data = CourseSerializer(empty_course).data
        self.assertEqual(data['lessons_count'], 0)
        self.assertEqual(data['lessons'], [])


class LessonAPITests(APITestCase):
    """Тесты для Generic-классов Lesson."""

    def setUp(self):
        self.user = User.objects.create_user(email='test@agro.ru', password='test12345')
        self.course = Course.objects.create(title='Курс', description='Описание')
        self.lesson = Lesson.objects.create(
            course=self.course,
            title='Урок 1',
            description='Описание урока',
            video_url='https://youtube.com/watch?v=123',
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
            'video_url': 'https://youtube.com/watch?v=456',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)

    def test_create_lesson_anonymous_forbidden(self):
        """Аноним не может создать урок (403)."""
        url = reverse('lesson-create')
        data = {'course': self.course.id, 'title': 'Урок 2'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_lesson_authenticated(self):
        """Авторизованный может обновить урок (200)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-update', args=[self.lesson.id])
        response = self.client.patch(url, {'title': 'Обновлённый урок'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Обновлённый урок')

    def test_delete_lesson_authenticated(self):
        """Авторизованный может удалить урок (204)."""
        self.client.force_authenticate(user=self.user)
        url = reverse('lesson-delete', args=[self.lesson.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(pk=self.lesson.pk).exists())
