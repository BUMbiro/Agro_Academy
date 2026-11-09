from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, CheckConstraint

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Кастомная модель пользователя (от AbstractBaseUser).

    Авторизация по email (USERNAME_FIELD).
    Доп. поля: phone, city, avatar.
    """

    email = models.EmailField(
        unique=True,
        verbose_name='Email',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Телефон',
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Город',
    )
    avatar = models.ImageField(
        upload_to='users/avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name='Статус персонала',
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата регистрации',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email


class Payment(models.Model):
    """Платёж: пользователь оплачивает курс ИЛИ отдельный урок.

    Валидация: должен быть выбран ровно один тип — курс ИЛИ урок.
    Реализовано на двух уровнях:
    - CheckConstraint в Meta (уровень БД, PostgreSQL);
    - clean() + PaymentSerializer.validate() (уровень приложения).
    """

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', 'Наличные'
        TRANSFER = 'transfer', 'Перевод на счёт'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь',
    )
    payment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата оплаты',
    )
    course = models.ForeignKey(
        'materials.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный курс',
    )
    lesson = models.ForeignKey(
        'materials.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный урок',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма оплаты',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.TRANSFER,
        verbose_name='Способ оплаты',
    )

    class Meta:
        verbose_name = 'Платёж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']
        constraints = [
            CheckConstraint(
                condition=(
                    (Q(course__isnull=False) & Q(lesson__isnull=True)) |
                    (Q(course__isnull=True) & Q(lesson__isnull=False))
                ),
                name='payment_course_xor_lesson',
            ),
        ]

    def clean(self):
        """Валидация: ровно один из course/lesson."""
        super().clean()
        if bool(self.course) == bool(self.lesson):
            raise ValidationError(
                'Должен быть выбран ровно один тип оплаты: курс ИЛИ урок.'
            )

    def __str__(self):
        target = self.course or self.lesson or '—'
        return f'{self.user.email} → {target} ({self.amount} ₽)'
