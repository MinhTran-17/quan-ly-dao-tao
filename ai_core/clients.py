import re
import time

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from .exceptions import (
    ChuaCauHinhKhoaAI,
    DauVaoQuaDai,
    HetThoiGianChoAI,
    LoiMoHinhAI,
    PhanHoiRongAI,
    PhanHoiSaiDinhDangAI,
    QuaGioiHanTanSuatAI,
)

_KHONG_THU_LAI = (PhanHoiRongAI, PhanHoiSaiDinhDangAI, DauVaoQuaDai, ChuaCauHinhKhoaAI)

# Trần thời gian chờ giữa các lần thử lại (giây), áp dụng cho cả backoff tăng dần lẫn
# thời gian nhà cung cấp đề xuất khi bị giới hạn tần suất — tránh chờ quá lâu một lần.
_GIOI_HAN_CHO_GIAY = 60.0


class ClientAI:
    """Giao diện chung: mọi client gọi AI (thật hoặc giả) đều implement sinh_noi_dung."""

    def sinh_noi_dung(self, *, he_thong, nguoi_dung):
        raise NotImplementedError


def _trich_van_ban_tu_phan_hoi(response):
    """Lấy nội dung text từ response của SDK; phân biệt rỗng và sai định dạng."""
    van_ban = getattr(response, 'text', None)
    if van_ban is None:
        raise PhanHoiSaiDinhDangAI()
    if not van_ban.strip():
        raise PhanHoiRongAI()
    return van_ban


def _trich_chi_tiet_an_toan(loi_goc):
    """Trích thông tin lỗi để chẩn đoán (loại lỗi gốc, mã HTTP, thông điệp do API trả
    về). Chỉ đọc các thuộc tính công khai của exception — không bao giờ có khóa API
    trong đó, vì khóa không phải một phần của exception hay của phản hồi API.
    """
    return {
        'loai': type(loi_goc).__name__,
        'ma_http': getattr(loi_goc, 'code', None),
        'thong_diep': getattr(loi_goc, 'message', None) or str(loi_goc) or None,
    }


def _lay_giay_tu_chuoi_thoi_luong(chuoi):
    """Google API trả thời lượng dạng chuỗi như '20s' hoặc '1.500s'. Trả None nếu không
    đọc được theo đúng dạng này."""
    if not isinstance(chuoi, str):
        return None
    khop = re.match(r'^(\d+(?:\.\d+)?)s$', chuoi.strip())
    return float(khop.group(1)) if khop else None


def _lay_thoi_gian_cho_tu_loi_429(loi_goc):
    """Đọc gợi ý thời gian chờ (giây) mà API trả về khi bị giới hạn tần suất: trước tiên
    thử header HTTP "Retry-After", sau đó thử trường RetryInfo.retryDelay trong nội dung
    lỗi (details, dạng {"error": {..., "details": [...]}} hoặc {..., "details": [...]}).
    Trả None nếu không tìm thấy gợi ý nào — khi đó dùng lại backoff tăng dần như cũ."""
    response = getattr(loi_goc, 'response', None)
    tieu_de = getattr(response, 'headers', None) if response is not None else None
    if tieu_de is not None:
        gia_tri = tieu_de.get('Retry-After')
        if gia_tri:
            try:
                return float(gia_tri)
            except ValueError:
                pass

    chi_tiet = getattr(loi_goc, 'details', None)
    if isinstance(chi_tiet, dict):
        loi_long = chi_tiet.get('error') if isinstance(chi_tiet.get('error'), dict) else chi_tiet
        for muc in (loi_long.get('details') or []):
            if isinstance(muc, dict) and 'RetryInfo' in str(muc.get('@type', '')):
                giay = _lay_giay_tu_chuoi_thoi_luong(muc.get('retryDelay'))
                if giay is not None:
                    return giay
    return None


def _gom_van_ban_chan_doan_429(loi_goc):
    """Gom các trường có cấu trúc trong chi tiết lỗi 429 hữu ích để phân biệt hết hạn mức
    theo NGÀY với vượt tần suất theo PHÚT: quotaId/quotaMetric/subject/description trong
    mọi QuotaFailure.violations (tên quotaId của Google thường có chứa "PerDay" hoặc
    "PerMinute", ví dụ "GenerateRequestsPerDayPerProjectPerModel-FreeTier")."""
    chi_tiet = getattr(loi_goc, 'details', None)
    if not isinstance(chi_tiet, dict):
        return ''
    loi_long = chi_tiet.get('error') if isinstance(chi_tiet.get('error'), dict) else chi_tiet
    ket_qua = []
    for muc in (loi_long.get('details') or []):
        if not isinstance(muc, dict) or 'QuotaFailure' not in str(muc.get('@type', '')):
            continue
        for vi_pham in (muc.get('violations') or []):
            if isinstance(vi_pham, dict):
                ket_qua.extend(str(vi_pham.get(khoa, '')) for khoa in ('quotaId', 'quotaMetric', 'subject', 'description'))
    return ' '.join(ket_qua)


def _phan_loai_gioi_han_tan_suat(loi_goc):
    """Phân biệt lỗi 429 do HẾT HẠN MỨC THEO NGÀY ('ngay') hay VƯỢT TẦN SUẤT THEO PHÚT
    ('phut'): trước tiên dò trong các trường có cấu trúc (quotaId/quotaMetric/...), nếu
    không có mới dò trong thông điệp lỗi thô. Trả None nếu không đủ căn cứ — không suy
    đoán khi API không nói rõ, khi đó dùng lại thông điệp giới hạn tần suất chung."""
    van_ban = _gom_van_ban_chan_doan_429(loi_goc)
    if not van_ban.strip():
        van_ban = getattr(loi_goc, 'message', None) or str(loi_goc) or ''
    van_ban = van_ban.lower()
    if re.search(r'per[_ -]?day|requests?\s+per\s+day|\bdaily\b|\brpd\b', van_ban):
        return 'ngay'
    if re.search(r'per[_ -]?minute|requests?\s+per\s+minute|\brpm\b', van_ban):
        return 'phut'
    return None


def _thu_lai_hoac_bao_loi(lan_thu, so_lan_thu_lai, cho_giay_ban_dau, ngoai_le, loi_goc, cho_giay_de_xuat=None):
    # Lưu ý quan trọng: mỗi lần thử lại là MỘT YÊU CẦU HTTP MỚI gửi tới nhà cung cấp AI,
    # nên nó VẪN TÍNH vào hạn mức/tần suất phía nhà cung cấp như mọi yêu cầu khác — thử
    # lại không "miễn phí" về quota. Vì vậy khi bị giới hạn tần suất (429), nên chờ đúng
    # thời gian nhà cung cấp đề xuất (cho_giay_de_xuat) thay vì chờ ít rồi thử lại ngay,
    # để không cộng dồn thêm yêu cầu trong lúc đang bị giới hạn.
    lan_thu += 1
    if lan_thu > so_lan_thu_lai:
        raise ngoai_le from loi_goc
    if cho_giay_de_xuat is not None:
        cho_giay = min(cho_giay_de_xuat, _GIOI_HAN_CHO_GIAY)
    else:
        cho_giay = min(cho_giay_ban_dau * (2 ** (lan_thu - 1)), _GIOI_HAN_CHO_GIAY)
    time.sleep(cho_giay)
    return lan_thu


def _goi_voi_thu_lai(ham_goi_mot_lan, *, so_lan_thu_lai, cho_giay_ban_dau=1.0):
    """Gọi ham_goi_mot_lan() một lần; nếu hết thời gian chờ, bị giới hạn tần suất (429)
    hoặc lỗi máy chủ (5xx) thì thử lại tối đa so_lan_thu_lai lần nữa. Thời gian chờ giữa
    các lần thử: với 429 thì ưu tiên thời gian nhà cung cấp đề xuất (nếu có), còn lại
    dùng backoff tăng dần — cả hai đều bị chặn trần ở _GIOI_HAN_CHO_GIAY giây. Mọi lỗi
    khác của thư viện được dịch sang ngoại lệ của dự án, không để lộ ra ngoài và không
    làm crash trang. Mỗi ngoại lệ mang theo chi_tiet an toàn (loại lỗi gốc, mã HTTP,
    thông điệp API) để lệnh kiem_tra_ai --chi_tiet hiển thị.
    """
    lan_thu = 0
    while True:
        try:
            return ham_goi_mot_lan()
        except _KHONG_THU_LAI:
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as loi_goc:
            lan_thu = _thu_lai_hoac_bao_loi(
                lan_thu, so_lan_thu_lai, cho_giay_ban_dau,
                HetThoiGianChoAI(_trich_chi_tiet_an_toan(loi_goc)), loi_goc,
            )
        except genai_errors.ServerError as loi_goc:
            lan_thu = _thu_lai_hoac_bao_loi(
                lan_thu, so_lan_thu_lai, cho_giay_ban_dau,
                LoiMoHinhAI(_trich_chi_tiet_an_toan(loi_goc)), loi_goc,
            )
        except genai_errors.ClientError as loi_goc:
            if loi_goc.code == 429:
                lan_thu = _thu_lai_hoac_bao_loi(
                    lan_thu, so_lan_thu_lai, cho_giay_ban_dau,
                    QuaGioiHanTanSuatAI(
                        _trich_chi_tiet_an_toan(loi_goc), pham_vi=_phan_loai_gioi_han_tan_suat(loi_goc),
                    ),
                    loi_goc,
                    cho_giay_de_xuat=_lay_thoi_gian_cho_tu_loi_429(loi_goc),
                )
            else:
                raise LoiMoHinhAI(_trich_chi_tiet_an_toan(loi_goc)) from loi_goc
        except Exception as loi_goc:
            raise LoiMoHinhAI(_trich_chi_tiet_an_toan(loi_goc)) from loi_goc


class GeminiClient(ClientAI):
    """Client gọi Gemini thật, qua SDK chính thức google-genai."""

    def __init__(self, api_key=None, model=None, timeout_giay=None, so_lan_thu_lai=None, gioi_han_ky_tu=None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not self.api_key:
            raise ChuaCauHinhKhoaAI()
        self.model = model or settings.GEMINI_MODEL
        self.timeout_giay = timeout_giay if timeout_giay is not None else settings.AI_TIMEOUT_GIAY
        self.so_lan_thu_lai = so_lan_thu_lai if so_lan_thu_lai is not None else settings.AI_SO_LAN_THU_LAI
        self.gioi_han_ky_tu = gioi_han_ky_tu if gioi_han_ky_tu is not None else settings.AI_GIOI_HAN_KY_TU
        try:
            self._client = genai.Client(api_key=self.api_key)
        except Exception as loi_goc:
            raise LoiMoHinhAI(_trich_chi_tiet_an_toan(loi_goc)) from loi_goc
        # Tên phiên bản model thực tế mà API trả lời (self.model có thể chỉ là một alias
        # như "gemini-flash-latest"); được điền sau lần gọi thành công gần nhất.
        self.model_version_thuc_te = None

    def sinh_noi_dung(self, *, he_thong, nguoi_dung):
        if len(nguoi_dung) > self.gioi_han_ky_tu:
            raise DauVaoQuaDai(len(nguoi_dung), self.gioi_han_ky_tu)

        def _goi_mot_lan():
            response = self._client.models.generate_content(
                model=self.model,
                contents=nguoi_dung,
                config=genai_types.GenerateContentConfig(
                    system_instruction=he_thong,
                    http_options=genai_types.HttpOptions(timeout=int(self.timeout_giay * 1000)),
                    # Hệ thống không dùng function calling; tắt hẳn AFC (thay vì chỉ để mặc
                    # định) để SDK không in cảnh báo "Direct use of automatic function
                    # calling (AFC)..." mỗi lần gọi.
                    automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            self.model_version_thuc_te = getattr(response, 'model_version', None)
            return _trich_van_ban_tu_phan_hoi(response)

        return _goi_voi_thu_lai(_goi_mot_lan, so_lan_thu_lai=self.so_lan_thu_lai)


class ClientAIGia(ClientAI):
    """Client giả để test hoặc demo, không gọi mạng.

    phan_hoi có thể là một chuỗi (luôn trả về) hoặc một Exception (luôn raise).
    Lưu lại mọi lần gọi vào cac_lan_goi để test kiểm tra nội dung đã gửi.
    """

    def __init__(self, phan_hoi='Đây là phản hồi giả từ AI để kiểm thử.'):
        self.phan_hoi = phan_hoi
        self.cac_lan_goi = []
        self.model_version_thuc_te = None

    def sinh_noi_dung(self, *, he_thong, nguoi_dung):
        self.cac_lan_goi.append({'he_thong': he_thong, 'nguoi_dung': nguoi_dung})
        if isinstance(self.phan_hoi, Exception):
            raise self.phan_hoi
        return self.phan_hoi


def lay_client_ai():
    """Chọn client theo settings.AI_BACKEND: 'gemini' (mặc định) hoặc 'gia' (giả, test/demo)."""
    if getattr(settings, 'AI_BACKEND', 'gemini') == 'gia':
        return ClientAIGia()
    return GeminiClient()
