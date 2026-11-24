# 👨‍🌾 Фермерская академия (AgroAcademy) 🎓

**Фермерская академия** — учебный REST API для образовательной платформы, созданный в рамках домашних
заданий по **Django REST Framework**.
Проект позволяет создавать курсы и уроки для фермеров и агробизнеса (ФГИС, декларации, агрономия).

---

## 🚀 Функционал

- **Пользователи** — CRUD через `ModelViewSet`, регистрация, редактирование профиля.
- **Курсы** — CRUD через `ModelViewSet` (количество уроков и вложенный список уроков).
- **Уроки** — CRUD через `Generic`-классы (привязка к курсу, ссылка на видео).
- **Платежи** — CRUD через `ModelViewSet` (фильтрация, сортировка, валидация).
- **JWT-авторизация** — получение и обновление токенов (`access`/`refresh`).
- **Роли** — модераторы (видят и редактируют всё, но не создают и не удаляют) и владельцы 
(работают только со своими объектами).
- **Подписки** — подписка на обновления курса и отписка от них (поле `is_subscribed` в курсе).
- **Валидация** — ссылки на видео принимаются только с YouTube (проверка хоста по белому списку).
- **Пагинация** — кастомный пагинатор (`page_size`, `page_size_query_param`, `max_page_size`) для курсов и уроков.
- **Оптимизация** — `select_related`, `prefetch_related` и `Prefetch` (для подписок) против N+1 запросов.
- **Связи** — Урок → FK → Курс (`related_name='lessons'`), Платёж → FK → Пользователь/Курс/Урок.

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
- Ссылка на видео: хост сравнивается с белым списком (`youtube.com`, `www.youtube.com`, `m.youtube.com`, `youtu.be`).
  Адреса вида `youtube.com.example.com` или `youtube.com@evil.com` отклоняются.

### Пользователи и платежи
- **Регистрация** (`POST /api/users/`) и **получение токенов** доступны без авторизации.
- **Профиль**: просматривать можно любой, редактировать только свой (админ может любой).
  История платежей в чужом профиле скрыта.
- **Удаление пользователей** — только админ (`is_staff`).
- **Платежи**: просмотр доступен всем, создание, изменение и удаление — только админу.

---

## 🧪 Тесты

В проекте **89 тестов** (`APITestCase` + `SimpleTestCase`), они покрывают:
- базовый CRUD для всех сущностей;
- права доступа (аноним, владелец, чужой пользователь, модератор, админ);
- фильтрацию списков: свои объекты и все объекты для модератора;
- запрет просмотра чужих курсов и уроков;
- валидацию YouTube-ссылок, включая поддельные домены (`youtube.com.example.com`);
- валидацию платежей (ровно один из курс/урок);
- фильтрацию и сортировку платежей;
- JWT: получение, обновление и использование токена, регистрацию;
- подписки (создание, повтор, отписка, `is_subscribed` в списке и детальной);
- запрет добавления урока в чужой курс.

**Запуск:**

```bash
python manage.py test
```

### 📊 Покрытие (Coverage): **95%**

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

> Миграции, тесты, `manage.py`, `asgi.py` и `wsgi.py` исключены из подсчёта (см. `.coveragerc`).

---

## 🛠 Технологический стек

- **Python 3.12**
- **Django 6.1.3**
- **Django REST Framework 3.18.3**
- **djangorestframework-simplejwt 5.5.1** — JWT-авторизация
- **django-filter 25.2** — фильтрация `queryset`
- **coverage 7.5.1** — анализ покрытия тестами
- **PostgreSQL 17** — база данных (через `psycopg2-binary`)
- **Pillow** — изображения (превью, аватары)
- Чтение `.env` — собственный мини-парсер в `config/settings.py`

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

### 4. Создайте базу данных PostgreSQL

В `psql` под суперпользователем `postgres`:

```sql
CREATE USER agro_academy_user WITH PASSWORD 'ваш_пароль';
ALTER USER agro_academy_user CREATEDB;
CREATE DATABASE agro_academy WITH OWNER = agro_academy_user ENCODING = 'UTF8';
```

> Право `CREATEDB` нужно, чтобы `python manage.py test` мог создать тестовую БД.

### 5. Настройте переменные окружения

```bash
cp .env.template .env    # Windows: copy .env.template .env
```

Пример `.env`:

```env
SECRET_KEY=ваш_секретный_ключ
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=agro_academy
DB_USER=agro_academy_user
DB_PASSWORD=ваш_пароль
DB_HOST=localhost
DB_PORT=5432
```

> `.env` добавлен в `.gitignore`, поэтому реальные пароли в репозиторий не попадают.
> В `.env.template` только заглушки.

### 6. Выполните миграции

```bash
python manage.py migrate
```

### 7. Загрузите фикстуры

```bash
python manage.py loaddata groups
python manage.py loaddata payments
```

- `groups.json` создаёт группу **Moderator**. Чтобы сделать пользователя модератором, добавьте его в эту группу через 
админку.
- `payments.json` создаёт 4 платежа. Для него в базе уже должны быть пользователи с ID 1–2, курсы с ID 1–2 и уроки 
с ID 2 и 4.

### 8. Создайте суперпользователя

```bash
python manage.py createsuperuser
```

> Django спросит **Email** (а не `username`): в кастомной модели `User` задано `USERNAME_FIELD = 'email'`.

### 9. Запустите сервер

```bash
python manage.py runserver
```

API: 👉 http://127.0.0.1:8000/api/

> Для запросов к курсам и урокам нужен заголовок `Authorization: Bearer <access_token>`.

---

## 📁 Структура проекта

```text
Agro_Academy/
├── users/                  # Пользователи и платежи
│   ├── fixtures/
│   │   ├── groups.json     # Группа Moderator
│   │   └── payments.json   # 4 тестовых платежа
│   ├── migrations/
│   ├── admin.py            # UserAdmin, PaymentAdmin
│   ├── apps.py
│   ├── managers.py         # UserManager (создание по email)
│   ├── models.py           # User (AbstractBaseUser), Payment (+ CheckConstraint)
│   ├── permissions.py      # is_moderator, IsModerator, IsNotModerator, IsOwner,
│   │                       # IsOwnerOrModerator, IsProfileOwner
│   ├── serializers.py      # UserSerializer, PaymentSerializer, CustomTokenObtainPairSerializer
│   ├── tests.py            # 30 тестов (JWT, регистрация, права, платежи)
│   ├── urls.py             # Роутер + эндпоинты JWT
│   └── views.py            # UserViewSet, PaymentViewSet
├── materials/              # Курсы, уроки, подписки
│   ├── migrations/
│   ├── admin.py            # CourseAdmin, LessonAdmin
│   ├── apps.py
│   ├── models.py           # Course, Lesson, Subscription
│   ├── paginators.py       # CustomPagination
│   ├── serializers.py      # CourseSerializer (is_subscribed), LessonSerializer
│   ├── tests.py            # 59 тестов (CRUD, права, YouTube, подписки, валидация)
│   ├── urls.py             # Роутер + Generic-классы
│   ├── validators.py       # validate_youtube_url (urlparse + белый список)
│   └── views.py            # CourseViewSet (+ subscribe), Lesson*APIView
├── config/                 # Настройки проекта
│   ├── settings.py         # PostgreSQL, DRF, JWT, django-filter, .env
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── htmlcov/                # HTML-отчёт покрытия
├── .coveragerc             # Настройки coverage
├── .env.template           # Шаблон переменных окружения
├── .gitignore
├── coverage.txt            # Текстовый отчёт покрытия
├── manage.py
├── README.md
└── requirements.txt
```

---

## 🔗 Эндпоинты

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
- `GET /api/payments/` — список
- `GET /api/payments/<id>/` — детальная
- `POST /api/payments/` — создать (только админ)
- `PUT/PATCH /api/payments/<id>/` — обновить (только админ)
- `DELETE /api/payments/<id>/` — удалить (только админ)

**Фильтры и сортировка платежей:**
- `?user=<id>`, `?course=<id>`, `?lesson=<id>`, `?payment_method=cash|transfer`
- `?ordering=payment_date` / `?ordering=-payment_date`

**Пагинация курсов и уроков:** `?page=<n>&page_size=<n>` (по умолчанию 10, максимум 50).

---

## 🗄 Модели

**Пользователи**
- `User (AbstractBaseUser)` — email (`USERNAME_FIELD`), password, phone, city, avatar, is_active, is_staff, date_joined.

**Платежи**
- `Payment` — user (FK), payment_date, course (FK, null), lesson (FK, null), amount, payment_method (cash/transfer).
- Валидация: ровно один из `course`/`lesson` (`CheckConstraint` + `clean()` + `serializer.validate()`).

**Материалы**
- `Course` — title, preview, description, video_url, owner (FK), created_at.
- `Lesson` — course (FK → Course), title, description, preview, video_url, owner (FK), created_at.
- `Subscription` — user (FK), course (FK), created_at. Пара (user, course) уникальна.

Для всех моделей заданы `Meta` (`verbose_name`, `verbose_name_plural`) и `__str__`.

---

## 🧪 Проверка через Postman

- ✅ CRUD для курсов, уроков, пользователей и платежей
- ✅ JWT: получение и обновление токенов, запросы с `Bearer`
- ✅ Права: владелец, чужой пользователь, модератор, админ
- ✅ Подписка и отписка на курс
- ✅ Фильтры `?course=`, `?lesson=`, `?payment_method=`, `?user=`
- ✅ Сортировка `?ordering=payment_date` / `-payment_date`

---

## 👨‍🌾 Об авторе

Александр **(BUMbiro)** — студент курса **Python-разработки**.
Проект создан в рамках домашних заданий по **Django REST Framework**.

**Стек:** Django · DRF · SimpleJWT · django-filter · PostgreSQL · Pillow

---

## 📝 Лицензия

Учебный проект. Не предназначен для коммерческого использования.