from django.contrib import admin

from .models import Course, Lesson


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Админка для курсов."""

    list_display = ('id', 'title', 'created_at')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """Админка для уроков."""

    list_display = ('id', 'title', 'course', 'created_at')
    list_filter = ('course',)
    search_fields = ('title', 'description', 'course__title')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    autocomplete_fields = ('course',)
