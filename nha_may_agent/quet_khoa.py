"""Quét chuỗi giống khóa API trong các tệp được chỉ định (dùng cho hook pre-commit).

    python -m nha_may_agent.quet_khoa <tệp> [<tệp> ...]

Mã thoát 1 nếu có tệp chứa chuỗi giống khóa (in tên tệp, số dòng, loại khóa — không in chính khóa), 0 nếu sạch.
Bỏ qua tệp nhị phân và tệp không đọc được dạng UTF-8. Dùng chung mẫu nhận diện với rào chắn nhà máy agent.
"""
import sys
from pathlib import Path

from .rao_chan import tim_khoa_api


def main(cac_tep):
    co_loi = False
    for ten in cac_tep:
        tep = Path(ten)
        if not tep.is_file():
            continue
        try:
            van_ban = tep.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        ket_qua = tim_khoa_api(van_ban)
        if ket_qua:
            mo_ta, vi_tri = ket_qua
            dong = van_ban.count('\n', 0, vi_tri) + 1
            print(f'{ten}:{dong}: có chuỗi giống {mo_ta}. Gỡ khóa khỏi tệp, đặt trong .env.', file=sys.stderr)
            co_loi = True
    return 1 if co_loi else 0


if __name__ == '__main__':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass
    sys.exit(main(sys.argv[1:]))
