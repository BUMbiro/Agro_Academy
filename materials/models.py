from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .validators import validate_youtube_url


class Course(models.Model):
    """Курс (например, «ФГИС Росаккредитация»)."""

    title = models.CharField(
        max_length=200,
        verbose_name='Название',
    )
    preview = models.ImageField(
        upload_to='courses/previews/',
        blank=True,
        null=True,
        verbose_name='Превью',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    video_url = models.URLField(
        blank=True,
        verbose_name='Ссылка на видео',
        validators=[validate_youtube_url],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Цена, ₽',
        help_text='Стоимость в рублях. 0 — бесплатно (онлайн-оплата недоступна).',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Владелец',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at'], name='course_owner_created_idx'),
        ]

    def __str__(self):
        return self.title

    @property
    def is_paid(self):
        """Есть ли у курса цена, пригодная для онлайн-оплаты."""
        return self.price > 0


class Lesson(models.Model):
    """Урок, привязанный к курсу."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название',
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание',
    )
    preview = models.ImageField(
        upload_to='lessons/previews/',
        blank=True,
        null=True,
        verbose_name='Превью',
    )
    video_url = models.URLField(
        blank=True,
        verbose_name='Ссылка на видео',
        validators=[validate_youtube_url],
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Цена, ₽',
        help_text='Стоимость отдельного урока в рублях. 0 — бесплатно.',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Владелец',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания',
    )

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner', '-created_at'], name='lesson_owner_created_idx'),
        ]

    def __str__(self):
        return f'{self.course.title} — {self.title}'

    @property
    def is_paid(self):
        """Есть ли у урока цена, пригодная для онлайн-оплаты."""
        return self.price > 0


class Subscription(models.Model):
    """Подписка пользователя на обновления курса."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь',
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Курс',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подписки',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        # Уникальность пары (пользователь, курс) — гарантия, что не будет дублей
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_subscription',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'course'], name='subscription_user_course_idx'),
        ]

    def __str__(self):
        return f'{self.user.email} подписан на {self.course.title}'
