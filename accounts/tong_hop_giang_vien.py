"""Dữ liệu tổng hợp cho trang chủ Giảng viên (accounts/templates/accounts/_trang_chu_giang_vien.html).

Chỉ GỌI LẠI các truy vấn/service có sẵn (cách chọn học kỳ đang xét của trang chủ Phòng Đào tạo, LichHoc/LichThi/Diem/
DiemDanh, thong_bao.services.thong_bao_lien_quan); không tính lại quy tắc nghiệp vụ. Mọi số liệu chỉ của các lớp học
phần do chính giảng viên này phụ trách; điểm dùng điểm thật vì đây là trang của giảng viên.
"""
from datetime import timedelta
from urllib.parse import urlencode

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from academics.models import HocKy
from classes.models import LichHoc, LichThi, LopHocPhan
from classes.services import CAC_THU
from diem_danh.models import DiemDanh
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from grades.models import Diem

from .tong_hop_chung import thong_bao_gan_day
from .tong_hop_phong_dao_tao import hoc_ky_dang_xet

SO_NGAY_LICH_THI_SAP_TOI = 7
SO_LOP_TOI_DA_TRONG_DONG = 3
TEN_THU = dict(CAC_THU)


def _liet_ke_lop(ma_lop, toi_da=SO_LOP_TOI_DA_TRONG_DONG):
    hien = ', '.join(ma_lop[:toi_da])
    con_lai = len(ma_lop) - toi_da
    return hien + (f' và {con_lai} lớp khác' if con_lai > 0 else '')


def _lop_chua_cong_bo_diem(giang_vien):
    """Mã các lớp của giảng viên (mọi học kỳ) còn ít nhất một điểm ĐÃ NHẬP nhưng chưa công bố cho sinh viên."""
    return list(
        Diem.objects.filter(
            ma_dang_ky__ma_lop_hoc_phan__ma_giang_vien=giang_vien,
            ma_dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC, da_cong_bo=False,
        ).filter(Q(diem_qua_trinh__isnull=False) | Q(diem_thi__isnull=False))
        .order_by('ma_dang_ky__ma_lop_hoc_phan_id')
        .values_list('ma_dang_ky__ma_lop_hoc_phan_id', flat=True).distinct()
    )


def _lop_chua_diem_danh_hom_qua(lop_hoc_ky, hoc_ky_xet, hom_qua):
    """Lớp của học kỳ đang xét có buổi dạy vào hôm qua (đúng thứ, hôm qua nằm trong học kỳ), có sinh viên đăng ký nhưng
    chưa có dòng điểm danh nào của ngày hôm qua."""
    if hoc_ky_xet is None:
        return []
    hoc_ky = HocKy.objects.filter(hoc_ky=int(hoc_ky_xet['hoc_ky']), nam_hoc=hoc_ky_xet['nam_hoc']).first()
    if hoc_ky is None or not (hoc_ky.ngay_bat_dau <= hom_qua <= hoc_ky.ngay_ket_thuc):
        return []
    co_buoi = set(
        LichHoc.objects.filter(ma_lop_hoc_phan__in=lop_hoc_ky, thu=hom_qua.weekday() + 2)
        .values_list('ma_lop_hoc_phan_id', flat=True)
    )
    co_sinh_vien = set(
        DangKyHocPhan.objects.filter(ma_lop_hoc_phan_id__in=co_buoi, trang_thai=TrangThaiDangKy.CON_HIEU_LUC)
        .values_list('ma_lop_hoc_phan_id', flat=True)
    )
    da_diem_danh = set(
        DiemDanh.objects.filter(lop_hoc_phan_id__in=co_buoi, ngay_diem_danh=hom_qua)
        .values_list('lop_hoc_phan_id', flat=True)
    )
    return sorted((co_buoi & co_sinh_vien) - da_diem_danh)


def _dong_canh_bao(lop_chua_cong_bo, lop_chua_diem_danh, hom_qua, lich_thi_sap_toi):
    """Mỗi loại một dòng theo thứ tự: điểm chưa công bố, chưa điểm danh hôm qua, lịch thi sắp tới."""
    url_lop = reverse('classes:lop_phu_trach')
    dong = []
    if lop_chua_cong_bo:
        mot_lop = len(lop_chua_cong_bo) == 1
        dong.append({
            'muc': 'diem',
            'noi_dung': f'{len(lop_chua_cong_bo)} lớp còn điểm chưa công bố: {_liet_ke_lop(lop_chua_cong_bo)}.',
            'url': reverse('grades:bang_diem_lop', args=[lop_chua_cong_bo[0]]) if mot_lop else url_lop,
            'nhan_nut': 'Xem bảng điểm lớp' if mot_lop else 'Xem lớp phụ trách',
        })
    if lop_chua_diem_danh:
        mot_lop = len(lop_chua_diem_danh) == 1
        dong.append({
            'muc': 'diem_danh',
            'noi_dung': (
                f'{len(lop_chua_diem_danh)} lớp có buổi dạy hôm qua ({hom_qua:%d/%m/%Y}) chưa điểm danh: '
                f'{_liet_ke_lop(lop_chua_diem_danh)}.'
            ),
            'url': (
                reverse('diem_danh:diem_danh_lop', args=[lop_chua_diem_danh[0]]) + '?' + urlencode({'ngay': hom_qua.isoformat()})
                if mot_lop else url_lop
            ),
            'nhan_nut': 'Điểm danh' if mot_lop else 'Xem lớp phụ trách',
        })
    if lich_thi_sap_toi:
        chi_tiet = [
            f'{lich.lop_hoc_phan_id} ({lich.ngay_thi:%d/%m} {lich.gio_bat_dau:%H:%M})' for lich in lich_thi_sap_toi
        ]
        dong.append({
            'muc': 'thi',
            'noi_dung': (
                f'{len(lich_thi_sap_toi)} lịch thi trong {SO_NGAY_LICH_THI_SAP_TOI} ngày tới: {_liet_ke_lop(chi_tiet)}.'
            ),
            'url': url_lop,
            'nhan_nut': 'Xem lớp phụ trách',
        })
    return dong


def tong_hop_trang_chu_giang_vien(giang_vien, tai_khoan, bay_gio=None):
    if giang_vien is None:
        return {'co_ho_so': False}
    bay_gio = bay_gio or timezone.now()
    hom_nay = timezone.localtime(bay_gio).date()
    hom_qua = hom_nay - timedelta(days=1)
    thu_hom_nay = hom_nay.weekday() + 2  # LichHoc.thu: 2 = Thứ 2 ... 8 = Chủ nhật

    hoc_ky_xet = hoc_ky_dang_xet(bay_gio)
    lop_hoc_ky = (
        LopHocPhan.objects.filter(ma_giang_vien=giang_vien, hoc_ky=hoc_ky_xet['hoc_ky'], nam_hoc=hoc_ky_xet['nam_hoc'])
        if hoc_ky_xet else LopHocPhan.objects.none()
    )
    lich_hom_nay = list(
        LichHoc.objects.filter(ma_lop_hoc_phan__in=lop_hoc_ky, thu=thu_hom_nay)
        .select_related('ma_lop_hoc_phan__ma_hoc_phan').order_by('tiet_bat_dau', 'ma_lop_hoc_phan_id')
    )
    lop_chua_cong_bo = _lop_chua_cong_bo_diem(giang_vien)
    lop_chua_diem_danh = _lop_chua_diem_danh_hom_qua(lop_hoc_ky, hoc_ky_xet, hom_qua)
    lich_thi_sap_toi = list(
        LichThi.objects.filter(
            lop_hoc_phan__ma_giang_vien=giang_vien, ngay_thi__gte=hom_nay,
            ngay_thi__lte=hom_nay + timedelta(days=SO_NGAY_LICH_THI_SAP_TOI),
        ).order_by('ngay_thi', 'gio_bat_dau')
    )

    return {
        'co_ho_so': True,
        'hoc_ky_xet': hoc_ky_xet,
        'so_lop': lop_hoc_ky.count() if hoc_ky_xet else None,
        'so_sinh_vien': (
            DangKyHocPhan.objects.filter(ma_lop_hoc_phan__in=lop_hoc_ky, trang_thai=TrangThaiDangKy.CON_HIEU_LUC)
            .values('ma_sinh_vien').distinct().count()
        ),
        'ten_thu_hom_nay': TEN_THU[thu_hom_nay],
        'so_buoi_hom_nay': len(lich_hom_nay),
        'so_buoi_tuan': LichHoc.objects.filter(ma_lop_hoc_phan__in=lop_hoc_ky).count(),
        'so_lop_chua_cong_bo': len(lop_chua_cong_bo),
        'lich_hom_nay': lich_hom_nay,
        'dong_canh_bao': _dong_canh_bao(lop_chua_cong_bo, lop_chua_diem_danh, hom_qua, lich_thi_sap_toi),
        'thong_bao_gan_day': thong_bao_gan_day(tai_khoan),
        'url_lop_phu_trach': reverse('classes:lop_phu_trach'),
        'url_lich_giang_day': reverse('classes:lich_giang_day'),
        'url_lich_giang_day_luoi': reverse('classes:lich_giang_day') + '?xem=luoi',
        'url_thong_bao': reverse('thong_bao:danh_sach'),
    }
