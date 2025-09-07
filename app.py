"""Основной модуль приложения для хостинга изображений."""

import http.server
import re
import logging
import json
import os
import time
from urllib.parse import urlparse
import uuid
from datetime import datetime

# Конфигурация приложения
STATIC_FILES_DIR = 'static'
UPLOAD_DIR = 'images'
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
LOG_DIR = 'logs'

# Создаем необходимые директории
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'app.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


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

    def do_GET(self):
        """Обработка GET запросов."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            # Главная страница
            self._handle_home_page()
        elif parsed_path.path.startswith('/images/'):
            # Запросы к изображениям должны обрабатываться Nginx
            logger.warning(f"Неожиданный запрос к изображению: {self.path}. Должен обрабатываться Nginx.")
            self._set_headers(404, 'text/plain')
            self.wfile.write(b"404 Not Found - Images should be served by Nginx")
        else:
            # Другие GET запросы
            logger.warning(f"Неожиданный GET запрос: {self.path}")
            self._set_headers(404, 'text/plain')
            self.wfile.write(b"404 Not Found")

    def _handle_home_page(self):
        """Обработка главной страницы."""
        try:
            # Читаем статический HTML файл
            static_file_path = os.path.join(STATIC_FILES_DIR, 'index.html')
            if os.path.exists(static_file_path):
                with open(static_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._set_headers(200, 'text/html')
                self.wfile.write(content.encode('utf-8'))
                logger.info("Главная страница успешно загружена")
            else:
                # Если файл не найден, возвращаем простую HTML страницу
                html_content = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Hosting Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 600px; margin: 0 auto; }
        .upload-area { border: 2px dashed #ccc; padding: 20px; text-align: center; margin: 20px 0; }
        .upload-area:hover { border-color: #999; }
        #fileInput { margin: 10px 0; }
        #uploadBtn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        #uploadBtn:hover { background: #0056b3; }
        #result { margin: 20px 0; padding: 10px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖼️ Image Hosting Service</h1>
        <p>Загрузите изображение для получения ссылки на него.</p>
        
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <p>Нажмите для выбора файла или перетащите изображение сюда</p>
            <input type="file" id="fileInput" accept=".jpg,.jpeg,.png,.gif" style="display: none;">
        </div>
        
        <button id="uploadBtn" onclick="uploadFile()" disabled>Загрузить</button>
        
        <div id="result"></div>
        
        <h3>Поддерживаемые форматы:</h3>
        <ul>
            <li>JPG/JPEG</li>
            <li>PNG</li>
            <li>GIF</li>
        </ul>
        <p><strong>Максимальный размер файла:</strong> 5 МБ</p>
    </div>

    <script>
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const result = document.getElementById('result');

        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                uploadBtn.disabled = false;
                result.innerHTML = `<p>Выбран файл: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} МБ)</p>`;
            }
        });

        async function uploadFile() {
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                uploadBtn.disabled = true;
                uploadBtn.textContent = 'Загрузка...';
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                
                if (data.status === 'success') {
                    result.innerHTML = `
                        <div class="success">
                            <h3>✅ Файл успешно загружен!</h3>
                            <p><strong>Имя файла:</strong> ${data.filename}</p>
                            <p><strong>Ссылка:</strong> <a href="${data.url}" target="_blank">${data.url}</a></p>
                        </div>
                    `;
                } else {
                    result.innerHTML = `
                        <div class="error">
                            <h3>❌ Ошибка загрузки</h3>
                            <p>${data.message}</p>
                        </div>
                    `;
                }
            } catch (error) {
                result.innerHTML = `
                    <div class="error">
                        <h3>❌ Ошибка сети</h3>
                        <p>Не удалось загрузить файл: ${error.message}</p>
                    </div>
                `;
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.textContent = 'Загрузить';
            }
        }
    </script>
</body>
</html>
                """
                self._set_headers(200, 'text/html')
                self.wfile.write(html_content.encode('utf-8'))
                logger.info("Главная страница (встроенная) успешно загружена")
        except Exception as e:
            logger.error(f"Ошибка при загрузке главной страницы: {e}")
            self._set_headers(500, 'text/plain')
            self.wfile.write(b"500 Internal Server Error")


    def do_POST(self):
        """Обработка POST запросов."""
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/upload':
            self._handle_upload()
        else:
            logger.warning(f"Неизвестный POST запрос на: {self.path}")
            self._set_headers(404, 'application/json')
            response = {"status": "error", "message": "Маршрут не найден"}
            self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_upload(self):
        """Обработка загрузки файла."""
        start_time = time.time()
        
        try:
            # 1. Получаем заголовок Content-Type
            content_type_header = self.headers.get('Content-Type')
            if not content_type_header or not content_type_header.startswith('multipart/form-data'):
                logger.warning("Ошибка загрузки - некорректный Content-Type")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Ожидается multipart/form-data"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 2. Извлекаем boundary из Content-Type
            try:
                boundary = content_type_header.split('boundary=')[1].encode('utf-8')
            except IndexError:
                logger.warning("Ошибка загрузки - boundary не найден в Content-Type")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Boundary не найден"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 3. Читаем тело запроса
            try:
                content_length = int(self.headers['Content-Length'])
                if content_length > MAX_FILE_SIZE * 2:  # Небольшой запас на служебную информацию multipart
                    logger.warning(f"Ошибка загрузки - запрос превышает максимальный размер ({content_length} байт)")
                    self._set_headers(413, 'application/json')  # Payload Too Large
                    response = {"status": "error", "message": "Запрос слишком большой"}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return

                raw_body = self.rfile.read(content_length)
            except (TypeError, ValueError):
                logger.error("Некорректный Content-Length")
                self._set_headers(411, 'application/json')  # Length Required
                response = {"status": "error", "message": "Некорректный Content-Length"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            except Exception as e:
                logger.error(f"Ошибка при чтении тела запроса: {e}")
                self._set_headers(500, 'application/json')
                response = {"status": "error", "message": "Ошибка при чтении запроса"}
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
                        logger.error(f"Ошибка при парсинге части multipart: {e}")
                        continue

            if not file_data or not filename:
                logger.warning("Ошибка загрузки - файл не найден в multipart-запросе")
                self._set_headers(400, 'application/json')
                response = {"status": "error", "message": "Файл не найден в запросе"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 5. Проверки файла
            file_size = len(file_data)
            file_extension = os.path.splitext(filename)[1].lower()

            if file_extension not in ALLOWED_EXTENSIONS:
                logger.warning(f"Ошибка загрузки - неподдерживаемый формат файла ({filename})")
                self._set_headers(400, 'application/json')
                response = {"status": "error",
                            "message": f"Неподдерживаемый формат файла. Допустимы: {', '.join(ALLOWED_EXTENSIONS)}"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            if file_size > MAX_FILE_SIZE:
                logger.warning(f"Ошибка загрузки - файл превышает максимальный размер ({filename}, {file_size} байт)")
                self._set_headers(400, 'application/json')
                response = {"status": "error",
                            "message": f"Файл превышает максимальный размер {MAX_FILE_SIZE / (1024 * 1024):.0f}MB"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return

            # 6. Сохранение файла
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            target_path = os.path.join(UPLOAD_DIR, unique_filename)

            try:
                with open(target_path, 'wb') as f:
                    f.write(file_data)

                file_url = f"/images/{unique_filename}"
                processing_time = time.time() - start_time
                
                logger.info(f"Успех: Изображение '{filename}' (сохранено как '{unique_filename}') загружено за {processing_time:.2f}с. Ссылка: {file_url}")
                
                self._set_headers(200, 'application/json')
                response = {
                    "status": "success",
                    "message": "Файл успешно загружен",
                    "filename": unique_filename,
                    "url": file_url,
                    "processing_time": f"{processing_time:.2f}с"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                logger.error(f"Ошибка при сохранении файла '{filename}' в '{target_path}': {e}")
                self._set_headers(500, 'application/json')
                response = {"status": "error", "message": "Произошла ошибка при сохранении файла"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке загрузки: {e}")
            self._set_headers(500, 'application/json')
            response = {"status": "error", "message": "Внутренняя ошибка сервера"}
            self.wfile.write(json.dumps(response).encode('utf-8'))


def run_server(server_class=http.server.HTTPServer, handler_class=ImageHostingHandler, port=8000):
    """Запускает сервер."""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Сервер запущен на порту {port}")
    logger.info(f"Директория для загрузок: {UPLOAD_DIR}")
    logger.info(f"Директория для логов: {LOG_DIR}")
    logger.info(f"Максимальный размер файла: {MAX_FILE_SIZE / (1024 * 1024):.0f} МБ")
    logger.info(f"Поддерживаемые форматы: {', '.join(ALLOWED_EXTENSIONS)}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки сервера")
    except Exception as e:
        logger.error(f"Ошибка сервера: {e}")
    finally:
        httpd.server_close()
        logger.info("Сервер остановлен")


if __name__ == '__main__':
    run_server()
