from django.db.models import Prefetch
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from users.permissions import IsNotModerator, IsOwner, IsOwnerOrModerator, is_moderator
from .models import Course, Lesson, Subscription
from .serializers import CourseSerializer, LessonSerializer
from .paginators import CustomPagination


class CourseViewSet(viewsets.ModelViewSet):
    """CRUD для курсов через ViewSet."""
    serializer_class = CourseSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Оптимизация: подгружаем уроки, владельца и подписки текущего пользователя.

        Доступ:
        - list: модератор видит все курсы, остальные только свои;
        - retrieve/update/destroy: queryset не фильтруется, доступ проверяют
          object-permissions (чужой курс отдаёт 403, а не 404);
        - subscribe: на чужой курс подписаться можно, поэтому тоже без фильтра.
        """
        user = self.request.user
        queryset = Course.objects.select_related('owner').prefetch_related('lessons')

        if not user.is_authenticated:
            return queryset.none()

        queryset = queryset.prefetch_related(
            Prefetch(
                'subscriptions',
                queryset=Subscription.objects.filter(user=user),
                to_attr='user_subscriptions',
            )
        )

        if self.action == 'list' and not is_moderator(user):
            queryset = queryset.filter(owner=user)

        return queryset

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsNotModerator()]
        if self.action in ('retrieve', 'update', 'partial_update'):
            return [IsAuthenticated(), IsOwnerOrModerator()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsNotModerator(), IsOwner()]
        # list и subscribe: любой авторизованный
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """
        Управление подпиской на курс.
        POST: подписаться (создаёт, если подписки нет).
        DELETE: отписаться (удаляет, если подписка есть).
        """
        course = self.get_object()

        if request.method == 'POST':
            _, created = Subscription.objects.get_or_create(user=request.user, course=course)
            if created:
                return Response(
                    {'message': 'Вы успешно подписались на обновления курса.'},
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {'message': 'Вы уже подписаны на этот курс.'},
                status=status.HTTP_200_OK,
            )

        deleted, _ = Subscription.objects.filter(user=request.user, course=course).delete()
        if deleted:
            return Response(
                {'message': 'Вы успешно отписались от обновлений курса.'},
                status=status.HTTP_204_NO_CONTENT,
            )
        return Response(
            {'message': 'Вы не были подписаны на этот курс.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LessonListAPIView(generics.ListAPIView):
    """Список уроков: модератор видит все, остальные только свои."""
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Lesson.objects.select_related('course', 'owner')
        if not user.is_authenticated:
            return queryset.none()
        if is_moderator(user):
            return queryset.all()
        return queryset.filter(owner=user)


class LessonRetrieveAPIView(generics.RetrieveAPIView):
    """Один урок: только владелец или модератор."""
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


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
