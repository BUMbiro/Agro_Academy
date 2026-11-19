from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Payment, User
from .serializers import PaymentSerializer, UserSerializer
from .permissions import IsProfileOwner


class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей."""
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action == 'destroy':
            return [IsAdminUser()]
        if self.action in ('update', 'partial_update'):
            # Редактировать может только владелец профиля (или админ)
            return [IsAuthenticated(), IsProfileOwner()]
        return [IsAuthenticatedOrReadOnly()]


class PaymentViewSet(viewsets.ModelViewSet):
    """CRUD для платежей с фильтрацией и сортировкой."""
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'course', 'lesson', 'payment_method']
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]
