from rest_framework import serializers

from .models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор урока."""

    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'preview', 'video_url']
        read_only_fields = ['id']


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса.

    Отдаёт:
    - количество уроков (SerializerMethodField — по заданию);
    - список уроков (вложенный LessonSerializer — по заданию).
    """

    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'preview',
            'description',
            'lessons_count',
            'lessons',
        ]
        read_only_fields = ['id']

    def get_lessons_count(self, obj):
        """Считает количество уроков у курса."""
        return obj.lessons.count()
