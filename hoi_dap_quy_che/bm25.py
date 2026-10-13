import math
import re
from collections import Counter

# Từ dừng tiếng Việt thường gặp (không đầy đủ, đủ dùng để loại bớt từ ít giá trị truy hồi).
TU_DUNG = frozenset([
    'và', 'là', 'của', 'các', 'một', 'những', 'để', 'khi', 'có', 'không', 'được', 'này',
    'đó', 'cho', 'với', 'trong', 'về', 'theo', 'tại', 'từ', 'đến', 'sẽ', 'đã', 'bị', 'phải',
    'nếu', 'thì', 'mà', 'hay', 'hoặc', 'như', 'còn', 'nên', 'vì', 'do', 'nhưng', 'cũng',
    'rất', 'chỉ', 'nữa', 'hơn', 'lại', 'ra', 'vào', 'lên', 'xuống', 'trên', 'dưới', 'sau',
    'trước', 'giữa', 'ngoài', 'cùng', 'mỗi', 'tất', 'cả', 'toàn', 'bộ', 'ở', 'đi', 'ai',
    'gì', 'nào', 'sao', 'vậy', 'thế', 'đây', 'kia', 'ấy', 'họ', 'tôi', 'ta', 'anh', 'chị',
    'em', 'là', 'khác', 'hơn', 'đang', 'vẫn', 'chưa', 'đều', 'nhiều', 'ít', 'lúc', 'ngay',
])

_MAU_TU = re.compile(r'\w+', re.UNICODE)


def tach_tu(van_ban):
    """Chuẩn hóa chữ thường, tách từ (giữ dấu tiếng Việt), bỏ từ dừng thường gặp."""
    van_ban = (van_ban or '').lower()
    return [tu for tu in _MAU_TU.findall(van_ban) if tu not in TU_DUNG]


def tach_tu_va_bigram(van_ban):
    """Như tach_tu, nhưng thêm cả bigram (hai âm tiết LIỀN NHAU trong văn bản gốc, ví dụ
    "buộc thôi", "thôi học") bên cạnh từ đơn — giúp bắt đúng hơn các từ ghép/cụm từ mà
    tách từ đơn âm tiết không phân biệt được (vd. nhầm "thời tiết" với "thời gian" vì
    cùng chứa âm tiết "thời"). Bỏ qua bigram có chứa âm tiết là từ dừng, vì loại bigram
    đó thường không mang nhiều ý nghĩa cụm từ."""
    van_ban = (van_ban or '').lower()
    am_tiet = _MAU_TU.findall(van_ban)
    ket_qua = [tu for tu in am_tiet if tu not in TU_DUNG]
    for a, b in zip(am_tiet, am_tiet[1:]):
        if a not in TU_DUNG and b not in TU_DUNG:
            ket_qua.append(f'{a}_{b}')
    return ket_qua


class BM25:
    """BM25 (Okapi) tự cài, không phụ thuộc thư viện ngoài — đủ dùng cho kho tài liệu
    nhỏ (quy chế đào tạo), không cần dịch vụ embedding."""

    def __init__(self, danh_sach_van_ban, k1=1.5, b=0.75, ham_tach_tu=tach_tu):
        self.k1 = k1
        self.b = b
        self.ham_tach_tu = ham_tach_tu
        self.danh_sach_tu = [self.ham_tach_tu(vb) for vb in danh_sach_van_ban]
        self.so_van_ban = len(self.danh_sach_tu)
        self.do_dai = [len(tu) for tu in self.danh_sach_tu]
        self.do_dai_trung_binh = (sum(self.do_dai) / self.so_van_ban) if self.so_van_ban else 0.0
        self.tan_suat = [Counter(tu) for tu in self.danh_sach_tu]
        self.idf = self._tinh_idf()

    def _tinh_idf(self):
        so_van_ban_chua_tu = Counter()
        for tu_da_tach in self.danh_sach_tu:
            for tu in set(tu_da_tach):
                so_van_ban_chua_tu[tu] += 1
        idf = {}
        for tu, n in so_van_ban_chua_tu.items():
            idf[tu] = math.log(1 + (self.so_van_ban - n + 0.5) / (n + 0.5))
        return idf

    def _diem_mot_van_ban(self, tu_khoa, chi_so):
        if self.do_dai_trung_binh == 0:
            return 0.0
        diem = 0.0
        tan_suat = self.tan_suat[chi_so]
        do_dai = self.do_dai[chi_so]
        for tu in tu_khoa:
            tf = tan_suat.get(tu, 0)
            if tf == 0:
                continue
            idf = self.idf.get(tu, 0.0)
            mau_so = tf + self.k1 * (1 - self.b + self.b * do_dai / self.do_dai_trung_binh)
            diem += idf * (tf * (self.k1 + 1)) / mau_so
        return diem

    def xep_hang(self, cau_truy_van):
        """Trả về list điểm số (float) tương ứng với từng văn bản đã nạp, theo đúng thứ tự."""
        tu_khoa = self.ham_tach_tu(cau_truy_van)
        return [self._diem_mot_van_ban(tu_khoa, i) for i in range(self.so_van_ban)]
