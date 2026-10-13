from django.utils import timezone

from .models import DotDangKy, HocKy


def danh_sach_bo_loc_hoc_ky():
    """Danh sách số học kỳ và năm học duy nhất trong danh mục hoc_ky, dùng để đổ vào
    <select> ở các trang lọc theo học kỳ/năm học (thay ô nhập tự do). Không đổi logic lọc:
    các view vẫn so khớp hoc_ky/nam_hoc dạng chuỗi như trước, chỉ đổi nguồn hiển thị lựa chọn.
    """
    cac_hoc_ky = HocKy.objects.order_by('hoc_ky').values_list('hoc_ky', flat=True).distinct()
    cac_nam_hoc = HocKy.objects.order_by('nam_hoc').values_list('nam_hoc', flat=True).distinct()
    return [str(hoc_ky) for hoc_ky in cac_hoc_ky], list(cac_nam_hoc)


def trang_thai_dot_dang_ky(hoc_ky_so, nam_hoc):
    """Xác định đợt đăng ký có đang mở hay không cho một học kỳ/năm học (dạng chuỗi như
    trên lop_hoc_phan.hoc_ky/nam_hoc — ánh xạ sang danh mục HocKy để tìm đợt tương ứng,
    cùng kiểu "sao chép giá trị" như dropdown chọn học kỳ, xem docs/erd.md).

    Trả về dict {'mo': bool, 'ly_do': str|None} — ly_do luôn có giá trị khi mo=False, để
    hiển thị/báo lỗi rõ ràng (chưa có đợt, chưa mở, hay đã đóng).
    """
    hoc_ky_obj = HocKy.objects.filter(hoc_ky=hoc_ky_so, nam_hoc=nam_hoc).first()
    if hoc_ky_obj is None:
        return {'mo': False, 'ly_do': 'Chưa có đợt đăng ký nào cho học kỳ này.'}

    cac_dot = list(DotDangKy.objects.filter(hoc_ky=hoc_ky_obj).order_by('ngay_mo'))
    if not cac_dot:
        return {'mo': False, 'ly_do': 'Chưa có đợt đăng ký nào cho học kỳ này.'}

    bay_gio = timezone.now()
    for dot in cac_dot:
        if dot.ngay_mo <= bay_gio <= dot.ngay_dong:
            return {'mo': True, 'ly_do': None}

    dot_sap_toi = next((dot for dot in cac_dot if dot.ngay_mo > bay_gio), None)
    if dot_sap_toi is not None:
        return {
            'mo': False,
            'ly_do': f'Đợt đăng ký chưa mở, sẽ mở lúc {timezone.localtime(dot_sap_toi.ngay_mo):%d/%m/%Y %H:%M}.',
        }
    return {'mo': False, 'ly_do': 'Đợt đăng ký của học kỳ này đã đóng.'}


def co_dang_ky_trong_dot(dot_dang_ky):
    """Đã có sinh viên đăng ký (bất kể còn hiệu lực hay đã hủy sau đó) trong khoảng thời
    gian của đợt này chưa — dùng để chặn xóa đợt. Import cục bộ vì enrollment phụ thuộc
    academics (HocKy, DieuKienTienQuyet...), nên academics không import enrollment ở mức
    module để tránh phụ thuộc vòng."""
    from enrollment.models import DangKyHocPhan

    hoc_ky = dot_dang_ky.hoc_ky
    return DangKyHocPhan.objects.filter(
        ma_lop_hoc_phan__hoc_ky=str(hoc_ky.hoc_ky),
        ma_lop_hoc_phan__nam_hoc=hoc_ky.nam_hoc,
        thoi_gian_dang_ky__gte=dot_dang_ky.ngay_mo,
        thoi_gian_dang_ky__lte=dot_dang_ky.ngay_dong,
    ).exists()
