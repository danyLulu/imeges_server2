# Multi-stage build для оптимизации размера образа
FROM python:3.12-slim AS builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.12-slim

# Установка только runtime зависимостей
RUN apt-get update && apt-get install -y \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создаем пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Копируем установленные пакеты из builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Копируем код приложения
COPY app.py .
COPY static/ ./static/

# Создаем необходимые директории
RUN mkdir -p images logs && \
    chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Добавляем локальные пакеты в PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Проверяем установку зависимостей
RUN python -c "import PIL; print('Pillow installed successfully')"

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["python", "app.py"]