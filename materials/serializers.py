from rest_framework import serializers

from .models import Course, Lesson


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса."""

    lessons_count = serializers.IntegerField(
        source='lessons.count',
        read_only=True,
    )

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count']
        read_only_fields = ['id']


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор урока."""

    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'preview', 'video_url']
        read_only_fields = ['id']
