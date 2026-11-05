# 👨‍🌾 Фермерская академия (AgroAcademy) 🎓

**Фермерская академия** — это учебный REST API для образовательной платформы, созданный в рамках курсовой работы по 
**Django REST Framework**.  
Проект позволяет создавать курсы и уроки для фермеров и агробизнеса (ФГИС, декларации, агрономия).

---

## 🚀 Функционал

- **Пользователи** — CRUD через `ModelViewSet` (включая редактирование профиля любого пользователя).
- **Курсы** — CRUD через `ModelViewSet` (название, превью, описание, количество уроков).
- **Уроки** — CRUD через `Generic`-классы (название, описание, превью, ссылка на видео, привязка к курсу).
- **Связь** — Урок → FK → Курс (`related_name='lessons'`).
- **Сериализаторы** — `ModelSerializer` для всех моделей.
- **Пагинация** — `PageNumberPagination` (по 10 записей).

---

## 🔒 Безопасность

- **Аноним** может **читать** (GET) курсы, уроки, пользователей.
- **Авторизованный** может **создавать/редактировать/удалять** (POST, PUT, PATCH, DELETE).
- Реализовано через `IsAuthenticatedOrReadOnly` (DRF).

---

## 🧪 Тесты

В проекте **12 unit-тестов** (`APITestCase`):

- **Курсы (6 тестов):**
  - Список и детальная для анонимов (200).
  - Запрет создания для анонимов (403).
  - Создание, обновление и удаление для авторизованных (201/200/204).

- **Уроки (6 тестов):**
  - Список и детальная для анонимов (200).
  - Запрет создания для анонимов (403).
  - Создание, обновление и удаление для авторизованных (201/200/204).

**Для запуска:**

```bash
python manage.py test
```

Все тесты — **OK**.

---

## 🛠 Технологический стек

- **Python 3.12** — язык программирования.
- **Django 6.1.1** — веб-фреймворк.
- **Django REST Framework 3.18.3** — создание REST API.
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
### 7. Создайте суперпользователя (для админки):

```bash
python manage.py createsuperuser
```

>Важно: `Django` спросит `Email` (а не `username`), потому что используется кастомная модель `User` с 
>`USERNAME_FIELD = 'email'`.

### 8. Запустите сервер:
```bash
python manage.py runserver
```

**Откройте браузер (DRF Browsable API):**

### 👉 http://127.0.0.1:8000/api/courses/

---

## 📁 Структура проекта
```text
Agro_Academy/
├── users/                  # Приложение пользователей
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── managers.py         # UserManager (создание по email)
│   ├── models.py           # User (AbstractBaseUser)
│   ├── serializers.py      # UserSerializer
│   ├── tests.py
│   ├── urls.py             # Роутер для UserViewSet
│   └── views.py            # UserViewSet (ModelViewSet)
├── materials/              # Приложение курсов и уроков
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py           # Course, Lesson (FK)
│   ├── serializers.py      # CourseSerializer, LessonSerializer
│   ├── tests.py            # 7 тестов (APITestCase)
│   ├── urls.py             # Роутер + Generic-классы
│   └── views.py            # CourseViewSet, Lesson*APIView
├── config/                 # Настройки проекта
│   ├── settings.py         # PostgreSQL, DRF, .env, ALLOWED_HOSTS
│   └── urls.py
├── .env                    # Переменные (не в git)
├── .env.template           # Шаблон .env
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

**Админка:**
- `/admin/` — админка Django

---

## 🗄 Модели

**Пользователи**
- `User (AbstractBaseUser) — email (USERNAME_FIELD), password, phone, city, avatar, is_active, is_staff, date_joined.`

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

---

## 👨‍🌾 Об авторе

Александр **(BUMbiro)** — студент курса **Python-разработки**.  
Проект создан в рамках курсовой работы по **Django REST Framework**.

**Стек:** Django · DRF · PostgreSQL · Pillow

---

## 📝 Лицензия

Учебный проект. Не предназначен для коммерческого использования.