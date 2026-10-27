"""Email và số điện thoại không được trùng giữa mọi hồ sơ sinh viên, giảng viên, cố vấn học tập.

- Email so sánh không phân biệt hoa thường.
- Số điện thoại so sánh sau khi bỏ khoảng trắng, dấu chấm, gạch, ngoặc ("0912 345 678" trùng "0912345678").
- Chỉ kiểm tra khi giá trị thay đổi so với hồ sơ đang sửa: dữ liệu cũ đang trùng không chặn việc sửa trường khác.
Ba bảng là ba bảng riêng (docs/erd.md) nên không đặt được ràng buộc UNIQUE chung ở CSDL; kiểm tra ở form và nhập Excel.
"""
import re

from .models import CoVanHocTap, GiangVien, SinhVien

_CAC_LOAI_HO_SO = (
    (SinhVien, 'sinh viên'),
    (GiangVien, 'giảng viên'),
    (CoVanHocTap, 'cố vấn học tập'),
)


def chuan_hoa_so_dien_thoai(so_dien_thoai):
    return re.sub(r'[\s.\-()]', '', so_dien_thoai or '')


def _cac_ho_so_khac(bo_qua):
    for model, nhan in _CAC_LOAI_HO_SO:
        qs = model.objects.all()
        if bo_qua is not None and bo_qua.pk and isinstance(bo_qua, model):
            qs = qs.exclude(pk=bo_qua.pk)
        yield qs, nhan


def _mo_ta(nhan, ho_so):
    return f'{nhan} {ho_so.pk} ({ho_so.ho_ten})'


def ho_so_trung_email(email, bo_qua=None):
    """Mô tả hồ sơ khác đang dùng email này (ví dụ 'sinh viên SV001 (Nguyễn Văn A)'), hoặc None."""
    email = (email or '').strip()
    if not email:
        return None
    for qs, nhan in _cac_ho_so_khac(bo_qua):
        ho_so = qs.filter(email__iexact=email).first()
        if ho_so is not None:
            return _mo_ta(nhan, ho_so)
    return None


def ho_so_trung_so_dien_thoai(so_dien_thoai, bo_qua=None):
    """Mô tả hồ sơ khác đang dùng số điện thoại này (so sánh sau chuẩn hóa), hoặc None."""
    can_tim = chuan_hoa_so_dien_thoai(so_dien_thoai)
    if not can_tim:
        return None
    for qs, nhan in _cac_ho_so_khac(bo_qua):
        for ho_so in qs.only('pk', 'ho_ten', 'so_dien_thoai'):
            if chuan_hoa_so_dien_thoai(ho_so.so_dien_thoai) == can_tim:
                return _mo_ta(nhan, ho_so)
    return None


def kiem_tra_lien_he(email, so_dien_thoai, ho_so_dang_sua=None, chi_tiet=True):
    """Trả dict {'email': thông báo lỗi, 'so_dien_thoai': thông báo lỗi} (chỉ có khóa bị trùng).

    chi_tiet=False (trang Thông tin cá nhân của chính người dùng): không nêu hồ sơ nào đang dùng, tránh lộ
    thông tin người khác; chi_tiet=True (Phòng Đào tạo): nêu rõ để xử lý.
    """
    loi = {}
    email_cu = (getattr(ho_so_dang_sua, 'email', '') or '').strip().lower()
    if email is not None and (email or '').strip().lower() != email_cu:
        trung = ho_so_trung_email(email, ho_so_dang_sua)
        if trung:
            loi['email'] = (f'Email "{email.strip()}" đã được dùng cho {trung}.' if chi_tiet
                            else 'Email này đã được dùng cho một hồ sơ khác, vui lòng dùng email khác.')
    sdt_cu = chuan_hoa_so_dien_thoai(getattr(ho_so_dang_sua, 'so_dien_thoai', ''))
    if so_dien_thoai is not None and chuan_hoa_so_dien_thoai(so_dien_thoai) != sdt_cu:
        trung = ho_so_trung_so_dien_thoai(so_dien_thoai, ho_so_dang_sua)
        if trung:
            loi['so_dien_thoai'] = (f'Số điện thoại "{so_dien_thoai.strip()}" đã được dùng cho {trung}.' if chi_tiet
                                    else 'Số điện thoại này đã được dùng cho một hồ sơ khác, vui lòng dùng số khác.')
    return loi
