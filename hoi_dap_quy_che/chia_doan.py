import re

GIOI_HAN_KY_TU_DOAN = 1500

_MAU_DIEU = re.compile(r'^[ \t]*Điều\s+(\d+)\b.*$', re.MULTILINE | re.IGNORECASE)
_MAU_KHOAN = re.compile(r'^[ \t]*(\d+)[.\)][ \t]+', re.MULTILINE)
_MAU_DIEM = re.compile(r'^[ \t]*([a-zđ])[.\)][ \t]+', re.MULTILINE | re.IGNORECASE)


def _chia_theo_mau(van_ban, mau):
    """Cắt van_ban tại mỗi vị trí khớp mau (đầu dòng); trả về list (nhan, noi_dung),
    trong đó phần trước khi khớp đầu tiên (nếu có nội dung) được giữ làm "tiêu đề"
    gắn vào đoạn kế tiếp — không tự tạo đoạn riêng cho phần tiêu đề đó."""
    vi_tri_khop = list(mau.finditer(van_ban))
    if not vi_tri_khop:
        return [(None, van_ban)]
    ket_qua = []
    tieu_de = van_ban[:vi_tri_khop[0].start()].strip()
    for i, khop in enumerate(vi_tri_khop):
        nhan = khop.group(1)
        bat_dau = khop.start()
        ket_thuc = vi_tri_khop[i + 1].start() if i + 1 < len(vi_tri_khop) else len(van_ban)
        noi_dung = van_ban[bat_dau:ket_thuc].strip()
        if tieu_de:
            noi_dung = f'{tieu_de}\n{noi_dung}'
        ket_qua.append((nhan, noi_dung))
    return ket_qua


def _cat_theo_do_dai(van_ban, gioi_han):
    """Cắt cứng theo độ dài (ưu tiên cắt tại khoảng trắng) khi không còn dấu mốc nào
    (Điều/khoản/điểm) để tách tiếp — chỉ dùng làm phương án cuối."""
    if len(van_ban) <= gioi_han:
        return [van_ban]
    ket_qua = []
    con_lai = van_ban
    while len(con_lai) > gioi_han:
        vi_tri_cat = con_lai.rfind(' ', 0, gioi_han)
        if vi_tri_cat <= 0:
            vi_tri_cat = gioi_han
        ket_qua.append(con_lai[:vi_tri_cat].strip())
        con_lai = con_lai[vi_tri_cat:].strip()
    if con_lai:
        ket_qua.append(con_lai)
    return ket_qua


def chia_doan_tai_lieu(ten_tai_lieu, van_ban, gioi_han=GIOI_HAN_KY_TU_DOAN):
    """Chia văn bản một tài liệu quy chế thành các đoạn theo Điều; Điều dài hơn
    gioi_han ký tự thì tách tiếp theo khoản, khoản vẫn dài thì tách tiếp theo điểm,
    vẫn dài thì cắt cứng theo độ dài. Mỗi đoạn giữ tên tài liệu, số Điều, số khoản
    (None nếu không tách khoản).

    noi_dung luôn là đoạn gốc (không chèn thêm tiêu đề) dùng để gửi AI/hiển thị, GIỮ
    NGUYÊN như trước — chỉ đoạn đầu tiên của một Điều/khoản dài tự nhiên có dòng tiêu đề
    ở đầu do cách _chia_theo_mau giữ phần văn bản trước dấu mốc, các mảnh cắt cứng sau đó
    thì không. tieu_de_dieu là dòng tiêu đề của Điều (vd. "Điều 14. Xếp loại học lực"),
    LUÔN có ở mọi đoạn thuộc Điều đó (kể cả các mảnh cắt cứng không tự nhiên chứa nó) —
    chỉ dùng để dựng chỉ mục truy hồi (xem hoi_dap_quy_che/chi_muc.py), không đưa vào
    noi_dung gửi AI/hiển thị.

    Trả về list[dict]: {'ten_tai_lieu', 'dieu', 'khoan', 'noi_dung', 'tieu_de_dieu'}.
    """
    doan = []
    if not (van_ban or '').strip():
        return doan

    for so_dieu, noi_dung_dieu in _chia_theo_mau(van_ban, _MAU_DIEU):
        tieu_de_dieu = noi_dung_dieu.splitlines()[0].strip() if so_dieu is not None else None
        if len(noi_dung_dieu) <= gioi_han:
            doan.append({
                'ten_tai_lieu': ten_tai_lieu, 'dieu': so_dieu, 'khoan': None,
                'noi_dung': noi_dung_dieu, 'tieu_de_dieu': tieu_de_dieu,
            })
            continue

        for so_khoan, noi_dung_khoan in _chia_theo_mau(noi_dung_dieu, _MAU_KHOAN):
            if len(noi_dung_khoan) <= gioi_han:
                doan.append({
                    'ten_tai_lieu': ten_tai_lieu, 'dieu': so_dieu, 'khoan': so_khoan,
                    'noi_dung': noi_dung_khoan, 'tieu_de_dieu': tieu_de_dieu,
                })
                continue

            for _, phan in _chia_theo_mau(noi_dung_khoan, _MAU_DIEM):
                for manh in _cat_theo_do_dai(phan, gioi_han):
                    doan.append({
                        'ten_tai_lieu': ten_tai_lieu, 'dieu': so_dieu, 'khoan': so_khoan,
                        'noi_dung': manh, 'tieu_de_dieu': tieu_de_dieu,
                    })
    return doan
