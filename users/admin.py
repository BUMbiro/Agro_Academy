from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import Payment, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для кастомного User (авторизация по email)."""

    list_display = ('email', 'phone', 'city', 'is_staff', 'is_active', 'date_joined', 'payments_count')
    list_filter = ('is_staff', 'is_active', 'city')
    search_fields = ('email', 'phone', 'city')
    ordering = ('-date_joined',)
    list_select_related = False

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

    def get_queryset(self, request):
        from django.db.models import Count

        return super().get_queryset(request).annotate(_payments_count=Count('payments'))

    @admin.display(description='Платежей', ordering='_payments_count')
    def payments_count(self, obj):
        return obj._payments_count


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Админка для платежей."""

    list_display = (
        'id', 'user', 'payment_date', 'course', 'lesson',
        'amount', 'payment_method', 'status', 'link_state',
    )
    list_display_links = ('id', 'user')
    list_filter = ('status', 'payment_method', 'course', 'lesson')
    search_fields = (
        'user__email', 'course__title', 'lesson__title',
        'stripe_session_id', 'stripe_product_id', 'stripe_price_id',
    )
    ordering = ('-payment_date',)
    list_select_related = ('user', 'course', 'lesson')
    date_hierarchy = 'payment_date'
    readonly_fields = (
        'payment_date',
        'stripe_product_id',
        'stripe_price_id',
        'stripe_session_id',
        'payment_link',
        'link_expires_at',
    )
    autocomplete_fields = ('user', 'course', 'lesson')
    fieldsets = (
        (None, {'fields': ('user', 'payment_date', 'status')}),
        ('Что оплачено', {'fields': ('course', 'lesson', 'amount', 'payment_method')}),
        ('Stripe', {
            'fields': (
                'stripe_product_id', 'stripe_price_id', 'stripe_session_id',
                'payment_link', 'link_expires_at',
            ),
            'description': 'Заполняется автоматически при создании онлайн-платежа.',
        }),
    )

    @admin.display(description='Ссылка на оплату')
    def link_state(self, obj):
        """Короткий статус кликабельной ссылки на оплату."""
        if not obj.payment_link:
            return '—'
        if obj.status != Payment.Status.PENDING:
            return obj.get_status_display()
        return format_html('<a href="{}" target="_blank" rel="noopener">открыть</a>', obj.payment_link)
