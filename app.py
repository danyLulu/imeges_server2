"""Модуль приложения для хостинга изображений."""

import http.server
import re
import logging
import json
import os
import time
from urllib.parse import urlparse, parse_qs
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor

STATIC_FILES_DIR = 'static'
UPLOAD_DIR = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
log_dir = 'logs'

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler()
    ]
)


def _resolve_db_defaults():
    """Определяет разумные значения по умолчанию для подключения к БД.

    - В контейнере Docker: host=db, port=5432
    - При локальном запуске: host=localhost, port=5433 (проброшенный порт Compose)
    Переменные окружения (DB_HOST, DB_PORT и т. д.) имеют приоритет.
    """
    running_in_container = os.path.exists('/.dockerenv') or os.environ.get('IN_DOCKER') == '1'
    default_host = 'db' if running_in_container else 'localhost'
    default_port = '5432' if running_in_container else '5433'
    return default_host, default_port


def get_db_connection(max_attempts: int = 30, delay_seconds: float = 1.0):
    """Создает соединение с PostgreSQL с ретраями ожидания готовности БД.

    max_attempts: сколько раз пробовать подключиться
    delay_seconds: задержка между попытками
    """
    default_host, default_port = _resolve_db_defaults()
    database_name = os.environ.get('DB_NAME', 'images_db')
    database_user = os.environ.get('DB_USER', 'postgres')
    database_password = os.environ.get('DB_PASSWORD', 'password')
    database_host = os.environ.get('DB_HOST', default_host)
    database_port = os.environ.get('DB_PORT', default_port)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg2.connect(
                dbname=database_name,
                user=database_user,
                password=database_password,
                host=database_host,
                port=database_port,
            )
        except Exception as e:
            last_error = e
            logging.warning(
                f"Ожидание БД (попытка {attempt}/{max_attempts}) — ошибка подключения: {e}"
            )
            time.sleep(delay_seconds)
    # Если не удалось подключиться после всех попыток — выбрасываем последнюю ошибку
    raise last_error


def init_db():
    """Создает таблицу images, если она не существует."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS images (
                        id SERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        original_name TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        file_type TEXT NOT NULL
                    );
                    """
                )
                conn.commit()
        logging.info("Инициализация БД: таблица images готова")
    except Exception as e:
        logging.error(f"Ошибка инициализации БД: {e}")


init_db()


class ImageHostingHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type='text/html'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def _get_content_type(self, file_path):
        if file_path.endswith('.html'):
            return 'text/html'
        elif file_path.endswith('.css'):
            return 'text/css'
        elif file_path.endswith('.js'):
            return 'application/javascript'
        elif file_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return 'image/' + file_path.split('.')[-1]
        else:
            return 'application/octet-stream'

    def handle_images_list(self, parsed_path):
        query = parse_qs(parsed_path.query)
        try:
            page = int(query.get('page', ['1'])[0])
            if page < 1:
                page = 1
        except Exception:
            page = 1
        per_page = 10
        offset = (page - 1) * per_page

        total = 0
        rows = []
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT COUNT(*) AS cnt FROM images")
                    total = int(cursor.fetchone()['cnt'])
                    cursor.execute(
                        """
                        SELECT id, filename, original_name, size, upload_time, file_type
                        FROM images
                        ORDER BY upload_time DESC
                        LIMIT %s OFFSET %s
                        """,
                        (per_page, offset),
                    )
                    rows = cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка при получении списка изображений: {e}")
            self._set_headers(500, 'application/json')
            self.wfile.write(json.dumps({"status": "error", "message": "Ошибка сервера"}).encode('utf-8'))
            return

        # Преобразуем datetime в строки для JSON
        for row in rows:
            if 'upload_time' in row and row['upload_time']:
                row['upload_time'] = row['upload_time'].isoformat()
            if 'size' in row:
                row['size_kb'] = int(row['size']) // 1024

        response = {
            "status": "success",
            "data": {
                "images": rows,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "has_prev": page > 1,
                    "has_next": offset + per_page < total,
                    "total_pages": (total + per_page - 1) // per_page
                }
            }
        }

        self._set_headers(200, 'application/json')
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def handle_delete(self, image_id: int):
        filename = None
        try:
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT filename FROM images WHERE id = %s", (image_id,))
                    row = cursor.fetchone()
                    if not row:
                        self._set_headers(404, 'text/html; charset=utf-8')
                        self.wfile.write("Изображение не найдено".encode('utf-8'))
                        return
                    filename = row['filename']
                    cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
                    conn.commit()
            
            if filename:
                try:
                    os.remove(os.path.join(UPLOAD_DIR, filename))
                    logging.info(f"Удалено изображение {filename} и запись id={image_id}")
                except FileNotFoundError:
                    logging.warning(f"Файл {filename} не найден на диске при удалении записи id={image_id}")
        except Exception as e:
            logging.error(f"Ошибка удаления изображения id={image_id}: {e}")
            self._set_headers(500, 'text/html; charset=utf-8')
            self.wfile.write("Ошибка сервера при удалении".encode('utf-8'))
            return

        self.send_response(303)
        self.send_header('Location', '/images-list')
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/images-list':
            self.handle_images_list(parsed_path)
            return

        # Удаление через GET (для простоты; в проде лучше POST/DELETE)
        delete_match = re.match(r'^/delete/(\d+)$', parsed_path.path)
        if delete_match:
            image_id = int(delete_match.group(1))
            self.handle_delete(image_id)
            return

        logging.warning(f"Действие: Неожиданный GET запрос: {self.path}.")
        self._set_headers(404, 'text/plain')
        self.wfile.write(b"404 Not Found")


    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path != '/upload':
            logging.warning(f"Неизвестный POST запрос на: {self.path}")
            self._set_headers(404, 'text/plain')
            self.wfile.write(b"404 Not Found")
            return
            
        # Проверка Content-Type
        content_type_header = self.headers.get('Content-Type', '')
        if not content_type_header.startswith('multipart/form-data'):
            self._send_error(400, "Ожидается multipart/form-data")
            return

        # Извлечение boundary
        try:
            boundary = content_type_header.split('boundary=')[1].encode('utf-8')
        except IndexError:
            self._send_error(400, "Boundary не найден")
            return

        # Чтение тела запроса
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > MAX_FILE_SIZE * 2:
                self._send_error(413, "Запрос слишком большой")
                return
            raw_body = self.rfile.read(content_length)
        except (TypeError, ValueError):
            self._send_error(411, "Некорректный Content-Length")
            return
        except Exception as e:
            logging.error(f"Ошибка при чтении тела запроса: {e}")
            self._send_error(500, "Ошибка при чтении запроса")
            return

        # Парсинг multipart/form-data
        file_data, filename = self._parse_multipart(raw_body, boundary)
        if not file_data or not filename:
            self._send_error(400, "Файл не найден в запросе")
            return

        # Проверка файла
        file_size = len(file_data)
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension not in ALLOWED_EXTENSIONS:
            self._send_error(400, f"Неподдерживаемый формат файла. Допустимы: {', '.join(ALLOWED_EXTENSIONS)}")
            return

        if file_size > MAX_FILE_SIZE:
            self._send_error(400, f"Файл превышает максимальный размер {MAX_FILE_SIZE / (1024 * 1024):.0f}MB")
            return

        # Сохранение файла
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        target_path = os.path.join(UPLOAD_DIR, unique_filename)

        try:
            # Сохраняем файл на диск
            with open(target_path, 'wb') as f:
                f.write(file_data)

            # Сохраняем метаданные в БД
            try:
                new_id = self._save_to_db(unique_filename, filename, file_size, file_extension)
                file_url = f"/images/{unique_filename}"
                
                logging.info(f"Изображение '{filename}' сохранено как '{unique_filename}' (id={new_id})")
                self._set_headers(200, 'application/json')
                response = {
                    "status": "success",
                    "message": "Файл успешно загружен",
                    "filename": unique_filename,
                    "url": file_url,
                    "id": new_id,
                    "original_name": filename,
                    "size": file_size,
                    "file_type": file_extension.lstrip('.')
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as db_err:
                # Откатываем сохранение файла при ошибке БД
                try:
                    os.remove(target_path)
                except Exception:
                    pass
                logging.error(f"Ошибка записи метаданных в БД: {db_err}")
                self._send_error(500, "Ошибка сохранения метаданных в БД")
        except Exception as e:
            logging.error(f"Ошибка при сохранении файла '{filename}': {e}")
            self._send_error(500, "Произошла ошибка при сохранении файла")
            
    def _send_error(self, status_code, message):
        """Вспомогательный метод для отправки ошибок в формате JSON"""
        self._set_headers(status_code, 'application/json')
        response = {"status": "error", "message": message}
        self.wfile.write(json.dumps(response).encode('utf-8'))
        
    def _parse_multipart(self, raw_body, boundary):
        """Парсинг multipart/form-data для извлечения файла"""
        parts = raw_body.split(b'--' + boundary)
        for part in parts:
            if b'Content-Disposition: form-data;' in part and b'filename=' in part:
                try:
                    headers_end = part.find(b'\r\n\r\n')
                    headers_str = part[0:headers_end].decode('utf-8')
                    
                    filename_match = re.search(r'filename="([^"]+)"', headers_str)
                    if filename_match:
                        filename = filename_match.group(1)
                        file_data = part[headers_end + 4:].strip()  # +4 для \r\n\r\n
                        return file_data, filename
                except Exception as e:
                    logging.error(f"Ошибка при парсинге части multipart: {e}")
        return None, None
        
    def _save_to_db(self, filename, original_name, size, file_extension):
        """Сохранение метаданных файла в БД"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO images (filename, original_name, size, file_type)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (filename, original_name, size, file_extension.lstrip('.')),
                )
                new_id = cursor.fetchone()[0]
                conn.commit()
                return new_id


def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port=8000):
    """Запускает сервер."""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f"Сервер запущен на порту {port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info("Сервер остановлен.")


if __name__ == '__main__':
    run_server()


    # --- Дополнительные методы класса ---
