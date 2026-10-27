import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings, tag

from ai_core.clients import ClientAI, lay_client_ai
from ai_core.exceptions import DauVaoQuaDai, HetThoiGianChoAI, LoiMoHinhAI, PhanHoiSaiDinhDangAI

from . import quet_khoa
from .dieu_phoi import (
    KetQuaNhaMay,
    NhaMayAgent,
    VuotSoLuotGoiAI,
    doc_json,
    ghi_nhat_ky,
    goi_y_khac_phuc,
    mo_ta_chi_tiet,
    mo_ta_ket_qua,
    tao_client,
)
from .rao_chan import ViPhamRaoChan, kiem_tra_doc, kiem_tra_ghi

# Chuỗi giống khóa API được ghép lúc chạy để mã nguồn test không chứa khóa (dù là khóa giả).
KHOA_GOOGLE_GIA = 'AI' + 'za' + 'B' * 35
KHOA_OPENAI_GIA = 's' + 'k-' + 'x' * 30
GAN_KHOA_GEMINI_GIA = 'GEMINI_API_KEY' + '=' + 'y' * 25
KHOA_CAU_HINH_GIA = 'khoa-cau-hinh-' + 'gia-de-test'      # giá trị đặt vào settings.GEMINI_API_KEY trong test
KHOA_KHONG_DUOC_IN = 'khoa-bi-mat-' + 'khong-duoc-in-ra'


class ClientKichBan(ClientAI):
    """Client AI giả trả lần lượt các phản hồi soạn sẵn (chuỗi hoặc ngoại lệ), ghi lại mọi lần gọi."""

    def __init__(self, *phan_hoi):
        self.phan_hoi = list(phan_hoi)
        self.cac_lan_goi = []

    def sinh_noi_dung(self, *, he_thong, nguoi_dung):
        self.cac_lan_goi.append({'he_thong': he_thong, 'nguoi_dung': nguoi_dung})
        if not self.phan_hoi:
            raise AssertionError('Nhà máy gọi AI nhiều hơn kịch bản.')
        tiep = self.phan_hoi.pop(0)
        if isinstance(tiep, Exception):
            raise tiep
        return tiep


def phan_tich(ngoai_de=False, tep_lien_quan=('grades/dich_vu.py',)):
    return json.dumps({'ngoai_de': ngoai_de, 'dac_ta': '## Đặc tả: thêm hàm chào', 'tep_lien_quan': list(tep_lien_quan)})


def thay_doi(*cap):
    return json.dumps({'thay_doi': [{'duong_dan': d, 'noi_dung': n} for d, n in cap], 'giai_thich': 'x'})


NHAN_XET = json.dumps({'nghiem_trong': [], 'trung_binh': ['[grades/dich_vu.py:1] thiếu chú thích'], 'nho': []})
CODE_MOI = ('grades/dich_vu.py', 'def chao():\n    return "xin chao"\n')
TEST_MOI = ('grades/tests_chao.py', 'from django.test import SimpleTestCase, tag\n\n\n@tag("don_vi")\nclass T(SimpleTestCase):\n    def test_chao(self):\n        pass\n')


class ThuMucTamMixin:
    def setUp(self):
        super().setUp()
        self.goc = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.goc, ignore_errors=True)
        (self.goc / 'grades').mkdir()
        (self.goc / 'grades' / 'dich_vu.py').write_bytes(b'# ban cu\r\n')

    def tao(self, duong_dan, noi_dung='x'):
        tep = self.goc / duong_dan
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text(noi_dung, encoding='utf-8')
        return tep


@tag('don_vi')
class RaoChanGhiTest(ThuMucTamMixin, SimpleTestCase):
    def test_cho_phep_ghi_trong_app_templates_prompts(self):
        for duong_dan in ('grades/dich_vu_moi.py', 'templates/grades/trang.html', 'prompts/abc/v1/system.txt',
                          'grades\\khac.py', 'grades/migrations/0099_moi.py'):
            self.assertTrue(kiem_tra_ghi(self.goc, duong_dan, 'x = 1\n'))
        self.assertEqual(kiem_tra_ghi(self.goc, 'grades\\khac.py', ''), 'grades/khac.py')

    def test_chan_tep_bi_mat_env(self):
        for duong_dan in ('.env', 'grades/.env', '.env.local', 'grades/.ENV.production'):
            with self.assertRaisesMessage(ViPhamRaoChan, 'bí mật'):
                kiem_tra_ghi(self.goc, duong_dan, 'A=1')

    def test_chan_settings_va_chinh_nha_may(self):
        with self.assertRaisesMessage(ViPhamRaoChan, 'cấu hình'):
            kiem_tra_ghi(self.goc, 'grades/settings.py', 'x')
        with self.assertRaisesMessage(ViPhamRaoChan, 'cấu hình'):
            kiem_tra_ghi(self.goc, 'qldt/settings.py', 'x')
        with self.assertRaisesMessage(ViPhamRaoChan, 'nhà máy agent'):
            kiem_tra_ghi(self.goc, 'nha_may_agent/rao_chan.py', 'x')

    def test_chan_migration_da_co(self):
        self.tao('grades/migrations/0001_initial.py')
        with self.assertRaisesMessage(ViPhamRaoChan, 'migration đã có'):
            kiem_tra_ghi(self.goc, 'grades/migrations/0001_initial.py', 'x')

    def test_chan_ngoai_thu_muc_duoc_ghi(self):
        for duong_dan in ('manage.py', 'docs/ai-log.md', 'agents/review_code.md', 'AGENTS.md',
                          '.github/workflows/ci.yml', 'qldt/urls.py', 'requirements.txt'):
            with self.assertRaisesMessage(ViPhamRaoChan, 'ngoài các thư mục được ghi'):
                kiem_tra_ghi(self.goc, duong_dan, 'x')

    def test_chan_duong_dan_tuyet_doi_va_vuot_ra_ngoai(self):
        for duong_dan in ('/etc/passwd', 'C:/Windows/x.py', '~/x.py', 'grades/../../x.py', '../x.py', '', None):
            with self.assertRaises(ViPhamRaoChan):
                kiem_tra_ghi(self.goc, duong_dan, 'x')

    def test_chan_duoi_tep_khong_cho_phep(self):
        for duong_dan in ('grades/chay.sh', 'grades/x.exe', 'grades/du_lieu.sql'):
            with self.assertRaisesMessage(ViPhamRaoChan, 'đuôi'):
                kiem_tra_ghi(self.goc, duong_dan, 'x')

    def test_chan_noi_dung_giong_khoa_api(self):
        for noi_dung in (f'KEY = "{KHOA_GOOGLE_GIA}"', f'k = "{KHOA_OPENAI_GIA}"', GAN_KHOA_GEMINI_GIA):
            with self.assertRaisesMessage(ViPhamRaoChan, 'giống'):
                kiem_tra_ghi(self.goc, 'grades/x.py', noi_dung)
        # Nhắc tên biến hay tiền tố ngắn trong chú thích thì không bị chặn.
        kiem_tra_ghi(self.goc, 'grades/x.py', '# đọc GEMINI_API_KEY từ settings, khóa dạng AIza...\n')

    def test_chan_ghi_de_lam_giam_so_test(self):
        self.tao('grades/tests.py', 'def test_a(self): pass\ndef test_b(self): pass\n')
        with self.assertRaisesMessage(ViPhamRaoChan, 'giảm số test'):
            kiem_tra_ghi(self.goc, 'grades/tests.py', 'def test_a(self): pass\n')
        kiem_tra_ghi(self.goc, 'grades/tests.py', 'def test_a(self): pass\ndef test_b(self): pass\ndef test_c(self): pass\n')


@tag('don_vi')
class RaoChanDocVaQuetKhoaTest(ThuMucTamMixin, SimpleTestCase):
    def test_khong_doc_tep_bi_mat_va_thu_muc_loai_tru(self):
        self.tao('.env', 'DB_PASSWORD=bi_mat')
        self.tao('venv/Lib/x.py')
        self.tao('.git/config')
        for duong_dan in ('.env', 'venv/Lib/x.py', '.git/config', 'grades/khong_co.py'):
            with self.assertRaises(ViPhamRaoChan):
                kiem_tra_doc(self.goc, duong_dan)
        self.assertEqual(kiem_tra_doc(self.goc, 'grades/dich_vu.py'), self.goc / 'grades' / 'dich_vu.py')

    def test_quet_khoa_bao_loi_khi_co_khoa_va_bo_qua_tep_nhi_phan(self):
        sach = self.tao('grades/sach.py', 'x = 1\n')
        ban = self.tao('grades/ban.py', f'a = 1\nKEY = "{KHOA_GOOGLE_GIA}"\n')
        nhi_phan = self.goc / 'anh.png'
        nhi_phan.write_bytes(b'\x89PNG\xff\xfe\x00')
        with patch('sys.stderr', new_callable=StringIO) as loi:
            self.assertEqual(quet_khoa.main([str(sach), str(nhi_phan)]), 0)
            self.assertEqual(quet_khoa.main([str(sach), str(ban)]), 1)
        self.assertIn('ban.py:2', loi.getvalue())
        self.assertNotIn(KHOA_GOOGLE_GIA, loi.getvalue())


@tag('don_vi')
class DocJsonTest(SimpleTestCase):
    def test_doc_json_trong_khoi_markdown_va_co_chu_thua(self):
        self.assertEqual(doc_json('```json\n{"a": 1}\n```'), {'a': 1})
        self.assertEqual(doc_json('Đây là kết quả: {"a": [1, 2]} hết.'), {'a': [1, 2]})

    def test_json_sai_nem_loi_ai_co_san(self):
        for van_ban in ('khong co json', '{"a": ', '[1, 2]', ''):
            with self.assertRaises(PhanHoiSaiDinhDangAI):
                doc_json(van_ban)


@tag('don_vi')
class NhaMayAgentTest(ThuMucTamMixin, SimpleTestCase):
    def _nha_may(self, client, tra_loi='y', ket_qua_test=None, **kw):
        self.cac_cau_hoi, self.so_lan_chay_test, self.dau_ra = [], 0, []
        tra_loi_lan_luot = list(tra_loi) if isinstance(tra_loi, (list, tuple)) else None
        ket_qua_test = list(ket_qua_test or [(True, 'Ran 3 tests in 0.1s\n\nOK')])

        def hoi(cau_hoi):
            self.cac_cau_hoi.append(cau_hoi)
            return tra_loi_lan_luot.pop(0) if tra_loi_lan_luot is not None else tra_loi

        def chay_test():
            self.so_lan_chay_test += 1
            return ket_qua_test.pop(0) if len(ket_qua_test) > 1 else ket_qua_test[0]

        return NhaMayAgent(client=client, goc=self.goc, hoi=hoi, in_ra=self.dau_ra.append, chay_test=chay_test, **kw)

    def test_luong_day_du_thanh_cong(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI), NHAN_XET, NHAN_XET)
        kq = self._nha_may(client).chay('Thêm hàm chào trong grades')
        self.assertEqual(kq.trang_thai, 'hoan_thanh')
        self.assertEqual(kq.agent_da_chay, ['phan_tich_yeu_cau', 'lap_trinh_vien', 'kiem_thu_vien',
                                            'chay_test (đạt)', 'review_code', 'kiem_tra_bao_mat'])
        self.assertEqual(kq.so_luot_ai, 5)
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_text(encoding='utf-8'), CODE_MOI[1])
        self.assertTrue((self.goc / 'grades' / 'tests_chao.py').is_file())
        self.assertEqual(sorted(kq.tep_da_doi), ['grades/dich_vu.py', 'grades/tests_chao.py'])
        self.assertEqual(kq.review['trung_binh'], ['[grades/dich_vu.py:1] thiếu chú thích'])
        self.assertIn('+    return "xin chao"', kq.diff)
        # Hai cổng người: duyệt đặc tả và duyệt diff.
        self.assertEqual(len(self.cac_cau_hoi), 2)
        # Prompt: vai trò từ agents/*.md, ngữ cảnh AGENTS.md, yêu cầu nằm trong khối dữ liệu.
        dau = client.cac_lan_goi[0]
        self.assertIn('Agent: Phân tích yêu cầu', dau['he_thong'])
        self.assertIn('# AGENTS.md', dau['he_thong'])
        khoi = dau['nguoi_dung']
        self.assertTrue(khoi.index('<<<DU_LIEU>>>') < khoi.index('Thêm hàm chào trong grades') < khoi.index('<<<HET_DU_LIEU>>>'))
        self.assertIn('Agent: Review code', client.cac_lan_goi[3]['he_thong'])
        self.assertIn('Agent: Kiểm tra bảo mật', client.cac_lan_goi[4]['he_thong'])

    def test_dung_khi_nguoi_khong_duyet_dac_ta(self):
        client = ClientKichBan(phan_tich())
        kq = self._nha_may(client, tra_loi='n').chay('Yêu cầu bất kỳ')
        self.assertEqual(kq.trang_thai, 'nguoi_tu_choi_dac_ta')
        self.assertEqual(len(client.cac_lan_goi), 1)
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')

    def test_ngoai_de_dung_ngay_khong_hoi(self):
        kq = self._nha_may(ClientKichBan(phan_tich(ngoai_de=True))).chay('Thêm chức năng thanh toán học phí online')
        self.assertEqual(kq.trang_thai, 'ngoai_de')
        self.assertEqual(self.cac_cau_hoi, [])

    def test_chay_thu_chi_in_diff_khong_ghi_tep_khong_chay_test(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI))
        kq = self._nha_may(client, chay_thu=True).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'chay_thu')
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')
        self.assertFalse((self.goc / 'grades' / 'tests_chao.py').exists())
        self.assertEqual(self.so_lan_chay_test, 0)
        self.assertEqual(len(self.cac_cau_hoi), 1)  # chỉ hỏi duyệt đặc tả
        self.assertIn('+def chao():', kq.diff)
        self.assertTrue(any('DIFF ĐỀ XUẤT' in d for d in self.dau_ra))

    def test_vong_sua_dung_sau_2_lan_va_hoan_tac(self):
        sua = thay_doi(('grades/dich_vu.py', 'def chao():\n    return 1\n'))
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI), sua, sua)
        kq = self._nha_may(client, ket_qua_test=[(False, 'FAILED (failures=1)')]).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'test_fail')
        self.assertEqual(kq.so_vong_sua, 2)
        self.assertEqual(self.so_lan_chay_test, 3)  # lần đầu + sau mỗi vòng sửa
        self.assertEqual(kq.agent_da_chay.count('lap_trinh_vien'), 3)
        self.assertNotIn('review_code', kq.agent_da_chay)
        self.assertEqual(client.phan_hoi, [])
        # Hoàn tác: tệp cũ trở lại đúng từng byte (giữ CRLF), tệp mới bị xóa.
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')
        self.assertFalse((self.goc / 'grades' / 'tests_chao.py').exists())
        self.assertIn('FAILED (failures=1)', client.cac_lan_goi[3]['nguoi_dung'])

    def test_sua_thanh_cong_o_vong_1(self):
        sua = thay_doi(('grades/dich_vu.py', 'def chao():\n    return "da sua"\n'))
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI), sua, NHAN_XET, NHAN_XET)
        kq = self._nha_may(client, ket_qua_test=[(False, 'FAILED'), (True, 'Ran 1 test\n\nOK')]).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'hoan_thanh')
        self.assertEqual(kq.so_vong_sua, 1)
        self.assertIn('da sua', (self.goc / 'grades' / 'dich_vu.py').read_text(encoding='utf-8'))
        self.assertIn('-# ban cu', kq.diff)

    def test_vi_pham_rao_chan_khong_ghi_tep_nao(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI, ('.env', 'GEMINI_API_KEY=x')))
        kq = self._nha_may(client).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'vi_pham_rao_chan')
        self.assertIn('.env', kq.ghi_chu)
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')
        self.assertFalse((self.goc / '.env').exists())

    def test_vi_pham_trong_vong_sua_thi_hoan_tac(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI),
                               thay_doi(('qldt/settings.py', 'DEBUG = True')))
        kq = self._nha_may(client, ket_qua_test=[(False, 'FAILED')]).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'vi_pham_rao_chan')
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')
        self.assertFalse((self.goc / 'grades' / 'tests_chao.py').exists())

    def test_gioi_han_so_luot_goi_ai(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI))
        kq = self._nha_may(client, so_luot_toi_da=2).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'loi_ai')
        self.assertEqual(kq.ghi_chu, str(VuotSoLuotGoiAI(2)))
        self.assertEqual(len(client.cac_lan_goi), 2)
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_bytes(), b'# ban cu\r\n')

    def test_loi_ai_va_json_sai_xu_ly_bang_exception_co_san(self):
        kq = self._nha_may(ClientKichBan(HetThoiGianChoAI())).chay('x')
        self.assertEqual((kq.trang_thai, kq.ghi_chu), ('loi_ai', str(HetThoiGianChoAI())))
        kq = self._nha_may(ClientKichBan('khong phai json')).chay('x')
        self.assertEqual((kq.trang_thai, kq.ghi_chu), ('loi_ai', str(PhanHoiSaiDinhDangAI())))

    def test_loi_ai_o_buoc_review_khong_hoan_tac_code_da_qua_test(self):
        client = ClientKichBan(phan_tich(), thay_doi(CODE_MOI), thay_doi(TEST_MOI), HetThoiGianChoAI(), NHAN_XET)
        kq = self._nha_may(client).chay('Thêm hàm chào')
        self.assertEqual(kq.trang_thai, 'hoan_thanh')
        self.assertIn('loi', kq.review)
        self.assertEqual((self.goc / 'grades' / 'dich_vu.py').read_text(encoding='utf-8'), CODE_MOI[1])

    def test_khong_dua_env_vao_prompt(self):
        self.tao('.env', 'DB_PASSWORD=MAT_KHAU_BI_MAT_123')
        client = ClientKichBan(phan_tich(tep_lien_quan=('.env', 'grades/dich_vu.py')), thay_doi(CODE_MOI), thay_doi(TEST_MOI))
        self._nha_may(client, chay_thu=True).chay('x')
        prompt_lap_trinh = client.cac_lan_goi[1]['nguoi_dung']
        self.assertNotIn('MAT_KHAU_BI_MAT_123', prompt_lap_trinh)
        self.assertIn('# ban cu', prompt_lap_trinh)
        self.assertIn('không đưa vào', prompt_lap_trinh)


@tag('don_vi')
class GhiNhatKyTest(ThuMucTamMixin, SimpleTestCase):
    def test_them_muc_vao_cuoi_khong_sua_noi_dung_cu(self):
        tep = self.tao('ai-log.md', '# Nhật ký\r\n\r\n## Mục cũ\r\nnội dung cũ\r\n')
        cu = tep.read_bytes()
        kq = KetQuaNhaMay(yeu_cau='Thêm hàm chào', trang_thai='hoan_thanh', agent_da_chay=['phan_tich_yeu_cau'], so_luot_ai=1)
        ghi_nhat_ky(tep, kq)
        ghi_nhat_ky(tep, kq)
        moi = tep.read_bytes()
        self.assertTrue(moi.startswith(cu))
        van_ban = moi.decode('utf-8')
        self.assertEqual(van_ban.count('## Nhật ký nhà máy agent'), 1)
        self.assertEqual(van_ban.count('Thêm hàm chào'), 4)  # tiêu đề + dòng Yêu cầu, hai lần chạy
        self.assertNotIn('\n\n\n', van_ban.replace('\r\n', '\n'))
        self.assertIn('- Trạng thái: Hoàn thành', van_ban)
        self.assertTrue(any(d.startswith('- Phần người cần kiểm tra') for d in mo_ta_ket_qua(kq)))


@tag('don_vi')
class LenhChayNhaMayTest(SimpleTestCase):
    def test_chay_thu_qua_lenh_khong_ghi_tep_va_khong_ghi_nhat_ky(self):
        tep_moi = settings.BASE_DIR / 'grades' / 'nha_may_thu_khong_duoc_ghi.py'
        nhat_ky = settings.BASE_DIR / 'docs' / 'ai-log.md'
        # Bản mã nguồn có thể không kèm docs/ai-log.md: khi đó chạy thử cũng không được tạo tệp này.
        nhat_ky_truoc = nhat_ky.read_bytes() if nhat_ky.exists() else None
        client = ClientKichBan(phan_tich(), thay_doi(('grades/nha_may_thu_khong_duoc_ghi.py', 'x = 1\n')), thay_doi())
        ra = StringIO()
        with patch('nha_may_agent.management.commands.chay_nha_may.tao_client', return_value=client), \
                patch('builtins.input', return_value='y'):
            call_command('chay_nha_may', 'Thêm hàm chào', '--chay-thu', stdout=ra)
        self.assertFalse(tep_moi.exists())
        self.assertEqual(nhat_ky.read_bytes() if nhat_ky.exists() else None, nhat_ky_truoc)
        self.assertIn('+x = 1', ra.getvalue())
        self.assertIn('Chạy thử', ra.getvalue())


LOI_HET_HAN_MAY_CHU = {'loai': 'ServerError', 'ma_http': 504, 'thong_diep': '504 DEADLINE_EXCEEDED. Deadline expired before operation could complete.'}


class ClientKiemTraDoDai(ClientKichBan):
    """Như GeminiClient: từ chối prompt người dùng dài hơn gioi_han (DauVaoQuaDai) trước khi 'gọi'."""

    def __init__(self, gioi_han, *phan_hoi):
        super().__init__(*phan_hoi)
        self.gioi_han = gioi_han

    def sinh_noi_dung(self, *, he_thong, nguoi_dung):
        if len(nguoi_dung) > self.gioi_han:
            raise DauVaoQuaDai(len(nguoi_dung), self.gioi_han)
        return super().sinh_noi_dung(he_thong=he_thong, nguoi_dung=nguoi_dung)


@tag('don_vi')
class CauHinhClientNhaMayTest(SimpleTestCase):
    @override_settings(
        AI_BACKEND='gemini', GEMINI_API_KEY=KHOA_CAU_HINH_GIA, GEMINI_MODEL='model-thu',
        NHA_MAY_GIOI_HAN_KY_TU=50000, NHA_MAY_TIMEOUT_GIAY=150, NHA_MAY_SO_LAN_THU_LAI=1,
        AI_GIOI_HAN_KY_TU=8000, AI_TIMEOUT_GIAY=20, AI_SO_LAN_THU_LAI=2,
    )
    def test_nha_may_dung_gioi_han_va_thoi_gian_cho_rieng_khong_doi_cau_hinh_san_pham(self):
        client = tao_client()
        self.assertEqual((client.gioi_han_ky_tu, client.timeout_giay, client.so_lan_thu_lai), (50000, 150, 1))
        san_pham = lay_client_ai()
        self.assertEqual((san_pham.gioi_han_ky_tu, san_pham.timeout_giay, san_pham.so_lan_thu_lai), (8000, 20, 2))


@tag('don_vi')
class ChanDoanLoiNhaMayTest(ThuMucTamMixin, SimpleTestCase):
    def test_loi_ai_ghi_nhan_agent_loi_chi_tiet_va_do_dai_prompt(self):
        client = ClientKichBan(LoiMoHinhAI(LOI_HET_HAN_MAY_CHU))
        kq = NhaMayAgent(client=client, goc=self.goc, hoi=lambda c: 'y', in_ra=lambda s: None).chay('Yêu cầu thử')
        self.assertEqual((kq.trang_thai, kq.agent_loi, kq.loai_loi), ('loi_ai', 'phan_tich_yeu_cau', 'LoiMoHinhAI'))
        self.assertEqual(kq.chi_tiet_loi, LOI_HET_HAN_MAY_CHU)
        lan = kq.lich_su_goi[0]
        self.assertEqual(lan['ky_tu_nguoi_dung'], len(client.cac_lan_goi[0]['nguoi_dung']))
        self.assertIsNotNone(lan['thoi_gian_giay'])
        self.assertIn('NHA_MAY_TIMEOUT_GIAY', goi_y_khac_phuc(kq))
        dong = '\n'.join(mo_ta_chi_tiet(kq))
        self.assertIn('Mã HTTP: 504', dong)
        self.assertIn('Agent lỗi: phan_tich_yeu_cau', dong)

    def test_goi_y_theo_loai_loi(self):
        def goi_y(loai, ma_http=None):
            return goi_y_khac_phuc(KetQuaNhaMay(yeu_cau='x', loai_loi=loai, chi_tiet_loi={'ma_http': ma_http}))
        self.assertIn('NHA_MAY_GIOI_HAN_KY_TU', goi_y('DauVaoQuaDai'))
        self.assertIn('NHA_MAY_TIMEOUT_GIAY', goi_y('HetThoiGianChoAI'))
        self.assertIn('hạn mức', goi_y('QuaGioiHanTanSuatAI', 429))
        self.assertIn('GEMINI_MODEL', goi_y('LoiMoHinhAI', 400))
        self.assertIn('GEMINI_API_KEY', goi_y('LoiMoHinhAI', 403))
        self.assertIn('JSON', goi_y('PhanHoiSaiDinhDangAI'))

    def test_phan_tich_chi_gui_de_bai_muc_1_den_5_va_bo_migration_init(self):
        self.tao('grades/__init__.py')
        self.tao('grades/migrations/0001_initial.py')
        client = ClientKichBan(phan_tich())
        NhaMayAgent(client=client, goc=self.goc, hoi=lambda c: 'n', in_ra=lambda s: None).chay('Yêu cầu thử')
        prompt = client.cac_lan_goi[0]['nguoi_dung']
        self.assertIn('grades/dich_vu.py', prompt)
        self.assertNotIn('migrations', prompt)
        self.assertNotIn('__init__.py', prompt)
        self.assertIn('## 5.', prompt)
        self.assertNotIn('## 6.', prompt)

    @override_settings(NHA_MAY_GIOI_HAN_KY_TU=40000)
    def test_prompt_moi_agent_khong_vuot_gioi_han_ky_tu_cua_nha_may(self):
        cac_tep = [f'grades/lon_{i}.py' for i in range(8)]
        for duong_dan in cac_tep:
            self.tao(duong_dan, '# dong code\n' * 3000)  # ~36.000 ký tự mỗi tệp, 8 tệp vượt xa giới hạn
        code_lon = ('grades/dich_vu.py', 'x = 1\n' * 6000)
        client = ClientKiemTraDoDai(40000, phan_tich(tep_lien_quan=cac_tep), thay_doi(code_lon), thay_doi(TEST_MOI))
        kq = NhaMayAgent(client=client, goc=self.goc, hoi=lambda c: 'y', in_ra=lambda s: None, chay_thu=True).chay('x')
        self.assertEqual(kq.trang_thai, 'chay_thu', kq.ghi_chu)
        self.assertTrue(all(lan['ky_tu_nguoi_dung'] <= 40000 for lan in kq.lich_su_goi), kq.lich_su_goi)
        prompt_lap_trinh = client.cac_lan_goi[1]['nguoi_dung']
        self.assertIn('đã cắt phần còn lại', prompt_lap_trinh)
        self.assertIn('### TỆP: grades/lon_0.py', prompt_lap_trinh)


@tag('don_vi')
class LenhChiTietTest(SimpleTestCase):
    def _chay_lenh(self, *tham_so):
        ra = StringIO()
        client = ClientKichBan(LoiMoHinhAI(LOI_HET_HAN_MAY_CHU))
        with patch('nha_may_agent.management.commands.chay_nha_may.tao_client', return_value=client), \
                patch('nha_may_agent.management.commands.chay_nha_may.ghi_nhat_ky') as ghi, \
                patch('builtins.input', return_value='y'):
            call_command('chay_nha_may', 'Yêu cầu thử', *tham_so, stdout=ra)
        return ra.getvalue(), ghi

    @override_settings(GEMINI_API_KEY=KHOA_KHONG_DUOC_IN)
    def test_chi_tiet_in_loai_loi_goc_ma_http_thong_diep_khong_in_khoa(self):
        dau_ra, ghi = self._chay_lenh('--chi-tiet')
        for chuoi in ('Agent lỗi: phan_tich_yeu_cau', 'Loại lỗi gốc: ServerError', 'Mã HTTP: 504',
                      'DEADLINE_EXCEEDED', 'NHA_MAY_TIMEOUT_GIAY', '1. phan_tich_yeu_cau: system '):
            self.assertIn(chuoi, dau_ra)
        self.assertNotIn(KHOA_KHONG_DUOC_IN, dau_ra)
        ghi.assert_called_once()
        # Nhật ký chỉ có thông điệp an toàn, không có thông điệp thô từ API.
        self.assertNotIn('DEADLINE_EXCEEDED', '\n'.join(mo_ta_ket_qua(ghi.call_args.args[1])))

    def test_khong_chi_tiet_thi_khong_in_chan_doan(self):
        dau_ra, _ = self._chay_lenh()
        self.assertIn('Dịch vụ AI gặp lỗi', dau_ra)
        self.assertNotIn('Mã HTTP', dau_ra)
        self.assertNotIn('CHI TIẾT CHẨN ĐOÁN', dau_ra)
        dau_ra, _ = self._chay_lenh('--chi_tiet')  # viết kiểu gạch dưới như kiem_tra_ai cũng được
        self.assertIn('Mã HTTP: 504', dau_ra)
