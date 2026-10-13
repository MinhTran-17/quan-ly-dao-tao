from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def yeu_cau_vai_tro(*vai_tro_cho_phep):
    """Decorator cho function-based view: chỉ cho phép các vai_tro liệt kê.

    Phân quyền dựa hoàn toàn vào cột vai_tro của tai_khoan, không dùng
    permission_required/has_perm của Django (theo quy ước dự án).
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.vai_tro not in vai_tro_cho_phep:
                raise PermissionDenied('Bạn không có quyền truy cập chức năng này.')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class YeuCauVaiTroMixin:
    """Mixin cho class-based view: chỉ cho phép các vai_tro trong vai_tro_cho_phep."""

    vai_tro_cho_phep = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.vai_tro not in self.vai_tro_cho_phep:
            raise PermissionDenied('Bạn không có quyền truy cập chức năng này.')
        return super().dispatch(request, *args, **kwargs)
