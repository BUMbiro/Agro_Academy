from rest_framework import viewsets

from .models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей (включая редактирование профиля)."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
