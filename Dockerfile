# Ảnh Docker của ứng dụng Django (Hệ thống quản lý đào tạo tích hợp AI).
# Cấu hình bí mật (mật khẩu CSDL, GEMINI_API_KEY, DJANGO_SECRET_KEY) KHÔNG nằm trong ảnh:
# docker-compose.yml đọc từ tệp .env lúc chạy (.env bị loại khỏi ảnh bởi .dockerignore).
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Cài thư viện trước khi chép mã nguồn để tận dụng cache của Docker khi chỉ sửa code.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Chạy bằng người dùng thường, không dùng root; logs/ và media/ là nơi duy nhất ứng dụng ghi.
RUN useradd --create-home --uid 1000 qldt \
    && mkdir -p logs media \
    && chown -R qldt:qldt /app
USER qldt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=5).status == 200 else 1)"

# Tự áp dụng migration rồi chạy máy chủ. runserver --insecure phục vụ cả tệp tĩnh khi DEBUG=False,
# đủ cho demo đồ án; triển khai thật nên thay bằng gunicorn + nginx.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000 --insecure"]
