CAC_THU = [
    (2, 'Thứ 2'), (3, 'Thứ 3'), (4, 'Thứ 4'), (5, 'Thứ 5'), (6, 'Thứ 6'), (7, 'Thứ 7'), (8, 'Chủ nhật'),
]


def xay_dung_luoi_tuan(danh_sach_lich):
    """Xếp một danh sách LichHoc vào lưới tuần (tiết x thứ) để hiển thị dạng bảng thay vì
    danh sách phẳng. Trả về list các dòng {'tiet': int, 'o': [list LichHoc theo đúng thứ
    tự CAC_THU]} — dùng list (không phải dict lồng nhau) vì template Django không tra được
    khóa dict theo biến vòng lặp; mỗi ô chỉ cần {% for %} phẳng.

    Một lớp trải dài nhiều tiết sẽ xuất hiện lặp lại ở mỗi dòng tiết nó chiếm — đơn giản
    hơn dùng rowspan và vẫn đúng yêu cầu "mỗi ô hiện mã lớp/tên học phần nếu trùng khung".
    """
    danh_sach_lich = list(danh_sach_lich)
    if not danh_sach_lich:
        return []

    tiet_toi_da = max(lich.tiet_bat_dau + lich.so_tiet - 1 for lich in danh_sach_lich)
    so_tiet_hien_thi = max(tiet_toi_da, 10)

    o_theo_thu = {thu: {tiet: [] for tiet in range(1, so_tiet_hien_thi + 1)} for thu, _ in CAC_THU}
    for lich in danh_sach_lich:
        for tiet in range(lich.tiet_bat_dau, lich.tiet_bat_dau + lich.so_tiet):
            if tiet <= so_tiet_hien_thi:
                o_theo_thu[lich.thu][tiet].append(lich)

    return [
        {'tiet': tiet, 'o': [o_theo_thu[thu][tiet] for thu, _ in CAC_THU]}
        for tiet in range(1, so_tiet_hien_thi + 1)
    ]
