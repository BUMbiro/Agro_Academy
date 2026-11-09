from rest_framework import serializers

from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор платежа.

    Валидация: должен быть выбран ровно один тип — курс ИЛИ урок.
    Учитывает PATCH: если поле не передано — берём из instance.
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

    def validate(self, attrs):
        """Валидация: ровно один из course/lesson.

        При PATCH поля могут не передаваться — берём текущие из instance.
        """
        if self.instance is not None:
            course = attrs.get('course', self.instance.course)
            lesson = attrs.get('lesson', self.instance.lesson)
        else:
            course = attrs.get('course')
            lesson = attrs.get('lesson')

        if bool(course) == bool(lesson):
            raise serializers.ValidationError(
                'Должен быть выбран ровно один тип оплаты: курс ИЛИ урок.'
            )
        return attrs


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
