from django.db.models import Prefetch
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from users.permissions import IsModerator, IsNotModerator, IsOwner, IsOwnerOrModerator
from .models import Course, Lesson, Subscription
from .serializers import CourseSerializer, LessonSerializer
from .paginators import CustomPagination


class CourseViewSet(viewsets.ModelViewSet):
    """CRUD для курсов через ViewSet."""
    serializer_class = CourseSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """Оптимизация: подгружаем уроки, владельца и подписки текущего пользователя."""
        queryset = Course.objects.prefetch_related('lessons').select_related('owner')
        if self.request.user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    'subscriptions',
                    queryset=Subscription.objects.filter(user=self.request.user),
                    to_attr='user_subscriptions'
                )
            )
        return queryset.all()

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsNotModerator()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsNotModerator(), IsOwner()]
        if self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), IsOwnerOrModerator()]
        return [IsAuthenticatedOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        """
        Управление подпиской на курс.
        POST — подписаться (создаёт, если нет).
        DELETE — отписаться (удаляет, если есть).
        """
        course = self.get_object()

        if request.method == 'POST':
            subscription, created = Subscription.objects.get_or_create(
                user=request.user,
                course=course
            )
            if created:
                return Response(
                    {'message': 'Вы успешно подписались на обновления курса.'},
                    status=status.HTTP_201_CREATED
                )
            return Response(
                {'message': 'Вы уже подписаны на этот курс.'},
                status=status.HTTP_200_OK
            )

        elif request.method == 'DELETE':
            subscription = Subscription.objects.filter(user=request.user, course=course)
            if subscription.exists():
                subscription.delete()
                return Response(
                    {'message': 'Вы успешно отписались от обновлений курса.'},
                    status=status.HTTP_204_NO_CONTENT
                )
            return Response(
                {'message': 'Вы не были подписаны на этот курс.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class LessonListAPIView(generics.ListAPIView):
    """Список уроков."""
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination


class LessonRetrieveAPIView(generics.RetrieveAPIView):
    """Один урок."""
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class LessonCreateAPIView(generics.CreateAPIView):
    """Создание урока."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsNotModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LessonUpdateAPIView(generics.UpdateAPIView):
    """Редактирование урока."""
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


class LessonDestroyAPIView(generics.DestroyAPIView):
    """Удаление урока."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsNotModerator, IsOwner]
