from rest_framework import permissions


class IsModerator(permissions.BasePermission):
    """Проверяет, входит ли пользователь в группу 'Moderator'."""
    message = 'Вы не являетесь модератором.'

    def has_permission(self, request, view):
        # Проверка на аутентификацию (рекомендация наставника)
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name='Moderator').exists()


class IsNotModerator(permissions.BasePermission):
    """Проверяет, что пользователь НЕ входит в группу 'Moderator'."""
    message = 'Модераторы не могут выполнять это действие.'

    def has_permission(self, request, view):
        # Проверка на аутентификацию (рекомендация наставника)
        if not request.user or not request.user.is_authenticated:
            return False
        return not request.user.groups.filter(name='Moderator').exists()


class IsOwner(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем объекта."""
    message = 'Вы не являетесь владельцем этого объекта.'

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrModerator(permissions.BasePermission):
    """Проверяет, является ли пользователь владельцем ИЛИ модератором."""
    message = 'Вы не являетесь владельцем или модератором.'

    def has_object_permission(self, request, view, obj):
        if request.user.groups.filter(name='Moderator').exists():
            return True
        return obj.owner == request.user


class IsProfileOwner(permissions.BasePermission):
    """Проверяет, что пользователь редактирует свой собственный профиль."""
    message = 'Вы можете редактировать только свой профиль.'

    def has_object_permission(self, request, view, obj):
        # Админ может редактировать кого угодно, остальные - только себя
        if request.user.is_staff:
            return True
        return obj == request.user
