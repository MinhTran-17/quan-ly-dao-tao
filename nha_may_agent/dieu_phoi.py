"""Điều phối dây chuyền nhà máy agent chạy bằng Gemini (qua ai_core).

phân tích → [người duyệt đặc tả] → lập trình → kiểm thử viên viết test → [người duyệt diff]
→ ghi tệp → chạy test (sửa tối đa 2 vòng, vẫn lỗi thì hoàn tác) → review + kiểm tra bảo mật.

Prompt vai trò đọc từ agents/<vai_tro>.md, ngữ cảnh từ AGENTS.md, khung prompt từ prompts/nha_may_*/.
Mọi thay đổi tệp đi qua rao_chan.kiem_tra_ghi trước khi ghi; mọi lỗi gọi AI là ai_core.exceptions.LoiAI.
"""
import difflib
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from ai_core.clients import ClientAIGia, GeminiClient
from ai_core.exceptions import LoiAI, PhanHoiSaiDinhDangAI
from ai_core.prompts import nap_prompt
from ai_core.theo_doi import goi_ai_co_ghi_log

from .rao_chan import THU_MUC_DUOC_GHI, ViPhamRaoChan, kiem_tra_doc, kiem_tra_ghi

SO_VONG_SUA_TOI_DA = 2
SO_TEP_MOI_LUOT_TOI_DA = 15
SO_TEP_NGU_CANH_TOI_DA = 8
GIOI_HAN_KY_TU_MOI_TEP = 20_000
GIOI_HAN_KY_TU_DAU_RA_TEST = 6_000
GIOI_HAN_KY_TU_DIFF = 40_000
SO_TEP_LIET_KE_TOI_DA = 600
# Chừa lại trong ngân sách ký tự của prompt (phần khung prompt có thể dài thêm chút ít sau khi điền biến).
KY_TU_CHUA_LAI = 2_000
NGAN_SACH_TOI_THIEU = 2_000


class VuotSoLuotGoiAI(LoiAI):
    def __init__(self, gioi_han):
        super().__init__(f'Đã dùng hết {gioi_han} lượt gọi AI cho lần chạy này (giới hạn của nhà máy agent).')


def tao_client():
    """Client Gemini với cấu hình riêng cho nhà máy, không đụng cấu hình của 3 chức năng AI trong sản phẩm:
    - giới hạn ký tự NHA_MAY_GIOI_HAN_KY_TU (prompt chứa mã nguồn dài hơn nhiều so với AI_GIOI_HAN_KY_TU);
    - thời gian chờ NHA_MAY_TIMEOUT_GIAY: SDK gửi timeout này lên máy chủ (header X-Server-Timeout), model
      trả lời không kịp thì máy chủ trả 504 DEADLINE_EXCEEDED — prompt dài + đầu ra dài cần lâu hơn AI_TIMEOUT_GIAY;
    - số lần thử lại NHA_MAY_SO_LAN_THU_LAI: mỗi lần thử lại một prompt dài đều tốn hạn mức.
    AI_BACKEND='gia' thì dùng client giả, không gọi mạng."""
    if getattr(settings, 'AI_BACKEND', 'gemini') == 'gia':
        return ClientAIGia()
    return GeminiClient(
        gioi_han_ky_tu=settings.NHA_MAY_GIOI_HAN_KY_TU,
        timeout_giay=settings.NHA_MAY_TIMEOUT_GIAY,
        so_lan_thu_lai=settings.NHA_MAY_SO_LAN_THU_LAI,
    )


def doc_de_bai_rut_gon():
    """Đề bài mục 1–5 (bài toán, mục tiêu, yêu cầu chức năng/kỹ thuật, dữ liệu) — đủ để xét "ngoài đề";
    bỏ mục 6 trở đi (hướng dẫn dùng AI theo giai đoạn SDLC, mức độ khó) để prompt ngắn hơn."""
    de_bai = (settings.BASE_DIR / 'docs' / 'de-bai.md').read_text(encoding='utf-8')
    return re.split(r'\n## 6\.', de_bai, maxsplit=1)[0].rstrip()


def doc_json(van_ban):
    """Đọc đối tượng JSON trong phản hồi AI (chấp nhận bọc ```json ... ``` hoặc có chữ thừa quanh)."""
    van_ban = (van_ban or '').strip()
    khop = re.match(r'^```(?:json)?\s*(.*?)\s*```$', van_ban, re.S)
    if khop:
        van_ban = khop.group(1)
    dau, cuoi = van_ban.find('{'), van_ban.rfind('}')
    if dau == -1 or cuoi < dau:
        raise PhanHoiSaiDinhDangAI()
    try:
        du_lieu = json.loads(van_ban[dau:cuoi + 1])
    except ValueError as loi:
        raise PhanHoiSaiDinhDangAI() from loi
    if not isinstance(du_lieu, dict):
        raise PhanHoiSaiDinhDangAI()
    return du_lieu


def _cat_duoi(van_ban, gioi_han):
    """Giữ phần cuối (đầu ra test: lỗi và tổng kết nằm ở cuối)."""
    return van_ban if len(van_ban) <= gioi_han else '…(đã cắt phần đầu)…\n' + van_ban[-gioi_han:]


def _cat_dau(van_ban, gioi_han):
    """Giữ phần đầu (code, diff)."""
    gioi_han = max(gioi_han, 0)
    return van_ban if len(van_ban) <= gioi_han else van_ban[:gioi_han] + '\n…(đã cắt phần còn lại)…'


def chay_bo_test(goc):
    """Chạy toàn bộ test của dự án trong tiến trình con; trả (đạt?, đầu ra)."""
    ket_qua = subprocess.run(
        [sys.executable, 'manage.py', 'test', '--noinput'],
        cwd=goc, capture_output=True, encoding='utf-8', errors='replace', timeout=1800,
    )
    return ket_qua.returncode == 0, (ket_qua.stdout or '') + (ket_qua.stderr or '')


def tom_tat_dau_ra_test(dau_ra):
    """Lấy dòng 'Ran N tests' và dòng kết luận (OK / FAILED (...)) từ đầu ra test."""
    dong = [d.strip() for d in (dau_ra or '').splitlines()]
    ran = next((d for d in dong if d.startswith('Ran ')), '')
    ket_luan = next((d for d in reversed(dong) if d == 'OK' or d.startswith('FAILED')), '')
    return ', '.join(phan for phan in (ran, ket_luan) if phan) or 'không đọc được kết quả'


@dataclass
class KetQuaNhaMay:
    yeu_cau: str
    # dang_chay | ngoai_de | nguoi_tu_choi_dac_ta | vi_pham_rao_chan | chay_thu | nguoi_tu_choi_ap_dung
    # | test_fail | loi_ai | hoan_thanh
    trang_thai: str = 'dang_chay'
    ghi_chu: str = ''
    dac_ta: str = ''
    agent_da_chay: list = field(default_factory=list)
    so_luot_ai: int = 0
    tep_da_doi: list = field(default_factory=list)
    diff: str = ''
    so_vong_sua: int = 0
    test_dat: object = None  # None: chưa chạy test
    dau_ra_test: str = ''
    review: dict = None
    bao_mat: dict = None
    # Chẩn đoán (in khi chay_nha_may --chi-tiet, không ghi vào nhật ký): mỗi lượt gọi AI một dict gồm
    # vai_tro, ky_tu_he_thong, ky_tu_nguoi_dung, thoi_gian_giay; khi dừng vì lỗi AI: agent, loại lỗi, chi tiết an toàn.
    lich_su_goi: list = field(default_factory=list)
    agent_loi: str = ''
    loai_loi: str = ''
    chi_tiet_loi: dict = None


class NhaMayAgent:
    def __init__(self, *, client, goc=None, hoi=input, in_ra=print, chay_test=None, so_luot_toi_da=None, chay_thu=False):
        self.client = client
        self.goc = Path(goc or settings.BASE_DIR)
        self.hoi = hoi
        self.in_ra = in_ra
        self.chay_test = chay_test or (lambda: chay_bo_test(self.goc))
        self.so_luot_toi_da = so_luot_toi_da or settings.NHA_MAY_SO_LUOT_AI_TOI_DA
        self.chay_thu = chay_thu
        self._ban_sao = {}        # đường dẫn tương đối -> bytes trước khi ghi (None nếu tệp mới)
        self._thu_muc_moi = []    # thư mục nhà máy tạo ra, xóa khi hoàn tác nếu rỗng
        self.ket_qua = None

    # ----- gọi AI -----

    def _dung_prompt(self, vai_tro, chuc_nang, **du_lieu):
        return nap_prompt(
            chuc_nang, settings.NHA_MAY_PHIEN_BAN_PROMPT,
            ngu_canh_du_an=(settings.BASE_DIR / 'AGENTS.md').read_text(encoding='utf-8'),
            vai_tro=(settings.BASE_DIR / 'agents' / f'{vai_tro}.md').read_text(encoding='utf-8'),
            **du_lieu,
        )

    def _ngan_sach(self, vai_tro, chuc_nang, **du_lieu_co_dinh):
        """Số ký tự còn dành cho phần dữ liệu dài (nội dung tệp, lỗi test, diff) để prompt người dùng không
        vượt NHA_MAY_GIOI_HAN_KY_TU: dựng prompt với phần dài để trống rồi lấy giới hạn trừ đi."""
        _, khung = self._dung_prompt(vai_tro, chuc_nang, **du_lieu_co_dinh)
        return max(NGAN_SACH_TOI_THIEU, settings.NHA_MAY_GIOI_HAN_KY_TU - len(khung) - KY_TU_CHUA_LAI)

    def _goi_ai(self, vai_tro, chuc_nang, **du_lieu):
        if self.ket_qua.so_luot_ai >= self.so_luot_toi_da:
            raise VuotSoLuotGoiAI(self.so_luot_toi_da)
        he_thong, nguoi_dung = self._dung_prompt(vai_tro, chuc_nang, **du_lieu)
        self.ket_qua.so_luot_ai += 1
        self.ket_qua.agent_da_chay.append(vai_tro)
        lan_goi = {'vai_tro': vai_tro, 'ky_tu_he_thong': len(he_thong), 'ky_tu_nguoi_dung': len(nguoi_dung), 'thoi_gian_giay': None}
        self.ket_qua.lich_su_goi.append(lan_goi)
        bat_dau = time.perf_counter()
        try:
            return goi_ai_co_ghi_log(f'nha_may_{vai_tro}', self.client, he_thong=he_thong, nguoi_dung=nguoi_dung)
        finally:
            lan_goi['thoi_gian_giay'] = round(time.perf_counter() - bat_dau, 1)

    # ----- tệp -----

    def _liet_ke_tep(self):
        ds = []
        for thu_muc in THU_MUC_DUOC_GHI + ('qldt',):
            goc_con = self.goc / thu_muc
            if not goc_con.is_dir():
                continue
            for tep in sorted(goc_con.rglob('*')):
                # Bỏ migration và __init__.py: agent phân tích không cần chọn chúng, danh sách ngắn hơn.
                if (tep.is_file() and tep.suffix in {'.py', '.html', '.txt', '.md'} and '__pycache__' not in tep.parts
                        and 'migrations' not in tep.parts and tep.name != '__init__.py'):
                    ds.append(tep.relative_to(self.goc).as_posix())
        return '\n'.join(ds[:SO_TEP_LIET_KE_TOI_DA])

    def _doc_tep_ngu_canh(self, cac_duong_dan, ngan_sach=None):
        """Nội dung các tệp làm ngữ cảnh, tổng không quá ngan_sach ký tự (tệp sau bị cắt hoặc bỏ khi hết ngân sách)."""
        con_lai = ngan_sach if ngan_sach is not None else SO_TEP_NGU_CANH_TOI_DA * GIOI_HAN_KY_TU_MOI_TEP
        phan = []
        for duong_dan in list(dict.fromkeys(cac_duong_dan))[:SO_TEP_NGU_CANH_TOI_DA]:
            try:
                tep = kiem_tra_doc(self.goc, duong_dan)
            except ViPhamRaoChan as loi:
                phan.append(f'### TỆP: {duong_dan}\n(không đưa vào: {loi})')
                continue
            tieu_de = f'### TỆP: {tep.relative_to(self.goc).as_posix()}\n'
            gioi_han = min(GIOI_HAN_KY_TU_MOI_TEP, con_lai - len(tieu_de) - 40)
            if gioi_han <= 200:
                phan.append(f'### TỆP: {duong_dan}\n(không đưa vào: hết ngân sách ký tự của prompt)')
                continue
            noi_dung = tep.read_text(encoding='utf-8', errors='replace')
            if len(noi_dung) > gioi_han:
                noi_dung = noi_dung[:gioi_han] + '\n…(đã cắt phần còn lại)…'
            phan.append(tieu_de + noi_dung)
            con_lai -= len(phan[-1]) + 2
        return '\n\n'.join(phan) or '(không có tệp nào)'

    def _kiem_tra_thay_doi(self, du_lieu):
        """Kiểm tra TOÀN BỘ thay đổi qua rào chắn trước khi ghi bất kỳ tệp nào."""
        cac_thay_doi = du_lieu.get('thay_doi')
        if not isinstance(cac_thay_doi, list):
            raise PhanHoiSaiDinhDangAI()
        if len(cac_thay_doi) > SO_TEP_MOI_LUOT_TOI_DA:
            raise ViPhamRaoChan(f'Agent đề xuất sửa {len(cac_thay_doi)} tệp, vượt giới hạn {SO_TEP_MOI_LUOT_TOI_DA} tệp mỗi lượt.')
        hop_le = {}
        for muc in cac_thay_doi:
            if not isinstance(muc, dict):
                raise PhanHoiSaiDinhDangAI()
            hop_le[kiem_tra_ghi(self.goc, muc.get('duong_dan'), muc.get('noi_dung'))] = muc['noi_dung']
        return hop_le

    def _noi_dung_hien_tai(self, duong_dan):
        tep = self.goc / duong_dan
        return tep.read_text(encoding='utf-8', errors='replace') if tep.is_file() else ''

    def _tao_diff(self, cu_theo_tep, moi_theo_tep):
        phan = []
        for duong_dan, moi in moi_theo_tep.items():
            cu = cu_theo_tep.get(duong_dan, '')
            phan.extend(difflib.unified_diff(
                cu.splitlines(keepends=True), moi.splitlines(keepends=True),
                fromfile=f'a/{duong_dan}' if cu else '/dev/null', tofile=f'b/{duong_dan}',
            ))
        return ''.join(d if d.endswith('\n') else d + '\n' for d in phan)

    def _ghi(self, thay_doi):
        for duong_dan, noi_dung in thay_doi.items():
            tep = self.goc / duong_dan
            if duong_dan not in self._ban_sao:
                self._ban_sao[duong_dan] = tep.read_bytes() if tep.is_file() else None
            for cha in reversed(tep.parents):
                if cha != self.goc and self.goc in cha.parents and not cha.exists():
                    cha.mkdir()
                    self._thu_muc_moi.append(cha)
            tep.write_bytes(noi_dung.encode('utf-8'))
        self.ket_qua.tep_da_doi = list(self._ban_sao)

    def _hoan_tac(self):
        for duong_dan, cu in self._ban_sao.items():
            tep = self.goc / duong_dan
            if cu is None:
                tep.unlink(missing_ok=True)
            else:
                tep.write_bytes(cu)
        for thu_muc in reversed(self._thu_muc_moi):
            if thu_muc.is_dir() and not any(thu_muc.iterdir()):
                thu_muc.rmdir()
        self._ban_sao, self._thu_muc_moi = {}, []

    def _hoi_co(self, cau_hoi):
        try:
            return self.hoi(cau_hoi).strip().lower() in {'y', 'yes', 'co', 'có'}
        except EOFError:
            return False

    # ----- dây chuyền -----

    def chay(self, yeu_cau):
        self.ket_qua = KetQuaNhaMay(yeu_cau=yeu_cau)
        try:
            self._chay(yeu_cau)
        except (LoiAI, ViPhamRaoChan) as loi:
            self._hoan_tac()
            self.ket_qua.trang_thai = 'vi_pham_rao_chan' if isinstance(loi, ViPhamRaoChan) else 'loi_ai'
            self.ket_qua.ghi_chu = str(loi)
            self.ket_qua.tep_da_doi = []
            if isinstance(loi, LoiAI):
                self.ket_qua.agent_loi = self.ket_qua.agent_da_chay[-1] if self.ket_qua.agent_da_chay else ''
                self.ket_qua.loai_loi = type(loi).__name__
                self.ket_qua.chi_tiet_loi = loi.chi_tiet
            self.in_ra(f'Dừng: {loi}')
        return self.ket_qua

    def _chay(self, yeu_cau):
        kq = self.ket_qua

        # 1. Phân tích yêu cầu
        phan_tich = doc_json(self._goi_ai(
            'phan_tich_yeu_cau', 'nha_may_phan_tich', yeu_cau=yeu_cau,
            de_bai=doc_de_bai_rut_gon(), danh_sach_tep=self._liet_ke_tep(),
        ))
        kq.dac_ta = str(phan_tich.get('dac_ta') or '').strip()
        if not kq.dac_ta:
            raise PhanHoiSaiDinhDangAI()
        self.in_ra(f'===== ĐẶC TẢ =====\n{kq.dac_ta}')
        if phan_tich.get('ngoai_de') is True:
            kq.trang_thai, kq.ghi_chu = 'ngoai_de', 'Agent phân tích kết luận yêu cầu nằm ngoài đề bài.'
            return
        if not self._hoi_co('Duyệt đặc tả và cho agent lập trình làm tiếp? (y/n): '):
            kq.trang_thai = 'nguoi_tu_choi_dac_ta'
            return
        tep_lien_quan = [str(t) for t in phan_tich.get('tep_lien_quan') or [] if isinstance(t, str)]

        # 2. Lập trình, rồi kiểm thử viên viết test cho phần code mới
        ngan_sach = self._ngan_sach('lap_trinh_vien', 'nha_may_lap_trinh', dac_ta=kq.dac_ta, noi_dung_tep='')
        thay_doi = self._kiem_tra_thay_doi(doc_json(self._goi_ai(
            'lap_trinh_vien', 'nha_may_lap_trinh', dac_ta=kq.dac_ta,
            noi_dung_tep=self._doc_tep_ngu_canh(tep_lien_quan, ngan_sach),
        )))
        # Kiểm thử viên: code mới được tối đa 2/3 ngân sách, phần còn lại cho test hiện có (mẫu dựng dữ liệu).
        ngan_sach = self._ngan_sach('kiem_thu_vien', 'nha_may_kiem_thu', dac_ta=kq.dac_ta, code_moi='', test_hien_co='')
        code_moi = _cat_dau('\n\n'.join(f'### TỆP: {d}\n{n}' for d, n in thay_doi.items()) or '(không có)', ngan_sach * 2 // 3)
        mau_test = [f'{d.split("/")[0]}/tests.py' for d in thay_doi if d.split('/')[0] not in {'templates', 'prompts'}]
        thay_doi.update(self._kiem_tra_thay_doi(doc_json(self._goi_ai(
            'kiem_thu_vien', 'nha_may_kiem_thu', dac_ta=kq.dac_ta, code_moi=code_moi,
            test_hien_co=self._doc_tep_ngu_canh(mau_test[:2], ngan_sach - len(code_moi)),
        ))))
        if not thay_doi:
            kq.trang_thai, kq.ghi_chu = 'hoan_thanh', 'Agent không đề xuất thay đổi tệp nào.'
            return
        kq.tep_da_doi = list(thay_doi)
        kq.diff = self._tao_diff({d: self._noi_dung_hien_tai(d) for d in thay_doi}, thay_doi)
        self.in_ra(f'===== DIFF ĐỀ XUẤT =====\n{kq.diff}')
        if self.chay_thu:
            kq.trang_thai, kq.ghi_chu = 'chay_thu', 'Chế độ chạy thử: chỉ in diff, không ghi tệp, không chạy test.'
            return
        if not self._hoi_co('Áp dụng các thay đổi trên và chạy test? (y/n): '):
            kq.trang_thai = 'nguoi_tu_choi_ap_dung'
            kq.tep_da_doi = []
            return
        self._ghi(thay_doi)

        # 3. Chạy test, sửa tối đa SO_VONG_SUA_TOI_DA vòng
        while True:
            dat, dau_ra = self.chay_test()
            kq.test_dat, kq.dau_ra_test = dat, dau_ra
            kq.agent_da_chay.append(f'chay_test ({"đạt" if dat else "lỗi"})')
            if dat:
                break
            if kq.so_vong_sua >= SO_VONG_SUA_TOI_DA:
                self._hoan_tac()
                kq.trang_thai = 'test_fail'
                kq.ghi_chu = f'Test vẫn lỗi sau {SO_VONG_SUA_TOI_DA} vòng sửa; đã hoàn tác mọi thay đổi.'
                kq.tep_da_doi = []
                self.in_ra(f'Dừng: {kq.ghi_chu}')
                return
            kq.so_vong_sua += 1
            du_lieu_sua = dict(dac_ta=kq.dac_ta, vong_sua=str(kq.so_vong_sua), loi_test=_cat_duoi(dau_ra, GIOI_HAN_KY_TU_DAU_RA_TEST))
            ngan_sach = self._ngan_sach('lap_trinh_vien', 'nha_may_sua_loi', noi_dung_tep='', **du_lieu_sua)
            sua = self._kiem_tra_thay_doi(doc_json(self._goi_ai(
                'lap_trinh_vien', 'nha_may_sua_loi', noi_dung_tep=self._doc_tep_ngu_canh(list(self._ban_sao), ngan_sach),
                **du_lieu_sua,
            )))
            self.in_ra(f'===== DIFF VÒNG SỬA {kq.so_vong_sua} =====\n'
                       + self._tao_diff({d: self._noi_dung_hien_tai(d) for d in sua}, sua))
            if not self._hoi_co('Áp dụng bản sửa và chạy lại test? (y/n): '):
                self._hoan_tac()
                kq.trang_thai, kq.ghi_chu, kq.tep_da_doi = 'nguoi_tu_choi_ap_dung', 'Đã hoàn tác mọi thay đổi.', []
                return
            self._ghi(sua)

        # 4. Review và kiểm tra bảo mật trên toàn bộ diff đã áp dụng
        kq.diff = self._tao_diff(
            {d: (b or b'').decode('utf-8', errors='replace') for d, b in self._ban_sao.items()},
            {d: self._noi_dung_hien_tai(d) for d in self._ban_sao},
        )
        for vai_tro, thuoc_tinh in (('review_code', 'review'), ('kiem_tra_bao_mat', 'bao_mat')):
            try:
                ngan_sach = self._ngan_sach(vai_tro, 'nha_may_nhan_xet', dac_ta=kq.dac_ta, diff='')
                nhan_xet = doc_json(self._goi_ai(
                    vai_tro, 'nha_may_nhan_xet', dac_ta=kq.dac_ta,
                    diff=_cat_dau(kq.diff, min(GIOI_HAN_KY_TU_DIFF, ngan_sach)),
                ))
                setattr(kq, thuoc_tinh, {
                    muc: [str(x) for x in nhan_xet.get(muc) or [] if x] for muc in ('nghiem_trong', 'trung_binh', 'nho')
                })
            except LoiAI as loi:
                # Code đã qua test: lỗi AI ở bước nhận xét không hoàn tác, chỉ ghi nhận.
                setattr(kq, thuoc_tinh, {'loi': str(loi)})
        kq.trang_thai = 'hoan_thanh'


# ----- chẩn đoán (chay_nha_may --chi-tiet) -----

def goi_y_khac_phuc(kq):
    """Gợi ý theo loại lỗi AI khi nhà máy dừng; chuỗi rỗng nếu không có gợi ý."""
    chi_tiet = kq.chi_tiet_loi or {}
    ma_http = chi_tiet.get('ma_http')
    thong_diep = str(chi_tiet.get('thong_diep') or '').upper()
    if kq.loai_loi == 'DauVaoQuaDai':
        return 'Prompt vượt NHA_MAY_GIOI_HAN_KY_TU: tăng biến này trong .env hoặc yêu cầu hẹp hơn (ít tệp liên quan hơn).'
    if kq.loai_loi == 'HetThoiGianChoAI' or ma_http == 504 or 'DEADLINE' in thong_diep:
        return ('Model trả lời không kịp thời gian chờ (prompt dài, đầu ra dài): tăng NHA_MAY_TIMEOUT_GIAY trong .env '
                f'(đang {settings.NHA_MAY_TIMEOUT_GIAY:g} giây) hoặc chia yêu cầu nhỏ hơn.')
    if kq.loai_loi == 'QuaGioiHanTanSuatAI' or ma_http == 429:
        return 'Hết hạn mức/tần suất của khóa API: chờ hạn mức đặt lại hoặc dùng khóa khác.'
    if ma_http == 400:
        return 'Yêu cầu bị từ chối (400): kiểm tra GEMINI_MODEL có đúng tên model không và thông điệp từ API ở trên.'
    if ma_http in (401, 403):
        return 'Khóa API không hợp lệ hoặc không có quyền dùng model này: kiểm tra GEMINI_API_KEY, GEMINI_MODEL.'
    if isinstance(ma_http, int) and ma_http >= 500:
        return 'Máy chủ AI đang lỗi/quá tải: thử lại sau ít phút.'
    if kq.loai_loi == 'PhanHoiSaiDinhDangAI':
        return 'Model không trả về JSON đúng lược đồ (có thể bị cắt vì đầu ra quá dài): thử lại, hoặc yêu cầu hẹp hơn.'
    return ''


def mo_ta_chi_tiet(kq, client=None):
    """Các dòng chẩn đoán cho --chi-tiet: cấu hình, từng lượt gọi AI (độ dài prompt, thời gian), lỗi gốc.
    Không bao giờ có khóa API hay nội dung prompt."""
    dong = ['===== CHI TIẾT CHẨN ĐOÁN =====',
            f'Cấu hình nhà máy: model={getattr(client, "model", "-")}, giới hạn ký tự={settings.NHA_MAY_GIOI_HAN_KY_TU}, '
            f'thời gian chờ={settings.NHA_MAY_TIMEOUT_GIAY:g} giây, số lần thử lại={settings.NHA_MAY_SO_LAN_THU_LAI}, '
            f'số lượt gọi tối đa={settings.NHA_MAY_SO_LUOT_AI_TOI_DA}']
    dong.append('Các lượt gọi AI:' if kq.lich_su_goi else 'Các lượt gọi AI: không có')
    for i, lan in enumerate(kq.lich_su_goi, 1):
        dong.append(f'  {i}. {lan["vai_tro"]}: system {lan["ky_tu_he_thong"]} ký tự, user {lan["ky_tu_nguoi_dung"]} ký tự, '
                    f'{lan["thoi_gian_giay"]} giây')
    if kq.trang_thai == 'loi_ai':
        chi_tiet = kq.chi_tiet_loi or {}
        dong += [f'Agent lỗi: {kq.agent_loi or "-"}', f'Loại lỗi: {kq.loai_loi}']
        if chi_tiet:
            dong += [f'  Loại lỗi gốc: {chi_tiet.get("loai")}', f'  Mã HTTP: {chi_tiet.get("ma_http")}',
                     f'  Thông điệp từ API: {chi_tiet.get("thong_diep")}']
        else:
            dong.append('  (Không có thêm chi tiết cho loại lỗi này.)')
        goi_y = goi_y_khac_phuc(kq)
        if goi_y:
            dong.append(f'Gợi ý: {goi_y}')
    return dong


# ----- nhật ký -----

TIEU_DE_NHAT_KY = '## Nhật ký nhà máy agent'
_MO_TA_TRANG_THAI = {
    'ngoai_de': 'Dừng – yêu cầu ngoài đề',
    'nguoi_tu_choi_dac_ta': 'Dừng – người không duyệt đặc tả',
    'vi_pham_rao_chan': 'Dừng – rào chắn chặn thay đổi',
    'chay_thu': 'Chạy thử (không ghi tệp)',
    'nguoi_tu_choi_ap_dung': 'Dừng – người không áp dụng thay đổi',
    'test_fail': 'Dừng – test vẫn lỗi sau 2 vòng sửa, đã hoàn tác',
    'loi_ai': 'Dừng – lỗi gọi AI',
    'hoan_thanh': 'Hoàn thành – chờ người kiểm tra và tự commit',
}


def _tom_tat_nhan_xet(nhan_xet):
    if not nhan_xet:
        return 'không chạy'
    if 'loi' in nhan_xet:
        return f'lỗi AI: {nhan_xet["loi"]}'
    dem = ', '.join(f'{ten} {len(nhan_xet.get(khoa, []))}' for khoa, ten in (
        ('nghiem_trong', 'Nghiêm trọng'), ('trung_binh', 'Trung bình'), ('nho', 'Nhỏ')))
    chi_tiet = [f'  - [{ten}] {muc}' for khoa, ten in (('nghiem_trong', 'Nghiêm trọng'), ('trung_binh', 'Trung bình'))
                for muc in nhan_xet.get(khoa, [])]
    return '\n'.join([dem] + chi_tiet)


def mo_ta_ket_qua(kq):
    """Các dòng báo cáo (Markdown) của một lần chạy, dùng cho cả màn hình và docs/ai-log.md."""
    if kq.test_dat is None:
        test = 'không chạy'
    else:
        test = f'{"đạt" if kq.test_dat else "lỗi"} – {tom_tat_dau_ra_test(kq.dau_ra_test)}; {kq.so_vong_sua} vòng sửa'
    trang_thai = _MO_TA_TRANG_THAI.get(kq.trang_thai, kq.trang_thai)
    return [
        f'- Yêu cầu: {" ".join(kq.yeu_cau.split())}',
        f'- Trạng thái: {trang_thai}' + (f' ({kq.ghi_chu})' if kq.ghi_chu else ''),
        f'- Agent đã chạy: {" → ".join(kq.agent_da_chay) or "không"} ({kq.so_luot_ai} lượt gọi AI)',
        f'- Tệp đã đổi: {", ".join(kq.tep_da_doi) or "không"}',
        f'- Kết quả test: {test}',
        f'- Review code: {_tom_tat_nhan_xet(kq.review)}',
        f'- Kiểm tra bảo mật: {_tom_tat_nhan_xet(kq.bao_mat)}',
        '- Phần người cần kiểm tra: [ ] đọc `git diff` [ ] xác minh từng nhận xét review/bảo mật '
        '[ ] thử tay trên trình duyệt [ ] tự commit (nhà máy không commit, không push)',
    ]


def ghi_nhat_ky(duong_dan, kq, thoi_diem=None):
    """Thêm một mục vào cuối tệp nhật ký, dưới mục "Nhật ký nhà máy agent" (tạo mục nếu chưa có).
    Chỉ ghi thêm vào cuối tệp, không sửa nội dung cũ."""
    tep = Path(duong_dan)
    cu = tep.read_text(encoding='utf-8') if tep.is_file() else ''
    xuong_dong = '\r\n' if '\r\n' in cu else '\n'
    thoi_diem = timezone.localtime(thoi_diem or timezone.now())
    dong = [] if (not cu or cu.endswith('\n')) else ['']
    if TIEU_DE_NHAT_KY not in cu:
        dong += ['', '---', '', TIEU_DE_NHAT_KY, '',
                 'Mỗi lần chạy `python manage.py chay_nha_may` (trừ chế độ `--chay-thu`) thêm một mục dưới đây. '
                 'Không ghi dữ liệu cá nhân, điểm thật hay khóa API.']
    yeu_cau_ngan = ' '.join(kq.yeu_cau.split())
    if len(yeu_cau_ngan) > 80:
        yeu_cau_ngan = yeu_cau_ngan[:77] + '...'
    dong += ['', f'### {thoi_diem:%Y-%m-%d %H:%M} – {yeu_cau_ngan}'] + mo_ta_ket_qua(kq)
    with tep.open('a', encoding='utf-8', newline='') as f:
        f.write(xuong_dong.join(dong) + xuong_dong)
