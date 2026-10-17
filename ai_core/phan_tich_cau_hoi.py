"""Đọc phạm vi (học kỳ, năm học, toàn khóa) từ câu người dùng gõ trong khung chat AI.

Code tự hiểu câu hỏi bằng quy tắc đơn giản, KHÔNG gửi câu gõ cho AI để xác định phạm vi: mỗi tin nhắn tốn đúng một
lượt gọi AI, và nội dung câu gõ (dữ liệu không tin cậy) không thể điều khiển việc lấy dữ liệu nào. Phần chọn dữ liệu
theo phạm vi do từng chức năng tự làm (vd. chỉ lấy điểm của học kỳ đã đọc được).
"""
import re
import unicodedata
from dataclasses import dataclass

_NAM_HOC = re.compile(r'(20\d{2})\s*[-–/]\s*(20\d{2})')
_HOC_KY = re.compile(r'\b(?:hoc\s*ky|hoc\s*ki|ky|ki|hk)\s*([1-3])\b')
_TOAN_KHOA = re.compile(r'\b(?:toan khoa|toan bo|tat ca|tich luy|ca qua trinh)\b')
_GAN_NHAT = re.compile(r'\b(?:gan nhat|moi nhat|vua roi|ky nay|hoc ky nay)\b')


def bo_dau(van_ban):
    """Chữ thường, bỏ dấu tiếng Việt (đ -> d), gộp khoảng trắng — để so khớp "kỳ"/"kì"/"ky" như nhau."""
    van_ban = unicodedata.normalize('NFD', (van_ban or '').lower().replace('đ', 'd'))
    van_ban = ''.join(ky_tu for ky_tu in van_ban if unicodedata.category(ky_tu) != 'Mn')
    return re.sub(r'\s+', ' ', van_ban).strip()


@dataclass
class PhamVi:
    """Phạm vi đọc được từ câu gõ. Mọi trường đều có thể trống (người dùng không nói tới)."""
    hoc_ky: str = ''        # '1', '2', '3'
    nam_hoc: str = ''       # '2024-2025'
    toan_khoa: bool = False  # "toàn khóa", "tất cả", "tích lũy"...
    gan_nhat: bool = False   # "học kỳ gần nhất", "kỳ này"...

    @property
    def co_noi_toi(self):
        return bool(self.hoc_ky or self.nam_hoc or self.toan_khoa or self.gan_nhat)


def doc_pham_vi(cau_go):
    """Đọc học kỳ, năm học, "toàn khóa", "gần nhất" từ câu gõ. Năm học chỉ nhận dạng YYYY-YYYY liên tiếp
    (vd. 2024-2025); "năm 2024" một mình không đủ để biết năm học nào nên bỏ qua."""
    chu = bo_dau(cau_go)
    pham_vi = PhamVi()
    khop_nam = _NAM_HOC.search(chu)
    if khop_nam and int(khop_nam.group(2)) == int(khop_nam.group(1)) + 1:
        pham_vi.nam_hoc = f'{khop_nam.group(1)}-{khop_nam.group(2)}'
    khop_ky = _HOC_KY.search(_NAM_HOC.sub(' ', chu))
    if khop_ky:
        pham_vi.hoc_ky = khop_ky.group(1)
    pham_vi.toan_khoa = bool(_TOAN_KHOA.search(chu))
    pham_vi.gan_nhat = bool(_GAN_NHAT.search(chu))
    return pham_vi
