from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticatedOrReadOnly

from .models import Payment, User
from .serializers import PaymentSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей (включая редактирование профиля).

    Удаление — только для админа (is_staff). Создание/редактирование —
    для любого авторизованного (по заданию — редактирование профиля).
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

    Фильтры (через query-параметры):
    - ?user=<id>            — платежи пользователя
    - ?course=<id>          — платежи по курсу
    - ?lesson=<id>          — платежи по уроку
    - ?payment_method=cash  — по способу оплаты (cash / transfer)

    Сортировка:
    - ?ordering=payment_date   — по возрастанию даты
    - ?ordering=-payment_date  — по убыванию даты
    """
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'course', 'lesson', 'payment_method']
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']  # по умолчанию — свежие сверху
