from django.conf import settings


def thong_tin_he_thong(request):
    """Đưa tên trường/tên hệ thống (đọc từ .env qua settings) vào mọi template, dùng cho
    logo ở trang đăng nhập và thanh menu trên (xem templates/_logo.html)."""
    return {
        'TEN_TRUONG': settings.TEN_TRUONG,
        'TEN_HE_THONG': settings.TEN_HE_THONG,
    }


def so_thong_bao_chua_doc(request):
    """Số thông báo chưa đọc của người dùng hiện tại — hiện thành chip nhỏ trên thanh menu
    (xem templates/base.html), tính lại mỗi lần tải trang nên luôn đúng ngay sau khi đọc."""
    if not request.user.is_authenticated:
        return {}
    from thong_bao.services import so_luong_chua_doc
    return {'SO_THONG_BAO_CHUA_DOC': so_luong_chua_doc(request.user)}
