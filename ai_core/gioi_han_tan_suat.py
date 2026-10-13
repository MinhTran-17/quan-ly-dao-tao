from django.core.cache import cache

SO_LAN_TOI_DA_MOI_PHUT_MAC_DINH = 10
THOI_GIAN_CUA_SO_GIAY_MAC_DINH = 60


def kiem_tra_va_dem(khoa, so_toi_da=SO_LAN_TOI_DA_MOI_PHUT_MAC_DINH, cua_so_giay=THOI_GIAN_CUA_SO_GIAY_MAC_DINH):
    """Đếm một lượt dùng một chức năng AI cho `khoa` (chuỗi định danh duy nhất theo
    chức năng + người dùng, ví dụ "tu_van_dang_ky:12") trong cửa sổ cua_so_giay giây gần
    nhất, dùng cache của Django (không tạo bảng CSDL mới — theo quy ước dự án).

    Dùng chung cho mọi chức năng AI cần giới hạn tần suất theo người dùng (hạn mức API
    của gói miễn phí rất thấp — xem ai_core/README hoặc docs/thiet_ke_ai.md — một người
    dùng gọi liên tục có thể làm cạn hạn mức dùng chung cho cả hệ thống).

    Dùng cache.add() để khởi tạo khóa an toàn khi nhiều tiến trình/luồng cùng truy cập,
    sau đó cache.incr() để tăng đếm nguyên tử. Trả về (được_phép: bool, thông_báo: str).
    """
    cache.add(khoa, 0, timeout=cua_so_giay)
    so_lan = cache.incr(khoa)
    if so_lan > so_toi_da:
        return False, (
            f'Bạn đã dùng chức năng này quá {so_toi_da} lần trong {cua_so_giay} giây, '
            'vui lòng thử lại sau một chút.'
        )
    return True, ''
