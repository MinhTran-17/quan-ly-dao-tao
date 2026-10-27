import secrets
import string

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def _sinh_chuoi_ngau_nhien():
    """12 ký tự ngẫu nhiên (secrets), có ít nhất một chữ hoa, một chữ thường, một chữ số."""
    bang_ky_tu = string.ascii_letters + string.digits
    mat_khau = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
    ]
    mat_khau += [secrets.choice(bang_ky_tu) for _ in range(9)]
    secrets.SystemRandom().shuffle(mat_khau)
    return ''.join(mat_khau)


def tao_mat_khau_tam(tai_khoan):
    """Sinh mật khẩu tạm ngẫu nhiên (không đoán được), đảm bảo có chữ hoa/thường/số nên
    luôn qua được NumericPasswordValidator; thử lại vài lần cho chắc với các validator
    còn lại (gần như không bao giờ cần vì chuỗi là ngẫu nhiên). Dùng chung cho đặt lại mật
    khẩu (accounts/views.py) và tạo tài khoản kèm khi nhập sinh viên từ Excel (people).
    Khi đặt lại mật khẩu, mật khẩu tạm không được trùng mật khẩu hiện tại của tài khoản."""
    for _ in range(5):
        mat_khau = _sinh_chuoi_ngau_nhien()
        if tai_khoan.pk and tai_khoan.has_usable_password() and tai_khoan.check_password(mat_khau):
            continue
        try:
            validate_password(mat_khau, user=tai_khoan)
            return mat_khau
        except ValidationError:
            continue
    raise RuntimeError('Không tạo được mật khẩu tạm hợp lệ sau nhiều lần thử.')
