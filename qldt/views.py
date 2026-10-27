from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def kiem_tra_suc_khoe(request):
    """GET /health/: trạng thái ứng dụng và kết nối CSDL, cho Docker healthcheck và người vận hành.

    Không cần đăng nhập, không trả thông tin nhạy cảm (tên CSDL, máy chủ, thông điệp lỗi chi tiết).
    CSDL lỗi thì trả 503 để công cụ giám sát nhận ra.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        csdl = 'ok'
    except DatabaseError:
        csdl = 'loi'
    trang_thai = 'ok' if csdl == 'ok' else 'loi'
    return JsonResponse(
        {'trang_thai': trang_thai, 'ung_dung': 'ok', 'csdl': csdl},
        status=200 if trang_thai == 'ok' else 503,
    )
