from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Payment, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для кастомного User (авторизация по email)."""

    list_display = ('email', 'phone', 'city', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'city')
    search_fields = ('email', 'phone', 'city')
    ordering = ('-date_joined',)

    # Переопределяем fieldsets под нашу модель (нет username/first_name/last_name)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {'fields': ('phone', 'city', 'avatar')}),
        ('Права', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Админка для платежей."""

    list_display = ('id', 'user', 'payment_date', 'course', 'lesson', 'amount', 'payment_method')
    list_filter = ('payment_method', 'course', 'lesson')
    search_fields = ('user__email', 'course__title', 'lesson__title')
    ordering = ('-payment_date',)
    readonly_fields = ('payment_date',)
    autocomplete_fields = ('user', 'course', 'lesson')
