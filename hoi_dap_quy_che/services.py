import json
import re

from django.conf import settings

from ai_core.clients import lay_client_ai
from ai_core.dinh_dang import dinh_dang_ket_qua
from ai_core.exceptions import LoiAI
from ai_core.prompts import nap_prompt

from .chi_muc import truy_hoi

CAU_TRA_LOI_KHONG_TIM_THAY = (
    'Không tìm thấy nội dung phù hợp trong quy chế, vui lòng liên hệ Phòng Đào tạo.'
)


class KetQuaHoiDap:
    """Kết quả hỏi đáp trả về cho view/template. loi_ai khác None nghĩa là AI thất bại,
    nhưng doan_truy_hoi (do code truy hồi) luôn có sẵn để sinh viên tự đọc."""

    def __init__(self, doan_truy_hoi):
        self.doan_truy_hoi = doan_truy_hoi
        self.tra_loi = ''
        self.co_trong_quy_che = None
        self.nguon = []
        self.ghi_chu_loc = []
        self.loi_ai = None
        # Tên lớp ngoại lệ ai_core gốc (vd. "QuaGioiHanTanSuatAI"), để nơi gọi (như lệnh
        # chay_ca_thu_quy_che) phân biệt được loại lỗi một cách chắc chắn, thay vì phải
        # so khớp chuỗi thông điệp (dễ vỡ nếu thông điệp đổi).
        self.loai_loi_ai = None
        # Chi tiết chẩn đoán an toàn từ ai_core (loại lỗi gốc, mã HTTP, thông điệp API) —
        # xem ai_core.clients._trich_chi_tiet_an_toan. Không bao giờ chứa khóa API.
        self.chi_tiet_loi_ai = None
        # Chỉ có giá trị khi loai_loi_ai == 'QuaGioiHanTanSuatAI': 'ngay' (hết hạn mức
        # hôm nay), 'phut' (vượt tần suất theo phút), hoặc None (không đủ căn cứ phân biệt).
        self.pham_vi_gioi_han_tan_suat = None
        # Số ký tự phần nội dung (nguoi_dung) đã gửi AI — có giá trị ngay cả khi AI báo
        # lỗi, vì được ghi lại trước khi gọi client, giúp chẩn đoán (vd. lỗi do quá dài).
        self.do_dai_prompt = None
        # Tên phiên bản model thực tế mà API trả lời (client.model_version_thuc_te) —
        # None nếu chưa từng gọi tới client (vd. lay_client_ai() tự thất bại) hoặc lời
        # gọi thất bại trước khi API kịp phản hồi.
        self.model_thuc_te = None
        self.khong_tim_thay = False


def _dinh_dang_doan_trich(doan_truy_hoi):
    dong = []
    for doan, _diem in doan_truy_hoi:
        khoan_text = f', khoản {doan["khoan"]}' if doan['khoan'] else ''
        dong.append(f"[Nguồn: {doan['ten_tai_lieu']}, Điều {doan['dieu']}{khoan_text}]\n{doan['noi_dung']}")
    return '\n\n'.join(dong)


def _trich_json(van_ban):
    van_ban = (van_ban or '').strip()
    khop = re.match(r'^```(?:json)?\s*(.*?)\s*```$', van_ban, re.DOTALL)
    if khop:
        van_ban = khop.group(1).strip()
    try:
        du_lieu = json.loads(van_ban)
    except json.JSONDecodeError as loi:
        raise ValueError('JSON không hợp lệ') from loi
    if not isinstance(du_lieu, dict):
        raise ValueError('JSON không đúng cấu trúc mong đợi (không phải object)')
    return du_lieu


_MAU_TIEN_TO_DIEU = re.compile(r'^\s*điều\s+', re.IGNORECASE)
_MAU_TIEN_TO_KHOAN = re.compile(r'^\s*khoản\s+', re.IGNORECASE)


def _chuan_hoa(gia_tri):
    """Chuẩn hóa một giá trị bất kỳ AI trả về (chuỗi/số nguyên/None) để so sánh: ép về
    chuỗi, cắt khoảng trắng, không phân biệt hoa/thường. Dùng chung cho tên tài liệu."""
    if gia_tri is None:
        return ''
    return str(gia_tri).strip().casefold()


def _chuan_hoa_dieu(gia_tri):
    """Như _chuan_hoa, thêm bỏ tiền tố "Điều " nếu có (AI có thể trả "3" hoặc "Điều 3")."""
    return _MAU_TIEN_TO_DIEU.sub('', _chuan_hoa(gia_tri)).strip()


def _chuan_hoa_khoan(gia_tri):
    """Như _chuan_hoa, thêm bỏ tiền tố "khoản " nếu có (AI có thể trả "3" hoặc "khoản 3")."""
    return _MAU_TIEN_TO_KHOAN.sub('', _chuan_hoa(gia_tri)).strip()


def _nhom_doan_theo_dieu(doan_truy_hoi):
    """Nhóm các đoạn đã truy hồi (đã gửi AI) theo (tên tài liệu, Điều) đã chuẩn hóa, để
    _tim_doan_khop tra theo Điều trước rồi mới xét khoản."""
    nhom = {}
    for doan, _diem in doan_truy_hoi:
        khoa = (_chuan_hoa(doan['ten_tai_lieu']), _chuan_hoa_dieu(doan['dieu']))
        nhom.setdefault(khoa, []).append(doan)
    return nhom


def _tim_doan_khop(muc, nhom_theo_dieu):
    """Tìm đoạn đã truy hồi khớp với một nguồn AI trích (muc), sau khi chuẩn hóa tên tài
    liệu/Điều/khoản (bỏ tiền tố "Điều "/"khoản ", ép kiểu, cắt khoảng trắng, không phân
    biệt hoa/thường).

    Nếu Điều đó chỉ được gửi AI dưới dạng MỘT đoạn KHÔNG tách khoản (khoan rỗng — toàn bộ
    Điều đủ ngắn để không cần chia theo khoản, xem chia_doan.py), chấp nhận nguồn bất kể
    AI có trích khoản hay không, vì mọi khoản của Điều đó đều nằm trong đúng đoạn gửi đi
    — hiển thị theo đoạn truy hồi (không có khoản), không theo khoản AI tự ghi thêm.

    Ngược lại (Điều được tách thành nhiều đoạn theo khoản), khoản AI trích phải khớp
    đúng một trong các đoạn đã gửi. Nguồn không khớp đoạn nào đã gửi (sai tài liệu, sai
    Điều, hoặc sai khoản khi Điều có tách khoản) coi là bịa, trả None — vẫn chống bịa.
    """
    khoa_dieu = (_chuan_hoa(muc.get('ten_tai_lieu')), _chuan_hoa_dieu(muc.get('dieu')))
    cac_doan = nhom_theo_dieu.get(khoa_dieu)
    if not cac_doan:
        return None
    if len(cac_doan) == 1 and not cac_doan[0]['khoan']:
        return cac_doan[0]
    khoan_can_tim = _chuan_hoa_khoan(muc.get('khoan'))
    for doan in cac_doan:
        if _chuan_hoa_khoan(doan['khoan']) == khoan_can_tim:
            return doan
    return None


def _loc_nguon(gia_tri, doan_truy_hoi, ghi_chu_loc):
    if not isinstance(gia_tri, list):
        return []
    nhom_theo_dieu = _nhom_doan_theo_dieu(doan_truy_hoi)
    ket_qua = []
    for muc in gia_tri:
        if not isinstance(muc, dict):
            continue
        doan = _tim_doan_khop(muc, nhom_theo_dieu)
        if doan is None:
            ghi_chu_loc.append(
                f"Đã bỏ một nguồn AI trích vì không khớp đoạn quy chế đã truy hồi "
                f"(tài liệu={muc.get('ten_tai_lieu')!r}, Điều={muc.get('dieu')!r}, "
                f"khoản={muc.get('khoan')!r})."
            )
            continue
        ket_qua.append({
            'ten_tai_lieu': doan['ten_tai_lieu'],
            'dieu': doan['dieu'],
            'khoan': doan['khoan'],
            'trich_doan': doan['noi_dung'],
        })
    return ket_qua


def hoi_dap_quy_che(cau_hoi):
    """Trả lời một câu hỏi quy chế dựa trên các đoạn truy hồi được (RAG đơn giản, không
    dùng dịch vụ embedding). Không gửi AI bất kỳ dữ liệu cá nhân/học tập nào — chỉ câu
    hỏi và các đoạn quy chế công khai đã truy hồi.
    """
    doan_truy_hoi = truy_hoi(cau_hoi)
    ket_qua = KetQuaHoiDap(doan_truy_hoi)

    if not doan_truy_hoi:
        ket_qua.khong_tim_thay = True
        ket_qua.tra_loi = CAU_TRA_LOI_KHONG_TIM_THAY
        return ket_qua

    he_thong, nguoi_dung = nap_prompt(
        'hoi_dap_quy_che', settings.AI_PHIEN_BAN_QUY_CHE,
        cau_hoi=cau_hoi.strip(),
        doan_trich=_dinh_dang_doan_trich(doan_truy_hoi),
    )
    ket_qua.do_dai_prompt = len(nguoi_dung)

    client = None
    try:
        client = lay_client_ai()
        phan_hoi_tho = client.sinh_noi_dung(he_thong=he_thong, nguoi_dung=nguoi_dung)
    except LoiAI as loi:
        ket_qua.loi_ai = str(loi)
        ket_qua.loai_loi_ai = type(loi).__name__
        ket_qua.chi_tiet_loi_ai = loi.chi_tiet
        ket_qua.pham_vi_gioi_han_tan_suat = getattr(loi, 'pham_vi', None)
        ket_qua.model_thuc_te = getattr(client, 'model_version_thuc_te', None)
        return ket_qua

    ket_qua.model_thuc_te = getattr(client, 'model_version_thuc_te', None)

    try:
        du_lieu_json = _trich_json(phan_hoi_tho)
    except ValueError:
        ket_qua.loi_ai = 'Phản hồi từ AI không đúng định dạng, vui lòng thử lại sau.'
        return ket_qua

    ghi_chu_loc = []
    nguon_hop_le = _loc_nguon(du_lieu_json.get('nguon'), doan_truy_hoi, ghi_chu_loc)
    co_trong_quy_che = bool(du_lieu_json.get('co_trong_quy_che'))

    if co_trong_quy_che and not nguon_hop_le:
        # AI nói "có trong quy chế" nhưng không còn nguồn nào hợp lệ sau khi lọc ->
        # không đủ tin cậy để hiển thị câu trả lời đó, coi như không tìm thấy.
        ket_qua.khong_tim_thay = True
        ket_qua.tra_loi = CAU_TRA_LOI_KHONG_TIM_THAY
        ket_qua.ghi_chu_loc = ghi_chu_loc
        return ket_qua

    tra_loi_goc = du_lieu_json.get('tra_loi') or ''
    ket_qua.tra_loi = dinh_dang_ket_qua(tra_loi_goc if isinstance(tra_loi_goc, str) else '')
    ket_qua.co_trong_quy_che = co_trong_quy_che
    ket_qua.nguon = nguon_hop_le
    ket_qua.ghi_chu_loc = ghi_chu_loc
    return ket_qua
