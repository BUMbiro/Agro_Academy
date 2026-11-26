# 👨‍🌾 Фермерская академия (AgroAcademy) 🎓

[![Checks](https://github.com/BUMbiro/Agro_Academy/actions/workflows/checks.yml/badge.svg)](https://github.com/BUMbiro/Agro_Academy/actions/workflows/checks.yml)

**Фермерская академия** — учебный REST API образовательной платформы, созданный в рамках домашних
заданий по **Django REST Framework**. Проект позволяет создавать курсы и уроки для фермеров и
агробизнеса (ФГИС, декларации, агрономия), оформлять подписки и продавать материалы с
онлайн-оплатой через **Stripe**.

---

## 🚀 Функционал

- **Пользователи** — CRUD через `ModelViewSet`, регистрация, редактирование профиля, история платежей.
- **Курсы** — CRUD через `ModelViewSet`: цена, количество уроков, вложенный список уроков, подписка.
- **Уроки** — CRUD через `Generic`-классы: привязка к курсу, цена, ссылка на видео.
- **Платежи** — ручные платежи (только админ), фильтрация, сортировка, статусы.
- **Онлайн-оплата (Stripe)** — продукт → цена (в копейках) → Checkout-сессия → ссылка на оплату;
  проверка статуса через Session Retrieve.
- **Документация API** — OpenAPI 3 на **drf-spectacular**: Swagger UI, ReDoc и сама схема.
  Описаны все эндпоинты, параметры, ответы и ошибки.
- **JWT-авторизация** — получение и обновление токенов (`access`/`refresh`).
- **Роли** — модераторы (видят и редактируют всё, но не создают и не удаляют) и владельцы
  (работают только со своими объектами).
- **Подписки** — подписка на обновления курса и отписка от них (поле `is_subscribed`).
- **Валидация** — ссылки на видео принимаются только с YouTube (проверка хоста по белому списку).
- **Пагинация** — кастомный пагинатор (`page`, `page_size`, максимум 50).
- **Оптимизация** — `select_related`, `prefetch_related`, `Prefetch` для подписок, индексы в БД.
- **Защита от злоупотреблений** — лимит 10 запросов на создание платёжной сессии в минуту.
- **Качество кода** — `flake8` без замечаний, `coverage` для контроля покрытия.
- **CI** — GitHub Actions: линтер, тесты на PostgreSQL и замер покрытия при каждом push.

---

## 📚 Документация API

| Адрес | Что это |
|---|---|
| http://127.0.0.1:8000/api/docs/ | **Swagger UI** — можно отправлять запросы прямо из браузера |
| http://127.0.0.1:8000/api/redoc/ | **ReDoc** — удобно читать |
| http://127.0.0.1:8000/api/schema/ | **OpenAPI-схема** (YAML) |

**Как авторизоваться в Swagger:**

1. `POST /api/token/` → тело `{"email": "...", "password": "..."}` → скопируйте `access`.
2. Нажмите кнопку **Authorize** и вставьте токен **без** слова `Bearer` (префикс добавляется сам).
3. Токен сохраняется после перезагрузки страницы (`persistAuthorization`).

Проверить схему на ошибки (вывод должен быть пустым):

```bash
python manage.py spectacular --validate --file schema.yml
```

---

## 🔒 Права доступа

### Курсы и уроки

| Действие | Кто может |
|---|---|
| Любой запрос анонима | ❌ никто (401) |
| Список (`GET /courses/`, `GET /lessons/`) | владелец видит **только свои**, модератор видит **все** |
| Детальный просмотр | владелец или модератор (иначе 403) |
| Создание | авторизованный, **не модератор** |
| Редактирование | владелец или модератор |
| Удаление | только владелец (модератор не может) |
| Подписка / отписка | любой авторизованный, в том числе на чужой курс |

- Урок можно добавить только в **свой** курс (иначе 400).
- Ссылка на видео: хост сравнивается с белым списком (`youtube.com`, `www.youtube.com`,
  `m.youtube.com`, `youtu.be`). Адреса вида `youtube.com.example.com` или
  `youtube.com@evil.com` отклоняются.

### Пользователи

- **Регистрация** (`POST /api/users/`) и **получение токенов** доступны без авторизации.
- **Профиль**: просматривать можно любой, редактировать только свой (админ может любой).
  История платежей в чужом профиле скрыта.
- **Удаление пользователей** — только админ (`is_staff`).

### Платежи

| Действие | Кто может |
|---|---|
| `GET /payments/`, `GET /payments/<id>/` | только **свои** платежи; админ — все |
| `POST /payments/checkout/` | любой авторизованный (кроме автора материала и повторной оплаты) |
| `GET /payments/<id>/status/` | только владелец платежа или админ |
| `GET /payments/success/`, `GET /payments/cancel/` | без авторизации (сюда возвращает Stripe) |
| `POST/PUT/PATCH/DELETE /payments/...` | только админ (ручные платежи) |

> Список платежей закрыт специально: там суммы и ссылки на оплату, публичными они быть не должны.
> Чужой платёж отдаёт **404**, а не 403 — так не раскрывается само существование записи.

---

## 💳 Онлайн-оплата (Stripe)

### Подключение

1. Зарегистрируйтесь: https://dashboard.stripe.com/register
   Подтверждать аккаунт не нужно — он остаётся в **тестовом режиме**.
2. Откройте https://dashboard.stripe.com/test/apikeys и скопируйте **Secret key** (`sk_test_...`).
3. Пропишите ключ в `.env`:

```env
STRIPE_SECRET_KEY=sk_test_ваш_ключ
STRIPE_CURRENCY=rub
STRIPE_MIN_AMOUNT=50
```

### Сценарий оплаты

1. Автор создаёт курс с ценой: `POST /api/courses/` → `{"title": "...", "price": "1500.00"}`.
2. Другой пользователь запрашивает оплату:

```http
POST /api/payments/checkout/
Authorization: Bearer <access>

{"course": 1}
```

3. В ответе приходит платёж со ссылкой `payment_link` — на неё нужно перенаправить пользователя:

```json
{
  "id": 5,
  "user": 2,
  "payment_date": "2026-11-25T12:00:00+03:00",
  "course": 1,
  "course_title": "ФГИС Росаккредитация",
  "lesson": null,
  "lesson_title": null,
  "amount": "1500.00",
  "payment_method": "stripe",
  "payment_method_display": "Онлайн-оплата (Stripe)",
  "status": "pending",
  "status_display": "Ожидает оплаты",
  "payment_link": "https://checkout.stripe.com/c/pay/cs_test_...",
  "link_expires_at": "2026-11-26T12:00:00+03:00",
  "stripe_product_id": "prod_RxYz123",
  "stripe_price_id": "price_1QaBcD",
  "stripe_session_id": "cs_test_..."
}
```

4. Оплатите тестовой картой (срок — любая будущая дата, CVC — любые 3 цифры):

| Карта | Результат |
|---|---|
| `4242 4242 4242 4242` | ✅ успешная оплата |
| `4000 0025 0000 3155` | 🔐 требует 3-D Secure |
| `4000 0000 0000 9995` | ❌ отказ: недостаточно средств |

5. Stripe вернёт пользователя на `/api/payments/success/?session_id=...` — статус платежа
   **обновится автоматически**. Проверить вручную: `GET /api/payments/<id>/status/`.

### Что происходит под капотом

`POST /api/payments/checkout/` вызывает три эндпоинта Stripe подряд:

| Шаг | Метод Stripe | Что сохраняем у себя |
|---|---|---|
| 1. Создание продукта | `products.create` | `stripe_product_id` |
| 2. Создание цены | `prices.create` (сумма × 100) | `stripe_price_id` |
| 3. Создание сессии | `checkout.sessions.create` (передаём `price_id`) | `stripe_session_id`, `payment_link`, `link_expires_at` |

- Все обращения к Stripe лежат в **`users/services.py`**. Функции возвращают обычные словари,
  View о SDK ничего не знает.
- Ошибки Stripe не выходят наружу как 500: они превращаются в `StripeServiceError`
  с понятным текстом и кодом **502** (Stripe отклонил запрос) или **503** (сервис недоступен /
  не задан ключ).
- **Сумму клиент не передаёт** — она берётся из цены курса/урока на сервере.
- Повторное нажатие «Оплатить» не создаёт новую сессию: пока старая ссылка активна,
  возвращается она (ответ 200).
- Нельзя оплатить собственный материал, бесплатный материал, сумму ниже минимума Stripe
  и уже оплаченный курс.

---

## 🧪 Тесты

В проекте **128 тестов** (`APITestCase` + `SimpleTestCase`):

| Файл | Тестов | Что покрыто |
|---|---|---|
| `materials/tests.py` | 59 | CRUD курсов и уроков, права (владелец / чужой / модератор), валидация YouTube, подписки, запрет урока в чужом курсе |
| `users/tests.py` | 39 | Регистрация, профиль, JWT, права на платежи, фильтры и сортировка, скрытие истории платежей |
| `users/test_stripe.py` | 27 | Сервисный слой Stripe (на моках), сквозной сценарий «продукт → цена → сессия», `checkout`, `status`, `success`/`cancel`, ошибки Stripe |
| `config/tests.py` | 3 | Доступность схемы, Swagger UI и ReDoc |

Запросы к Stripe в тестах **замоканы** — сеть не нужна, CI не зависит от внешнего сервиса.
Проверяется в том числе, что в Stripe уходит сумма в **копейках** (`1500.00 → 150000`)
и правильный `price_id`.

**Запуск:**

```bash
python manage.py test
```

В тестовом режиме используется быстрый `MD5PasswordHasher` (см. `config/settings.py`),
поэтому прогон занимает несколько секунд. Можно ещё быстрее — в параллель:

```bash
python manage.py test --parallel
```

### 📊 Покрытие: **94%**

Готовые отчёты лежат в репозитории:
- `coverage.txt` — текстовый отчёт;
- `htmlcov/index.html` — HTML-отчёт.

Пересобрать отчёты:

```bash
coverage run --source=. manage.py test
coverage report -m > coverage.txt      # cmd / bash
coverage html
```

> В PowerShell используйте `coverage report -m | Set-Content -Encoding ascii coverage.txt`,
> иначе файл сохранится в UTF-16.

> Миграции, тесты, `manage.py`, `asgi.py`, `wsgi.py` и служебные скрипты исключены из подсчёта
> (см. `.coveragerc`).

### 🔍 Проверка стиля

```bash
flake8 .
```

Вывод должен быть пустым. Настройки лежат в `.flake8` (лимит строки — 120 символов, миграции
и виртуальное окружение исключены).

---

## ⚙️ CI (GitHub Actions)

Workflow `.github/workflows/checks.yml` запускается при каждом push и pull request:

1. Поднимает контейнер **PostgreSQL 17** как service.
2. Ставит зависимости из `requirements.txt` и `requirements-dev.txt`.
3. Запускает `flake8 .` (линтер).
4. Запускает `python manage.py test` (128 тестов).
5. Считает покрытие через `coverage report -m`.

Переменные окружения (`SECRET_KEY`, `DB_*`, `STRIPE_SECRET_KEY`) передаются через `env:`
в workflow, поэтому `.env` в CI не нужен. Статус последнего запуска виден по бейджу вверху
страницы.

---

## 🛠 Технологический стек

- **Python 3.12**
- **Django 6.1.3**
- **Django REST Framework 3.18.3**
- **drf-spectacular 0.30.0** — документация OpenAPI 3 (Swagger UI, ReDoc)
- **stripe 17.1.0** — онлайн-оплата (современный `StripeClient`)
- **djangorestframework-simplejwt 5.5.1** — JWT-авторизация
- **django-filter 25.2** — фильтрация `queryset`
- **psycopg 3.3.9** (`psycopg[binary]`) — драйвер PostgreSQL
- **coverage 7.5.1** — анализ покрытия тестами
- **flake8** — проверка соответствия PEP 8
- **GitHub Actions** — CI: линтер, тесты, покрытие
- **PostgreSQL 17** — база данных
- **Pillow 13.0.0** — изображения (превью, аватары)
- Чтение `.env` — собственный мини-парсер в `config/settings.py`

> Используется **psycopg 3**, а не psycopg2: psycopg2 падает с `UnicodeDecodeError`
> на русскоязычных сообщениях PostgreSQL в Windows и вместо реальной ошибки показывает
> набор символов. psycopg 3 в такой ситуации корректно выводит причину.

---

## 📦 Установка и запуск

### 1. Клонируйте репозиторий

```bash
git clone https://github.com/BUMbiro/Agro_Academy.git
cd Agro_Academy
```

### 2. Создайте и активируйте виртуальное окружение

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
```

### 3. Установите зависимости

```bash
pip install -r requirements.txt
```

Для разработки (линтер и покрытие) дополнительно:

```bash
pip install -r requirements-dev.txt
```

### 4. Создайте пользователя и базу PostgreSQL

В `psql` под суперпользователем `postgres`:

```sql
CREATE USER agro_academy_user WITH LOGIN PASSWORD 'ваш_пароль' CREATEDB;

CREATE DATABASE agro_academy
    WITH OWNER = agro_academy_user
         ENCODING = 'UTF8'
         TEMPLATE = template0;
```

> `CREATEDB` нужен, чтобы `python manage.py test` мог создать тестовую БД.
> `TEMPLATE = template0` нужен на Windows с русской локалью — иначе PostgreSQL
> откажется создавать базу в UTF8.
>
> Если роль и база уже были созданы ранее, пароль задаётся отдельно:
> `ALTER ROLE agro_academy_user WITH LOGIN PASSWORD 'ваш_пароль' CREATEDB;`

### 5. Настройте переменные окружения

```bash
cp .env.template .env    # Windows: copy .env.template .env
```

Пример `.env`:

```env
SECRET_KEY=длинная_случайная_строка_не_короче_32_символов
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=agro_academy
DB_USER=agro_academy_user
DB_PASSWORD=ваш_пароль
DB_HOST=localhost
DB_PORT=5432

# Stripe (тестовый режим)
STRIPE_SECRET_KEY=sk_test_ваш_ключ
STRIPE_CURRENCY=rub
STRIPE_MIN_AMOUNT=50
STRIPE_SUCCESS_URL=
STRIPE_CANCEL_URL=
```

> Значения пишутся **без кавычек и без пробелов** — парсер в `settings.py` снимает только
> пробелы по краям, кавычки останутся частью пароля.
> `.env` добавлен в `.gitignore`, реальные секреты в репозиторий не попадают.

**Переменные Stripe:**

| Переменная | Назначение |
|---|---|
| `STRIPE_SECRET_KEY` | Секретный ключ тестового режима. Без него `checkout` вернёт 503 |
| `STRIPE_CURRENCY` | Валюта, по умолчанию `rub` |
| `STRIPE_MIN_AMOUNT` | Минимальная сумма онлайн-оплаты в рублях (по умолчанию 50) |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | Адреса возврата. Пусто = строятся автоматически |

`SECRET_KEY` короче 32 символов вызовет предупреждение `InsecureKeyLengthWarning` от PyJWT.
Сгенерировать нормальный:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Проверьте подключение к базе (по желанию)

```bash
python check_db.py
```

Скрипт берёт параметры из вашего `settings.py` и проверяет два подключения: к служебной базе
`postgres` (сервер + логин + пароль) и к рабочей `agro_academy` (существует ли она).
Нужно увидеть `[OK]` два раза.

### 7. Выполните миграции

```bash
python manage.py migrate
```

### 8. Загрузите фикстуры

```bash
python manage.py loaddata groups
python manage.py loaddata payments
```

- `groups.json` создаёт группу **Moderator**. Чтобы сделать пользователя модератором,
  добавьте его в эту группу через админку.
- `payments.json` создаёт 4 платежа со статусом `paid`. Для него в базе уже должны быть
  пользователи с ID 1–2, курсы с ID 1–2 и уроки с ID 2 и 4.

### 9. Создайте суперпользователя

```bash
python manage.py createsuperuser
```

> Django спросит **Email** (а не `username`): в кастомной модели `User` задано
> `USERNAME_FIELD = 'email'`.

### 10. Запустите сервер

```bash
python manage.py runserver
```

- API: 👉 http://127.0.0.1:8000/api/
- Документация: 👉 http://127.0.0.1:8000/api/docs/
- Админка: 👉 http://127.0.0.1:8000/admin/

> Для запросов к курсам, урокам и платежам нужен заголовок `Authorization: Bearer <access_token>`.

---

## 📁 Структура проекта

```text
Agro_Academy/
├── .github/
│   └── workflows/
│       └── checks.yml          # CI: PostgreSQL, flake8, тесты, покрытие
├── users/                      # Пользователи и платежи
│   ├── fixtures/
│   │   ├── groups.json         # Группа Moderator
│   │   └── payments.json       # 4 тестовых платежа
│   ├── migrations/
│   ├── admin.py                # UserAdmin, PaymentAdmin
│   ├── apps.py
│   ├── managers.py             # UserManager (создание по email)
│   ├── models.py               # User (AbstractBaseUser), Payment (+ статусы, Stripe-поля)
│   ├── permissions.py          # is_moderator, IsModerator, IsNotModerator, IsOwner,
│   │                           # IsOwnerOrModerator, IsProfileOwner
│   ├── serializers.py          # UserSerializer, PaymentSerializer, PaymentCheckoutSerializer,
│   │                           # PaymentStatusSerializer, JWT-сериализаторы
│   ├── services.py             # 🔌 сервисный слой Stripe (продукт → цена → сессия)
│   ├── test_stripe.py          # 27 тестов Stripe и онлайн-оплаты (на моках)
│   ├── tests.py                # 39 тестов (JWT, регистрация, права, платежи)
│   ├── urls.py                 # Роутер + эндпоинты JWT
│   └── views.py                # UserViewSet, PaymentViewSet (+ checkout, status, success, cancel)
├── materials/                  # Курсы, уроки, подписки
│   ├── migrations/
│   ├── admin.py                # CourseAdmin, LessonAdmin, SubscriptionAdmin
│   ├── apps.py
│   ├── models.py               # Course, Lesson (с ценой), Subscription
│   ├── paginators.py           # CustomPagination
│   ├── serializers.py          # CourseSerializer (is_subscribed), LessonSerializer
│   ├── tests.py                # 59 тестов (CRUD, права, YouTube, подписки, валидация)
│   ├── urls.py                 # Роутер + Generic-классы
│   ├── validators.py           # validate_youtube_url (urlparse + белый список)
│   └── views.py                # CourseViewSet (+ subscribe), Lesson*APIView
├── config/                     # Настройки проекта
│   ├── openapi.py              # Общие элементы схемы: ErrorDetailSerializer, error_responses()
│   ├── settings.py             # PostgreSQL, DRF, JWT, django-filter, drf-spectacular, Stripe
│   ├── tests.py                # 3 теста: схема, Swagger UI, ReDoc
│   ├── urls.py                 # admin, /api/schema/, /api/docs/, /api/redoc/
│   ├── asgi.py
│   └── wsgi.py
├── htmlcov/                    # HTML-отчёт покрытия
├── .coveragerc                 # Настройки coverage
├── .editorconfig               # Единый стиль файлов в редакторе
├── .env.template               # Шаблон переменных окружения
├── .flake8                     # Настройки проверки стиля
├── .gitignore
├── check_db.py                 # Диагностика подключения к PostgreSQL
├── coverage.txt                # Текстовый отчёт покрытия
├── manage.py
├── README.md
├── requirements.txt            # Боевые зависимости
└── requirements-dev.txt        # Линтер и coverage для CI
```

---

## 🔗 Эндпоинты

### Документация
- `GET /api/schema/` — OpenAPI-схема (YAML)
- `GET /api/docs/` — Swagger UI
- `GET /api/redoc/` — ReDoc

### Авторизация
- `POST /api/token/` — получить `access` и `refresh` (email + password)
- `POST /api/token/refresh/` — обновить `access`

### Пользователи
- `GET /api/users/` — список
- `POST /api/users/` — регистрация (без авторизации)
- `GET /api/users/<id>/` — профиль (платежи видны только владельцу и админу)
- `PUT/PATCH /api/users/<id>/` — обновить (только свой профиль)
- `DELETE /api/users/<id>/` — удалить (только админ)

### Курсы
- `GET /api/courses/` — список (свои; модератор видит все)
- `POST /api/courses/` — создать (не модератор)
- `GET /api/courses/<id>/` — детальная (владелец или модератор)
- `PUT/PATCH /api/courses/<id>/` — обновить (владелец или модератор)
- `DELETE /api/courses/<id>/` — удалить (только владелец)
- `POST /api/courses/<id>/subscribe/` — подписаться (любой авторизованный)
- `DELETE /api/courses/<id>/subscribe/` — отписаться

### Уроки
- `GET /api/lessons/` — список (свои; модератор видит все)
- `POST /api/lessons/create/` — создать в своём курсе (не модератор)
- `GET /api/lessons/<id>/` — детальная (владелец или модератор)
- `PUT/PATCH /api/lessons/<id>/update/` — обновить (владелец или модератор)
- `DELETE /api/lessons/<id>/delete/` — удалить (только владелец)

### Платежи
- `GET /api/payments/` — свои платежи (админ — все)
- `GET /api/payments/<id>/` — детальная (свой платёж или админ)
- `POST /api/payments/checkout/` — 💳 **оплатить курс или урок через Stripe**, вернёт `payment_link`
- `GET /api/payments/<id>/status/` — сверить статус со Stripe (Session Retrieve)
- `GET /api/payments/success/?session_id=...` — возврат после оплаты, статус обновляется сам
- `GET /api/payments/cancel/` — возврат при отмене оплаты
- `POST /api/payments/` — создать ручной платёж (только админ; статус по умолчанию `paid`)
- `PUT/PATCH /api/payments/<id>/` — обновить (только админ)
- `DELETE /api/payments/<id>/` — удалить (только админ)

**Фильтры и сортировка платежей:**
- `?user=<id>`, `?course=<id>`, `?lesson=<id>`
- `?payment_method=cash|transfer|stripe`, `?status=pending|paid|expired`
- `?ordering=payment_date` / `-payment_date` / `amount` / `-amount`

**Пагинация курсов и уроков:** `?page=<n>&page_size=<n>` (по умолчанию 10, максимум 50).

**Лимиты:** `POST /api/payments/checkout/` — не более 10 запросов в минуту на пользователя (иначе 429).

---

## 🗄 Модели

**Пользователи**
- `User (AbstractBaseUser)` — email (`USERNAME_FIELD`), password, phone, city, avatar,
  is_active, is_staff, date_joined.

**Материалы**
- `Course` — title, preview, description, video_url, **price**, owner (FK), created_at.
- `Lesson` — course (FK → Course), title, description, preview, video_url, **price**,
  owner (FK), created_at.
- `Subscription` — user (FK), course (FK), created_at. Пара (user, course) уникальна.

**Платежи**
- `Payment` — user (FK), payment_date, course (FK, null), lesson (FK, null), amount,
  payment_method (`cash` / `transfer` / `stripe`), status (`pending` / `paid` / `expired`).
- Поля Stripe: `stripe_product_id`, `stripe_price_id`, `stripe_session_id`,
  `payment_link`, `link_expires_at`.
- Валидация: ровно один из `course`/`lesson` (`CheckConstraint` + `clean()` + валидация сериализатора).
- `stripe_session_id` уникален — одна сессия Stripe не может быть привязана к двум платежам.

Для всех моделей заданы `Meta` (`verbose_name`, `verbose_name_plural`), `__str__`,
индексы по `owner + created_at` (курсы, уроки) и по `user + course` (подписки).

---

## 🧪 Ручная проверка через Postman

- ✅ CRUD для курсов, уроков, пользователей и платежей
- ✅ JWT: получение и обновление токенов, запросы с `Bearer`
- ✅ Права: владелец, чужой пользователь, модератор, админ
- ✅ Подписка и отписка на курс
- ✅ Фильтры `?course=`, `?lesson=`, `?payment_method=`, `?status=`, `?user=`
- ✅ Сортировка `?ordering=payment_date` / `-payment_date` / `amount`
- ✅ Онлайн-оплата: `checkout` → `payment_link` → оплата тестовой картой → `status` = `paid`
- ✅ Swagger UI на `/api/docs/` с авторизацией через **Authorize**

---

## ❓ Частые проблемы

| Симптом | Причина и решение |
|---|---|
| `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2 in position 61` | Установлен **psycopg2**, он не может прочитать русское сообщение PostgreSQL (CP1251) и падает вместо показа причины. Установите `psycopg[binary]` |
| `ФАТАЛЬНО: пользователь ... не прошёл проверку подлинности (по паролю)` | Пароль в `.env` не совпадает с паролем роли: `ALTER ROLE agro_academy_user WITH LOGIN PASSWORD 'тот-же-пароль';` |
| `connection refused` | Служба PostgreSQL не запущена: `Get-Service *postgres*`, затем `Start-Service postgresql-x64-17` |
| `new encoding (UTF8) is incompatible with the encoding of the template database` | Создавайте базу с `TEMPLATE = template0` (см. шаг 4) |
| `checkout` возвращает 503 «Онлайн-оплата не настроена» | Не задан `STRIPE_SECRET_KEY` в `.env` |
| `checkout` возвращает 502 «Invalid currency» | Валюта не поддерживается для страны аккаунта: поставьте `STRIPE_CURRENCY=usd` и `STRIPE_MIN_AMOUNT=1` |
| 400 «Нельзя оплатить собственный материал» | Оплату нужно проверять от имени **другого** пользователя, не автора курса |
| 400 «Минимальная сумма онлайн-оплаты…» | Цена курса ниже `STRIPE_MIN_AMOUNT` |
| 400 «Материал бесплатный — оплата не требуется» | У курса/урока `price = 0` |
| 429 Too Many Requests | Сработал лимит 10 запросов в минуту на `checkout` |
| Swagger открывается, но запросы дают 401 | Не нажали **Authorize** или вставили токен вместе со словом `Bearer` |
| `InsecureKeyLengthWarning` от PyJWT | `SECRET_KEY` короче 32 символов — сгенерируйте новый |
| `W292 no newline at end of file` | В конце файла нет перевода строки. Включите `insert_final_newline` — он уже задан в `.editorconfig` |
| `flake8` ругается на `.venv` и миграции | Параметр `--exclude` в командной строке **заменяет** список из `.flake8`. Запускайте просто `flake8 .` или используйте `--extend-exclude` |
| CI падает на шаге Tests | Проверьте, что сервис `postgres` поднялся (ветка `services` в workflow) и `DB_*` в `env:` совпадают с ним |

---

## 👨‍🌾 Об авторе

Александр **(BUMbiro)** — студент курса **Python-разработки**.
Проект создан в рамках домашних заданий по **Django REST Framework**.

**Стек:** Django · DRF · SimpleJWT · django-filter · drf-spectacular · Stripe · PostgreSQL · Pillow

---

## 📝 Лицензия

Учебный проект. Не предназначен для коммерческого использования.
