"""Quy tắc mã hồ sơ (mã sinh viên, mã giảng viên, mã cố vấn học tập): chỉ chữ cái không dấu và chữ số.

Mã là khóa chính và nằm trong URL (/nhan-su/sinh-vien/<mã>/sua/, /diem/sinh-vien/<mã>/). Ký tự như "/"
làm {% url %} ném NoReverseMatch và sập cả trang danh sách. Áp dụng ở form tạo hồ sơ và nhập Excel; dữ liệu
cũ không hợp lệ được báo bằng lệnh `python manage.py kiem_tra_ma_ho_so` và không làm sập trang (thuộc tính
ma_dung_duoc_trong_url của model: chỉ bỏ liên kết khi mã chứa "/" hay là "." ".."). 
"""
import re

MAU_MA_HO_SO = re.compile(r'[A-Za-z0-9]+')


def ma_hop_le(ma):
    return isinstance(ma, str) and MAU_MA_HO_SO.fullmatch(ma) is not None


def thong_bao_ma_khong_hop_le(nhan, ma):
    return (f'{nhan} "{ma}" không hợp lệ: chỉ được dùng chữ cái không dấu và chữ số (A-Z, a-z, 0-9), '
            'không có khoảng trắng, dấu tiếng Việt hay ký tự đặc biệt.')


def ma_dung_duoc_trong_url(ma):
    """Mã có tạo liên kết được không (dùng cho dữ liệu cũ khi hiển thị). Lỏng hơn ma_hop_le: chỉ loại mã chứa "/"
    (làm {% url %} ném NoReverseMatch vì bộ chuyển đổi <str:> không nhận "/"), mã rỗng, "." và ".." (trình duyệt tự
    rút gọn /../ thành đường dẫn khác). Ký tự khác như "]", dấu cách, chữ có dấu được Django mã hóa %xx và giải mã lại."""
    return isinstance(ma, str) and ma not in ('', '.', '..') and '/' not in ma
