from enrollment.services import danh_sach_hoc_phan_da_dat

from academics.models import ChiTietChuongTrinh


def tinh_tien_do(sinh_vien, chi_diem_da_cong_bo=False):
    """Tính tiến độ chương trình đào tạo của một sinh viên.

    Lấy chương trình đào tạo qua lớp hành chính của sinh viên (academics.LopHanhChinh.
    chuong_trinh_dao_tao — có thể chưa gán). So sánh chi_tiet_chuong_trinh của chương
    trình đó với danh sách học phần đã đạt — dùng lại đúng
    enrollment.services.danh_sach_hoc_phan_da_dat (điểm tổng kết từ settings.
    DIEM_DAT_TOI_THIEU, chỉ tính đăng ký còn hiệu lực), không tính lại ngưỡng đạt ở đây.

    chi_diem_da_cong_bo=True lọc thêm điểm đã công bố — dùng khi chính sinh viên tự xem
    tiến độ của mình (điểm chưa công bố không được coi là "đã đạt"). Mặc định False (điểm
    thật) khi Cố vấn học tập xem tiến độ của một sinh viên phụ trách.

    Trả về dict:
    - co_chuong_trinh: False nếu lớp hành chính chưa gán chương trình đào tạo.
    - chuong_trinh: ChuongTrinhDaoTao hoặc None.
    - da_dat_bat_buoc/da_dat_tu_chon, con_thieu_bat_buoc/con_thieu_tu_chon: list[ChiTietChuongTrinh].
    - so_bat_buoc_da_dat, tong_so_bat_buoc: int.
    - phan_tram_hoan_thanh: float, chỉ tính trên học phần bắt buộc.
    """
    chuong_trinh = sinh_vien.ma_lop.chuong_trinh_dao_tao
    if chuong_trinh is None:
        return {'co_chuong_trinh': False, 'chuong_trinh': None}

    ma_hoc_phan_da_dat = {
        hoc_phan.pk for hoc_phan, _ in danh_sach_hoc_phan_da_dat(sinh_vien, chi_diem_da_cong_bo)
    }

    chi_tiet_qs = ChiTietChuongTrinh.objects.filter(chuong_trinh=chuong_trinh).select_related(
        'hoc_phan'
    ).order_by('hoc_ky_du_kien', 'hoc_phan')

    da_dat_bat_buoc, da_dat_tu_chon = [], []
    con_thieu_bat_buoc, con_thieu_tu_chon = [], []
    for chi_tiet in chi_tiet_qs:
        da_dat = chi_tiet.hoc_phan_id in ma_hoc_phan_da_dat
        if chi_tiet.bat_buoc:
            (da_dat_bat_buoc if da_dat else con_thieu_bat_buoc).append(chi_tiet)
        else:
            (da_dat_tu_chon if da_dat else con_thieu_tu_chon).append(chi_tiet)

    tong_so_bat_buoc = len(da_dat_bat_buoc) + len(con_thieu_bat_buoc)
    phan_tram_hoan_thanh = round(len(da_dat_bat_buoc) * 100 / tong_so_bat_buoc, 1) if tong_so_bat_buoc else 0

    return {
        'co_chuong_trinh': True,
        'chuong_trinh': chuong_trinh,
        'da_dat_bat_buoc': da_dat_bat_buoc,
        'da_dat_tu_chon': da_dat_tu_chon,
        'con_thieu_bat_buoc': con_thieu_bat_buoc,
        'con_thieu_tu_chon': con_thieu_tu_chon,
        'so_bat_buoc_da_dat': len(da_dat_bat_buoc),
        'tong_so_bat_buoc': tong_so_bat_buoc,
        'phan_tram_hoan_thanh': phan_tram_hoan_thanh,
    }
