from string import Template

from django.conf import settings


class KhongTimThayPrompt(Exception):
    """Không tìm thấy thư mục hoặc tệp prompt tương ứng."""


def _thu_muc_phien_ban(ten_chuc_nang, phien_ban):
    return settings.AI_PROMPTS_DIR / ten_chuc_nang / phien_ban


def nap_prompt(ten_chuc_nang, phien_ban, **bien):
    """Nạp cặp prompt (system, user) của một chức năng/phiên bản trong thư mục prompts/.

    Cấu trúc: prompts/<ten_chuc_nang>/<phien_ban>/system.txt và user.txt.
    Chỗ điền biến dùng cú pháp $ten_bien (string.Template) — không dùng {ten_bien} của
    str.format, để có thể viết thẳng ví dụ JSON (có dấu ngoặc nhọn { }) trong nội dung
    prompt mà không phải escape. Phần dữ liệu người dùng nên được đặt trong khối đánh
    dấu rõ ràng ngay trong nội dung user.txt (xem prompts/README.md), không phải chỉ thị.

    Trả về tuple (he_thong, nguoi_dung) đã điền biến.
    """
    thu_muc = _thu_muc_phien_ban(ten_chuc_nang, phien_ban)
    duong_dan_he_thong = thu_muc / 'system.txt'
    duong_dan_nguoi_dung = thu_muc / 'user.txt'
    if not duong_dan_he_thong.exists() or not duong_dan_nguoi_dung.exists():
        raise KhongTimThayPrompt(
            f'Không tìm thấy prompt cho chức năng "{ten_chuc_nang}" phiên bản "{phien_ban}".'
        )
    he_thong = duong_dan_he_thong.read_text(encoding='utf-8')
    nguoi_dung = duong_dan_nguoi_dung.read_text(encoding='utf-8')
    if bien:
        he_thong = Template(he_thong).substitute(**bien)
        nguoi_dung = Template(nguoi_dung).substitute(**bien)
    return he_thong, nguoi_dung
