"""Dữ liệu tổng hợp cho trang chủ Sinh viên (accounts/templates/accounts/_trang_chu_sinh_vien.html).

Chỉ GỌI LẠI các service đã có (grades, tien_do_hoc_tap, thong_bao) và đọc lịch học/lịch thi;
không tính lại quy tắc điểm/cảnh báo ở đây. Mọi số liệu điểm dùng điểm ĐÃ CÔNG BỐ
(chi_diem_da_cong_bo=True) vì đây là trang sinh viên tự xem — cùng ranh giới đã thống nhất ở
lượt tính năng 4/6: điểm chưa công bố không được tính vào điểm trung bình/cảnh báo/tiến độ.
"""
from django.db.models import Exists, OuterRef
from django.utils import timezone

from academics.models import HocKy
from classes.models import LichHoc, LichThi
from classes.services import CAC_THU
from enrollment.models import TrangThaiDangKy
from grades.services import (
    canh_bao_hoc_vu, diem_trung_binh_hoc_ky, diem_trung_binh_tich_luy, hoc_ky_gan_nhat_co_du_diem,
    xep_loai_hoc_luc,
)
from thong_bao.models import DaDocThongBao
from thong_bao.services import thong_bao_lien_quan
from tien_do_hoc_tap.services import tinh_tien_do

SO_LICH_THI_TOI_DA = 3
SO_BUOI_HOM_NAY_TOI_DA = 3
SO_THONG_BAO_TOI_DA = 3


def _tom_tat_hoc_tap(sinh_vien, hoc_ky_gan_nhat):
    diem_tb_tich_luy = diem_trung_binh_tich_luy(sinh_vien, chi_diem_da_cong_bo=True)
    tien_do = tinh_tien_do(sinh_vien, chi_diem_da_cong_bo=True)

    ket_qua = {
        'diem_tb_tich_luy': diem_tb_tich_luy,
        'xep_loai': xep_loai_hoc_luc(diem_tb_tich_luy),
        'co_chuong_trinh': tien_do['co_chuong_trinh'],
        'hoc_ky_gan_nhat': None,
    }
    if hoc_ky_gan_nhat is not None:
        hoc_ky, nam_hoc = hoc_ky_gan_nhat
        ket_qua['hoc_ky_gan_nhat'] = {
            'hoc_ky': hoc_ky, 'nam_hoc': nam_hoc,
            'diem_tb': diem_trung_binh_hoc_ky(sinh_vien, hoc_ky, nam_hoc, chi_diem_da_cong_bo=True),
        }

    if tien_do['co_chuong_trinh']:
        da_dat = tien_do['da_dat_bat_buoc'] + tien_do['da_dat_tu_chon']
        con_thieu = tien_do['con_thieu_bat_buoc'] + tien_do['con_thieu_tu_chon']
        tin_chi_tich_luy = sum(chi_tiet.hoc_phan.so_tin_chi for chi_tiet in da_dat)
        ket_qua.update({
            'ten_chuong_trinh': tien_do['chuong_trinh'].ten_chuong_trinh,
            'tin_chi_tich_luy': tin_chi_tich_luy,
            'tong_tin_chi': tin_chi_tich_luy + sum(chi_tiet.hoc_phan.so_tin_chi for chi_tiet in con_thieu),
            'phan_tram_hoan_thanh': tien_do['phan_tram_hoan_thanh'],
            'so_bat_buoc_da_dat': tien_do['so_bat_buoc_da_dat'],
            'tong_so_bat_buoc': tien_do['tong_so_bat_buoc'],
        })
    return ket_qua


def _canh_bao(sinh_vien, hoc_ky_gan_nhat):
    """Cảnh báo học vụ ở học kỳ gần nhất có đủ điểm, hoặc None nếu không bị cảnh báo. Logic
    cảnh báo có sẵn chỉ có hai điều kiện, nên mức độ hiển thị chia theo số lý do: một lý do là
    mức nhẹ (nền vàng nhạt), cả hai là mức nặng (nền đỏ nhạt)."""
    if hoc_ky_gan_nhat is None:
        return None
    hoc_ky, nam_hoc = hoc_ky_gan_nhat
    ket_qua = canh_bao_hoc_vu(sinh_vien, hoc_ky, nam_hoc, chi_diem_da_cong_bo=True)
    if not ket_qua['canh_bao']:
        return None
    return {
        'hoc_ky': hoc_ky, 'nam_hoc': nam_hoc, 'ly_do': ket_qua['ly_do'],
        'muc': 'nang' if len(ket_qua['ly_do']) >= 2 else 'nhe',
    }


def _lich_thi_sap_toi(sinh_vien, hom_nay):
    return list(
        LichThi.objects.filter(
            lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
            lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
            ngay_thi__gte=hom_nay,
        ).select_related('lop_hoc_phan__ma_hoc_phan').order_by('ngay_thi', 'gio_bat_dau')[:SO_LICH_THI_TOI_DA]
    )


def _buoi_hoc(sinh_vien, hom_nay):
    """Số buổi học hôm nay/tuần này từ thời khóa biểu. lich_hoc chỉ có thứ + tiết (không có
    ngày cụ thể), nên chỉ tính các lớp thuộc học kỳ đang diễn ra hôm nay theo danh mục hoc_ky;
    không có học kỳ hiện tại hoặc không có buổi học nào thì trả về None (không hiển thị)."""
    hoc_ky = HocKy.objects.filter(ngay_bat_dau__lte=hom_nay, ngay_ket_thuc__gte=hom_nay).first()
    if hoc_ky is None:
        return None
    tuan_nay = list(
        LichHoc.objects.filter(
            ma_lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
            ma_lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
            ma_lop_hoc_phan__hoc_ky=str(hoc_ky.hoc_ky),
            ma_lop_hoc_phan__nam_hoc=hoc_ky.nam_hoc,
        ).select_related('ma_lop_hoc_phan__ma_hoc_phan').order_by('thu', 'tiet_bat_dau')
    )
    if not tuan_nay:
        return None
    thu_hom_nay = hom_nay.weekday() + 2  # Thứ 2 = 2, ..., Chủ nhật = 8 (giống lich_hoc.thu)
    hom_nay_ds = [lich for lich in tuan_nay if lich.thu == thu_hom_nay]
    return {
        'ten_thu': dict(CAC_THU)[thu_hom_nay],
        'so_hom_nay': len(hom_nay_ds),
        'so_tuan_nay': len(tuan_nay),
        'hom_nay': hom_nay_ds[:SO_BUOI_HOM_NAY_TOI_DA],
        'so_hom_nay_con_lai': max(len(hom_nay_ds) - SO_BUOI_HOM_NAY_TOI_DA, 0),
    }


def thong_bao_moi_nhat(tai_khoan, so_luong=SO_THONG_BAO_TOI_DA):
    return list(
        thong_bao_lien_quan(tai_khoan).annotate(
            da_doc_boi_toi=Exists(DaDocThongBao.objects.filter(thong_bao=OuterRef('pk'), tai_khoan=tai_khoan))
        )[:so_luong]
    )


def tong_hop_trang_chu_sinh_vien(tai_khoan, sinh_vien):
    """Toàn bộ dữ liệu trang chủ Sinh viên. sinh_vien có thể là None (tài khoản chưa gắn hồ
    sơ) — khi đó chỉ trả về cờ co_ho_so=False và các thông báo (không cần hồ sơ)."""
    ket_qua = {'co_ho_so': sinh_vien is not None, 'thong_bao_moi': thong_bao_moi_nhat(tai_khoan)}
    if sinh_vien is None:
        return ket_qua

    hom_nay = timezone.localdate()
    hoc_ky_gan_nhat = hoc_ky_gan_nhat_co_du_diem(sinh_vien, chi_diem_da_cong_bo=True)
    lich_thi = _lich_thi_sap_toi(sinh_vien, hom_nay)
    buoi_hoc = _buoi_hoc(sinh_vien, hom_nay)
    ket_qua.update({
        'sinh_vien': sinh_vien,
        'tom_tat': _tom_tat_hoc_tap(sinh_vien, hoc_ky_gan_nhat),
        'canh_bao': _canh_bao(sinh_vien, hoc_ky_gan_nhat),
        'lich_thi': lich_thi,
        'buoi_hoc': buoi_hoc,
        'co_sap_dien_ra': bool(lich_thi or buoi_hoc),
    })
    return ket_qua
