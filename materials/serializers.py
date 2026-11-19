from rest_framework import serializers

from .models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор урока."""
    owner_email = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'preview', 'video_url', 'owner_email']
        read_only_fields = ['id']

    def validate_course(self, value):
        """Проверяем, что пользователь добавляет урок только в свой курс."""
        request = self.context.get('request')
        # Если это обновление (PATCH), и курс не меняется - пропускаем
        if self.instance and self.instance.course == value:
            return value

        if request and request.user.is_authenticated:
            if value.owner != request.user and not request.user.is_staff:
                raise serializers.ValidationError("Вы не можете добавить урок в чужой курс.")
        return value


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса."""
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    owner_email = serializers.ReadOnlyField(source='owner.email')

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'preview',
            'description',
            'lessons_count',
            'lessons',
            'owner_email',
        ]
        read_only_fields = ['id']

    def get_lessons_count(self, obj):
        return obj.lessons.count()
