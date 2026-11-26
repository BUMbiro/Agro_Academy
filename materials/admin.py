from django.contrib import admin
from django.db.models import Count

from .models import Course, Lesson, Subscription


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Админка для курсов."""

    list_display = ('id', 'title', 'price', 'lessons_count', 'owner', 'created_at')
    list_display_links = ('id', 'title')
    list_filter = ('owner',)
    search_fields = ('title', 'description', 'owner__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    list_select_related = ('owner',)
    fieldsets = (
        (None, {'fields': ('title', 'description', 'preview')}),
        ('Материалы и цена', {'fields': ('video_url', 'price')}),
        ('Служебное', {'fields': ('owner', 'created_at')}),
    )

    def get_queryset(self, request):
        """Аннотируем количество уроков, чтобы не делать запрос на каждую строку."""
        return (
            super()
            .get_queryset(request)
            .select_related('owner')
            .annotate(lessons_count_annotated=Count('lessons'))
        )

    @admin.display(description='Уроков', ordering='lessons_count_annotated')
    def lessons_count(self, obj):
        return obj.lessons_count_annotated


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Админка для уроков."""

    list_display = ('id', 'title', 'course', 'price', 'owner', 'created_at')
    list_display_links = ('id', 'title')
    list_filter = ('course', 'owner')
    search_fields = ('title', 'description', 'course__title', 'owner__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('course',)
    list_select_related = ('course', 'owner')
    fieldsets = (
        (None, {'fields': ('course', 'title', 'description', 'preview')}),
        ('Материалы и цена', {'fields': ('video_url', 'price')}),
        ('Служебное', {'fields': ('owner', 'created_at')}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админка для подписок (только чтение: подписки создаются из API)."""

    list_display = ('id', 'user', 'course', 'created_at')
    list_filter = ('course',)
    search_fields = ('user__email', 'course__title')
    ordering = ('-created_at',)
    readonly_fields = ('user', 'course', 'created_at')
    list_select_related = ('user', 'course')

    def has_add_permission(self, request):
        return False
