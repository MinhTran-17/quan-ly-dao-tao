from django.core.cache import cache

SO_CAU_HOI_TOI_DA_MOI_PHUT = 10
THOI_GIAN_CUA_SO_GIAY = 60


def _khoa_cache(tai_khoan):
    return f'hoi_dap_quy_che:so_cau_hoi:{tai_khoan.pk}'


def kiem_tra_va_dem(tai_khoan):
    """Đếm một lượt hỏi cho tai_khoan trong cửa sổ 60 giây gần nhất, dùng cache của
    Django (không tạo bảng CSDL mới). Trả về (được_phép: bool, thông_báo: str).

    Dùng cache.add() để khởi tạo khóa một cách an toàn khi có nhiều tiến trình/luồng
    cùng truy cập, sau đó cache.incr() để tăng đếm nguyên tử.
    """
    khoa = _khoa_cache(tai_khoan)
    cache.add(khoa, 0, timeout=THOI_GIAN_CUA_SO_GIAY)
    so_lan = cache.incr(khoa)
    if so_lan > SO_CAU_HOI_TOI_DA_MOI_PHUT:
        return False, 'Bạn đã hỏi quá nhiều câu trong 1 phút, vui lòng thử lại sau một chút.'
    return True, ''
