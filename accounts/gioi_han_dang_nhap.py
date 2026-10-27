"""Tạm chặn đăng nhập sau nhiều lần sai, theo tên đăng nhập và theo IP; giới hạn số yêu cầu "Quên mật khẩu" theo
email và theo IP. Dùng cache của Django (không tạo bảng CSDL mới — theo quy ước dự án).

- Sai SO_LAN_SAI_TOI_DA lần trong CUA_SO_GIAY giây (tính từ lần sai đầu tiên) thì chặn THOI_GIAN_CHAN_GIAY giây.
- Đếm cả tên đăng nhập không tồn tại, để thông báo tạm chặn không tiết lộ tài khoản nào có thật.
- Khóa cache dùng mã băm, không chứa tên đăng nhập hay IP ở dạng rõ.
- IP lấy từ REMOTE_ADDR (không tin X-Forwarded-For do người dùng tự gửi được).
"""
import hashlib

from django.core.cache import cache

SO_LAN_SAI_TOI_DA = 5
CUA_SO_GIAY = 15 * 60
THOI_GIAN_CHAN_GIAY = 15 * 60


def _khoa(loai, gia_tri):
    return f'dang_nhap_sai:{loai}:{hashlib.sha256(gia_tri.encode()).hexdigest()}'


def _cac_doi_tuong(ten_dang_nhap, ip):
    doi_tuong = []
    if ten_dang_nhap:
        doi_tuong.append(('ten', ten_dang_nhap.strip().lower()))
    if ip:
        doi_tuong.append(('ip', ip))
    return doi_tuong


def lay_ip(request):
    return (request.META.get('REMOTE_ADDR') or '') if request is not None else ''


def dang_bi_chan(ten_dang_nhap, ip):
    return any(cache.get(_khoa(f'chan_{loai}', gia_tri)) for loai, gia_tri in _cac_doi_tuong(ten_dang_nhap, ip))


def ghi_nhan_sai(ten_dang_nhap, ip):
    for loai, gia_tri in _cac_doi_tuong(ten_dang_nhap, ip):
        khoa_dem = _khoa(loai, gia_tri)
        cache.add(khoa_dem, 0, timeout=CUA_SO_GIAY)
        if cache.incr(khoa_dem) >= SO_LAN_SAI_TOI_DA:
            cache.set(_khoa(f'chan_{loai}', gia_tri), True, timeout=THOI_GIAN_CHAN_GIAY)
            cache.delete(khoa_dem)


SO_YEU_CAU_QUEN_MAT_KHAU_TOI_DA = 3


def cho_phep_yeu_cau_quen_mat_khau(email, ip):
    """Đếm một yêu cầu "Quên mật khẩu"; False nếu email hoặc IP đã vượt SO_YEU_CAU_QUEN_MAT_KHAU_TOI_DA yêu cầu
    trong CUA_SO_GIAY giây. Đếm cả email không có trong hệ thống, nên thông báo vượt giới hạn không lộ email nào có
    thật."""
    vuot = False
    for loai, gia_tri in (('quen_email', (email or '').strip().lower()), ('quen_ip', ip)):
        if not gia_tri:
            continue
        khoa = _khoa(loai, gia_tri)
        cache.add(khoa, 0, timeout=CUA_SO_GIAY)
        if cache.incr(khoa) > SO_YEU_CAU_QUEN_MAT_KHAU_TOI_DA:
            vuot = True
    return not vuot


def xoa_dem_sai(ten_dang_nhap):
    """Đăng nhập đúng hoặc đặt lại mật khẩu qua email thì xóa số lần sai và trạng thái tạm chặn của tên đăng nhập
    đó (bộ đếm theo IP giữ nguyên, để một tài khoản đúng không mở đường thử tiếp các tài khoản khác từ cùng IP)."""
    for loai, gia_tri in _cac_doi_tuong(ten_dang_nhap, ''):
        cache.delete_many([_khoa(loai, gia_tri), _khoa(f'chan_{loai}', gia_tri)])
