from django.contrib import messages
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

# Các trang vẫn phải vào được dù đang bị buộc đổi mật khẩu, để người dùng có đường thoát
# (đăng xuất) và có nơi để thực hiện việc đổi mật khẩu.
_DUONG_DAN_DUOC_PHEP = {'accounts:doi_mat_khau', 'accounts:dang_xuat'}


class BatBuocDoiMatKhauMiddleware:
    """Nếu tài khoản đang đăng nhập có phai_doi_mat_khau=True (vừa được Phòng Đào tạo đặt
    lại mật khẩu, hoặc tài khoản mới cần đổi mật khẩu ngay), chặn mọi trang khác và chuyển
    hướng về trang đổi mật khẩu, trừ chính trang đó và trang đăng xuất."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and getattr(user, 'phai_doi_mat_khau', False):
            try:
                match = resolve(request.path_info)
            except Resolver404:
                match = None
            if match is not None:
                ten_url_day_du = f'{match.app_name}:{match.url_name}' if match.app_name else match.url_name
                if ten_url_day_du not in _DUONG_DAN_DUOC_PHEP:
                    messages.warning(request, 'Bạn cần đổi mật khẩu trước khi tiếp tục sử dụng hệ thống.')
                    return redirect('accounts:doi_mat_khau')
        return self.get_response(request)
