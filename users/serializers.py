from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Payment, User


class PaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True, allow_null=True, default=None)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, allow_null=True, default=None)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'user', 'payment_date', 'course', 'course_title', 'lesson', 'lesson_title', 'amount',
                  'payment_method', 'payment_method_display']
        read_only_fields = ['id', 'payment_date']

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


class UserSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'phone', 'city', 'avatar', 'payments', 'payments_count']
        read_only_fields = ['id']

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

        # Получаем текущего пользователя из контекста запроса
        request = self.context.get('request')

        # Если запрос есть, и пользователь смотрит НЕ свой профиль (и он не админ)
        if request and request.user != instance and not request.user.is_staff:
            representation.pop('payments', None)
            representation.pop('payments_count', None)

        return representation


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Кастомный сериализатор токенов: использует email вместо username."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        return token
