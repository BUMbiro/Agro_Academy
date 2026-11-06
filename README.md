# 👨‍🌾 Фермерская академия (AgroAcademy) 🎓

**Фермерская академия** — это учебный REST API для образовательной платформы, созданный в рамках домашних 
заданий по **Django REST Framework**.  
Проект позволяет создавать курсы и уроки для фермеров и агробизнеса (ФГИС, декларации, агрономия).

---

## 🚀 Функционал

- **Пользователи** — CRUD через `ModelViewSet` (включая редактирование профиля любого пользователя).
- **Курсы** — CRUD через `ModelViewSet` (название, превью, описание, количество уроков).
- **Уроки** — CRUD через `Generic`-классы (название, описание, превью, ссылка на видео, привязка к курсу).
- **Платежи** — CRUD через `ModelViewSet` (пользователь, дата, курс/урок, сумма, способ оплаты).
- **Связь** — Урок → FK → Курс (`related_name='lessons'`), Платёж → FK → Пользователь/Курс/Урок.
- **Сериализаторы** — `ModelSerializer` для всех моделей, `SerializerMethodField` для подсчёта уроков и платежей.
- **Пагинация** — `PageNumberPagination` (по 10 записей).
- **Фильтрация** — `DjangoFilterBackend` (по курсу, уроку, способу оплаты).
- **Сортировка** — `OrderingFilter` (по дате оплаты, asc/desc).

---

## 🔒 Безопасность

- **Аноним** может **читать** (GET) курсы, уроки, пользователей, платежи.
- **Авторизованный** может **создавать/редактировать/удалять** (POST, PUT, PATCH, DELETE).
- Реализовано через `IsAuthenticatedOrReadOnly` (DRF).

---

## 🧪 Тесты

В проекте **30 unit-тестов** (`APITestCase`):

**Курсы (6 тестов):**
- Список и детальная для анонимов (200).
- Запрет создания для анонимов (403).
- Создание, обновление и удаление для авторизованных (201/200/204).

**Сериализатор курса (3 теста):**
- `lessons_count` возвращает корректное число (`SerializerMethodField`).
- Вложенный `LessonSerializer` отдаёт список уроков курса.
- Курс без уроков: `lessons_count=0`, `lessons=[]`.

**Уроки (6 тестов):**
- Список и детальная для анонимов (200).
- Запрет создания для анонимов (403).
- Создание, обновление и удаление для авторизованных (201/200/204).

**Платежи (11 тестов):**
- Список для анонимов (200), запрет создания (403).
- CRUD для авторизованных (201/200/204).
- Фильтр по курсу (`?course=<id>`).
- Фильтр по уроку (`?lesson=<id>`).
- Фильтр по способу оплаты (`?payment_method=cash`).
- Сортировка по дате: asc (`?ordering=payment_date`) и desc (`?ordering=-payment_date`).

**Пользователи (3 теста):**
- Список для анонимов (200).
- Запрет создания для анонимов (403).
- Детальная с `payments` и `payments_count`.

**История платежей (1 тест):**
- `UserSerializer` отдаёт `payments` и `payments_count` (доп. задание*).

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
python manage.py loaddata payments
```
Фикстура лежит в `users/fixtures/payments.json` — 4 платежа (курсы, уроки, разные способы оплаты).

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
│   │   └── payments.json   # Фикстура платежей (4 записи)
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_payment.py
│   │   └── 0003_alter_user_options.py
│   ├── admin.py            # UserAdmin, PaymentAdmin
│   ├── apps.py
│   ├── managers.py         # UserManager (создание по email)
│   ├── models.py           # User (AbstractBaseUser), Payment
│   ├── serializers.py      # UserSerializer, PaymentSerializer
│   ├── tests.py            # 15 тестов (12 Payment + 3 UserViewSet)
│   ├── urls.py             # Роутер для UserViewSet, PaymentViewSet
│   └── views.py            # UserViewSet, PaymentViewSet
├── materials/              # Приложение курсов и уроков
│   ├── migrations/
│   │   └── 0001_initial.py
│   ├── admin.py            # CourseAdmin, LessonAdmin
│   ├── apps.py
│   ├── models.py           # Course, Lesson (FK)
│   ├── serializers.py      # CourseSerializer, LessonSerializer
│   ├── tests.py            # 15 тестов (6 Course + 6 Lesson + 3 Serializer)
│   ├── urls.py             # Роутер + Generic-классы
│   └── views.py            # CourseViewSet, Lesson*APIView
├── config/                 # Настройки проекта
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py         # PostgreSQL, DRF, django-filter, .env
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

**Курсы (CourseViewSet):**
- `GET /api/courses/` — список
- `POST /api/courses/` — создать
- `GET /api/courses/<id>/` — детальная
- `PUT/PATCH /api/courses/<id>/` — обновить
- `DELETE /api/courses/<id>/` — удалить

**Уроки (Generic):**
- `GET /api/lessons/` — список
- `POST /api/lessons/create/` — создать
- `GET /api/lessons/<id>/` — детальная
- `PUT/PATCH /api/lessons/<id>/update/` — обновить
- `DELETE /api/lessons/<id>/delete/` — удалить

**Пользователи (UserViewSet):**
- `GET /api/users/` — список
- `POST /api/users/` — создать
- `GET /api/users/<id>/` — детальная
- `PUT/PATCH /api/users/<id>/` — обновить профиль
- `DELETE /api/users/<id>/` — удалить

**Платежи (PaymentViewSet):**
- `GET /api/payments/` — список
- `POST /api/payments/` — создать
- `GET /api/payments/<id>/` — детальная
- `PUT/PATCH /api/payments/<id>/` — обновить
- `DELETE /api/payments/<id>/` — удалить

**Фильтры для платежей:**
- `?course=<id>` — по курсу
- `?lesson=<id>` — по уроку
- `?payment_method=cash|transfer` — по способу оплаты
- `?ordering=payment_date` — сортировка по возрастанию
- `?ordering=-payment_date` — сортировка по убыванию

**Админка:**
- `/admin/` — админка Django

---

## 🗄 Модели

**Пользователи**
- `User (AbstractBaseUser) — email (USERNAME_FIELD), password, phone, city, avatar, is_active, is_staff, date_joined.`

**Платежи**
- `Payment — user (FK), payment_date, course (FK, null), lesson (FK, null), amount, payment_method (cash/transfer).`

**Материалы**
- `Course — title, preview, description, created_at.`
- `Lesson — course (FK → Course), title, description, preview, video_url, created_at.`

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