from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from academics.models import DieuKienTienQuyet
from academics.services import trang_thai_dot_dang_ky
from classes.models import LichHoc, LopHocPhan

from .models import DangKyHocPhan, TrangThaiDangKy

# Mã trạng thái của một sinh viên đối với một lớp học phần (xac_dinh_trang_thai).
# Dùng chung cho việc đăng ký thật và cho tư vấn (không ghi CSDL).
DU_DIEU_KIEN = 'du_dieu_kien'
DA_DANG_KY = 'da_dang_ky'
THIEU_TIEN_QUYET = 'thieu_tien_quyet'
TRUNG_LICH = 'trung_lich'
DA_DAY = 'da_day'
NGOAI_DOT_DANG_KY = 'ngoai_dot_dang_ky'


class LoiDangKyHocPhan(Exception):
    """Lỗi nghiệp vụ khi đăng ký học phần; thông điệp đã sẵn sàng hiển thị cho người dùng."""


def _da_dat_hoc_phan(sinh_vien, ma_hoc_phan_id):
    """Sinh viên đã có lần đăng ký nào của học phần này đạt điểm tổng kết >= ngưỡng chưa.

    Chỉ xét các đăng ký CÒN HIỆU LỰC (một đăng ký đã hủy không thể có điểm — việc hủy bị
    chặn khi đã có điểm, xem huy_dang_ky_hoc_phan — nhưng lọc tường minh ở đây để đúng yêu
    cầu "chỉ tính đăng ký còn hiệu lực" bất kể dữ liệu lịch sử).

    Truy cập điểm qua thuộc tính ngược "diem" (từ grades.Diem.ma_dang_ky) thay vì
    import model Diem trực tiếp, để enrollment không phụ thuộc Python vào app grades
    (grades mới là app có khóa ngoại trỏ về enrollment).
    """
    dang_ky_qs = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien,
        ma_lop_hoc_phan__ma_hoc_phan_id=ma_hoc_phan_id,
        trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('diem')
    for dang_ky in dang_ky_qs:
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            continue
        diem_tong_ket = diem.tinh_diem_tong_ket()
        if diem_tong_ket is not None and diem_tong_ket >= settings.DIEM_DAT_TOI_THIEU:
            return True
    return False


def danh_sach_hoc_phan_da_dat(sinh_vien, chi_diem_da_cong_bo=False):
    """Danh sách (hoc_phan, diem_tong_ket) sinh viên đã đạt, xét trên các lần đăng ký còn
    hiệu lực (nếu học lại nhiều lần thì giữ điểm tổng kết cao nhất). Dùng chung công thức
    tính điểm và ngưỡng đạt với _da_dat_hoc_phan, không viết lại quy tắc.

    chi_diem_da_cong_bo=True lọc thêm điểm đã công bố (grades.Diem.da_cong_bo=True) — dùng
    khi gọi cho chính sinh viên tự xem (vd. trang tiến độ học tập của sinh viên), để điểm
    chưa công bố không được coi là "đã đạt". Mặc định False giữ nguyên hành vi cũ (điểm
    thật, không lọc) cho các nơi gọi khác (vd. tư vấn AI/đăng ký — ngoài phạm vi thay đổi
    lần này)."""
    ket_qua = {}
    dang_ky_qs = DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan__ma_hoc_phan', 'diem')
    for dang_ky in dang_ky_qs:
        diem = getattr(dang_ky, 'diem', None)
        if diem is None:
            continue
        if chi_diem_da_cong_bo and not diem.da_cong_bo:
            continue
        diem_tong_ket = diem.tinh_diem_tong_ket()
        if diem_tong_ket is None or diem_tong_ket < settings.DIEM_DAT_TOI_THIEU:
            continue
        hoc_phan = dang_ky.ma_lop_hoc_phan.ma_hoc_phan
        if hoc_phan.pk not in ket_qua or diem_tong_ket > ket_qua[hoc_phan.pk][1]:
            ket_qua[hoc_phan.pk] = (hoc_phan, diem_tong_ket)
    return list(ket_qua.values())


def tim_hoc_phan_tien_quyet_con_thieu(sinh_vien, hoc_phan):
    """Danh sách HocPhan tiên quyết mà sinh viên CHƯA đạt (rỗng nếu đã đủ điều kiện)."""
    con_thieu = []
    dieu_kien_qs = DieuKienTienQuyet.objects.filter(ma_hoc_phan=hoc_phan).select_related('ma_hoc_phan_tien_quyet')
    for dieu_kien in dieu_kien_qs:
        tien_quyet = dieu_kien.ma_hoc_phan_tien_quyet
        if not _da_dat_hoc_phan(sinh_vien, tien_quyet.pk):
            con_thieu.append(tien_quyet)
    return con_thieu


def _kiem_tra_tien_quyet(sinh_vien, hoc_phan):
    con_thieu = tim_hoc_phan_tien_quyet_con_thieu(sinh_vien, hoc_phan)
    if con_thieu:
        raise LoiDangKyHocPhan(f'Chưa đạt học phần tiên quyết "{con_thieu[0].ten_hoc_phan}".')


def _khoang_tiet_giao_nhau(a_bat_dau, a_so_tiet, b_bat_dau, b_so_tiet):
    a_ket_thuc = a_bat_dau + a_so_tiet - 1
    b_ket_thuc = b_bat_dau + b_so_tiet - 1
    return a_bat_dau <= b_ket_thuc and b_bat_dau <= a_ket_thuc


def tim_lich_trung(sinh_vien, lop_hoc_phan):
    """Trả về LichHoc (thuộc lớp sinh viên đang có đăng ký CÒN HIỆU LỰC cùng học kỳ/năm
    học) trùng giờ với lịch của lop_hoc_phan, hoặc None nếu không trùng lớp nào."""
    lich_moi_qs = LichHoc.objects.filter(ma_lop_hoc_phan=lop_hoc_phan)
    lich_da_dang_ky_qs = LichHoc.objects.filter(
        ma_lop_hoc_phan__dang_ky__ma_sinh_vien=sinh_vien,
        ma_lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        ma_lop_hoc_phan__hoc_ky=lop_hoc_phan.hoc_ky,
        ma_lop_hoc_phan__nam_hoc=lop_hoc_phan.nam_hoc,
    ).select_related('ma_lop_hoc_phan')
    for lich_moi in lich_moi_qs:
        for lich_cu in lich_da_dang_ky_qs:
            if lich_moi.thu != lich_cu.thu:
                continue
            if _khoang_tiet_giao_nhau(lich_moi.tiet_bat_dau, lich_moi.so_tiet, lich_cu.tiet_bat_dau, lich_cu.so_tiet):
                return lich_cu
    return None


def _kiem_tra_trung_lich(sinh_vien, lop_hoc_phan):
    lich_cu = tim_lich_trung(sinh_vien, lop_hoc_phan)
    if lich_cu is not None:
        tiet_ket_thuc = lich_cu.tiet_bat_dau + lich_cu.so_tiet - 1
        raise LoiDangKyHocPhan(
            f'Lịch học trùng với lớp "{lich_cu.ma_lop_hoc_phan_id}" '
            f'(Thứ {lich_cu.thu}, tiết {lich_cu.tiet_bat_dau}-{tiet_ket_thuc}).'
        )


def xac_dinh_trang_thai(sinh_vien, lop_hoc_phan):
    """Xác định trạng thái của một sinh viên đối với một lớp học phần, KHÔNG ghi CSDL
    và không khóa dòng (chỉ để tra cứu/tư vấn, không dùng để đăng ký thật).

    Dùng đúng các hàm kiểm tra ở trên (đã đăng ký, đợt đăng ký, tiên quyết, trùng lịch,
    sĩ số) theo cùng thứ tự với dang_ky_hoc_phan(), không viết lại quy tắc nghiệp vụ.

    Trả về dict: {'trang_thai', 'hoc_phan_con_thieu', 'lich_trung', 'ly_do_dot_dang_ky'}.
    """
    if DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).exists():
        return {
            'trang_thai': DA_DANG_KY, 'hoc_phan_con_thieu': [], 'lich_trung': None, 'ly_do_dot_dang_ky': None,
        }

    dot = trang_thai_dot_dang_ky(lop_hoc_phan.hoc_ky, lop_hoc_phan.nam_hoc)
    if not dot['mo']:
        return {
            'trang_thai': NGOAI_DOT_DANG_KY, 'hoc_phan_con_thieu': [], 'lich_trung': None,
            'ly_do_dot_dang_ky': dot['ly_do'],
        }

    con_thieu = tim_hoc_phan_tien_quyet_con_thieu(sinh_vien, lop_hoc_phan.ma_hoc_phan)
    if con_thieu:
        return {
            'trang_thai': THIEU_TIEN_QUYET, 'hoc_phan_con_thieu': con_thieu, 'lich_trung': None,
            'ly_do_dot_dang_ky': None,
        }

    lich_trung = tim_lich_trung(sinh_vien, lop_hoc_phan)
    if lich_trung is not None:
        return {
            'trang_thai': TRUNG_LICH, 'hoc_phan_con_thieu': [], 'lich_trung': lich_trung,
            'ly_do_dot_dang_ky': None,
        }

    so_dang_ky = DangKyHocPhan.objects.filter(
        ma_lop_hoc_phan=lop_hoc_phan, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).count()
    if so_dang_ky >= lop_hoc_phan.si_so_toi_da:
        return {'trang_thai': DA_DAY, 'hoc_phan_con_thieu': [], 'lich_trung': None, 'ly_do_dot_dang_ky': None}

    return {'trang_thai': DU_DIEU_KIEN, 'hoc_phan_con_thieu': [], 'lich_trung': None, 'ly_do_dot_dang_ky': None}


@transaction.atomic
def dang_ky_hoc_phan(sinh_vien, lop_hoc_phan):
    """Đăng ký một sinh viên vào một lớp học phần.

    Thứ tự kiểm tra: đã có đăng ký còn hiệu lực cho lớp này chưa (chặn sớm để tránh báo
    nhầm "trùng lịch" với chính lớp đang đăng ký) -> đợt đăng ký -> tiên quyết -> trùng
    lịch -> sĩ số (theo quy ước dự án; kiểm tra đợt đăng ký thực hiện trước 3 kiểm tra sau).
    Khóa dòng lop_hoc_phan (SELECT ... FOR UPDATE) khi đếm sĩ số để 2 người không
    giành nhau chỗ cuối cùng.

    Sinh viên đã hủy đăng ký lớp này trước đó vẫn đăng ký lại được: mỗi lần gọi hàm này
    luôn TẠO DÒNG MỚI (không cập nhật dòng cũ), giữ nguyên lịch sử các lần hủy trước —
    xem UniqueConstraint uk_dang_ky_hoc_phan_dang_hieu_luc (chỉ chặn trùng ở các dòng còn
    hiệu lực, không chặn giữa các dòng lịch sử) ở enrollment/models.py.
    """
    if DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).exists():
        raise LoiDangKyHocPhan('Sinh viên đã đăng ký lớp học phần này rồi.')

    dot = trang_thai_dot_dang_ky(lop_hoc_phan.hoc_ky, lop_hoc_phan.nam_hoc)
    if not dot['mo']:
        raise LoiDangKyHocPhan(dot['ly_do'])

    _kiem_tra_tien_quyet(sinh_vien, lop_hoc_phan.ma_hoc_phan)
    _kiem_tra_trung_lich(sinh_vien, lop_hoc_phan)

    lop_khoa = LopHocPhan.objects.select_for_update().get(pk=lop_hoc_phan.pk)
    so_dang_ky = DangKyHocPhan.objects.filter(
        ma_lop_hoc_phan=lop_khoa, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).count()
    if so_dang_ky >= lop_khoa.si_so_toi_da:
        raise LoiDangKyHocPhan(f'Lớp học phần "{lop_khoa.ma_lop_hoc_phan}" đã đủ sĩ số.')

    try:
        return DangKyHocPhan.objects.create(
            ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_khoa, thoi_gian_dang_ky=timezone.now(),
        )
    except IntegrityError:
        raise LoiDangKyHocPhan('Sinh viên đã đăng ký lớp học phần này rồi.')


def huy_dang_ky_hoc_phan(dang_ky):
    """Hủy một đăng ký học phần: chỉ đổi trang_thai sang DA_HUY, KHÔNG xóa dòng, để giữ
    lịch sử. Chặn nếu đăng ký đã bị hủy trước đó, hoặc đã có điểm (quá trình hoặc thi).
    Không giới hạn theo đợt đăng ký — hủy được vào bất kỳ lúc nào trong học kỳ đó (khác
    với ĐĂNG KÝ, vốn bị giới hạn theo đợt ở dang_ky_hoc_phan())."""
    if dang_ky.trang_thai == TrangThaiDangKy.DA_HUY:
        raise LoiDangKyHocPhan('Đăng ký này đã được hủy trước đó.')
    diem = getattr(dang_ky, 'diem', None)
    if diem is not None and (diem.diem_qua_trinh is not None or diem.diem_thi is not None):
        raise LoiDangKyHocPhan('Không thể hủy vì lớp học phần này đã có điểm.')
    dang_ky.trang_thai = TrangThaiDangKy.DA_HUY
    dang_ky.save(update_fields=['trang_thai'])
    return dang_ky
