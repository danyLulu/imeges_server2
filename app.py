"""Основной модуль приложения."""

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
            self._set_headers(500, 'text/html; charset=utf-8')
            self.wfile.write("<h1>Ошибка сервера</h1>".encode('utf-8'))
            return

        has_prev = page > 1
        has_next = offset + per_page < total

        html = [
            "<!DOCTYPE html>",
            "<html lang=\"ru\">",
            "<head>",
            "<meta charset=\"UTF-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            "<title>Список изображений</title>",
            "<link rel=\"stylesheet\" href=\"/style.css\">",
            "</head>",
            "<body>",
            "<div style=\"max-width:1000px;margin:20px auto;padding:16px;background:#fff;border-radius:8px;\">",
            "<h1 style=\"margin-bottom:16px;\">Список изображений</h1>",
            ("<p>Нет загруженных изображений</p>" if total == 0 else
             "<table style=\"width:100%;border-collapse:collapse;\">"
             "<thead><tr>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\">Имя файла</th>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\">Оригинальное имя</th>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\">Размер (КБ)</th>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\">Дата загрузки</th>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\">Тип</th>"
             "<th style=\"text-align:left;border-bottom:1px solid #dee2e6;padding:8px;\"></th>"
             "</tr></thead><tbody>")
        ]

        for r in rows:
            html.append(
                f"<tr>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\"><a href=\"/images/{r['filename']}\" target=\"_blank\">{r['filename']}</a></td>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\">{r['original_name']}</td>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\">{int(r['size']) // 1024}</td>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\">{r['upload_time']}</td>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\">{r['file_type']}</td>"
                f"<td style=\"padding:8px;border-bottom:1px solid #f1f1f1;\">"
                f"<a href=\"/delete/{r['id']}\" style=\"color:#dc3545;\" onclick=\"return confirm('Удалить изображение?');\">Удалить</a>"
                f"</td>"
                f"</tr>"
            )

        if total > 0:
            html.append("</tbody></table>")

        # Навигация
        nav = ["<div style=\"margin-top:16px;display:flex;gap:8px;\">"]
        if has_prev:
            nav.append(f"<a href=\"/images-list?page={page-1}\" style=\"padding:8px 12px;border:1px solid #dee2e6;border-radius:4px;text-decoration:none;\">Предыдущая страница</a>")
        else:
            nav.append("<span style=\"padding:8px 12px;color:#6c757d;border:1px solid #eee;border-radius:4px;\">Предыдущая страница</span>")
        if has_next:
            nav.append(f"<a href=\"/images-list?page={page+1}\" style=\"padding:8px 12px;border:1px solid #dee2e6;border-radius:4px;text-decoration:none;\">Следующая страница</a>")
        else:
            nav.append("<span style=\"padding:8px 12px;color:#6c757d;border:1px solid #eee;border-radius:4px;\">Следующая страница</span>")
        nav.append("</div>")
        html.extend(nav)
        html.append("</div></body></html>")

        self._set_headers(200, 'text/html; charset=utf-8')
        self.wfile.write("".join(html).encode('utf-8'))

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
            # Удаляем файл с диска
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

        # Редирект обратно на список
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
        if parsed_path.path == '/upload':
            # 1. Получаем заголовок Content-Type
            content_type_header = self.headers.get('Content-Type')
            if not content_type_header or not content_type_header.startswith('multipart/form-data'):
                logging.warning("Действие: Ошибка загрузки - некорректный Content-Type.")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Ожидается multipart/form-data."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 2. Извлекаем boundary из Content-Type
            try:
                boundary = content_type_header.split('boundary=')[1].encode('utf-8')
            except IndexError:
                logging.warning("Действие: Ошибка загрузки - boundary не найден в Content-Type.")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Boundary не найден."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 3. Читаем тело запроса
            try:
                content_length = int(self.headers['Content-Length'])
                if content_length > MAX_FILE_SIZE * 2:  # Небольшой запас на служебную информацию multipart
                    logging.warning(
                        f"Действие: Ошибка загрузки - запрос превышает максимальный размер ({content_length} байт).")
                    self._set_headers(413, 'application/json')  # Payload Too Large
                    response = {"status": "error", "message": f"Запрос слишком большой."}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return

                raw_body = self.rfile.read(content_length)
            except (TypeError, ValueError):
                logging.error("Ошибка: Некорректный Content-Length.")
                self._set_headers(411, 'application/json')  # Length Required
                response = {"status": "error", "message": "Некорректный Content-Length."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            except Exception as e:
                logging.error(f"Ошибка при чтении тела запроса: {e}")
                self._set_headers(500, 'application/json')
                response = {"status": "error", "message": "Ошибка при чтении запроса."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 4. Парсим multipart/form-data (упрощенно, только для одного файла)
            parts = raw_body.split(b'--' + boundary)
            file_data = None
            filename = None

            for part in parts:
                if b'Content-Disposition: form-data;' in part and b'filename=' in part:
                    try:
                        headers_end = part.find(b'\r\n\r\n')
                        headers_str = part[0:headers_end].decode('utf-8')

                        # Извлекаем имя файла
                        filename_match = re.search(r'filename="([^"]+)"', headers_str)
                        if filename_match:
                            filename = filename_match.group(1)

                        # Извлекаем данные файла
                        file_data = part[headers_end + 4:].strip()  # +4 для \r\n\r\n
                        break
                    except Exception as e:
                        logging.error(f"Ошибка при парсинге части multipart: {e}")
                        continue

            if not file_data or not filename:
                logging.warning(f"Действие: Ошибка загрузки - файл не найден в multipart-запросе.")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Файл не найден в запросе."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # Теперь у нас есть filename (строка) и file_data (bytes)
            # 5. Проверки файла
            file_size = len(file_data)
            file_extension = os.path.splitext(filename)[1].lower()

            if file_extension not in ALLOWED_EXTENSIONS:
                logging.warning(f"Действие: Ошибка загрузки - неподдерживаемый формат файла ({filename})")
                self._set_headers(400, 'application/json')
                response = {"status": "error",
                            "message": f"Неподдерживаемый формат файла. Допустимы: {', '.join(ALLOWED_EXTENSIONS)}"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            if file_size > MAX_FILE_SIZE:
                logging.warning(
                    f"Действие: Ошибка загрузки - файл превышает максимальный размер ({filename}, {file_size} байт)")
                self._set_headers(400, 'application/json')
                response = {"status": "error",
                            "message": f"Файл превышает максимальный размер {MAX_FILE_SIZE / (1024 * 1024):.0f}MB."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 6. Сохранение файла
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            target_path = os.path.join(UPLOAD_DIR, unique_filename)

            try:
                # Сначала сохраняем файл на диск
                with open(target_path, 'wb') as f:
                    f.write(file_data)

                # Затем сохраняем метаданные в БД
                try:
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO images (filename, original_name, size, file_type)
                                VALUES (%s, %s, %s, %s)
                                RETURNING id
                                """,
                                (unique_filename, filename, file_size, file_extension.lstrip('.')),
                            )
                            new_id = cursor.fetchone()[0]
                            conn.commit()
                    file_url = f"/images/{unique_filename}"
                    logging.info(
                        f"Действие: Изображение '{filename}' (сохранено как '{unique_filename}') и метаданные записаны в БД (id={new_id}).")
                    self._set_headers(200, 'application/json')
                    response = {
                        "status": "success",
                        "message": "Файл успешно загружен.",
                        "filename": unique_filename,
                        "url": file_url,
                        "id": new_id,
                        "original_name": filename,
                        "size": file_size,
                        "file_type": file_extension.lstrip('.')
                    }
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                except Exception as db_err:
                    # Откатываем сохранение файла, если БД не записалась
                    try:
                        os.remove(target_path)
                    except Exception:
                        pass
                    logging.error(f"Ошибка записи метаданных в БД: {db_err}")
                    self._set_headers(500, 'application/json')
                    response = {"status": "error", "message": "Ошибка сохранения метаданных в БД."}
                    self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                logging.error(f"Ошибка при сохранении файла '{filename}' в '{target_path}': {e}")
                self._set_headers(500, 'application/json')
                response = {"status": "error", "message": "Произошла ошибка при сохранении файла."}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            # Если POST запрос пришел не на /upload, то это неизвестный путь
            logging.warning(f"Действие: Неизвестный POST запрос на: {self.path}")
            self._set_headers(404, 'text/plain')
            self.wfile.write(b"404 Not Found")


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
