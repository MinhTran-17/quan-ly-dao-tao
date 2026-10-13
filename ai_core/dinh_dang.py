CANH_BAO_AI = (
    'Nội dung do AI tạo, chỉ mang tính tham khảo, không thay thế quyết định của phòng đào tạo.'
)


def dinh_dang_ket_qua(noi_dung):
    """Chuẩn hóa kết quả AI trước khi hiển thị: bỏ khoảng trắng thừa, luôn kèm cảnh báo cố định."""
    noi_dung = (noi_dung or '').strip()
    return f'{noi_dung}\n\n{CANH_BAO_AI}'
