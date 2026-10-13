"""Dữ liệu tổng hợp cho trang chủ Cố vấn học tập (accounts/templates/accounts/_trang_chu_co_van.html).

Chỉ GỌI LẠI các service có sẵn (grades.services cho cảnh báo học vụ — đúng cách của trang "Cảnh báo học vụ" của Cố vấn,
điểm thật, mỗi sinh viên xét ở học kỳ gần nhất có đủ điểm của riêng họ; cách chọn học kỳ đang xét của trang chủ Phòng Đào
tạo; thong_bao.services). Mọi số liệu chỉ của sinh viên thuộc các lớp hành chính do cố vấn này phụ trách.
"""
from django.urls import reverse
from django.utils import timezone

from academics.models import LopHanhChinh
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from grades.services import canh_bao_hoc_vu, hoc_ky_gan_nhat_co_du_diem
from people.models import SinhVien
from thong_bao.services import so_luong_chua_doc

from .tong_hop_chung import liet_ke, thong_bao_gan_day
from .tong_hop_phong_dao_tao import hoc_ky_dang_xet

SO_SINH_VIEN_CAN_QUAN_TAM_TOI_DA = 5


def _sinh_vien_bi_canh_bao(sinh_vien):
    """Danh sách cảnh báo, mức đỏ (2 lý do) xếp trước rồi theo mã sinh viên."""
    ket_qua = []
    for sv in sinh_vien:
        hoc_ky_nam_hoc = hoc_ky_gan_nhat_co_du_diem(sv)
        if hoc_ky_nam_hoc is None:
            continue
        canh_bao = canh_bao_hoc_vu(sv, hoc_ky_nam_hoc[0], hoc_ky_nam_hoc[1])
        if canh_bao['canh_bao']:
            ket_qua.append({
                'sinh_vien': sv, 'muc_do': len(canh_bao['ly_do']) >= 2, 'ly_do': canh_bao['ly_do'],
                'diem_trung_binh': canh_bao['diem_trung_binh'],
                'hoc_ky': hoc_ky_nam_hoc[0], 'nam_hoc': hoc_ky_nam_hoc[1],
            })
    ket_qua.sort(key=lambda d: (not d['muc_do'], d['sinh_vien'].pk))
    return ket_qua


def _sinh_vien_chua_dang_ky(sinh_vien, hoc_ky_xet):
    """Sinh viên chưa có đăng ký còn hiệu lực nào trong học kỳ đang xét."""
    if hoc_ky_xet is None or not sinh_vien:
        return []
    da_dang_ky = set(
        DangKyHocPhan.objects.filter(
            ma_sinh_vien__in=sinh_vien, ma_lop_hoc_phan__hoc_ky=hoc_ky_xet['hoc_ky'],
            ma_lop_hoc_phan__nam_hoc=hoc_ky_xet['nam_hoc'], trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ).values_list('ma_sinh_vien_id', flat=True)
    )
    return [sv for sv in sinh_vien if sv.pk not in da_dang_ky]


def _dong_canh_bao(bi_canh_bao, chua_dang_ky, hoc_ky_xet):
    """Mỗi loại một dòng: sinh viên cảnh báo mức đỏ; sinh viên chưa đăng ký học phần khi đang trong đợt đăng ký."""
    dong = []
    so_do = [d for d in bi_canh_bao if d['muc_do']]
    if so_do:
        dong.append({
            'muc': 'do',
            'noi_dung': (
                f'{len(so_do)} sinh viên bị cảnh báo học vụ mức đỏ (điểm trung bình dưới 5.0 và có từ 2 học phần chưa đạt): '
                f'{liet_ke((d["sinh_vien"].pk for d in so_do), don_vi="sinh viên")}.'
            ),
            'url': reverse('grades:canh_bao_co_van'),
            'nhan_nut': 'Xem cảnh báo học vụ',
        })
    if chua_dang_ky and hoc_ky_xet and hoc_ky_xet['nguon'] == 'dot':
        dong.append({
            'muc': 'chua_dang_ky',
            'noi_dung': (
                f'{len(chua_dang_ky)} sinh viên chưa đăng ký học phần nào trong Học kỳ {hoc_ky_xet["hoc_ky"]} năm học '
                f'{hoc_ky_xet["nam_hoc"]} (đang trong đợt đăng ký): {liet_ke((sv.pk for sv in chua_dang_ky), don_vi="sinh viên")}.'
            ),
            'url': reverse('enrollment:sinh_vien_phu_trach'),
            'nhan_nut': 'Xem sinh viên phụ trách',
        })
    return dong


def tong_hop_trang_chu_co_van(co_van, tai_khoan, bay_gio=None):
    if co_van is None:
        return {'co_ho_so': False}
    bay_gio = bay_gio or timezone.now()
    lop_phu_trach = list(LopHanhChinh.objects.filter(ma_co_van=co_van).order_by('ma_lop'))
    sinh_vien = list(SinhVien.objects.filter(ma_lop__ma_co_van=co_van).select_related('ma_lop').order_by('ma_sinh_vien'))
    hoc_ky_xet = hoc_ky_dang_xet(bay_gio)
    bi_canh_bao = _sinh_vien_bi_canh_bao(sinh_vien)
    chua_dang_ky = _sinh_vien_chua_dang_ky(sinh_vien, hoc_ky_xet)

    return {
        'co_ho_so': True,
        'hoc_ky_xet': hoc_ky_xet,
        'so_lop': len(lop_phu_trach),
        'ma_lop': [lop.pk for lop in lop_phu_trach],
        'so_sinh_vien': len(sinh_vien),
        'so_canh_bao': len(bi_canh_bao),
        'so_canh_bao_do': sum(1 for d in bi_canh_bao if d['muc_do']),
        'so_chua_dang_ky': len(chua_dang_ky) if hoc_ky_xet else None,
        'so_thong_bao_chua_doc': so_luong_chua_doc(tai_khoan),
        'dong_canh_bao': _dong_canh_bao(bi_canh_bao, chua_dang_ky, hoc_ky_xet),
        'can_quan_tam': bi_canh_bao[:SO_SINH_VIEN_CAN_QUAN_TAM_TOI_DA],
        'thong_bao_gan_day': thong_bao_gan_day(tai_khoan),
        'url_sinh_vien_phu_trach': reverse('enrollment:sinh_vien_phu_trach'),
        'url_canh_bao': reverse('grades:canh_bao_co_van'),
        'url_thong_bao': reverse('thong_bao:danh_sach'),
    }
