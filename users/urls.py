from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views
from .serializers import CustomTokenObtainPairSerializer

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'payments', views.PaymentViewSet, basename='payment')


class CustomTokenObtainPairView(TokenObtainPairView):
    """Кастомный view для получения токенов (email вместо username)."""
    serializer_class = CustomTokenObtainPairSerializer


urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
