import json
import re

from django.conf import settings

from ai_core.clients import lay_client_ai
from ai_core.dinh_dang import dinh_dang_ket_qua
from ai_core.exceptions import LoiAI
from ai_core.prompts import nap_prompt
from classes.models import LichHoc, LopHocPhan
from enrollment.services import (
    DA_DANG_KY,
    DA_DAY,
    DU_DIEU_KIEN,
    NGOAI_DOT_DANG_KY,
    THIEU_TIEN_QUYET,
    TRUNG_LICH,
    danh_sach_hoc_phan_da_dat,
    xac_dinh_trang_thai,
)

_MO_TA_TRANG_THAI = {
    DU_DIEU_KIEN: 'đủ điều kiện đăng ký',
    DA_DANG_KY: 'đã đăng ký',
    DA_DAY: 'đã đủ sĩ số',
}


class KetQuaTuVan:
    """Kết quả tư vấn trả về cho view/template. loi_ai khác None nghĩa là AI thất bại,
    nhưng danh_sach_trang_thai (do code tính) luôn có sẵn để sinh viên vẫn dùng được."""

    def __init__(self, danh_sach_trang_thai):
        self.danh_sach_trang_thai = danh_sach_trang_thai
        self.goi_y = []
        self.chua_nen_dang_ky = []
        self.luu_y = ''
        self.ghi_chu_loc = []
        self.loi_ai = None
        # Nội dung prompt đã dựng (điền cả khi goi_ai=False, để công cụ ca thử kiểm tra
        # độ dài/không rò rỉ dữ liệu cá nhân mà không cần gọi AI thật). None nếu không có
        # lớp học phần nào để tư vấn (chưa dựng prompt).
        self.he_thong = None
        self.nguoi_dung = None
        self.do_dai_prompt = None
        # Tên phiên bản model thực tế mà API trả lời — None nếu không gọi AI hoặc gọi thất bại.
        self.model_thuc_te = None


def _mo_ta_trang_thai(muc):
    trang_thai = muc['trang_thai']
    if trang_thai == THIEU_TIEN_QUYET:
        ten_cac_hoc_phan = ', '.join(hp.ten_hoc_phan for hp in muc['hoc_phan_con_thieu'])
        return f'thiếu tiên quyết ({ten_cac_hoc_phan})'
    if trang_thai == TRUNG_LICH:
        lich = muc['lich_trung']
        return f'trùng lịch với lớp {lich.ma_lop_hoc_phan_id} (Thứ {lich.thu})'
    if trang_thai == NGOAI_DOT_DANG_KY:
        return f"ngoài đợt đăng ký ({muc['ly_do_dot_dang_ky']})"
    return _MO_TA_TRANG_THAI.get(trang_thai, trang_thai)


def _dinh_dang_lich(danh_sach_lich):
    if not danh_sach_lich:
        return 'chưa có lịch'
    return ', '.join(
        f'Thứ {l.thu} tiết {l.tiet_bat_dau}-{l.tiet_bat_dau + l.so_tiet - 1}' for l in danh_sach_lich
    )


def _dinh_dang_hoc_phan_da_dat(danh_sach):
    if not danh_sach:
        return '(Sinh viên chưa đạt học phần nào.)'
    dong = [
        f'- {hoc_phan.pk}: {hoc_phan.ten_hoc_phan} ({hoc_phan.so_tin_chi} tín chỉ), '
        f'điểm tổng kết {diem_tong_ket}'
        for hoc_phan, diem_tong_ket in danh_sach
    ]
    return '\n'.join(dong)


def _dinh_dang_danh_sach_lop(danh_sach_trang_thai):
    if not danh_sach_trang_thai:
        return '(Không có lớp học phần nào đang mở trong học kỳ này.)'
    dong = []
    for muc in danh_sach_trang_thai:
        lop = muc['lop']
        dong.append(
            f"- {lop.ma_lop_hoc_phan}: {lop.ma_hoc_phan.ten_hoc_phan}, "
            f"lịch: {_dinh_dang_lich(muc['lich'])}, trạng thái: {muc['trang_thai_hien_thi']}"
        )
    return '\n'.join(dong)


def _tinh_danh_sach_trang_thai(sinh_vien, hoc_ky, nam_hoc):
    danh_sach_lop = LopHocPhan.objects.filter(hoc_ky=hoc_ky, nam_hoc=nam_hoc).select_related(
        'ma_hoc_phan', 'ma_giang_vien'
    ).order_by('ma_lop_hoc_phan')

    ket_qua = []
    for lop in danh_sach_lop:
        thong_tin = xac_dinh_trang_thai(sinh_vien, lop)
        lich = list(LichHoc.objects.filter(ma_lop_hoc_phan=lop).order_by('thu', 'tiet_bat_dau'))
        muc = {'lop': lop, 'lich': lich, **thong_tin}
        muc['trang_thai_hien_thi'] = _mo_ta_trang_thai(muc)
        ket_qua.append(muc)
    return ket_qua


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


def _lay_danh_sach_muc(du_lieu_json, khoa):
    gia_tri = du_lieu_json.get(khoa)
    if not isinstance(gia_tri, list):
        return []
    return [muc for muc in gia_tri if isinstance(muc, dict)]


def _loc_va_lam_giau(du_lieu_json, danh_sach_trang_thai, ghi_chu_loc):
    theo_ma = {muc['lop'].ma_lop_hoc_phan: muc for muc in danh_sach_trang_thai}
    ma_du_dieu_kien = {ma for ma, muc in theo_ma.items() if muc['trang_thai'] == DU_DIEU_KIEN}

    def _lam_giau(ma, ly_do):
        muc = theo_ma[ma]
        return {
            'ma_lop_hoc_phan': ma,
            'ten_hoc_phan': muc['lop'].ma_hoc_phan.ten_hoc_phan,
            'lich': _dinh_dang_lich(muc['lich']),
            'ly_do': ly_do,
        }

    goi_y_hop_le = []
    for muc in _lay_danh_sach_muc(du_lieu_json, 'goi_y'):
        ma = str(muc.get('ma_lop_hoc_phan', '')).strip()
        if ma not in theo_ma:
            ghi_chu_loc.append(f'Đã bỏ gợi ý lớp "{ma}" vì không có trong danh sách lớp đang mở.')
            continue
        if ma not in ma_du_dieu_kien:
            ghi_chu_loc.append(f'Đã bỏ gợi ý lớp "{ma}" vì lớp này chưa đủ điều kiện đăng ký.')
            continue
        goi_y_hop_le.append(_lam_giau(ma, muc.get('ly_do', '')))

    chua_nen_hop_le = []
    for muc in _lay_danh_sach_muc(du_lieu_json, 'chua_nen_dang_ky'):
        ma = str(muc.get('ma_lop_hoc_phan', '')).strip()
        if ma not in theo_ma:
            ghi_chu_loc.append(f'Đã bỏ mục "{ma}" vì không có trong danh sách lớp đang mở.')
            continue
        chua_nen_hop_le.append(_lam_giau(ma, muc.get('ly_do', '')))

    return goi_y_hop_le, chua_nen_hop_le


def tu_van_dang_ky(sinh_vien, hoc_ky, nam_hoc, ghi_chu, goi_ai=True):
    """Tư vấn đăng ký học phần cho một sinh viên trong một học kỳ/năm học.

    Nguyên tắc: CODE tính trạng thái từng lớp (dùng đúng hàm kiểm tra của
    enrollment.services), AI chỉ giải thích/xếp loại dựa trên trạng thái đã tính sẵn,
    không tự quyết định điều kiện. Không gửi họ tên, email, mã sinh viên, mã tài khoản
    cho AI — chỉ gửi mã/tên học phần, điểm, lịch học và ghi chú của sinh viên.

    goi_ai=False dựng prompt (điền vào ket_qua.he_thong/nguoi_dung/do_dai_prompt) nhưng
    KHÔNG gọi AI — dùng cho công cụ ca thử (chay_ca_thu_tu_van --tep) khi không có --ai,
    để kiểm tra độ dài/không rò rỉ dữ liệu cá nhân mà không tốn quota. Trang web luôn gọi
    với goi_ai=True (mặc định), hành vi không đổi.
    """
    danh_sach_trang_thai = _tinh_danh_sach_trang_thai(sinh_vien, hoc_ky, nam_hoc)
    ket_qua = KetQuaTuVan(danh_sach_trang_thai)

    if not danh_sach_trang_thai:
        ket_qua.luu_y = 'Không có lớp học phần nào đang mở trong học kỳ/năm học đã chọn.'
        return ket_qua

    hoc_phan_da_dat = danh_sach_hoc_phan_da_dat(sinh_vien)
    ghi_chu_sach = (ghi_chu or '').strip() or '(không có)'

    he_thong, nguoi_dung = nap_prompt(
        'tu_van_dang_ky', settings.AI_PHIEN_BAN_TU_VAN,
        hoc_ky=hoc_ky,
        nam_hoc=nam_hoc,
        hoc_phan_da_dat=_dinh_dang_hoc_phan_da_dat(hoc_phan_da_dat),
        danh_sach_lop=_dinh_dang_danh_sach_lop(danh_sach_trang_thai),
        ghi_chu=ghi_chu_sach,
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
    goi_y, chua_nen = _loc_va_lam_giau(du_lieu_json, danh_sach_trang_thai, ghi_chu_loc)
    ket_qua.goi_y = goi_y
    ket_qua.chua_nen_dang_ky = chua_nen
    ket_qua.ghi_chu_loc = ghi_chu_loc
    luu_y_goc = du_lieu_json.get('luu_y') or ''
    ket_qua.luu_y = dinh_dang_ket_qua(luu_y_goc if isinstance(luu_y_goc, str) else '')
    return ket_qua
