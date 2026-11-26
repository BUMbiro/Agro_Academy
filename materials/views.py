from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.openapi import MessageSerializer, error_responses
from users.permissions import IsNotModerator, IsOwner, IsOwnerOrModerator, is_moderator
from .models import Course, Lesson, Subscription
from .paginators import CustomPagination
from .serializers import CourseSerializer, LessonSerializer

TAG_COURSES = ['Курсы']
TAG_LESSONS = ['Уроки']
TAG_SUBSCRIPTIONS = ['Подписки']


@extend_schema_view(
    list=extend_schema(
        tags=TAG_COURSES,
        summary='Список курсов',
        description=(
            'Владелец видит только свои курсы, модератор — все.\n\n'
            'Пагинация: `page`, `page_size` (по умолчанию 10, максимум 50).'
        ),
        responses={200: CourseSerializer(many=True), **error_responses(401)},
    ),
    create=extend_schema(
        tags=TAG_COURSES,
        summary='Создать курс',
        description='Владелец назначается автоматически. Модераторам создание запрещено.',
        responses={201: CourseSerializer, **error_responses(400, 401, 403)},
    ),
    retrieve=extend_schema(
        tags=TAG_COURSES,
        summary='Детальная информация о курсе',
        description='Доступно владельцу и модератору. Включает вложенный список уроков.',
        responses={200: CourseSerializer, **error_responses(401, 403, 404)},
    ),
    update=extend_schema(
        tags=TAG_COURSES,
        summary='Полностью обновить курс',
        description='Владелец или модератор.',
        responses={200: CourseSerializer, **error_responses(400, 401, 403, 404)},
    ),
    partial_update=extend_schema(
        tags=TAG_COURSES,
        summary='Частично обновить курс',
        description='Владелец или модератор.',
        responses={200: CourseSerializer, **error_responses(400, 401, 403, 404)},
    ),
    destroy=extend_schema(
        tags=TAG_COURSES,
        summary='Удалить курс',
        description='Только владелец. Модератор удалять не может.',
        responses={204: OpenApiResponse(description='Курс удалён.'), **error_responses(401, 403, 404)},
    ),
)
class CourseViewSet(viewsets.ModelViewSet):
    """CRUD для курсов через ViewSet."""
    serializer_class = CourseSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        """
        Оптимизация: подгружаем уроки, владельца и подписки текущего пользователя.

        - list: модератор видит все курсы, остальные — только свои;
        - retrieve/update/destroy: без фильтра, доступ проверяют object-permissions (403, а не 404);
        - subscribe: подписаться можно и на чужой курс.
        """
        user = self.request.user
        queryset = Course.objects.select_related('owner').prefetch_related('lessons')

        if not user.is_authenticated:
            return queryset.none()

        queryset = queryset.prefetch_related(
            Prefetch(
                'subscriptions',
                queryset=Subscription.objects.filter(user=user),
                to_attr='user_subscriptions',
            )
        )

        if self.action == 'list' and not is_moderator(user):
            queryset = queryset.filter(owner=user)

        return queryset

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsNotModerator()]
        if self.action in ('retrieve', 'update', 'partial_update'):
            return [IsAuthenticated(), IsOwnerOrModerator()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsNotModerator(), IsOwner()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        methods=['POST'],
        tags=TAG_SUBSCRIPTIONS,
        summary='Подписаться на обновления курса',
        description='Доступно любому авторизованному пользователю, в том числе на чужой курс. Тело запроса не нужно.',
        request=None,
        responses={
            201: OpenApiResponse(MessageSerializer, description='Подписка оформлена.'),
            200: OpenApiResponse(MessageSerializer, description='Подписка уже была оформлена ранее.'),
            **error_responses(401, 404),
        },
    )
    @extend_schema(
        methods=['DELETE'],
        tags=TAG_SUBSCRIPTIONS,
        summary='Отписаться от обновлений курса',
        request=None,
        responses={
            204: OpenApiResponse(description='Подписка удалена.'),
            400: OpenApiResponse(MessageSerializer, description='Пользователь не был подписан.'),
            **error_responses(401, 404),
        },
    )
    @action(detail=True, methods=['post', 'delete'])
    def subscribe(self, request, pk=None):
        """POST — подписаться, DELETE — отписаться."""
        course = self.get_object()

        if request.method == 'POST':
            _, created = Subscription.objects.get_or_create(user=request.user, course=course)
            if created:
                return Response(
                    {'message': 'Вы успешно подписались на обновления курса.'},
                    status=status.HTTP_201_CREATED,
                )
            return Response({'message': 'Вы уже подписаны на этот курс.'}, status=status.HTTP_200_OK)

        deleted, _ = Subscription.objects.filter(user=request.user, course=course).delete()
        if deleted:
            # 204 No Content по стандарту HTTP не содержит тела
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'message': 'Вы не были подписаны на этот курс.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(
    tags=TAG_LESSONS,
    summary='Список уроков',
    description='Владелец видит свои уроки, модератор — все. Пагинация: `page`, `page_size` (макс. 50).',
    responses={200: LessonSerializer(many=True), **error_responses(401)},
)
class LessonListAPIView(generics.ListAPIView):
    """Список уроков: модератор видит все, остальные только свои."""
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Lesson.objects.select_related('course', 'owner')
        if not user.is_authenticated:
            return queryset.none()
        if is_moderator(user):
            return queryset.all()
        return queryset.filter(owner=user)


@extend_schema(
    tags=TAG_LESSONS,
    summary='Детальная информация об уроке',
    description='Доступно владельцу и модератору.',
    responses={200: LessonSerializer, **error_responses(401, 403, 404)},
)
class LessonRetrieveAPIView(generics.RetrieveAPIView):
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


@extend_schema(
    tags=TAG_LESSONS,
    summary='Создать урок',
    description='Урок можно добавить только в свой курс. Модераторам создание запрещено.',
    responses={201: LessonSerializer, **error_responses(400, 401, 403)},
)
class LessonCreateAPIView(generics.CreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsNotModerator]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@extend_schema_view(
    put=extend_schema(
        tags=TAG_LESSONS,
        summary='Полностью обновить урок',
        description='Владелец или модератор.',
        responses={200: LessonSerializer, **error_responses(400, 401, 403, 404)},
    ),
    patch=extend_schema(
        tags=TAG_LESSONS,
        summary='Частично обновить урок',
        description='Владелец или модератор.',
        responses={200: LessonSerializer, **error_responses(400, 401, 403, 404)},
    ),
)
class LessonUpdateAPIView(generics.UpdateAPIView):
    queryset = Lesson.objects.select_related('course', 'owner').all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]


@extend_schema(
    tags=TAG_LESSONS,
    summary='Удалить урок',
    description='Только владелец. Модератор удалять не может.',
    responses={204: OpenApiResponse(description='Урок удалён.'), **error_responses(401, 403, 404)},
)
class LessonDestroyAPIView(generics.DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsNotModerator, IsOwner]
