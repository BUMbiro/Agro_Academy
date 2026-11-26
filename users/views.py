from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAdminUser,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.openapi import ErrorDetailSerializer, MessageSerializer, error_responses
from .models import Payment, User
from .permissions import IsProfileOwner
from .serializers import (
    CustomTokenObtainPairSerializer,
    PaymentCheckoutSerializer,
    PaymentSerializer,
    PaymentStatusSerializer,
    TokenAccessResponseSerializer,
    TokenPairResponseSerializer,
    UserSerializer,
)
from .services import StripeServiceError, start_checkout, sync_payment_with_stripe

TAG_AUTH = ['Авторизация']
TAG_USERS = ['Пользователи']
TAG_PAYMENTS = ['Платежи']


# ============================================================
# Авторизация
# ============================================================

@extend_schema_view(
    post=extend_schema(
        tags=TAG_AUTH,
        summary='Получить пару JWT-токенов',
        description=(
            'Вход по email и паролю. '
            '`access` передаётся в заголовке `Authorization: Bearer <access>`.'
        ),
        responses={
            200: TokenPairResponseSerializer,
            **error_responses(400),
            401: OpenApiResponse(
                ErrorDetailSerializer, description='Неверный email или пароль.',
            ),
        },
    ),
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    post=extend_schema(
        tags=TAG_AUTH,
        summary='Обновить access-токен',
        description='Принимает `refresh`, возвращает новый `access`.',
        responses={
            200: TokenAccessResponseSerializer,
            **error_responses(400),
            401: OpenApiResponse(
                ErrorDetailSerializer,
                description='Refresh-токен недействителен или истёк.',
            ),
        },
    ),
)
class CustomTokenRefreshView(TokenRefreshView):
    pass


# ============================================================
# Пользователи
# ============================================================

@extend_schema_view(
    list=extend_schema(
        tags=TAG_USERS,
        summary='Список пользователей',
        description=(
            'Доступен всем. Поля `payments` и `payments_count` присутствуют только '
            'в собственном профиле (и у всех — для администратора).'
        ),
        responses={200: UserSerializer(many=True)},
    ),
    create=extend_schema(
        tags=TAG_USERS,
        summary='Регистрация',
        description='Доступна без авторизации. Пароль хешируется и в ответе не возвращается.',
        responses={201: UserSerializer, **error_responses(400)},
    ),
    retrieve=extend_schema(
        tags=TAG_USERS,
        summary='Профиль пользователя',
        description='История платежей видна только владельцу профиля и администратору.',
        responses={200: UserSerializer, **error_responses(404)},
    ),
    update=extend_schema(
        tags=TAG_USERS,
        summary='Полностью обновить профиль',
        description='Только свой профиль (админ — любой).',
        responses={200: UserSerializer, **error_responses(400, 401, 403, 404)},
    ),
    partial_update=extend_schema(
        tags=TAG_USERS,
        summary='Частично обновить профиль',
        description='Только свой профиль (админ — любой).',
        responses={200: UserSerializer, **error_responses(400, 401, 403, 404)},
    ),
    destroy=extend_schema(
        tags=TAG_USERS,
        summary='Удалить пользователя',
        description='Только администратор (`is_staff`).',
        responses={
            204: OpenApiResponse(description='Пользователь удалён.'),
            **error_responses(401, 403, 404),
        },
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """CRUD для пользователей."""

    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action == 'destroy':
            return [IsAdminUser()]
        if self.action in ('update', 'partial_update'):
            return [IsAuthenticated(), IsProfileOwner()]
        return [IsAuthenticatedOrReadOnly()]


# ============================================================
# Платежи
# ============================================================

PAYMENT_EXAMPLE = {
    'id': 5,
    'user': 2,
    'payment_date': '2026-11-25T12:00:00+03:00',
    'course': 1,
    'course_title': 'ФГИС Росаккредитация',
    'lesson': None,
    'lesson_title': None,
    'amount': '1500.00',
    'payment_method': 'stripe',
    'payment_method_display': 'Онлайн-оплата (Stripe)',
    'status': 'pending',
    'status_display': 'Ожидает оплаты',
    'payment_link': 'https://checkout.stripe.com/c/pay/cs_test_a1B2c3',
    'link_expires_at': '2026-11-26T12:00:00+03:00',
    'stripe_product_id': 'prod_RxYz123',
    'stripe_price_id': 'price_1QaBcD',
    'stripe_session_id': 'cs_test_a1B2c3',
}

STATUS_RESPONSES = {
    200: PaymentStatusSerializer,
    **error_responses(502, 503),
}


@extend_schema_view(
    list=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Список платежей',
        description=(
            'Пользователь видит только свои платежи, администратор — все.\n\n'
            'Фильтры: `user`, `course`, `lesson`, `payment_method`, `status`. '
            'Сортировка: `ordering=payment_date | -payment_date | amount | -amount`.'
        ),
        responses={200: PaymentSerializer(many=True), **error_responses(401)},
    ),
    retrieve=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Детальная информация о платеже',
        description='Свой платёж или любой — для администратора. Чужой платёж отдаёт 404.',
        responses={200: PaymentSerializer, **error_responses(401, 404)},
    ),
    create=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Создать платёж вручную (админ)',
        description=(
            'Для наличных и переводов. Если `status` не передан — платёж сразу `paid`. '
            'Онлайн-оплата создаётся только через `POST /api/payments/checkout/`.'
        ),
        responses={201: PaymentSerializer, **error_responses(400, 401, 403)},
    ),
    update=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Полностью обновить платёж (админ)',
        responses={200: PaymentSerializer, **error_responses(400, 401, 403, 404)},
    ),
    partial_update=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Частично обновить платёж (админ)',
        responses={200: PaymentSerializer, **error_responses(400, 401, 403, 404)},
    ),
    destroy=extend_schema(
        tags=TAG_PAYMENTS,
        summary='Удалить платёж (админ)',
        responses={
            204: OpenApiResponse(description='Платёж удалён.'),
            **error_responses(401, 403, 404),
        },
    ),
)
class PaymentViewSet(viewsets.ModelViewSet):
    """Платежи: история, ручные платежи (админ) и онлайн-оплата через Stripe."""

    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'course', 'lesson', 'payment_method', 'status']
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']
    throttle_scope = 'payments_checkout'  # применяется только в checkout

    def get_queryset(self):
        queryset = Payment.objects.select_related('user', 'course', 'lesson')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_staff:
            return queryset
        return queryset.filter(user=user)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminUser()]
        if self.action in ('success', 'cancel'):
            # Сюда Stripe возвращает браузер пользователя — без JWT
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # Ручной платёж (наличные/перевод) по умолчанию считается оплаченным
        serializer.save(
            status=serializer.validated_data.get('status', Payment.Status.PAID),
        )

    # ---------- Вспомогательные методы ----------

    @staticmethod
    def _return_urls(request):
        """URL возврата из Stripe. {CHECKOUT_SESSION_ID} Stripe подставит сам."""
        success_url = settings.STRIPE_SUCCESS_URL or (
            request.build_absolute_uri(reverse('payment-success'))
            + '?session_id={CHECKOUT_SESSION_ID}'
        )
        cancel_url = settings.STRIPE_CANCEL_URL or request.build_absolute_uri(
            reverse('payment-cancel'),
        )
        return success_url, cancel_url

    @staticmethod
    def _sync_and_respond(payment):
        """Сверяет платёж со Stripe и возвращает актуальный статус."""
        try:
            session = sync_payment_with_stripe(payment)
        except StripeServiceError as exc:
            return Response({'detail': exc.message}, status=exc.status_code)

        data = {
            'payment_id': payment.pk,
            'status': payment.status,
            'status_display': payment.get_status_display(),
            'stripe_session_id': session['id'],
            'stripe_session_status': session['status'],
            'stripe_payment_status': session['payment_status'],
            'amount': payment.amount,
            'currency': session['currency'],
            'payment_link': (
                payment.payment_link
                if payment.status == Payment.Status.PENDING
                else None
            ),
        }
        return Response(PaymentStatusSerializer(instance=data).data)

    # ---------- Онлайн-оплата ----------

    @extend_schema(
        tags=TAG_PAYMENTS,
        summary='Оплатить курс или урок через Stripe',
        description=(
            'Создаёт в Stripe **продукт → цену (в копейках) → Checkout-сессию** и сохраняет '
            'платёж со статусом `pending`. Ссылка на оплату — в поле `payment_link`.\n\n'
            'Сумму клиент не передаёт: она берётся из цены курса/урока на сервере.\n\n'
            'Если по этому материалу уже есть неоплаченная активная ссылка, вернётся она (200), '
            'новая сессия не создаётся.\n\n'
            'Тестовая карта: `4242 4242 4242 4242`, любая будущая дата, любой CVC.\n\n'
            'Лимит: 10 запросов в минуту на пользователя.'
        ),
        request=PaymentCheckoutSerializer,
        examples=[
            OpenApiExample('Оплата курса', value={'course': 1}, request_only=True),
            OpenApiExample('Оплата урока', value={'lesson': 2}, request_only=True),
        ],
        responses={
            201: OpenApiResponse(
                PaymentSerializer,
                description='Платёж создан. Ссылка на оплату — в `payment_link`.',
                examples=[
                    OpenApiExample(
                        'Создан платёж', value=PAYMENT_EXAMPLE, response_only=True,
                    ),
                ],
            ),
            200: OpenApiResponse(
                PaymentSerializer,
                description='Возвращена существующая активная ссылка.',
            ),
            400: OpenApiResponse(
                OpenApiTypes.OBJECT,
                description=(
                    'Неверные данные: не выбран / выбраны оба объекта, материал бесплатный, '
                    'свой материал, сумма ниже минимальной, уже оплачено.'
                ),
                examples=[
                    OpenApiExample(
                        'Не выбран объект',
                        value={
                            'non_field_errors': [
                                'Укажите ровно один объект для оплаты: course ИЛИ lesson.',
                            ],
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        'Уже оплачено',
                        value={'course': ['Этот материал уже оплачен.']},
                        response_only=True,
                    ),
                ],
            ),
            **error_responses(401, 429, 502, 503),
        },
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='checkout',
        serializer_class=PaymentCheckoutSerializer,
        throttle_classes=[ScopedRateThrottle],
    )
    def checkout(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data.get('course')
        lesson = serializer.validated_data.get('lesson')
        product = serializer.validated_data['product']
        context = self.get_serializer_context()

        # Идемпотентность: не плодим сессии, пока старая ссылка жива
        existing = Payment.objects.filter(
            user=request.user,
            course=course,
            lesson=lesson,
            payment_method=Payment.PaymentMethod.STRIPE,
            status=Payment.Status.PENDING,
            link_expires_at__gt=timezone.now(),
        ).first()
        if existing:
            return Response(
                PaymentSerializer(existing, context=context).data,
                status=status.HTTP_200_OK,
            )

        success_url, cancel_url = self._return_urls(request)
        try:
            checkout = start_checkout(
                user=request.user,
                product=product,
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except StripeServiceError as exc:
            return Response({'detail': exc.message}, status=exc.status_code)

        payment = Payment.objects.create(
            user=request.user,
            course=course,
            lesson=lesson,
            amount=product.price,
            payment_method=Payment.PaymentMethod.STRIPE,
            status=Payment.Status.PENDING,
            stripe_product_id=checkout['product_id'],
            stripe_price_id=checkout['price_id'],
            stripe_session_id=checkout['session_id'],
            payment_link=checkout['url'],
            link_expires_at=checkout['expires_at'],
        )
        return Response(
            PaymentSerializer(payment, context=context).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=TAG_PAYMENTS,
        summary='Проверить статус оплаты в Stripe',
        description=(
            'Запрашивает Checkout-сессию в Stripe (Session Retrieve) и синхронизирует статус '
            'платежа: `paid` — оплачено, `pending` — ожидает, `expired` — ссылка истекла.'
        ),
        responses={
            **STATUS_RESPONSES,
            400: OpenApiResponse(
                ErrorDetailSerializer, description='Платёж создан не через Stripe.',
            ),
            **error_responses(401, 404),
        },
    )
    @action(detail=True, methods=['get'], url_path='status', url_name='status')
    def payment_status(self, request, pk=None):
        payment = self.get_object()
        if not payment.stripe_session_id:
            return Response(
                {
                    'detail': (
                        'Платёж создан вручную (не через Stripe) — проверять в Stripe нечего.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self._sync_and_respond(payment)

    @extend_schema(
        tags=TAG_PAYMENTS,
        summary='Возврат после успешной оплаты (success_url)',
        description=(
            'Сюда Stripe перенаправляет пользователя после оплаты. '
            'Статус платежа сверяется автоматически.'
        ),
        parameters=[
            OpenApiParameter(
                'session_id',
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                required=True,
                description='ID Checkout-сессии (Stripe подставляет его сам).',
            ),
        ],
        responses={
            **STATUS_RESPONSES,
            400: OpenApiResponse(
                ErrorDetailSerializer, description='Не передан session_id.',
            ),
            **error_responses(404),
        },
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='success',
        filter_backends=[],
        pagination_class=None,
    )
    def success(self, request):
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response(
                {'detail': 'Не передан параметр session_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payment = Payment.objects.filter(stripe_session_id=session_id).first()
        if payment is None:
            return Response(
                {'detail': 'Платёж не найден.'}, status=status.HTTP_404_NOT_FOUND,
            )
        return self._sync_and_respond(payment)

    @extend_schema(
        tags=TAG_PAYMENTS,
        summary='Возврат при отмене оплаты (cancel_url)',
        description='Сюда Stripe перенаправляет пользователя, если он отказался от оплаты.',
        responses={200: MessageSerializer},
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='cancel',
        filter_backends=[],
        pagination_class=None,
    )
    def cancel(self, request):
        return Response({
            'message': (
                'Оплата отменена. Вернуться к ней можно по ссылке из платежа, '
                'пока она активна.'
            ),
        })
