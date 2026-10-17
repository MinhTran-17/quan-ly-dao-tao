"""Khung chat tóm tắt kết quả học tập: chọn phạm vi từ câu gõ, chuyển kết quả sang dạng lưu được trong session (ai_core.lich_su_chat). Phần gọi AI vẫn là services.tom_tat_ket_qua_hoc_tap."""
from django.utils.formats import localize

from ai_core.phan_tich_cau_hoi import bo_dau, doc_pham_vi
from enrollment.models import DangKyHocPhan, TrangThaiDangKy

_TU_KHOA_TOM_TAT = ('tom tat', 'ket qua', 'hoc tap', 'diem', 'nhan xet', 'danh gia', 'hoc luc', 'cai thien')


class LuaChonPhamVi:
    """Kết quả đọc câu gõ. tra_loi_ngay khác '' nghĩa là trả lời luôn (chưa có điểm, câu không liên quan...) mà
    KHÔNG gọi AI; ngược lại gọi tom_tat_ket_qua_hoc_tap với hoc_ky/nam_hoc (None = không giới hạn)."""

    def __init__(self, hoc_ky=None, nam_hoc=None, mo_ta='Toàn khóa', ghi_chu='', tra_loi_ngay=''):
        self.hoc_ky = hoc_ky
        self.nam_hoc = nam_hoc
        self.mo_ta = mo_ta
        self.ghi_chu = ghi_chu
        self.tra_loi_ngay = tra_loi_ngay


def cac_ky_co_diem(sinh_vien):
    """Các (hoc_ky, nam_hoc) mà sinh viên có ít nhất một học phần đủ điểm (đăng ký còn hiệu lực), mới nhất trước.
    Cùng điều kiện "đủ điểm" với grades.services.bang_diem_chi_tiet (Diem.tinh_diem_tong_ket() khác None)."""
    cac_ky = set()
    for dang_ky in DangKyHocPhan.objects.filter(
        ma_sinh_vien=sinh_vien, trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
    ).select_related('ma_lop_hoc_phan', 'diem'):
        diem = getattr(dang_ky, 'diem', None)
        if diem is not None and diem.tinh_diem_tong_ket() is not None:
            cac_ky.add((dang_ky.ma_lop_hoc_phan.hoc_ky, dang_ky.ma_lop_hoc_phan.nam_hoc))
    return sorted(cac_ky, key=lambda ky: (ky[1], ky[0]), reverse=True)


def _liet_ke(cac_ky):
    return ', '.join(f'học kỳ {hk} năm học {nh}' for hk, nh in cac_ky)


def chon_pham_vi(sinh_vien, cau_go):
    """Đọc phạm vi (ai_core.phan_tich_cau_hoi) rồi đối chiếu với các học kỳ thật sự có điểm của sinh viên.

    - Kỳ + năm: đúng học kỳ đó. Chỉ năm: cả năm học (năm mới có một học kỳ thì tóm tắt học kỳ đó).
    - Chỉ kỳ: học kỳ đó của năm học gần nhất có điểm. "Gần nhất": học kỳ mới nhất có điểm.
    - "Toàn khóa"/"tích lũy" hoặc chỉ hỏi chung (có từ "tóm tắt", "kết quả"...): toàn khóa.
    - Phạm vi chưa có điểm, hoặc câu không liên quan tới tóm tắt: trả lời ngay, không gọi AI.
    """
    cac_ky = cac_ky_co_diem(sinh_vien)
    if not cac_ky:
        return LuaChonPhamVi(tra_loi_ngay='Chưa có học phần nào đủ điểm (điểm quá trình và điểm thi) để tóm tắt.')
    pham_vi = doc_pham_vi(cau_go)
    co_diem_o = f'Hiện có điểm ở: {_liet_ke(cac_ky)}.'

    if pham_vi.hoc_ky and pham_vi.nam_hoc:
        if (pham_vi.hoc_ky, pham_vi.nam_hoc) not in cac_ky:
            return LuaChonPhamVi(
                tra_loi_ngay=f'Chưa có điểm học kỳ {pham_vi.hoc_ky} năm học {pham_vi.nam_hoc}. {co_diem_o}',
            )
        return LuaChonPhamVi(pham_vi.hoc_ky, pham_vi.nam_hoc, f'Học kỳ {pham_vi.hoc_ky} năm học {pham_vi.nam_hoc}')

    if pham_vi.nam_hoc:
        ky_trong_nam = [hk for hk, nh in cac_ky if nh == pham_vi.nam_hoc]
        if not ky_trong_nam:
            return LuaChonPhamVi(tra_loi_ngay=f'Chưa có điểm năm học {pham_vi.nam_hoc}. {co_diem_o}')
        if len(ky_trong_nam) == 1:
            hk = ky_trong_nam[0]
            return LuaChonPhamVi(
                hk, pham_vi.nam_hoc, f'Học kỳ {hk} năm học {pham_vi.nam_hoc}',
                ghi_chu=f'Năm học {pham_vi.nam_hoc} mới có điểm học kỳ {hk} nên tóm tắt học kỳ {hk}.',
            )
        return LuaChonPhamVi(None, pham_vi.nam_hoc, f'Cả năm học {pham_vi.nam_hoc}')

    if pham_vi.hoc_ky:
        nam_co_ky = [nh for hk, nh in cac_ky if hk == pham_vi.hoc_ky]
        if not nam_co_ky:
            return LuaChonPhamVi(tra_loi_ngay=f'Chưa có điểm học kỳ {pham_vi.hoc_ky} ở năm học nào. {co_diem_o}')
        nh = nam_co_ky[0]
        ghi_chu = '' if len(nam_co_ky) == 1 else (
            f'Bạn chưa nói năm học nên tóm tắt học kỳ {pham_vi.hoc_ky} của năm học gần nhất có điểm ({nh}).'
        )
        return LuaChonPhamVi(pham_vi.hoc_ky, nh, f'Học kỳ {pham_vi.hoc_ky} năm học {nh}', ghi_chu=ghi_chu)

    if pham_vi.gan_nhat:
        hk, nh = cac_ky[0]
        return LuaChonPhamVi(hk, nh, f'Học kỳ {hk} năm học {nh} (gần nhất có điểm)')

    if pham_vi.toan_khoa or any(tu in bo_dau(cau_go) for tu in _TU_KHOA_TOM_TAT):
        return LuaChonPhamVi()

    return LuaChonPhamVi(tra_loi_ngay=(
        'Mình tóm tắt kết quả học tập theo học kỳ, năm học hoặc toàn khóa. Ví dụ: "Tóm tắt học kỳ '
        f'{cac_ky[0][0]} năm học {cac_ky[0][1]}", "Tóm tắt năm học {cac_ky[0][1]}", "Tóm tắt toàn khóa".'
    ))




def _so(gia_tri):
    return '' if gia_tri is None else localize(gia_tri)


def tra_loi_ngay_thanh_dict(noi_dung):
    return {'loai': 'thong_bao', 'noi_dung': noi_dung}


def ket_qua_thanh_dict(ket_qua, lua_chon):
    """Chuyển services.KetQuaTomTat thành dict chỉ gồm chuỗi/số/danh sách để lưu lịch sử chat trong session."""
    du_lieu = {
        'loai': 'tom_tat',
        'pham_vi': lua_chon.mo_ta,
        'ghi_chu': lua_chon.ghi_chu,
        'loi_ai': ket_qua.loi_ai or '',
        'tom_tat': ket_qua.tom_tat,
        'diem_manh': list(ket_qua.diem_manh),
        'can_cai_thien': [
            {'ma_hoc_phan': m['ma_hoc_phan'], 'ten_hoc_phan': m['ten_hoc_phan'],
             'diem_tong_ket': _so(m['diem_tong_ket']), 'ly_do': str(m.get('ly_do') or '')}
            for m in ket_qua.can_cai_thien
        ],
        'ke_hoach_goi_y': list(ket_qua.ke_hoach_goi_y),
        'ghi_chu_loc': list(ket_qua.ghi_chu_loc),
        'luu_y': (ket_qua.luu_y or '').strip(),
        'so_lieu': None,
        'bang_diem': [],
    }
    if ket_qua.so_lieu:
        cao, thap = ket_qua.so_lieu['hoc_phan_diem_cao_nhat'], ket_qua.so_lieu['hoc_phan_diem_thap_nhat']
        du_lieu['so_lieu'] = {
            'tong_tin_chi_dat': ket_qua.so_lieu['tong_tin_chi_dat'],
            'so_hoc_phan_dat': ket_qua.so_lieu['so_hoc_phan_dat'],
            'so_hoc_phan_chua_dat': ket_qua.so_lieu['so_hoc_phan_chua_dat'],
            'cao_nhat': f"{cao['hoc_phan'].ten_hoc_phan} ({_so(cao['diem_tong_ket'])})",
            'thap_nhat': f"{thap['hoc_phan'].ten_hoc_phan} ({_so(thap['diem_tong_ket'])})",
        }
        du_lieu['bang_diem'] = [
            {'ma': m['hoc_phan'].ma_hoc_phan, 'ten': m['hoc_phan'].ten_hoc_phan, 'hoc_ky': m['hoc_ky'],
             'nam_hoc': m['nam_hoc'], 'qua_trinh': _so(m['diem_qua_trinh']), 'thi': _so(m['diem_thi']),
             'tong_ket': _so(m['diem_tong_ket'])}
            for m in sorted(ket_qua.bang_diem, key=lambda m: (m['nam_hoc'], m['hoc_ky'], m['hoc_phan'].pk))
        ]
    return du_lieu
