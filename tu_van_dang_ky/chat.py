"""Khung chat tư vấn đăng ký học phần: chọn học kỳ cần tư vấn từ câu gõ, chuyển kết quả sang dạng lưu được
trong session (ai_core.lich_su_chat). Cả câu gõ được dùng làm "ghi chú của sinh viên" (dữ liệu không tin cậy, nằm
trong khối dữ liệu của prompt) — đúng như ô ghi chú trước đây. Phần tính trạng thái và gọi AI vẫn là
services.tu_van_dang_ky."""
from django.utils import timezone

from accounts.tong_hop_phong_dao_tao import hoc_ky_dang_xet
from ai_core.phan_tich_cau_hoi import bo_dau, doc_pham_vi
from classes.models import LopHocPhan

from .services import _dinh_dang_lich

_TU_KHOA_TU_VAN = (
    'tu van', 'dang ky', 'lop', 'hoc phan', 'mon', 'nen hoc', 'goi y', 'ky toi', 'ky sau', 'hoc gi', 'trung lich',
    'tien quyet', 'tin chi',
)


class LuaChonHocKy:
    """tra_loi_ngay khác '' nghĩa là trả lời luôn (không có lớp mở, cần hỏi lại học kỳ, câu không liên quan) mà
    KHÔNG gọi AI."""

    def __init__(self, hoc_ky='', nam_hoc='', ghi_chu='', tra_loi_ngay=''):
        self.hoc_ky = hoc_ky
        self.nam_hoc = nam_hoc
        self.ghi_chu = ghi_chu
        self.tra_loi_ngay = tra_loi_ngay

    @property
    def mo_ta(self):
        return f'Học kỳ {self.hoc_ky} năm học {self.nam_hoc}'


def cac_ky_co_lop():
    """Các (hoc_ky, nam_hoc) có lớp học phần, mới nhất trước."""
    return sorted(
        set(LopHocPhan.objects.values_list('hoc_ky', 'nam_hoc').distinct()),
        key=lambda ky: (ky[1], ky[0]), reverse=True,
    )


def hoc_ky_mac_dinh(cac_ky):
    """Học kỳ đang có đợt đăng ký (cách chọn như trang chủ Phòng Đào tạo); không có thì học kỳ mới nhất có lớp."""
    dang_xet = hoc_ky_dang_xet(timezone.now())
    if dang_xet and (dang_xet['hoc_ky'], dang_xet['nam_hoc']) in cac_ky:
        return dang_xet['hoc_ky'], dang_xet['nam_hoc']
    return cac_ky[0]


def _liet_ke(cac_ky):
    return ', '.join(f'học kỳ {hk} năm học {nh}' for hk, nh in cac_ky[:6])


def chon_hoc_ky(cau_go):
    cac_ky = cac_ky_co_lop()
    if not cac_ky:
        return LuaChonHocKy(tra_loi_ngay='Hiện chưa có lớp học phần nào được mở để tư vấn.')
    pham_vi = doc_pham_vi(cau_go)
    co_lop_o = f'Học kỳ có lớp mở: {_liet_ke(cac_ky)}.'

    if pham_vi.hoc_ky and pham_vi.nam_hoc:
        if (pham_vi.hoc_ky, pham_vi.nam_hoc) not in cac_ky:
            return LuaChonHocKy(
                tra_loi_ngay=f'Không có lớp học phần nào mở trong học kỳ {pham_vi.hoc_ky} năm học {pham_vi.nam_hoc}. {co_lop_o}',
            )
        return LuaChonHocKy(pham_vi.hoc_ky, pham_vi.nam_hoc)

    if pham_vi.nam_hoc:
        ky_trong_nam = sorted(hk for hk, nh in cac_ky if nh == pham_vi.nam_hoc)
        if not ky_trong_nam:
            return LuaChonHocKy(tra_loi_ngay=f'Không có lớp học phần nào mở trong năm học {pham_vi.nam_hoc}. {co_lop_o}')
        if len(ky_trong_nam) == 1:
            return LuaChonHocKy(ky_trong_nam[0], pham_vi.nam_hoc)
        return LuaChonHocKy(tra_loi_ngay=(
            f'Năm học {pham_vi.nam_hoc} có mở lớp ở học kỳ {", ".join(ky_trong_nam)}. Bạn muốn tư vấn học kỳ nào? '
            f'Ví dụ: "Tư vấn học kỳ {ky_trong_nam[-1]} năm học {pham_vi.nam_hoc}".'
        ))

    if pham_vi.hoc_ky:
        nam_co_ky = [nh for hk, nh in cac_ky if hk == pham_vi.hoc_ky]
        if not nam_co_ky:
            return LuaChonHocKy(tra_loi_ngay=f'Không có lớp học phần nào mở trong học kỳ {pham_vi.hoc_ky}. {co_lop_o}')
        ghi_chu = '' if len(nam_co_ky) == 1 else (
            f'Bạn chưa nói năm học nên tư vấn học kỳ {pham_vi.hoc_ky} của năm học gần nhất có mở lớp ({nam_co_ky[0]}).'
        )
        return LuaChonHocKy(pham_vi.hoc_ky, nam_co_ky[0], ghi_chu=ghi_chu)

    if not any(tu in bo_dau(cau_go) for tu in _TU_KHOA_TU_VAN):
        hk, nh = hoc_ky_mac_dinh(cac_ky)
        return LuaChonHocKy(tra_loi_ngay=(
            'Mình tư vấn nên đăng ký lớp học phần nào, dựa trên tiên quyết, lịch học và sĩ số do hệ thống tính. '
            f'Ví dụ: "Tư vấn đăng ký học kỳ {hk} năm học {nh}, em muốn học các môn về AI".'
        ))
    hk, nh = hoc_ky_mac_dinh(cac_ky)
    return LuaChonHocKy(hk, nh, ghi_chu=f'Bạn chưa nói học kỳ nên tư vấn học kỳ {hk} năm học {nh}.')




def tra_loi_ngay_thanh_dict(noi_dung):
    return {'loai': 'thong_bao', 'noi_dung': noi_dung}


def ket_qua_thanh_dict(ket_qua, lua_chon):
    """Chuyển services.KetQuaTuVan thành dict chỉ gồm chuỗi/danh sách để lưu lịch sử chat trong session."""
    return {
        'loai': 'tu_van',
        'pham_vi': lua_chon.mo_ta,
        'hoc_ky': lua_chon.hoc_ky,
        'nam_hoc': lua_chon.nam_hoc,
        'ghi_chu': lua_chon.ghi_chu,
        'loi_ai': ket_qua.loi_ai or '',
        'goi_y': [dict(muc) for muc in ket_qua.goi_y],
        'chua_nen_dang_ky': [dict(muc) for muc in ket_qua.chua_nen_dang_ky],
        'ghi_chu_loc': list(ket_qua.ghi_chu_loc),
        'luu_y': (ket_qua.luu_y or '').strip(),
        'danh_sach': [
            {'ma': muc['lop'].ma_lop_hoc_phan, 'ten': muc['lop'].ma_hoc_phan.ten_hoc_phan, 'lich': _dinh_dang_lich(muc['lich']),
             'trang_thai': muc['trang_thai'], 'trang_thai_hien_thi': muc['trang_thai_hien_thi']}
            for muc in ket_qua.danh_sach_trang_thai
        ],
    }
