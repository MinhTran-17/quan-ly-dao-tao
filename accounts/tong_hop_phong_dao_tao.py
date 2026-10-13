"""Dữ liệu tổng hợp cho trang chủ Phòng Đào tạo (accounts/templates/accounts/_trang_chu_phong_dao_tao.html).

Chỉ GỌI LẠI các service/truy vấn đã có (grades.services cho cảnh báo học vụ, cách đếm sĩ số giống trang lớp đang
mở và báo cáo sĩ số, DotDangKy/HocKy, ThongBao); không tính lại quy tắc nghiệp vụ ở đây. Cảnh báo học vụ dùng
điểm thật (giống trang của Cố vấn/Phòng Đào tạo), mỗi sinh viên xét ở học kỳ gần nhất có đủ điểm CỦA RIÊNG HỌ nên
có thể lệch nhẹ so với trang cảnh báo học vụ lọc theo một học kỳ (đã ghi chú trên giao diện).
"""
from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Count, F, Q
from django.urls import reverse
from django.utils import timezone

from academics.models import DotDangKy, HocKy
from accounts.models import VaiTro
from classes.models import LopHocPhan
from enrollment.models import TrangThaiDangKy
from grades.services import canh_bao_hoc_vu, hoc_ky_gan_nhat_co_du_diem
from people.models import SinhVien
from thong_bao.models import ThongBao

SO_DONG_CANH_BAO_TOI_DA = 5
SO_NGAY_DOT_SAP_DONG = 3
SO_THONG_BAO_TOI_DA = 5
SO_LOP_DAY_TOI_DA_TRONG_DONG = 3


def _url(ten_url, **tham_so):
    duong_dan = reverse(ten_url)
    tham_so = {khoa: gia_tri for khoa, gia_tri in tham_so.items() if gia_tri}
    return f'{duong_dan}?{urlencode(tham_so)}' if tham_so else duong_dan


def hoc_ky_dang_xet(bay_gio):
    """Học kỳ dùng cho các số liệu theo học kỳ: học kỳ của đợt đăng ký đang hiệu lực (nếu có nhiều đợt thì lấy học
    kỳ mới nhất), nếu không có thì học kỳ mới nhất trong danh mục (sắp theo năm học rồi số học kỳ, giảm dần).
    Trả về dict {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'dot'|'danh_muc'} hoặc None nếu danh mục trống."""
    dot = (
        DotDangKy.objects.select_related('hoc_ky')
        .filter(ngay_mo__lte=bay_gio, ngay_dong__gte=bay_gio)
        .order_by('-hoc_ky__nam_hoc', '-hoc_ky__hoc_ky', '-ngay_mo')
        .first()
    )
    if dot is not None:
        hoc_ky, nguon = dot.hoc_ky, 'dot'
    else:
        hoc_ky, nguon = HocKy.objects.order_by('-nam_hoc', '-hoc_ky').first(), 'danh_muc'
    if hoc_ky is None:
        return None
    # Cùng dạng chuỗi với lop_hoc_phan.hoc_ky/nam_hoc để lọc trực tiếp.
    return {'hoc_ky': str(hoc_ky.hoc_ky), 'nam_hoc': hoc_ky.nam_hoc, 'nguon': nguon}


def _thong_ke_canh_bao_hoc_vu():
    """(tổng số sinh viên đang hoạt động bị cảnh báo, số bị mức đỏ). Mức đỏ = có cả 2 lý do (điểm trung bình dưới
    5.0 và từ 2 học phần chưa đạt), cùng quy ước với trang chủ Sinh viên."""
    tong = so_do = 0
    for sinh_vien in SinhVien.objects.filter(ma_tai_khoan__is_active=True):
        hoc_ky_nam_hoc = hoc_ky_gan_nhat_co_du_diem(sinh_vien)
        if hoc_ky_nam_hoc is None:
            continue
        ket_qua = canh_bao_hoc_vu(sinh_vien, hoc_ky_nam_hoc[0], hoc_ky_nam_hoc[1])
        if ket_qua['canh_bao']:
            tong += 1
            if len(ket_qua['ly_do']) >= 2:
                so_do += 1
    return tong, so_do


def _lop_hoc_phan_theo_hoc_ky(hoc_ky_xet):
    if hoc_ky_xet is None:
        return LopHocPhan.objects.none()
    return LopHocPhan.objects.filter(hoc_ky=hoc_ky_xet['hoc_ky'], nam_hoc=hoc_ky_xet['nam_hoc'])


def _lop_hoc_phan_day(hoc_ky_xet):
    """Lớp của học kỳ đang xét có số đăng ký còn hiệu lực đạt sĩ số tối đa (cách đếm như trang lớp đang mở)."""
    return list(
        _lop_hoc_phan_theo_hoc_ky(hoc_ky_xet)
        .annotate(so_dang_ky=Count('dang_ky', filter=Q(dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC)))
        .filter(so_dang_ky__gte=F('si_so_toi_da'))
        .order_by('ma_lop_hoc_phan')
        .values_list('ma_lop_hoc_phan', flat=True)
    )


def _dong_canh_bao(so_do, lop_day, dot_sap_dong, hoc_ky_xet):
    """Các dòng "cảnh báo cần chú ý", mỗi loại một dòng theo thứ tự ưu tiên; tối đa SO_DONG_CANH_BAO_TOI_DA."""
    tham_so_hoc_ky = {'hoc_ky': hoc_ky_xet['hoc_ky'], 'nam_hoc': hoc_ky_xet['nam_hoc']} if hoc_ky_xet else {}
    dong = []
    if so_do:
        dong.append({
            'muc': 'do',
            'noi_dung': f'{so_do} sinh viên bị cảnh báo học vụ mức đỏ (điểm trung bình dưới 5.0 và có từ 2 học phần chưa đạt).',
            'url': _url('grades:canh_bao_phong_dao_tao', **tham_so_hoc_ky),
            'nhan_nut': 'Xem cảnh báo học vụ',
        })
    if lop_day:
        hien = ', '.join(lop_day[:SO_LOP_DAY_TOI_DA_TRONG_DONG])
        con_lai = len(lop_day) - SO_LOP_DAY_TOI_DA_TRONG_DONG
        dong.append({
            'muc': 'day',
            'noi_dung': f'{len(lop_day)} lớp học phần đã đầy chỗ: {hien}' + (f' và {con_lai} lớp khác.' if con_lai > 0 else '.'),
            'url': _url('reports:si_so_theo_lop', **tham_so_hoc_ky),
            'nhan_nut': 'Xem sĩ số theo lớp',
        })
    for dot in dot_sap_dong:
        dong.append({
            'muc': 'dot',
            'noi_dung': (
                f'Đợt đăng ký Học kỳ {dot.hoc_ky.hoc_ky} năm học {dot.hoc_ky.nam_hoc} sắp đóng, '
                f'lúc {timezone.localtime(dot.ngay_dong):%d/%m/%Y %H:%M}.'
            ),
            'url': reverse('academics:dot_dang_ky_danh_sach'),
            'nhan_nut': 'Xem đợt đăng ký',
        })
    return dong[:SO_DONG_CANH_BAO_TOI_DA]


def tong_hop_trang_chu_phong_dao_tao(bay_gio=None):
    bay_gio = bay_gio or timezone.now()
    hoc_ky_xet = hoc_ky_dang_xet(bay_gio)
    tham_so_hoc_ky = {'hoc_ky': hoc_ky_xet['hoc_ky'], 'nam_hoc': hoc_ky_xet['nam_hoc']} if hoc_ky_xet else {}

    dot_hieu_luc = DotDangKy.objects.select_related('hoc_ky').filter(ngay_mo__lte=bay_gio, ngay_dong__gte=bay_gio)
    dot_sap_dong = list(
        dot_hieu_luc.filter(ngay_dong__lte=bay_gio + timedelta(days=SO_NGAY_DOT_SAP_DONG)).order_by('ngay_dong')
    )
    so_canh_bao, so_do = _thong_ke_canh_bao_hoc_vu()
    lop_day = _lop_hoc_phan_day(hoc_ky_xet)

    return {
        'hoc_ky_xet': hoc_ky_xet,
        'so_sinh_vien_hoat_dong': SinhVien.objects.filter(ma_tai_khoan__is_active=True).count(),
        'so_lop_hoc_phan': _lop_hoc_phan_theo_hoc_ky(hoc_ky_xet).count() if hoc_ky_xet else None,
        'so_dot_hieu_luc': dot_hieu_luc.count(),
        'so_canh_bao': so_canh_bao,
        'so_canh_bao_do': so_do,
        'so_lop_day': len(lop_day),
        'dong_canh_bao': _dong_canh_bao(so_do, lop_day, dot_sap_dong, hoc_ky_xet),
        'thong_bao_gan_day': list(
            ThongBao.objects.filter(nguoi_gui__vai_tro=VaiTro.PHONG_DAO_TAO)
            .select_related('lop_hoc_phan', 'lop_hanh_chinh').order_by('-thoi_gian_gui', '-pk')[:SO_THONG_BAO_TOI_DA]
        ),
        'url_sinh_vien': reverse('people:sinh_vien_danh_sach'),
        'url_lop_hoc_phan': _url('classes:lop_hoc_phan_danh_sach', **tham_so_hoc_ky),
        'url_dot_dang_ky': reverse('academics:dot_dang_ky_danh_sach'),
        'url_canh_bao': _url('grades:canh_bao_phong_dao_tao', **tham_so_hoc_ky),
        'url_si_so': _url('reports:si_so_theo_lop', **tham_so_hoc_ky),
        'url_thong_bao_da_gui': reverse('thong_bao:da_gui'),
    }
