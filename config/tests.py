from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class ApiDocsTests(APITestCase):
    """Документация генерируется без ошибок и доступна по адресам."""

    def test_schema_contains_all_endpoints(self):
        response = self.client.get(reverse('schema'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        for path in (
            '/api/token/', '/api/users/', '/api/courses/', '/api/courses/{id}/subscribe/',
            '/api/lessons/', '/api/payments/', '/api/payments/checkout/', '/api/payments/{id}/status/',
        ):
            with self.subTest(path=path):
                self.assertIn(path, content)

    def test_swagger_ui_available(self):
        self.assertEqual(self.client.get(reverse('swagger-ui')).status_code, status.HTTP_200_OK)

    def test_redoc_available(self):
        self.assertEqual(self.client.get(reverse('redoc')).status_code, status.HTTP_200_OK)
