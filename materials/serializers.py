from rest_framework import serializers

from .models import Course, Lesson, Subscription
from .validators import validate_youtube_url


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор урока."""
    owner_email = serializers.ReadOnlyField(source='owner.email')
    video_url = serializers.URLField(
        validators=[validate_youtube_url],
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'preview', 'video_url', 'owner_email']
        read_only_fields = ['id']

    def validate_course(self, value):
        """Проверяем, что пользователь добавляет урок только в свой курс."""
        request = self.context.get('request')
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
    is_subscribed = serializers.SerializerMethodField()
    video_url = serializers.URLField(
        validators=[validate_youtube_url],
        required=False,
        allow_blank=True
    )

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'preview',
            'description',
            'video_url',
            'lessons_count',
            'lessons',
            'owner_email',
            'is_subscribed',
        ]
        read_only_fields = ['id']

    def get_lessons_count(self, obj):
        return obj.lessons.count()

    def get_is_subscribed(self, obj):
        """Проверяем подписку, используя оптимизированный queryset."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Если мы использовали Prefetch во вьюхе
            if hasattr(obj, 'user_subscriptions'):
                return len(obj.user_subscriptions) > 0
            # Запасной вариант (для detail-view)
            return Subscription.objects.filter(user=request.user, course=obj).exists()
        return False
