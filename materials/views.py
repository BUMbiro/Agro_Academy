from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from users.permissions import IsModerator, IsNotModerator, IsOwner, IsOwnerOrModerator
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """CRUD для курсов через ViewSet."""
    # Оптимизация: prefetch_related для уроков (чтобы не делать запрос в цикле)
    queryset = Course.objects.prefetch_related('lessons').select_related('owner').all()
    serializer_class = CourseSerializer

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


class LessonListAPIView(generics.ListAPIView):
    """Список уроков."""
    # Оптимизация: select_related для курса и владельца
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


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
