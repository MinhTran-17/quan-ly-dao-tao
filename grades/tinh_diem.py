from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings


def tinh_diem_tong_ket(diem_qua_trinh, diem_thi):
    """Tính điểm tổng kết từ điểm quá trình và điểm thi.

    Làm tròn 1 chữ số thập phân, tròn lên từ 5 (ROUND_HALF_UP).
    Trả về None nếu thiếu điểm quá trình hoặc điểm thi.
    """
    if diem_qua_trinh is None or diem_thi is None:
        return None
    tong = diem_qua_trinh * settings.TY_LE_DIEM_QUA_TRINH + diem_thi * settings.TY_LE_DIEM_THI
    return tong.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
