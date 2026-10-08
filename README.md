# ⚡ Hackathon Starter

> Переиспользуемый fullstack-каркас (**FastAPI + React 19 + TypeScript + SQLite/Postgres**) для команды **Y-not-devs** на 24–48 часовых хакатонах.
> 
> **Цель:** поднять готовый рабочий скелет за 2 минуты после объявления темы хакатона и сразу сфокусироваться на ценности продукта, алгоритмах и вау-демонстрации.

---

## 🚀 Быстрый старт (всего 2 команды)

Всё настроено так, чтобы запускаться кроссплатформенно (Windows PowerShell / macOS / Linux):

```bash
# 1. Разовая установка: создаст .env, виртуальное окружение, накатит миграции и сиды, поставит npm-пакеты
npm run setup

# 2. Запуск бэкенда и фронтенда параллельно с красивыми логами:
npm run dev
```

После старта доступны:
- 🌐 **Frontend:** [http://localhost:5173](http://localhost:5173) (с проксированием всех `/api` запросов на бэкенд)
- 📚 **FastAPI Swagger Docs:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- 🩺 **Healthcheck:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

## 🛠 Технологический стек

| Слой | Технологии | Почему выбрано для хакатона |
| :--- | :--- | :--- |
| **Backend** | **Python 3.11+**, **FastAPI**, **Pydantic v2** | Мгновенная разработка API, строгая валидация, автодокументация Swagger/OpenAPI. |
| **Database** | **SQLAlchemy 2.0** + **Alembic** | По умолчанию лёгкий SQLite в файле (ноль настроек). Поддержка PostgreSQL в 1 строчку переменной `DATABASE_URL`. |
| **Frontend** | **React 19**, **TypeScript**, **Vite** | Быстрый HMR, строгая типизация контрактов бэкенда, высокая скорость рендера. |
| **Styling** | **Design Tokens & Modern CSS** | Тёмная палитра, стекломорфизм, микроанимации. Любой цвет меняется централизованно в `tokens.css`. Никаких громоздких сторонних UI-библиотек. |
| **Tooling** | **Node Scripts**, **Ruff**, **Pytest**, **Docker** | Единый запуск `npm run dev`, автолинтер кода, фикстуры с БД в памяти для тестов. |

---

## 📁 Структура проекта

Архитектура организована по принципу **Feature-Sliced / Модульность по фичам**, чтобы несколько разработчиков могли одновременно писать свои модули без merge-конфликтов:

```text
hackathon-starter/
├── .env.example              # Шаблон конфигурации (общий для бэка, фронта и докера)
├── package.json              # Корневой таск-раннер (npm run dev, npm run db:*, npm run test)
├── Dockerfile                # Multi-stage сборка: фронтенд + бэкенд в одном контейнере
├── docker-compose.yml        # Готовый запуск сервиса + опциональный PostgreSQL
├── scripts/                  # Скрипты запуска (dev, setup, миграции) на чистом Node.js
│
├── backend/
│   ├── pyproject.toml        # Зависимости Python (совместимо с uv и pip)
│   ├── alembic.ini           # Конфигурация миграций
│   ├── app/
│   │   ├── main.py           # Инициализация FastAPI, CORS, SPA-раздача
│   │   ├── api.py            # Точка сборки всех роутеров под /api
│   │   ├── seed.py           # Заполнение базы демо-данными для презентации
│   │   ├── core/             # Фундамент: config.py, db.py, errors.py, schemas.py
│   │   └── features/         # МОДУЛИ (каждый модуль изолирован):
│   │       ├── items/        # Базовый CRUD-пример (models, schemas, service, router)
│   │       ├── auth/         # JWT + bcrypt авторизация (опционально)
│   │       ├── uploads/      # Загрузка и раздача файлов до 10 МБ (опционально)
│   │       └── ai/           # Клиент к OpenAI/Groq/OpenRouter/Ollama (опционально)
│   └── tests/                # Быстрые pytest-тесты с БД в памяти
│
└── frontend/
    ├── vite.config.ts        # Настройка проксирования /api и сборки
    └── src/
        ├── App.tsx           # Корневой переключатель экранов
        ├── styles/           # tokens.css (переменные темы) и global.css
        ├── lib/              # api.ts (клиент fetch), hooks.ts (useQuery), format.ts
        ├── components/
        │   ├── ui/           # Переиспользуемые компоненты (Button, Card, Modal, Input, Badge, Toast)
        │   └── layout/       # Сайдбар, навигация, индикатор здоровья бэкенда
        └── features/         # UI-экраны фич (items, ai, uploads, auth)
```

---

## 🧩 Гайд: Как добавить новую фичу за 5 минут

Предположим, вам нужно добавить сущность **Проекты (Projects)**.

### Шаг 1. Создать модуль на бэкенде
Создайте папку `backend/app/features/projects/`:

1. **`models.py`** — SQLAlchemy модель:
   ```python
   from sqlalchemy import String, Text
   from sqlalchemy.orm import Mapped, mapped_column
   from app.core.db import Base, TimestampMixin

   class Project(TimestampMixin, Base):
       __tablename__ = "projects"
       id: Mapped[int] = mapped_column(primary_key=True)
       name: Mapped[str] = mapped_column(String(100))
       summary: Mapped[str] = mapped_column(Text, default="")
   ```

2. **`schemas.py`** — Pydantic контракты:
   ```python
   from pydantic import BaseModel

   class ProjectCreate(BaseModel):
       name: str
       summary: str = ""

   class ProjectRead(ProjectCreate):
       id: int
       class Config:
           from_attributes = True
   ```

3. **`service.py`** — Чистая бизнес-логика (не знает про HTTP):
   ```python
   from sqlalchemy.orm import Session
   from app.features.projects.models import Project
   from app.features.projects.schemas import ProjectCreate

   def create_project(db: Session, data: ProjectCreate) -> Project:
       proj = Project(**data.model_dump())
       db.add(proj)
       db.commit()
       db.refresh(proj)
       return proj
   ```

4. **`router.py`** — FastAPI эндпоинты:
   ```python
   from fastapi import APIRouter
   from app.core.db import DbSession
   from app.features.projects import service
   from app.features.projects.schemas import ProjectCreate, ProjectRead

   router = APIRouter(prefix="/projects", tags=["projects"])

   @router.post("", response_model=ProjectRead)
   def create(data: ProjectCreate, db: DbSession):
       return service.create_project(db, data)
   ```

### Шаг 2. Подключить роутер в `backend/app/api.py`
Добавьте одну строчку:
```python
from app.features.projects.router import router as projects_router
api.include_router(projects_router)
```
*(Модели подключаются в Alembic автоматически благодаря механизму `import_all_models()`!)*

### Шаг 3. Сгенерировать и накатить миграцию базы данных
```bash
npm run db:revision "add_projects_table"
npm run db:migrate
```

### Шаг 4. Делать запросы с фронтенда
```typescript
import { api } from '@/lib/api'

// Типизированный вызов:
const project = await api.post<Project>('/projects', { name: 'Super AI' })
```

---

## 🎛 Опциональные модули (включаются в `.env`)

Вам не нужно писать код авторизации или загрузки файлов с нуля — они уже готовы:

### 1. Авторизация (JWT + Bcrypt)
- В `.env`: `ENABLE_AUTH=true`
- Готовые роуты: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`
- Для защиты любого роута на бэкенде:
  ```python
  from app.features.auth.deps import CurrentUser

  @router.get("/protected")
  def secret_route(user: CurrentUser):
      return {"hello": user.email}
  ```

### 2. Загрузка файлов (Uploads)
- В `.env`: `ENABLE_UPLOADS=true`
- Готовые роуты: `POST /api/uploads` (до 10 МБ с проверкой типа), `GET /api/uploads`
- Файлы безопасно сохраняются в `./data/uploads` и раздаются напрямую через `/uploads/<file_id>`.

### 3. Интеграция с AI (OpenAI / Groq / Ollama / OpenRouter)
- В `.env`: `ENABLE_AI=true`, задайте `AI_API_KEY` и `AI_MODEL`.
- Если ключ **не задан**, модуль работает в **Mock-режиме** (фронтенд можно верстать и тестировать без расхода токенов!).
- Для вызова LLM из любой вашей бизнес-логики:
  ```python
  from app.features.ai.service import complete

  summary = complete("Сделай выжимку из текста: ...")
  ```

---

## 📜 Доступные команды (NPM Scripts)

| Команда | Описание |
| :--- | :--- |
| `npm run setup` | Полная инициализация проекта с нуля (venv, pip, alembic, seed, npm install) |
| `npm run dev` | Запуск бэкенда и фронтенда параллельно |
| `npm run dev:api` | Запуск только FastAPI сервера с горячей перезагрузкой |
| `npm run dev:web` | Запуск только Vite фронтенда |
| `npm run db:migrate` | Применить все ожидающие миграции Alembic |
| `npm run db:revision -- "desc"` | Сгенерировать новую миграцию на основе измененных моделей |
| `npm run db:seed` | Заполнить базу демо-данными (`app/seed.py`) |
| `npm run db:reset` | Сбросить базу, накатить миграции и сиды заново |
| `npm run test` | Запуск тестов бэкенда через Pytest |
| `npm run lint` | Проверка кода линтером Ruff и проверка типов TypeScript |
| `npm run format` | Автоформатирование кода (Ruff) |
| `npm run build` | Продакшн-сборка фронтенда |

---

## 🐳 Запуск через Docker

Для демонстрации проекта жюри или быстрого деплоя на виртуальный сервер:

```bash
docker compose up --build
```
Единый контейнер соберет фронтенд и поднимет FastAPI, раздавая всё на порту `8000`.

---

## 💡 Чек-лист перед презентацией на хакатоне
- [ ] Отредактируйте `backend/app/seed.py`: добавьте яркие, реалистичные демо-данные под тему кейса.
- [ ] Запустите `npm run db:seed`.
- [ ] Настройте название проекта в `APP_NAME` в файле `.env`.
- [ ] Подготовьте сценарий клика по интерфейсу на 2–3 минуты.
- [ ] Держите открытой вкладку с `/api/docs` для демонстрации бэкенд-архитектуры жюри.
