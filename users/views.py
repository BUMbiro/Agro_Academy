from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly

from .models import Payment, User
from .serializers import PaymentSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей (включая редактирование профиля).

    Удаление — только для админа (is_staff).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """Удаление — только админ. Остальное — по глобальным правилам."""
        if self.action == 'destroy':
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]


class PaymentViewSet(viewsets.ModelViewSet):
    """CRUD для платежей с фильтрацией и сортировкой.

    Чтение — всем. Создание/изменение/удаление — только админ (is_staff).

    Фильтры:
    - ?user=<id>            — платежи пользователя
    - ?course=<id>          — платежи по курсу
    - ?lesson=<id>          — платежи по уроку
    - ?payment_method=cash  — по способу оплаты

    Сортировка:
    - ?ordering=payment_date   — по возрастанию
    - ?ordering=-payment_date  — по убыванию
    """
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'course', 'lesson', 'payment_method']
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']

    def get_permissions(self):
        """Создание/изменение/удаление — только админ. Чтение — всем."""
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
