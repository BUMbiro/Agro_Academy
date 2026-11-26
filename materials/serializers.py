from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Course, Lesson, Subscription
from .validators import validate_youtube_url

YOUTUBE_HELP = 'Только YouTube: youtube.com, www.youtube.com, m.youtube.com, youtu.be.'


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор урока."""
    owner_email = serializers.EmailField(
        source='owner.email', read_only=True, help_text='Email владельца урока.',
    )
    video_url = serializers.URLField(
        validators=[validate_youtube_url],
        required=False,
        allow_blank=True,
        help_text=YOUTUBE_HELP,
    )

    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'preview', 'video_url', 'price', 'owner_email']
        read_only_fields = ['id']

    def validate_course(self, value):
        """Проверяем, что пользователь добавляет урок только в свой курс."""
        request = self.context.get('request')
        if self.instance and self.instance.course == value:
            return value

        if request and request.user.is_authenticated:
            if value.owner != request.user and not request.user.is_staff:
                raise serializers.ValidationError('Вы не можете добавить урок в чужой курс.')
        return value


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор курса."""
    lessons_count = serializers.SerializerMethodField(help_text='Количество уроков в курсе.')
    lessons = LessonSerializer(many=True, read_only=True)
    owner_email = serializers.EmailField(
        source='owner.email', read_only=True, help_text='Email владельца курса.',
    )
    is_subscribed = serializers.SerializerMethodField(
        help_text='Подписан ли текущий пользователь на обновления курса.',
    )
    video_url = serializers.URLField(
        validators=[validate_youtube_url],
        required=False,
        allow_blank=True,
        help_text=YOUTUBE_HELP,
    )

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'preview', 'description', 'video_url', 'price',
            'lessons_count', 'lessons', 'owner_email', 'is_subscribed',
        ]
        read_only_fields = ['id']

    @extend_schema_field(OpenApiTypes.INT)
    def get_lessons_count(self, obj):
        return obj.lessons.count()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_subscribed(self, obj):
        """Проверяем подписку, используя оптимизированный queryset."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(obj, 'user_subscriptions'):
                return len(obj.user_subscriptions) > 0
            return Subscription.objects.filter(user=request.user, course=obj).exists()
        return False
