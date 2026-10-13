from django.db.models import Q

from enrollment.models import TrangThaiDangKy

from .models import DaDocThongBao, DoiTuongThongBao, ThongBao


def _dieu_kien_lien_quan(tai_khoan):
    """Điều kiện lọc ThongBao mà tai_khoan này được xem, theo đúng vai trò và các lớp
    mình thuộc/đăng ký/phụ trách — dùng chung cho danh sách và đếm số chưa đọc."""
    dieu_kien = Q(doi_tuong=DoiTuongThongBao.TAT_CA) | Q(doi_tuong=tai_khoan.vai_tro)

    sinh_vien = getattr(tai_khoan, 'ho_so_sinh_vien', None)
    if sinh_vien is not None:
        dieu_kien |= Q(
            doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN,
            lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
            lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        )
        dieu_kien |= Q(doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH, lop_hanh_chinh=sinh_vien.ma_lop_id)

    giang_vien = getattr(tai_khoan, 'ho_so_giang_vien', None)
    if giang_vien is not None:
        dieu_kien |= Q(doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN, lop_hoc_phan__ma_giang_vien=giang_vien)

    co_van = getattr(tai_khoan, 'ho_so_co_van', None)
    if co_van is not None:
        dieu_kien |= Q(doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH, lop_hanh_chinh__ma_co_van=co_van)

    return dieu_kien


def thong_bao_lien_quan(tai_khoan):
    """Danh sách thông báo mà tai_khoan này được xem, mới nhất trước — dùng .distinct() vì
    một sinh viên có thể khớp điều kiện lớp học phần qua nhiều dòng đăng ký khác nhau."""
    return ThongBao.objects.filter(_dieu_kien_lien_quan(tai_khoan)).select_related(
        'nguoi_gui', 'lop_hoc_phan__ma_hoc_phan', 'lop_hanh_chinh',
    ).distinct()


def so_luong_chua_doc(tai_khoan):
    return thong_bao_lien_quan(tai_khoan).exclude(da_doc__tai_khoan=tai_khoan).count()


def danh_dau_da_doc(thong_bao, tai_khoan):
    DaDocThongBao.objects.get_or_create(thong_bao=thong_bao, tai_khoan=tai_khoan)
