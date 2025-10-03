# 🖼️ Image Hosting Service

Современный сервис для хостинга изображений, построенный на Python и Nginx с использованием Docker.

## 🚀 Возможности

- **Загрузка изображений** с поддержкой форматов JPG, PNG, GIF
- **Быстрая раздача** статических файлов через Nginx
- **Валидация файлов** по размеру (максимум 5 МБ) и формату
- **Безопасность** - защита от загрузки вредоносных файлов
- **Логирование** всех операций в файл
- **Контейнеризация** с Docker и Docker Compose
- **Автоматический перезапуск** при сбоях
- **Health checks** для мониторинга состояния

## 📋 Требования

- Docker 20.10+
- Docker Compose 2.0+
- 2 ГБ свободного места на диске

## 🛠️ Установка и запуск

### Быстрый старт

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd images-server3
# Запустите проект одной командой
docker compose up --build
```

### Доступ к сервису

- **Главная страница**: http://localhost:8080
- **Прямой доступ к бэкенду**: http://localhost:8000
- **Изображения**: http://localhost:8080/images/<имя_файла>

## 📁 Структура проекта

```
project/
├── app.py                # Python-бэкенд
├── requirements.txt      # Зависимости Python
├── Dockerfile            # Dockerfile для бэкенда
├── docker-compose.yml    # Конфигурация Docker Compose
├── nginx.conf            # Конфигурация Nginx
├── images/               # Папка для загруженных изображений (volume)
├── logs/                 # Папка для логов (volume)
└── static/               # Статические файлы (CSS/JS)
```

## 🔧 API

### POST /upload

Загрузка изображения.

**Параметры:**
- `file` (multipart/form-data) - файл изображения

**Ответ при успехе:**
```json
{
  "status": "success",
  "message": "Файл успешно загружен",
  "filename": "unique_filename.jpg",
  "url": "/images/unique_filename.jpg",
  "processing_time": "0.15с"
}
```

**Ответ при ошибке:**
```json
{
  "status": "error",
  "message": "Описание ошибки"
}
```

### GET /

Главная страница с интерфейсом загрузки.

## 🛡️ Безопасность

- **Валидация файлов**: только JPG, PNG, GIF
- **Ограничение размера**: максимум 5 МБ
- **Защита от вредоносных файлов**: проверка расширений
- **Безопасный доступ**: только через Nginx
- **Непривилегированный пользователь** в контейнере

## 📊 Производительность

- **Многозадачность**: до 10 одновременных загрузок
- **Скорость загрузки**: менее 1 секунды для файлов до 5 МБ
- **Раздача изображений**: менее 100 мс через Nginx
- **Кэширование**: статические файлы кэшируются на 1 год
- **Сжатие**: gzip для текстовых файлов

## 📝 Логирование

Логи сохраняются в файл `logs/app.log` в формате:
```
[2025-01-24 14:00:00] INFO: Успех: Изображение 'photo.jpg' загружено за 0.15с
[2025-01-24 14:01:00] WARNING: Ошибка загрузки - файл превышает максимальный размер
```

## 🔄 Управление сервисом

```bash
# Запуск
docker compose up -d

# Остановка
docker compose down

# Просмотр логов
docker compose logs -f

# Пересборка
docker compose up --build

# Очистка volumes (удаляет все загруженные изображения и логи)
docker compose down -v
```

## 🐛 Отладка

### Проверка состояния контейнеров
```bash
docker compose ps
```

### Просмотр логов конкретного сервиса
```bash
# Логи бэкенда
docker compose logs app

# Логи Nginx
docker compose logs nginx
```

### Вход в контейнер
```bash
# В контейнер бэкенда
docker compose exec app bash

# В контейнер Nginx
docker compose exec nginx sh
```

## 📈 Мониторинг

Сервис включает health checks:
- **Бэкенд**: проверка доступности на порту 8000
- **Nginx**: проверка доступности на порту 80

## 🔧 Настройка

### Изменение максимального размера файла

В файле `app.py` измените константу:
```python
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ
```

### Добавление новых форматов

В файле `app.py` обновите список:
```python
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
```

## 🚀 Развертывание в продакшене

1. Настройте reverse proxy (например, Traefik)
2. Используйте SSL сертификаты
3. Настройте мониторинг (Prometheus + Grafana)
4. Настройте резервное копирование volumes
5. Используйте внешние volumes для данных

## 📄 Лицензия

MIT License

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs`
2. Убедитесь, что порты 8000 и 8080 свободны

Проект создан при помощи JavaRush school 
 
## 🗄️ База данных и SQL (PostgreSQL)

### Параметры подключения

- **СУБД**: PostgreSQL 16
- **База**: `images_db`
- **Пользователь**: `postgres`
- **Пароль**: `password`
- **Хост (в контейнерах)**: `db:5432`
- **Хост (с хоста)**: `localhost:5433`

Эти значения можно переопределить переменными окружения в `docker-compose.yml`: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

### Подключение к БД

- С хост-машины (нужен установленный `psql`):
```bash
psql -h localhost -p 5433 -U postgres -d images_db
```

- Из контейнера БД:
```bash
docker compose exec -e PGPASSWORD=password db psql -U postgres -d images_db
```

### Инициализация схемы

Схема создаётся автоматически приложением при старте. Для ручного запуска выполните:
```sql
CREATE TABLE IF NOT EXISTS images (
  id SERIAL PRIMARY KEY,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  size INTEGER NOT NULL,
  upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  file_type TEXT NOT NULL
);
```

Рекомендуемые индексы (опционально для ускорения сортировки и поиска):
```sql
CREATE INDEX IF NOT EXISTS idx_images_upload_time ON images (upload_time DESC);
CREATE INDEX IF NOT EXISTS idx_images_file_type ON images (file_type);
```

### Часто используемые SQL-запросы

- Вставка метаданных изображения:
```sql
INSERT INTO images (filename, original_name, size, file_type)
VALUES ('<generated>.png', 'source.png', 123456, 'png')
RETURNING id;
```

- Список с пагинацией (10 на страницу):
```sql
-- page = 1 -> OFFSET 0, page = 2 -> OFFSET 10 и т.д.
SELECT id, filename, original_name, size, upload_time, file_type
FROM images
ORDER BY upload_time DESC
LIMIT 10 OFFSET 0;
```

- Подсчёт общего количества:
```sql
SELECT COUNT(*) AS cnt FROM images;
```

- Удаление по `id`:
```sql
DELETE FROM images WHERE id = $1; -- подставьте нужный id
```

### Резервное копирование и восстановление

- Бэкап в файл на хосте (stdout из контейнера БД перенаправляем в файл):
```bash
docker compose exec db pg_dump -U postgres -d images_db > backups/backup_$(date +%F_%H-%M-%S).sql
```

- Восстановление из файла на хосте:
```bash
cat backups/backup_YYYY-MM-DD_HH-MM-SS.sql | docker compose exec -T db psql -U postgres -d images_db
```

- Бэкап конкретной таблицы:
```bash
docker compose exec db pg_dump -U postgres -d images_db -t images > backups/images_$(date +%F_%H-%M-%S).sql
```

### Обслуживание

- Просмотр активных подключений:
```sql
SELECT pid, usename, application_name, state, query
FROM pg_stat_activity
ORDER BY state;
```

- Анализ и актуализация статистики:
```sql
ANALYZE;
```

- Очистка свободного места (в простых сценариях):
```sql
VACUUM;
```

Примечание: команды `VACUUM FULL` и т.п. выполняйте осознанно, так как они могут блокировать таблицы.