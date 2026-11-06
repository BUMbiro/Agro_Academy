from rest_framework import serializers

from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор платежа.

    Отдаёт:
    - user (id),
    - course (id) и course_title (для читаемости),
    - lesson (id) и lesson_title (для читаемости),
    - amount, payment_method, payment_date.
    """

    course_title = serializers.CharField(
        source='course.title',
        read_only=True,
        allow_null=True,
        default=None,
    )
    lesson_title = serializers.CharField(
        source='lesson.title',
        read_only=True,
        allow_null=True,
        default=None,
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True,
    )

    class Meta:
        model = Payment
        fields = [
            'id',
            'user',
            'payment_date',
            'course',
            'course_title',
            'lesson',
            'lesson_title',
            'amount',
            'payment_method',
            'payment_method_display',
        ]
        read_only_fields = ['id', 'payment_date']


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя.

    Отдаёт:
    - базовые поля (email, phone, city, avatar),
    - историю платежей (доп. задание *).
    """

    payments = PaymentSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'phone',
            'city',
            'avatar',
            'payments',
            'payments_count',
        ]
        read_only_fields = ['id']

    def get_payments_count(self, obj):
        """Считает количество платежей у пользователя."""
        return obj.payments.count()
