from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

from enrollment.models import DangKyHocPhan, TrangThaiDangKy

# Mốc xếp loại học lực theo điểm trung bình (thang 10), duyệt từ cao xuống thấp — mốc
# đầu tiên mà điểm trung bình đạt được là xếp loại tương ứng.
_MOC_XEP_LOAI = [
    (Decimal('9'), 'Xuất sắc'),
    (Decimal('8'), 'Giỏi'),
    (Decimal('7'), 'Khá'),
    (Decimal('5'), 'Trung bình'),
    (Decimal('4'), 'Yếu'),
]


def bang_diem_chi_tiet(sinh_vien, hoc_ky=None, nam_hoc=None):
    """Danh sách học phần sinh viên đã có đủ điểm (điểm quá trình + điểm thi) để tính
    điểm tổng kết, mỗi học phần một dòng đại diện (nếu học lại nhiều lần thì giữ lần có
    điểm tổng kết cao nhất). Dùng đúng Diem.tinh_diem_tong_ket() (bọc grades.tinh_diem),
    không tính lại công thức điểm ở đây.

    Chỉ xét đăng ký còn hiệu lực (một đăng ký đã hủy không thể có điểm — việc hủy bị chặn
    khi đã có điểm — nhưng lọc tường minh cho đúng yêu cầu "chỉ tính đăng ký còn hiệu lực").

    hoc_ky/nam_hoc (tùy chọn) giới hạn trong một học kỳ hoặc một năm học (dùng cho tóm tắt AI theo phạm vi);
    mặc định lấy mọi học kỳ như trước.

    Trả về list[dict]: {'hoc_phan', 'hoc_ky', 'nam_hoc', 'diem_qua_trinh', 'diem_thi',
    'diem_tong_ket', 'dat'}.
    """
    theo_hoc_phan = {}
    dang_ky_qs = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan', 'diem')
    if hoc_ky is not None:
        dang_ky_qs = dang_ky_qs.filter(ma_lop_hoc_phan__hoc_ky=hoc_ky)
    if nam_hoc is not None:
        dang_ky_qs = dang_ky_qs.filter(ma_lop_hoc_phan__nam_hoc=nam_hoc)
    for dang_ky in dang_ky_qs:
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            continue
        diem_tong_ket = diem.tinh_diem_tong_ket()
        if diem_tong_ket is None:
            continue
        hoc_phan = dang_ky.ma_lop_hoc_phan.ma_hoc_phan
        muc = {
            'hoc_phan': hoc_phan,
            'hoc_ky': dang_ky.ma_lop_hoc_phan.hoc_ky,
            'nam_hoc': dang_ky.ma_lop_hoc_phan.nam_hoc,
            'diem_qua_trinh': diem.diem_qua_trinh,
            'diem_thi': diem.diem_thi,
            'diem_tong_ket': diem_tong_ket,
            'dat': diem_tong_ket >= settings.DIEM_DAT_TOI_THIEU,
        }
        hien_co = theo_hoc_phan.get(hoc_phan.pk)
        if hien_co is None or diem_tong_ket > hien_co['diem_tong_ket']:
            theo_hoc_phan[hoc_phan.pk] = muc
    return list(theo_hoc_phan.values())


def xep_loai_hoc_luc(diem_trung_binh):
    """Xếp loại học lực theo điểm trung bình (thang 10): Xuất sắc (9-10), Giỏi (8 đến
    dưới 9), Khá (7 đến dưới 8), Trung bình (5 đến dưới 7), Yếu (4 đến dưới 5), Kém (dưới
    4). Trả về None nếu chưa có điểm trung bình để xếp loại."""
    if diem_trung_binh is None:
        return None
    for moc, ten in _MOC_XEP_LOAI:
        if diem_trung_binh >= moc:
            return ten
    return 'Kém'


def _danh_sach_diem_hop_le(sinh_vien, chi_diem_da_cong_bo, hoc_ky=None, nam_hoc=None):
    """Danh sách (dang_ky, diem_tong_ket) có đủ điểm, chỉ tính đăng ký còn hiệu lực — dùng
    chung cho điểm trung bình và cảnh báo học vụ để không viết lại quy tắc.

    chi_diem_da_cong_bo=True lọc thêm da_cong_bo=True trên từng điểm (dùng khi chính sinh
    viên tự xem — theo yêu cầu, điểm chưa công bố không được tính vào điểm trung
    bình/tích lũy/cảnh báo học vụ ở phía sinh viên). Mặc định False: giữ nguyên điểm thật,
    dùng cho Giảng viên/Cố vấn học tập/Phòng Đào tạo.
    """
    dang_ky_qs = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan', 'diem')
    if hoc_ky is not None:
        dang_ky_qs = dang_ky_qs.filter(ma_lop_hoc_phan__hoc_ky=hoc_ky)
    if nam_hoc is not None:
        dang_ky_qs = dang_ky_qs.filter(ma_lop_hoc_phan__nam_hoc=nam_hoc)

    ket_qua = []
    for dang_ky in dang_ky_qs:
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            continue
        if chi_diem_da_cong_bo and not diem.da_cong_bo:
            continue
        diem_tong_ket = diem.tinh_diem_tong_ket()
        if diem_tong_ket is None:
            continue
        ket_qua.append((dang_ky, diem_tong_ket))
    return ket_qua


def _trung_binh_co_trong_so(danh_sach_dang_ky_diem):
    """Trung bình điểm tổng kết có trọng số theo số tín chỉ của từng học phần."""
    if not danh_sach_dang_ky_diem:
        return None
    tong_diem_x_tin_chi = Decimal('0')
    tong_tin_chi = 0
    for dang_ky, diem_tong_ket in danh_sach_dang_ky_diem:
        so_tin_chi = dang_ky.ma_lop_hoc_phan.ma_hoc_phan.so_tin_chi
        tong_diem_x_tin_chi += diem_tong_ket * so_tin_chi
        tong_tin_chi += so_tin_chi
    if tong_tin_chi == 0:
        return None
    return (tong_diem_x_tin_chi / tong_tin_chi).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def diem_trung_binh_hoc_ky(sinh_vien, hoc_ky, nam_hoc, chi_diem_da_cong_bo=False):
    """Điểm trung bình có trọng số tín chỉ của một học kỳ cụ thể, chỉ tính học phần có đủ
    điểm và đăng ký còn hiệu lực. None nếu học kỳ đó chưa có học phần nào đủ điểm."""
    return _trung_binh_co_trong_so(_danh_sach_diem_hop_le(sinh_vien, chi_diem_da_cong_bo, hoc_ky, nam_hoc))


def diem_trung_binh_nam_hoc(sinh_vien, nam_hoc, chi_diem_da_cong_bo=False):
    """Điểm trung bình có trọng số tín chỉ của cả một năm học (mọi học kỳ của năm đó), cùng quy tắc
    với điểm trung bình học kỳ. None nếu năm học đó chưa có học phần nào đủ điểm."""
    return _trung_binh_co_trong_so(_danh_sach_diem_hop_le(sinh_vien, chi_diem_da_cong_bo, nam_hoc=nam_hoc))


def diem_trung_binh_tich_luy(sinh_vien, chi_diem_da_cong_bo=False):
    """Điểm trung bình tích lũy có trọng số tín chỉ trên toàn bộ học phần đã có đủ điểm
    (đăng ký còn hiệu lực), không giới hạn học kỳ/năm học."""
    return _trung_binh_co_trong_so(_danh_sach_diem_hop_le(sinh_vien, chi_diem_da_cong_bo))


def hoc_ky_gan_nhat_co_du_diem(sinh_vien, chi_diem_da_cong_bo=False):
    """(hoc_ky, nam_hoc) gần nhất mà sinh viên có ít nhất một học phần đủ điểm (đăng ký
    còn hiệu lực), hoặc None nếu chưa có học kỳ nào như vậy. Dùng làm học kỳ mặc định để
    hiển thị điểm trung bình/cảnh báo học vụ khi người dùng chưa chọn học kỳ."""
    dang_ky_qs = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan', 'diem').order_by('-ma_lop_hoc_phan__nam_hoc', '-ma_lop_hoc_phan__hoc_ky')
    for dang_ky in dang_ky_qs:
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            continue
        if chi_diem_da_cong_bo and not diem.da_cong_bo:
            continue
        if diem.tinh_diem_tong_ket() is None:
            continue
        return dang_ky.ma_lop_hoc_phan.hoc_ky, dang_ky.ma_lop_hoc_phan.nam_hoc
    return None


def canh_bao_hoc_vu(sinh_vien, hoc_ky, nam_hoc, chi_diem_da_cong_bo=False):
    """Cảnh báo học vụ của một học kỳ cụ thể theo 2 điều kiện: (1) điểm trung bình học kỳ
    dưới 5.0, hoặc (2) có từ 2 học phần chưa đạt (DIEM_DAT_TOI_THIEU) trở lên trong học kỳ
    đó. Chỉ tính học phần có đủ điểm và đăng ký còn hiệu lực.

    Trả về dict {'canh_bao': bool, 'ly_do': list[str], 'diem_trung_binh': Decimal|None,
    'so_hoc_phan_chua_dat': int}.
    """
    danh_sach = _danh_sach_diem_hop_le(sinh_vien, chi_diem_da_cong_bo, hoc_ky, nam_hoc)
    if not danh_sach:
        return {'canh_bao': False, 'ly_do': [], 'diem_trung_binh': None, 'so_hoc_phan_chua_dat': 0}

    diem_trung_binh = _trung_binh_co_trong_so(danh_sach)
    so_chua_dat = sum(1 for _, diem_tong_ket in danh_sach if diem_tong_ket < settings.DIEM_DAT_TOI_THIEU)

    ly_do = []
    if diem_trung_binh is not None and diem_trung_binh < Decimal('5.0'):
        ly_do.append(f'Điểm trung bình học kỳ ({diem_trung_binh}) dưới 5.0.')
    if so_chua_dat >= 2:
        ly_do.append(f'Có {so_chua_dat} học phần chưa đạt trong học kỳ.')

    return {
        'canh_bao': bool(ly_do), 'ly_do': ly_do,
        'diem_trung_binh': diem_trung_binh, 'so_hoc_phan_chua_dat': so_chua_dat,
    }
