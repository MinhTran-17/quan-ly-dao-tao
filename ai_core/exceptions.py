class LoiAI(Exception):
    """Lỗi gốc cho mọi lỗi khi gọi AI. Thông điệp (str(loi)) luôn an toàn để hiển thị
    cho người dùng, không bao giờ chứa khóa API hay nội dung prompt.

    chi_tiet (tùy chọn) chỉ dùng cho chẩn đoán/gỡ lỗi (ví dụ lệnh kiem_tra_ai --chi_tiet),
    gồm loại lỗi gốc, mã HTTP và thông điệp lỗi do API trả về — cũng không bao giờ
    chứa khóa API.
    """

    def __init__(self, thong_diep, chi_tiet=None):
        super().__init__(thong_diep)
        self.chi_tiet = chi_tiet


class ChuaCauHinhKhoaAI(LoiAI):
    def __init__(self):
        super().__init__('Chưa cấu hình khóa API cho dịch vụ AI (GEMINI_API_KEY).')


class DauVaoQuaDai(LoiAI):
    def __init__(self, do_dai, gioi_han):
        super().__init__(f'Nội dung gửi cho AI quá dài ({do_dai} ký tự, giới hạn {gioi_han} ký tự).')


class HetThoiGianChoAI(LoiAI):
    def __init__(self, chi_tiet=None):
        super().__init__('Dịch vụ AI không phản hồi kịp thời gian chờ, vui lòng thử lại sau.', chi_tiet)


class QuaGioiHanTanSuatAI(LoiAI):
    """Lỗi 429. pham_vi phân biệt HẾT HẠN MỨC THEO NGÀY ('ngay') với VƯỢT TẦN SUẤT THEO
    PHÚT ('phut') khi xác định được từ chi tiết lỗi API — None nếu không đủ căn cứ để
    phân biệt (không suy đoán), khi đó dùng thông điệp chung như trước."""

    _THONG_DIEP = {
        'ngay': 'Dịch vụ AI đã hết hạn mức sử dụng hôm nay, vui lòng thử lại sau khi hạn mức được đặt lại.',
        'phut': 'Dịch vụ AI đang bị vượt tần suất theo phút, vui lòng thử lại sau ít phút.',
    }

    def __init__(self, chi_tiet=None, pham_vi=None):
        thong_diep = self._THONG_DIEP.get(pham_vi, 'Dịch vụ AI đang bị giới hạn tần suất sử dụng, vui lòng thử lại sau.')
        super().__init__(thong_diep, chi_tiet)
        self.pham_vi = pham_vi


class PhanHoiRongAI(LoiAI):
    def __init__(self):
        super().__init__('Dịch vụ AI trả về phản hồi rỗng.')


class PhanHoiSaiDinhDangAI(LoiAI):
    def __init__(self):
        super().__init__('Phản hồi từ dịch vụ AI không đúng định dạng mong đợi.')


class LoiMoHinhAI(LoiAI):
    def __init__(self, chi_tiet=None):
        super().__init__('Dịch vụ AI gặp lỗi, vui lòng thử lại sau.', chi_tiet)
