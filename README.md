# 👨‍🌾 Фермерская академия (AgroAcademy) 🎓

**Фермерская академия** — это учебный REST API для образовательной платформы, созданный в рамках домашних 
заданий по **Django REST Framework**.  
Проект позволяет создавать курсы и уроки для фермеров и агробизнеса (ФГИС, декларации, агрономия).

---

## 🚀 Функционал

- **Пользователи** — CRUD через `ModelViewSet`, регистрация, редактирование профиля.
- **Курсы** — CRUD через `ModelViewSet` (включая количество уроков и вложенный список).
- **Уроки** — CRUD через `Generic`-классы (привязка к курсу, ссылка на видео).
- **Платежи** — CRUD через `ModelViewSet` (фильтрация, сортировка, валидация).
- **JWT-авторизация** — получение и обновление токенов (`access`/`refresh`).
- **Роли** — модераторы (редактируют всё, но не создают/удаляют) и владельцы (управляют только своими объектами).
- **Связи** — Урок → FK → Курс (`related_name='lessons'`), Платёж → FK → Пользователь/Курс/Урок. Курсы и уроки имеют
владельца (`owner`).
- **Оптимизация** — `select_related` и `prefetch_related` для избежания N+1 запросов.
- **Сериализаторы** — `ModelSerializer` для всех моделей, `SerializerMethodField` для подсчёта уроков и платежей.
- **Пагинация** — `PageNumberPagination` (по 10 записей).
- **Фильтрация** — `DjangoFilterBackend` (по курсу, уроку, способу оплаты).
- **Сортировка** — `OrderingFilter` (по дате оплаты, asc/desc).

---

## 🔒 Безопасность

- **Аноним** может **читать** (GET) курсы, уроки, пользователей, платежи.
- **Регистрация** и **получение токенов** доступны без авторизации.
- **Создание/удаление курсов и уроков** — только авторизованные пользователи (НЕ модераторы).
- **Редактирование курсов и уроков** — модератор ИЛИ владелец объекта.
- **Удаление пользователей** и **управление платежами** — только админ (`is_staff`).
- **Профиль пользователя** — любой авторизованный может смотреть чужой профиль, но редактировать только свой. 
При просмотре чужого профиля история платежей скрыта (доп. задание*).

---

## 🧪 Тесты

В проекте **52 unit-теста** (`APITestCase`), покрывающих:
- Базовый CRUD для всех сущностей.
- Права доступа (аноним, авторизованный, модератор, владелец, админ).
- Валидацию платежей (ровно один из course/lesson).
- Фильтрацию и сортировку.
- JWT-аутентификацию и регистрацию.
- Скрытие истории платежей для чужих профилей.

**Для запуска:**

```bash
python manage.py test
```

Все тесты — **OK**.

---

## 🛠 Технологический стек

- **Python 3.12** — язык программирования.
- **Django 6.1.3** — веб-фреймворк.
- **Django REST Framework 3.18.3** — создание `REST API`.
- **djangorestframework-simplejwt 5.5.1** — JWT-авторизация.
- **django-filter 25.2** — фильтрация `queryset`.
- **PostgreSQL 17** — база данных (через `psycopg2-binary`).
- **Pillow** — работа с изображениями (превью, аватары).
- **python-dotenv** — чтение `.env` (свой парсер в `settings.py`).

---

## 📦 Установка и запуск

### 1. Клонируйте репозиторий:

```bash
git clone https://github.com/BUMbiro/Agro_Academy.git
cd Agro_Academy
```

### 2. Создайте и активируйте виртуальное окружение:
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 3. Установите зависимости:
```bash
pip install -r requirements.txt
```

### 4. Создайте базу данных PostgreSQL

**В psql под суперпользователем postgres:**

```sql
CREATE USER agro_academy_user WITH PASSWORD 'ваш_пароль';
ALTER USER agro_academy_user CREATEDB;
CREATE DATABASE agro_academy WITH OWNER = agro_academy_user ENCODING = 'UTF8';
```

### 5. Настройте переменные окружения

**Скопируйте .env.template в .env и заполните:**

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

>.env добавлен в .gitignore — реальные пароли в репозиторий не попадают.
>В .env.template только заглушки.

### 6. Выполните миграции:

```bash
python manage.py migrate
```

### 7. Загрузите фикстуру платежей:

```bash
python manage.py loaddata groups
python manage.py loaddata payments
```
Фикстура groups.json создаёт группу Moderator (для модераторов).

Фикстура payments.json создаёт 4 платежа (требует наличия пользователей, курсов и уроков с указанными ID).

### 8. Создайте суперпользователя (для админки):

```bash
python manage.py createsuperuser
```

>Важно: `Django` спросит `Email` (а не `username`), потому что используется кастомная модель `User` с 
>`USERNAME_FIELD = 'email'`.

### 9. Запустите сервер:
```bash
python manage.py runserver
```

**Откройте браузер (DRF Browsable API):**

### 👉 http://127.0.0.1:8000/api/courses/

---

## 📁 Структура проекта
```text
Agro_Academy/
├── users/                  # Приложение пользователей и платежей
│   ├── fixtures/
│   │   ├── groups.json     # Фикстура группы Moderator
│   │   └── payments.json   # Фикстура платежей (4 записи)
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_payment.py
│   │   ├── 0003_alter_user_options.py
│   │   └── 0004_payment_payment_course_xor_lesson.py
│   ├── admin.py            # UserAdmin, PaymentAdmin
│   ├── apps.py
│   ├── managers.py         # UserManager (создание по email)
│   ├── models.py           # User (AbstractBaseUser), Payment (+ валидация)
│   ├── permissions.py      # IsModerator, IsOwner, IsNotModerator, IsProfileOwner
│   ├── serializers.py      # UserSerializer, PaymentSerializer, CustomToken...
│   ├── tests.py            # 34 теста (JWT, регистрация, права, платежи)
│   ├── urls.py             # Роутер + эндпоинты JWT
│   └── views.py            # UserViewSet, PaymentViewSet (+ permissions)
├── materials/              # Приложение курсов и уроков
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── 0002_course_owner_lesson_owner.py
│   ├── admin.py            # CourseAdmin, LessonAdmin
│   ├── apps.py
│   ├── models.py           # Course, Lesson (FK, owner)
│   ├── serializers.py      # CourseSerializer, LessonSerializer
│   ├── tests.py            # 18 тестов (права модераторов и владельцев)
│   ├── urls.py             # Роутер + Generic-классы
│   └── views.py            # CourseViewSet, Lesson*APIView
├── config/                 # Настройки проекта
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py         # PostgreSQL, DRF, JWT, django-filter, .env
│   ├── urls.py
│   └── wsgi.py
├── .env                    # Переменные (не в git)
├── .env.template           # Шаблон .env
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

---

## 🔗 Эндпоинты

### Авторизация
- `POST /api/token/` — получить `access` и `refresh` токены (email + password).
- `POST /api/token/refresh/` — обновить `access` токен.

### Пользователи
- `GET /api/users/` — список
- `POST /api/users/` — регистрация (доступно анонимам)
- `GET /api/users/<id>/` — детальная
- `PUT/PATCH /api/users/<id>/` — обновить (только свой профиль)
- `DELETE /api/users/<id>/` — удалить (только админ)

### Курсы
- `GET /api/courses/` — список
- `POST /api/courses/` — создать (не модератор)
- `GET /api/courses/<id>/` — детальная
- `PUT/PATCH /api/courses/<id>/` — обновить (модератор или владелец)
- `DELETE /api/courses/<id>/` — удалить (только владелец, не модератор)

### Уроки
- `GET /api/lessons/` — список
- `POST /api/lessons/create/` — создать (не модератор)
- `GET /api/lessons/<id>/` — детальная
- `PUT/PATCH /api/lessons/<id>/update/` — обновить (модератор или владелец)
- `DELETE /api/lessons/<id>/delete/` — удалить (только владелец, не модератор)

### Платежи
- `GET /api/payments/` — список
- `POST /api/payments/` — создать (только админ)
- `GET /api/payments/<id>/` — детальная
- `PUT/PATCH /api/payments/<id>/` — обновить (только админ)
- `DELETE /api/payments/<id>/` — удалить (только админ)

**Фильтры для платежей:**
- `?user=<id>`, `?course=<id>`, `?lesson=<id>`, `?payment_method=cash|transfer`
- `?ordering=payment_date` / `?ordering=-payment_date`

---

## 🗄 Модели

**Пользователи**
- `User (AbstractBaseUser) — email (USERNAME_FIELD), password, phone, city, avatar, is_active, is_staff, date_joined.`

**Платежи**
- `Payment — user (FK), payment_date, course (FK, null), lesson (FK, null), amount, payment_method (cash/transfer).`
- Валидация: ровно один из `course/lesson` (`CheckConstraint + clean()` + `serializer.validate()`).

**Материалы**
- `Course — title, preview, description, owner (FK), created_at.`
- `Lesson — course (FK → Course), title, description, preview, video_url, owner (FK), created_at.`

Для всех моделей заданы `Meta` (`verbose_name`, `verbose_name_plural`) и метод `__str__`.

---

## 🧪 Проверка через Postman

Все эндпоинты проверены через **Postman**:
- ✅ GET, POST, PUT/PATCH, DELETE для курсов.
- ✅ GET, POST, PUT/PATCH, DELETE для уроков.
- ✅ GET, POST, PUT/PATCH, DELETE для пользователей.
- ✅ GET, POST, PUT/PATCH, DELETE для платежей.
- ✅ Фильтры: `?course=`, `?lesson=`, `?payment_method=`.
- ✅ Сортировка: `?ordering=payment_date`, `?ordering=-payment_date`.

---

## 👨‍🌾 Об авторе

Александр **(BUMbiro)** — студент курса **Python-разработки**.  
Проект создан в рамках домашних заданий по **Django REST Framework**.

**Стек:** Django · DRF · django-filter · PostgreSQL · Pillow

---

## 📝 Лицензия

Учебный проект. Не предназначен для коммерческого использования.