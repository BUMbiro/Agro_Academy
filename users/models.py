from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

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

    def __str__(self):
        return self.email
