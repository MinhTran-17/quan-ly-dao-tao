from django.conf import settings

from regulations.models import TaiLieuQuyChe

from .bm25 import BM25, tach_tu, tach_tu_va_bigram
from .chia_doan import chia_doan_tai_lieu
from .trich_xuat import trich_van_ban

# Hai phiên bản truy hồi để so sánh công bằng qua settings.AI_TRUY_HOI_PHIEN_BAN:
# - v1 (bản cũ): tách từ đơn âm tiết, chỉ mục hóa đúng nội dung đoạn gốc, tối đa 4 đoạn.
# - v2 (bản mới): thêm bigram âm tiết liền nhau, chỉ mục hóa gộp thêm tiêu đề Điều (chỉ
#   để xếp hạng — nội dung gửi AI/hiển thị vẫn là đoạn gốc), tối đa 6 đoạn.
SO_DOAN_TOI_DA = {'v1': 4, 'v2': 6}
_HAM_TACH_TU = {'v1': tach_tu, 'v2': tach_tu_va_bigram}


def _phien_ban_truy_hoi():
    return getattr(settings, 'AI_TRUY_HOI_PHIEN_BAN', 'v1')


def _van_ban_de_lap_chi_muc(doan, phien_ban):
    if phien_ban == 'v2' and doan.get('tieu_de_dieu'):
        return f"{doan['tieu_de_dieu']}\n{doan['noi_dung']}"
    return doan['noi_dung']


# Bộ nhớ đệm chỉ mục cấp module (đúng nghĩa "giữ trong bộ nhớ", không dùng bảng CSDL
# hay cache framework). "chu_ky" là chữ ký của toàn bộ dữ liệu tai_lieu_quy_che hiện có
# (xem _chu_ky_hien_tai) — mỗi lần truy hồi đều so lại chữ ký này với DB (một truy vấn
# nhẹ, không đọc lại từng tệp), nếu khác thì mới trích xuất + chia đoạn + dựng lại BM25.
# Nhờ vậy chỉ mục tự làm mới khi có tài liệu được tải lên, cập nhật hoặc xóa, mà không
# cần regulations báo hiệu chủ động.
_bo_nho_dem = {'chu_ky': None, 'bm25': None, 'doan': []}


def _chu_ky_hien_tai():
    # Chữ ký gồm cả duong_dan_file (tên tệp trên đĩa, đổi mỗi lần tải tệp mới vì dùng
    # uuid4 — xem regulations/models.py), không chỉ ngay_cap_nhat. ngay_cap_nhat là
    # DateField (độ chính xác theo NGÀY), nên nếu chỉ dựa vào nó thì thay tệp hai lần
    # trong cùng một ngày sẽ không đổi chữ ký và chỉ mục sẽ không được làm mới.
    # Có cả phiên bản truy hồi (AI_TRUY_HOI_PHIEN_BAN) vì đổi phiên bản (vd. trong test
    # dùng override_settings) làm thay đổi cách chỉ mục được dựng dù dữ liệu DB không đổi.
    return (
        _phien_ban_truy_hoi(),
        tuple(sorted(TaiLieuQuyChe.objects.values_list('ma_tai_lieu', 'ngay_cap_nhat', 'duong_dan_file'))),
    )


def _xay_dung_chi_so(chu_ky_moi):
    doan = []
    for tai_lieu in TaiLieuQuyChe.objects.all():
        if not tai_lieu.duong_dan_file:
            continue
        van_ban = trich_van_ban(tai_lieu.duong_dan_file)
        doan.extend(chia_doan_tai_lieu(tai_lieu.ten_tai_lieu, van_ban))

    phien_ban = chu_ky_moi[0]
    van_ban_chi_muc = [_van_ban_de_lap_chi_muc(d, phien_ban) for d in doan]
    bm25 = BM25(van_ban_chi_muc, ham_tach_tu=_HAM_TACH_TU.get(phien_ban, tach_tu)) if doan else None
    _bo_nho_dem['chu_ky'] = chu_ky_moi
    _bo_nho_dem['bm25'] = bm25
    _bo_nho_dem['doan'] = doan


def lay_chi_so():
    """Trả về (bm25, danh_sach_doan) hiện hành, dựng lại nếu dữ liệu tai_lieu_quy_che
    đã thay đổi kể từ lần dựng gần nhất."""
    chu_ky_moi = _chu_ky_hien_tai()
    if _bo_nho_dem['chu_ky'] != chu_ky_moi:
        _xay_dung_chi_so(chu_ky_moi)
    return _bo_nho_dem['bm25'], _bo_nho_dem['doan']


def lam_moi_chi_so():
    """Buộc dựng lại chỉ mục ngay ở lần gọi lay_chi_so()/truy_hoi() kế tiếp."""
    _bo_nho_dem['chu_ky'] = None


def _cat_bot_theo_gioi_han(ket_qua):
    """Nếu tổng độ dài các đoạn (đã sắp điểm giảm dần) vượt AI_GIOI_HAN_KY_TU thì bỏ
    bớt từ cuối danh sách (đoạn điểm thấp nhất) cho tới khi vừa giới hạn, thay vì báo lỗi.

    Luôn giữ lại ít nhất đoạn tốt nhất (dù một mình nó cũng đã vượt giới hạn) — thà gửi
    hơi dài (ai_core sẽ tự chặn nếu quá dài) còn hơn không gửi đoạn nào dù đã tìm thấy."""
    while len(ket_qua) > 1 and sum(len(doan['noi_dung']) for doan, _diem in ket_qua) > settings.AI_GIOI_HAN_KY_TU:
        ket_qua = ket_qua[:-1]
    return ket_qua


def truy_hoi(cau_hoi):
    """Truy hồi tối đa SO_DOAN_TOI_DA đoạn quy chế liên quan nhất tới cau_hoi, đã lọc
    theo ngưỡng AI_NGUONG_DIEM_TRUY_HOI và cắt bớt nếu tổng độ dài vượt AI_GIOI_HAN_KY_TU.

    Trả về list[(doan, diem)], sắp theo điểm giảm dần. Danh sách rỗng nghĩa là không có
    đoạn nào đủ liên quan (kể cả khi kho tài liệu trống).
    """
    bm25, doan = lay_chi_so()
    if bm25 is None or not doan:
        return []
    so_doan_toi_da = SO_DOAN_TOI_DA.get(_phien_ban_truy_hoi(), SO_DOAN_TOI_DA['v1'])
    diem_so = bm25.xep_hang(cau_hoi)
    ket_qua = sorted(zip(doan, diem_so), key=lambda cap: cap[1], reverse=True)
    ket_qua = [cap for cap in ket_qua if cap[1] >= settings.AI_NGUONG_DIEM_TRUY_HOI][:so_doan_toi_da]
    return _cat_bot_theo_gioi_han(ket_qua)
