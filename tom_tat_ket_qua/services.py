import json
import re

from django.conf import settings

from ai_core.clients import lay_client_ai
from ai_core.dinh_dang import dinh_dang_ket_qua
from ai_core.exceptions import LoiAI
from ai_core.prompts import nap_prompt
from grades.services import bang_diem_chi_tiet


class KetQuaTomTat:
    """Kết quả tóm tắt trả về cho view/template. loi_ai khác None nghĩa là AI thất bại,
    nhưng bang_diem/so_lieu (do code tính) luôn có sẵn để vẫn dùng được."""

    def __init__(self, bang_diem, so_lieu):
        self.bang_diem = bang_diem
        self.so_lieu = so_lieu
        self.tom_tat = ''
        self.diem_manh = []
        self.can_cai_thien = []
        self.ke_hoach_goi_y = []
        self.luu_y = ''
        self.ghi_chu_loc = []
        self.loi_ai = None
        self.chua_co_du_lieu = False
        # Nội dung prompt đã dựng (điền cả khi goi_ai=False). None nếu chưa có điểm nào.
        self.he_thong = None
        self.nguoi_dung = None
        self.do_dai_prompt = None
        # Tên phiên bản model thực tế mà API trả lời — None nếu không gọi AI hoặc gọi thất bại.
        self.model_thuc_te = None


def _tinh_so_lieu_tong_hop(bang_diem):
    da_dat = [muc for muc in bang_diem if muc['dat']]
    chua_dat = [muc for muc in bang_diem if not muc['dat']]
    return {
        'tong_tin_chi_dat': sum(muc['hoc_phan'].so_tin_chi for muc in da_dat),
        'so_hoc_phan_dat': len(da_dat),
        'so_hoc_phan_chua_dat': len(chua_dat),
        'hoc_phan_diem_cao_nhat': max(bang_diem, key=lambda m: m['diem_tong_ket']),
        'hoc_phan_diem_thap_nhat': min(bang_diem, key=lambda m: m['diem_tong_ket']),
    }


def _dinh_dang_bang_diem(bang_diem):
    dong = []
    for muc in sorted(bang_diem, key=lambda m: (m['nam_hoc'], m['hoc_ky'], m['hoc_phan'].pk)):
        hoc_phan = muc['hoc_phan']
        trang_thai = 'đạt' if muc['dat'] else 'chưa đạt'
        dong.append(
            f"- {hoc_phan.pk}: {hoc_phan.ten_hoc_phan} ({hoc_phan.so_tin_chi} tín chỉ), "
            f"học kỳ {muc['hoc_ky']} năm học {muc['nam_hoc']}, điểm quá trình "
            f"{muc['diem_qua_trinh']}, điểm thi {muc['diem_thi']}, điểm tổng kết "
            f"{muc['diem_tong_ket']} ({trang_thai})"
        )
    return '\n'.join(dong)


def _dinh_dang_so_lieu(so_lieu):
    cao_nhat = so_lieu['hoc_phan_diem_cao_nhat']
    thap_nhat = so_lieu['hoc_phan_diem_thap_nhat']
    return '\n'.join([
        f"- Tổng tín chỉ đã đạt: {so_lieu['tong_tin_chi_dat']}",
        f"- Số học phần đã đạt: {so_lieu['so_hoc_phan_dat']}",
        f"- Số học phần chưa đạt: {so_lieu['so_hoc_phan_chua_dat']}",
        f"- Học phần điểm cao nhất: {cao_nhat['hoc_phan'].pk} ({cao_nhat['hoc_phan'].ten_hoc_phan}), "
        f"điểm tổng kết {cao_nhat['diem_tong_ket']}",
        f"- Học phần điểm thấp nhất: {thap_nhat['hoc_phan'].pk} ({thap_nhat['hoc_phan'].ten_hoc_phan}), "
        f"điểm tổng kết {thap_nhat['diem_tong_ket']}",
    ])


def _trich_json(van_ban):
    """Phân tích JSON từ phản hồi AI; bỏ khối markdown ```json ... ``` nếu có."""
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


def _loc_danh_sach_chuoi(gia_tri):
    if not isinstance(gia_tri, list):
        return []
    return [str(x) for x in gia_tri if isinstance(x, (str, int, float))]


def _loc_can_cai_thien(gia_tri, bang_diem, ghi_chu_loc):
    if not isinstance(gia_tri, list):
        return []
    theo_ma = {muc['hoc_phan'].pk: muc for muc in bang_diem}
    ket_qua = []
    for muc in gia_tri:
        if not isinstance(muc, dict):
            continue
        ma = str(muc.get('ma_hoc_phan', '')).strip()
        if ma not in theo_ma:
            ghi_chu_loc.append(f'Đã bỏ mục "{ma}" vì không có trong dữ liệu điểm đã gửi.')
            continue
        hoc_phan_muc = theo_ma[ma]
        ket_qua.append({
            'ma_hoc_phan': ma,
            'ten_hoc_phan': hoc_phan_muc['hoc_phan'].ten_hoc_phan,
            'diem_tong_ket': hoc_phan_muc['diem_tong_ket'],
            'ly_do': muc.get('ly_do', ''),
        })
    return ket_qua


def tom_tat_ket_qua_hoc_tap(sinh_vien, goi_ai=True):
    """Tóm tắt kết quả học tập của một sinh viên.

    Nguyên tắc: CODE tính số liệu (tổng tín chỉ đã đạt, số học phần đạt/chưa đạt, điểm
    cao nhất/thấp nhất), AI chỉ diễn giải dựa trên số liệu đã tính sẵn, không tự tính lại.
    Không gửi họ tên, email, mã sinh viên, mã tài khoản cho AI — chỉ gửi mã/tên học phần,
    tín chỉ, học kỳ, điểm và số liệu tổng hợp.

    goi_ai=False dựng prompt (điền vào ket_qua.he_thong/nguoi_dung/do_dai_prompt) nhưng
    KHÔNG gọi AI — dùng cho công cụ ca thử (chay_ca_thu_tom_tat) khi không có --ai, để
    kiểm tra độ dài/không rò rỉ dữ liệu cá nhân mà không tốn quota. Trang web luôn gọi với
    goi_ai=True (mặc định), hành vi không đổi.
    """
    bang_diem = bang_diem_chi_tiet(sinh_vien)
    if not bang_diem:
        ket_qua = KetQuaTomTat([], None)
        ket_qua.chua_co_du_lieu = True
        ket_qua.luu_y = 'Sinh viên chưa có điểm nào để tóm tắt.'
        return ket_qua

    so_lieu = _tinh_so_lieu_tong_hop(bang_diem)
    ket_qua = KetQuaTomTat(bang_diem, so_lieu)

    he_thong, nguoi_dung = nap_prompt(
        'tom_tat_ket_qua', settings.AI_PHIEN_BAN_TOM_TAT,
        so_lieu_tong_hop=_dinh_dang_so_lieu(so_lieu),
        bang_diem=_dinh_dang_bang_diem(bang_diem),
    )
    ket_qua.he_thong = he_thong
    ket_qua.nguoi_dung = nguoi_dung
    ket_qua.do_dai_prompt = len(nguoi_dung)

    if not goi_ai:
        return ket_qua

    client = None
    try:
        client = lay_client_ai()
        phan_hoi_tho = client.sinh_noi_dung(he_thong=he_thong, nguoi_dung=nguoi_dung)
    except LoiAI as loi:
        ket_qua.loi_ai = str(loi)
        ket_qua.model_thuc_te = getattr(client, 'model_version_thuc_te', None)
        return ket_qua

    ket_qua.model_thuc_te = getattr(client, 'model_version_thuc_te', None)

    try:
        du_lieu_json = _trich_json(phan_hoi_tho)
    except ValueError:
        ket_qua.loi_ai = 'Phản hồi từ AI không đúng định dạng, vui lòng thử lại sau.'
        return ket_qua

    ghi_chu_loc = []
    tom_tat_goc = du_lieu_json.get('tom_tat') or ''
    ket_qua.tom_tat = tom_tat_goc if isinstance(tom_tat_goc, str) else ''
    ket_qua.diem_manh = _loc_danh_sach_chuoi(du_lieu_json.get('diem_manh'))
    ket_qua.can_cai_thien = _loc_can_cai_thien(du_lieu_json.get('can_cai_thien'), bang_diem, ghi_chu_loc)
    ket_qua.ke_hoach_goi_y = _loc_danh_sach_chuoi(du_lieu_json.get('ke_hoach_goi_y'))
    ket_qua.ghi_chu_loc = ghi_chu_loc
    luu_y_goc = du_lieu_json.get('luu_y') or ''
    ket_qua.luu_y = dinh_dang_ket_qua(luu_y_goc if isinstance(luu_y_goc, str) else '')
    return ket_qua
