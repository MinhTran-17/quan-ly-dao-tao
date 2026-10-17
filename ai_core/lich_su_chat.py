"""Lịch sử hội thoại của khung chat AI, lưu trong session của người dùng (không tạo bảng CSDL mới).

Mỗi lượt là {'cau_hoi': str, 'tra_loi': dict}; 'tra_loi' chỉ gồm chuỗi/số/danh sách/dict để session lưu được dạng
JSON. Lịch sử chỉ để HIỂN THỊ lại trên trang — không gửi các lượt cũ cho AI (mỗi tin nhắn là một yêu cầu độc lập,
chỉ gửi dữ liệu tối thiểu của đúng yêu cầu đó). Giữ tối đa SO_LUOT_TOI_DA lượt gần nhất; mất khi đăng xuất.
"""

SO_LUOT_TOI_DA = 10
_TIEN_TO = 'chat_ai:'


def cau_gui_len(request):
    """Câu người dùng gõ trong ô nhập (name="cau_hoi"), đã bỏ khoảng trắng hai đầu."""
    return (request.POST.get('cau_hoi') or '').strip()


def doc(request, khoa):
    return list(request.session.get(_TIEN_TO + khoa, []))


def them(request, khoa, cau_hoi, tra_loi):
    lich_su = doc(request, khoa)
    lich_su.append({'cau_hoi': cau_hoi, 'tra_loi': tra_loi})
    request.session[_TIEN_TO + khoa] = lich_su[-SO_LUOT_TOI_DA:]


def xoa(request, khoa):
    request.session.pop(_TIEN_TO + khoa, None)
