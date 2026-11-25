from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from materials.models import Course, Lesson
from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True, allow_null=True, default=None)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, allow_null=True, default=None)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'payment_date',
            'course', 'course_title', 'lesson', 'lesson_title',
            'amount', 'payment_method', 'payment_method_display',
            'status', 'status_display',
            'payment_link', 'link_expires_at',
            'stripe_product_id', 'stripe_price_id', 'stripe_session_id',
        ]
        read_only_fields = [
            'id', 'payment_date', 'payment_link', 'link_expires_at',
            'stripe_product_id', 'stripe_price_id', 'stripe_session_id',
        ]

    def validate_payment_method(self, value):
        if value == Payment.PaymentMethod.STRIPE:
            raise serializers.ValidationError(
                'Онлайн-платежи создаются только через POST /api/payments/checkout/.'
            )
        return value

    def validate(self, attrs):
        if self.instance is not None:
            course = attrs.get('course', self.instance.course)
            lesson = attrs.get('lesson', self.instance.lesson)
        else:
            course = attrs.get('course')
            lesson = attrs.get('lesson')
        if bool(course) == bool(lesson):
            raise serializers.ValidationError('Должен быть выбран ровно один тип оплаты: курс ИЛИ урок.')
        return attrs


class PaymentCheckoutSerializer(serializers.Serializer):
    """Запрос на онлайн-оплату. Сумма берётся из цены материала на сервере."""
    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), required=False, allow_null=True,
        help_text='ID курса. Передайте либо `course`, либо `lesson`.',
    )
    lesson = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.select_related('course'), required=False, allow_null=True,
        help_text='ID урока. Передайте либо `course`, либо `lesson`.',
    )

    def validate(self, attrs):
        course, lesson = attrs.get('course'), attrs.get('lesson')
        if bool(course) == bool(lesson):
            raise serializers.ValidationError('Укажите ровно один объект для оплаты: course ИЛИ lesson.')

        product = course or lesson
        field = 'course' if course else 'lesson'
        user = self.context['request'].user

        if product.owner_id == user.pk:
            raise serializers.ValidationError({field: 'Нельзя оплатить собственный материал.'})
        if product.price <= 0:
            raise serializers.ValidationError({field: 'Материал бесплатный — оплата не требуется.'})
        if product.price < settings.STRIPE_MIN_AMOUNT:
            raise serializers.ValidationError(
                {field: f'Минимальная сумма онлайн-оплаты — {settings.STRIPE_MIN_AMOUNT} ₽.'}
            )
        if Payment.objects.filter(
            user=user, course=course, lesson=lesson, status=Payment.Status.PAID,
        ).exists():
            raise serializers.ValidationError({field: 'Этот материал уже оплачен.'})

        attrs['product'] = product
        return attrs


class PaymentStatusSerializer(serializers.Serializer):
    """Статус платежа после сверки со Stripe."""
    payment_id = serializers.IntegerField(help_text='ID платежа в нашей системе.')
    status = serializers.ChoiceField(choices=Payment.Status.choices, help_text='Статус платежа в нашей системе.')
    status_display = serializers.CharField(help_text='Статус платежа текстом.')
    stripe_session_id = serializers.CharField(help_text='ID Checkout-сессии Stripe.')
    stripe_session_status = serializers.CharField(help_text='Статус сессии Stripe: open, complete, expired.')
    stripe_payment_status = serializers.CharField(
        help_text='Статус оплаты в Stripe: paid, unpaid, no_payment_required.',
    )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, help_text='Сумма, ₽.')
    currency = serializers.CharField(help_text='Валюта (ISO, нижний регистр).')
    payment_link = serializers.URLField(
        allow_null=True, help_text='Ссылка на оплату (только пока платёж ожидает оплаты).',
    )


class UserSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(
        many=True, read_only=True,
        help_text='История платежей. Видна только владельцу профиля и администратору.',
    )
    payments_count = serializers.SerializerMethodField(
        help_text='Количество платежей. Видно только владельцу профиля и администратору.',
    )
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'phone', 'city', 'avatar', 'payments', 'payments_count']
        read_only_fields = ['id']

    @extend_schema_field(OpenApiTypes.INT)
    def get_payments_count(self, obj):
        return obj.payments.count()

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def to_representation(self, instance):
        """Скрываем историю платежей при просмотре чужого профиля."""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user != instance and not request.user.is_staff:
            representation.pop('payments', None)
            representation.pop('payments_count', None)
        return representation


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный сериализатор токенов: добавляет email в payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        return token


class TokenPairResponseSerializer(serializers.Serializer):
    """Ответ при получении токенов (для документации)."""
    access = serializers.CharField(help_text='Access-токен (живёт 60 минут).')
    refresh = serializers.CharField(help_text='Refresh-токен (живёт 1 день).')


class TokenAccessResponseSerializer(serializers.Serializer):
    """Ответ при обновлении токена (для документации)."""
    access = serializers.CharField(help_text='Новый access-токен.')
