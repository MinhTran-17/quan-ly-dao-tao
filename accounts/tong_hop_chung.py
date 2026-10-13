"""Phần dùng chung của dữ liệu tổng hợp ở trang chủ các vai trò (Giảng viên, Cố vấn học tập)."""
from django.db.models import Exists, OuterRef

from thong_bao.models import DaDocThongBao
from thong_bao.services import thong_bao_lien_quan

SO_THONG_BAO_TOI_DA = 5
SO_MA_TOI_DA_TRONG_DONG = 3


def liet_ke(danh_sach, toi_da=SO_MA_TOI_DA_TRONG_DONG, don_vi='mục'):
    """"A, B, C và 2 sinh viên khác" — ghép tối đa `toi_da` phần tử đầu và nêu số còn lại."""
    danh_sach = list(danh_sach)
    hien = ', '.join(danh_sach[:toi_da])
    con_lai = len(danh_sach) - toi_da
    return hien + (f' và {con_lai} {don_vi} khác' if con_lai > 0 else '')


def thong_bao_gan_day(tai_khoan, so_luong=SO_THONG_BAO_TOI_DA):
    """Các thông báo liên quan tới tài khoản (cùng phạm vi trang "Thông báo"), mới nhất trước; mỗi thông báo có cờ
    da_doc_boi_toi. Chỉ đọc, không tự đánh dấu đã đọc."""
    return list(
        thong_bao_lien_quan(tai_khoan).annotate(
            da_doc_boi_toi=Exists(DaDocThongBao.objects.filter(thong_bao=OuterRef('pk'), tai_khoan=tai_khoan))
        )[:so_luong]
    )
