from rest_framework import viewsets, generics

from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer


# ============================================================
# Курс — ViewSet (по заданию)
# ============================================================

class CourseViewSet(viewsets.ModelViewSet):
    """CRUD для курсов через ViewSet."""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


# ============================================================
# Урок — Generic-классы (по заданию)
# ============================================================

class LessonListAPIView(generics.ListAPIView):
    """Список уроков."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonRetrieveAPIView(generics.RetrieveAPIView):
    """Один урок."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonCreateAPIView(generics.CreateAPIView):
    """Создание урока."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonUpdateAPIView(generics.UpdateAPIView):
    """Редактирование урока."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonDestroyAPIView(generics.DestroyAPIView):
    """Удаление урока."""
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
