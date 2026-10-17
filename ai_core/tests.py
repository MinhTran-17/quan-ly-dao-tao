import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from .clients import (
    ClientAIGia,
    GeminiClient,
    _goi_voi_thu_lai,
    _lay_giay_tu_chuoi_thoi_luong,
    _lay_thoi_gian_cho_tu_loi_429,
    _phan_loai_gioi_han_tan_suat,
    _trich_van_ban_tu_phan_hoi,
    lay_client_ai,
)
from .dinh_dang import CANH_BAO_AI, dinh_dang_ket_qua
from .exceptions import (
    ChuaCauHinhKhoaAI,
    DauVaoQuaDai,
    HetThoiGianChoAI,
    LoiMoHinhAI,
    PhanHoiRongAI,
    PhanHoiSaiDinhDangAI,
    QuaGioiHanTanSuatAI,
)
from .gioi_han_tan_suat import SO_LAN_TOI_DA_MOI_PHUT_MAC_DINH, kiem_tra_va_dem
from .prompts import KhongTimThayPrompt, nap_prompt

# Cố định các cấu hình AI mà test trong tệp này ngầm dựa vào, để không phụ thuộc vào
# .env của máy chạy. Mọi TestCase trong tệp này kế thừa từ đây thay vì TestCase trực
# tiếp; override_settings khác (GEMINI_API_KEY, AI_BACKEND, AI_TIMEOUT_GIAY, ...) ở cấp
# lớp con/phương thức vẫn chồng lên bình thường.
_CAU_HINH_AI_CO_DINH = dict(
    AI_NGUONG_DIEM_TRUY_HOI=0.5,
    AI_TRUY_HOI_PHIEN_BAN='v2',
    AI_GIOI_HAN_KY_TU=8000,
    AI_BACKEND='gemini',
    AI_PHIEN_BAN_TU_VAN='v1',
    AI_PHIEN_BAN_TOM_TAT='v1',
    AI_PHIEN_BAN_QUY_CHE='v1',
)


@override_settings(**_CAU_HINH_AI_CO_DINH)
class KiemThuCoDinhCauHinhAI(TestCase):
    pass


class GoiVoiThuLaiTest(KiemThuCoDinhCauHinhAI):
    """Kiểm tra logic thử lại độc lập với mạng thật, dùng hàm giả lập mô phỏng lỗi."""

    def test_thu_lai_roi_thanh_cong(self):
        ham = Mock(side_effect=[httpx.TimeoutException('timeout'), httpx.TimeoutException('timeout'), 'ket qua'])
        ket_qua = _goi_voi_thu_lai(ham, so_lan_thu_lai=2, cho_giay_ban_dau=0.01)
        self.assertEqual(ket_qua, 'ket qua')
        self.assertEqual(ham.call_count, 3)

    def test_het_thoi_gian_cho_sau_khi_thu_lai_het_so_lan(self):
        ham = Mock(side_effect=httpx.TimeoutException('timeout'))
        with self.assertRaises(HetThoiGianChoAI):
            _goi_voi_thu_lai(ham, so_lan_thu_lai=2, cho_giay_ban_dau=0.01)
        self.assertEqual(ham.call_count, 3)  # 1 lần đầu + 2 lần thử lại

    def test_qua_gioi_han_tan_suat_429_sau_khi_thu_lai_het_so_lan(self):
        loi_429 = genai_errors.ClientError(429, {'error': {'message': 'rate limited'}})
        ham = Mock(side_effect=loi_429)
        with self.assertRaises(QuaGioiHanTanSuatAI):
            _goi_voi_thu_lai(ham, so_lan_thu_lai=1, cho_giay_ban_dau=0.01)
        self.assertEqual(ham.call_count, 2)

    def test_429_het_han_muc_theo_ngay_duoc_gan_pham_vi_va_thong_diep_rieng(self):
        loi_429 = genai_errors.ClientError(429, {'error': {'details': [{
            '@type': 'type.googleapis.com/google.rpc.QuotaFailure',
            'violations': [{'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}],
        }]}})
        ham = Mock(side_effect=loi_429)
        with self.assertRaises(QuaGioiHanTanSuatAI) as bat_loi:
            _goi_voi_thu_lai(ham, so_lan_thu_lai=0, cho_giay_ban_dau=0.01)
        self.assertEqual(bat_loi.exception.pham_vi, 'ngay')
        self.assertIn('hết hạn mức', str(bat_loi.exception))
        self.assertIn('hôm nay', str(bat_loi.exception))

    def test_loi_may_chu_5xx_thu_lai_roi_van_that_bai(self):
        loi_503 = genai_errors.ServerError(503, {'error': {'message': 'busy'}})
        ham = Mock(side_effect=loi_503)
        with self.assertRaises(LoiMoHinhAI):
            _goi_voi_thu_lai(ham, so_lan_thu_lai=1, cho_giay_ban_dau=0.01)
        self.assertEqual(ham.call_count, 2)

    def test_loi_client_khac_429_khong_thu_lai(self):
        loi_400 = genai_errors.ClientError(400, {'error': {'message': 'bad request'}})
        ham = Mock(side_effect=loi_400)
        with self.assertRaises(LoiMoHinhAI):
            _goi_voi_thu_lai(ham, so_lan_thu_lai=2, cho_giay_ban_dau=0.01)
        self.assertEqual(ham.call_count, 1)

    def test_loi_nghiep_vu_khong_bi_thu_lai(self):
        ham = Mock(side_effect=PhanHoiRongAI())
        with self.assertRaises(PhanHoiRongAI):
            _goi_voi_thu_lai(ham, so_lan_thu_lai=2, cho_giay_ban_dau=0.01)
        self.assertEqual(ham.call_count, 1)

    def test_429_co_goi_y_thoi_gian_cho_thi_cho_dung_thoi_gian_do(self):
        # API trả retryDelay=21s trong details -> phải chờ đúng 21 giây (không dùng
        # backoff tăng dần mặc định), và MỖI lần thử lại vẫn tính là một request mới.
        loi_429 = genai_errors.ClientError(429, {
            'error': {
                'code': 429, 'message': 'rate limited', 'status': 'RESOURCE_EXHAUSTED',
                'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '21s'}],
            },
        })
        ham = Mock(side_effect=[loi_429, 'ket qua'])
        with patch('ai_core.clients.time.sleep') as gia_lap_sleep:
            ket_qua = _goi_voi_thu_lai(ham, so_lan_thu_lai=1, cho_giay_ban_dau=0.01)
        self.assertEqual(ket_qua, 'ket qua')
        gia_lap_sleep.assert_called_once_with(21.0)

    def test_429_thoi_gian_de_xuat_vuot_qua_van_bi_chan_tran(self):
        loi_429 = genai_errors.ClientError(429, {
            'error': {'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '120s'}]},
        })
        ham = Mock(side_effect=[loi_429, 'ket qua'])
        with patch('ai_core.clients.time.sleep') as gia_lap_sleep:
            _goi_voi_thu_lai(ham, so_lan_thu_lai=1, cho_giay_ban_dau=0.01)
        gia_lap_sleep.assert_called_once_with(60.0)

    def test_429_khong_co_goi_y_thi_dung_backoff_cu(self):
        loi_429 = genai_errors.ClientError(429, {'error': {'message': 'rate limited'}})
        ham = Mock(side_effect=[loi_429, 'ket qua'])
        with patch('ai_core.clients.time.sleep') as gia_lap_sleep:
            _goi_voi_thu_lai(ham, so_lan_thu_lai=1, cho_giay_ban_dau=2.0)
        gia_lap_sleep.assert_called_once_with(2.0)  # 2.0 * 2**(1-1)


class PhanLoaiGioiHanTanSuatTest(KiemThuCoDinhCauHinhAI):
    """Phân biệt HẾT HẠN MỨC THEO NGÀY với VƯỢT TẦN SUẤT THEO PHÚT từ chi tiết lỗi 429."""

    def test_quota_id_chua_perday_duoc_nhan_dien_la_theo_ngay(self):
        loi = genai_errors.ClientError(429, {'error': {'details': [{
            '@type': 'type.googleapis.com/google.rpc.QuotaFailure',
            'violations': [{
                'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests',
                'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier',
            }],
        }]}})
        self.assertEqual(_phan_loai_gioi_han_tan_suat(loi), 'ngay')

    def test_quota_id_chua_perminute_duoc_nhan_dien_la_theo_phut(self):
        loi = genai_errors.ClientError(429, {'error': {'details': [{
            '@type': 'type.googleapis.com/google.rpc.QuotaFailure',
            'violations': [{
                'quotaMetric': 'generativelanguage.googleapis.com/generate_requests',
                'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier',
            }],
        }]}})
        self.assertEqual(_phan_loai_gioi_han_tan_suat(loi), 'phut')

    def test_khong_co_du_can_cu_tra_ve_none(self):
        # Ví dụ THẬT ghi nhận được: thông điệp chỉ nói "limit: 20" mà không có quotaId
        # cấu trúc hay từ khóa "day"/"minute" rõ ràng -> không suy đoán, trả None.
        loi = genai_errors.ClientError(429, {'error': {
            'message': (
                'Quota exceeded for metric: generativelanguage.googleapis.com/'
                'generate_content_free_tier_requests, limit: 20, model: gemini-3.8-flash. '
                'Please retry in 43s.'
            ),
        }})
        self.assertIsNone(_phan_loai_gioi_han_tan_suat(loi))

    def test_tu_khoa_requests_per_day_trong_thong_diep_tho_cung_nhan_dien_duoc(self):
        loi = genai_errors.ClientError(429, {'error': {'message': 'You exceeded your requests per day quota.'}})
        self.assertEqual(_phan_loai_gioi_han_tan_suat(loi), 'ngay')


class LayThoiGianChoTu429Test(KiemThuCoDinhCauHinhAI):
    def test_doc_duoc_retry_delay_dang_lay_trong_details(self):
        loi = genai_errors.ClientError(429, {
            'error': {'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '7.5s'}]},
        })
        self.assertEqual(_lay_thoi_gian_cho_tu_loi_429(loi), 7.5)

    def test_khong_co_details_tra_ve_none(self):
        loi = genai_errors.ClientError(429, {'error': {'message': 'rate limited'}})
        self.assertIsNone(_lay_thoi_gian_cho_tu_loi_429(loi))

    def test_tach_giay_tu_chuoi_thoi_luong(self):
        self.assertEqual(_lay_giay_tu_chuoi_thoi_luong('20s'), 20.0)
        self.assertEqual(_lay_giay_tu_chuoi_thoi_luong('1.5s'), 1.5)
        self.assertIsNone(_lay_giay_tu_chuoi_thoi_luong('khong hop le'))
        self.assertIsNone(_lay_giay_tu_chuoi_thoi_luong(None))


class QuaGioiHanTanSuatAIThongDiepTest(KiemThuCoDinhCauHinhAI):
    def test_pham_vi_ngay_co_thong_diep_rieng(self):
        loi = QuaGioiHanTanSuatAI(pham_vi='ngay')
        self.assertIn('hết hạn mức', str(loi))
        self.assertIn('hôm nay', str(loi))
        self.assertIn('đặt lại', str(loi))

    def test_pham_vi_phut_co_thong_diep_rieng(self):
        loi = QuaGioiHanTanSuatAI(pham_vi='phut')
        self.assertIn('vượt tần suất theo phút', str(loi))

    def test_khong_ro_pham_vi_dung_thong_diep_chung_nhu_truoc(self):
        loi = QuaGioiHanTanSuatAI()
        self.assertEqual(str(loi), 'Dịch vụ AI đang bị giới hạn tần suất sử dụng, vui lòng thử lại sau.')


class TrichVanBanTuPhanHoiTest(KiemThuCoDinhCauHinhAI):
    def test_phan_hoi_rong(self):
        with self.assertRaises(PhanHoiRongAI):
            _trich_van_ban_tu_phan_hoi(Mock(text='   '))

    def test_phan_hoi_sai_dinh_dang(self):
        with self.assertRaises(PhanHoiSaiDinhDangAI):
            _trich_van_ban_tu_phan_hoi(Mock(text=None))

    def test_phan_hoi_hop_le(self):
        van_ban = _trich_van_ban_tu_phan_hoi(Mock(text='Xin chào'))
        self.assertEqual(van_ban, 'Xin chào')


class GeminiClientTest(KiemThuCoDinhCauHinhAI):
    @override_settings(GEMINI_API_KEY='')
    def test_thieu_khoa_bao_loi_ngay_khong_goi_mang(self):
        with self.assertRaises(ChuaCauHinhKhoaAI):
            GeminiClient()

    @override_settings(GEMINI_API_KEY='khoa-gia-de-test', AI_GIOI_HAN_KY_TU=20)
    def test_dau_vao_qua_dai_bi_tu_choi_truoc_khi_goi_api(self):
        client = GeminiClient()
        with self.assertRaises(DauVaoQuaDai):
            client.sinh_noi_dung(he_thong='he thong', nguoi_dung='noi dung dai hon hai muoi ky tu rat nhieu')

    @override_settings(GEMINI_API_KEY='khoa-gia-de-test', AI_TIMEOUT_GIAY=5, AI_SO_LAN_THU_LAI=1)
    def test_doc_dung_cac_gia_tri_cau_hinh_tu_settings(self):
        client = GeminiClient()
        self.assertEqual(client.model, settings.GEMINI_MODEL)
        self.assertEqual(client.timeout_giay, 5)
        self.assertEqual(client.so_lan_thu_lai, 1)

    @override_settings(GEMINI_API_KEY='khoa-gia-de-test')
    def test_tham_so_truyen_truc_tiep_ghi_de_settings(self):
        client = GeminiClient(model='mo-hinh-khac', timeout_giay=9, so_lan_thu_lai=3, gioi_han_ky_tu=50)
        self.assertEqual(client.model, 'mo-hinh-khac')
        self.assertEqual(client.timeout_giay, 9)
        self.assertEqual(client.so_lan_thu_lai, 3)
        self.assertEqual(client.gioi_han_ky_tu, 50)

    @override_settings(GEMINI_API_KEY='khoa-gia-de-test')
    def test_tat_automatic_function_calling_de_khong_in_canh_bao(self):
        # Hệ thống không dùng function calling; tắt hẳn AFC để SDK không in cảnh báo
        # "Direct use of automatic function calling (AFC)..." mỗi lần gọi.
        client = GeminiClient()
        client._client = Mock()
        client._client.models.generate_content.return_value = Mock(text='Xin chao', model_version='v-test')
        client.sinh_noi_dung(he_thong='he thong', nguoi_dung='noi dung')
        _, kwargs = client._client.models.generate_content.call_args
        cau_hinh_afc = kwargs['config'].automatic_function_calling
        self.assertIsInstance(cau_hinh_afc, genai_types.AutomaticFunctionCallingConfig)
        self.assertTrue(cau_hinh_afc.disable)


class ClientAIGiaTest(KiemThuCoDinhCauHinhAI):
    def test_tra_ve_phan_hoi_co_dinh_va_luu_lai_lan_goi(self):
        client = ClientAIGia(phan_hoi='Xin chào từ AI giả')
        ket_qua = client.sinh_noi_dung(he_thong='he thong', nguoi_dung='noi dung')
        self.assertEqual(ket_qua, 'Xin chào từ AI giả')
        self.assertEqual(client.cac_lan_goi, [{'he_thong': 'he thong', 'nguoi_dung': 'noi dung'}])

    def test_co_the_gia_lap_loi(self):
        client = ClientAIGia(phan_hoi=PhanHoiRongAI())
        with self.assertRaises(PhanHoiRongAI):
            client.sinh_noi_dung(he_thong='a', nguoi_dung='b')


class LayClientAiTest(KiemThuCoDinhCauHinhAI):
    @override_settings(AI_BACKEND='gia')
    def test_chon_client_gia_qua_cau_hinh(self):
        self.assertIsInstance(lay_client_ai(), ClientAIGia)

    @override_settings(AI_BACKEND='gemini', GEMINI_API_KEY='khoa-gia-de-test')
    def test_chon_client_that_qua_cau_hinh(self):
        self.assertIsInstance(lay_client_ai(), GeminiClient)


class DinhDangKetQuaTest(KiemThuCoDinhCauHinhAI):
    def test_luon_kem_canh_bao_co_dinh(self):
        ket_qua = dinh_dang_ket_qua('Nội dung trả lời của AI')
        self.assertIn('Nội dung trả lời của AI', ket_qua)
        self.assertIn(CANH_BAO_AI, ket_qua)

    def test_noi_dung_rong_van_co_canh_bao(self):
        ket_qua = dinh_dang_ket_qua('')
        self.assertIn(CANH_BAO_AI, ket_qua)


class NapPromptTest(KiemThuCoDinhCauHinhAI):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thu_muc_tam = Path(tempfile.mkdtemp(prefix='qldt_prompts_test_'))
        (cls.thu_muc_tam / 'demo' / 'v1').mkdir(parents=True)
        (cls.thu_muc_tam / 'demo' / 'v1' / 'system.txt').write_text('He thong phien ban 1', encoding='utf-8')
        (cls.thu_muc_tam / 'demo' / 'v1' / 'user.txt').write_text('Xin chao $ten', encoding='utf-8')
        (cls.thu_muc_tam / 'demo' / 'v2').mkdir(parents=True)
        (cls.thu_muc_tam / 'demo' / 'v2' / 'system.txt').write_text(
            'He thong phien ban 2 vi du JSON {"a": 1} khong can escape', encoding='utf-8'
        )
        (cls.thu_muc_tam / 'demo' / 'v2' / 'user.txt').write_text('Chao ban $ten', encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.thu_muc_tam, ignore_errors=True)
        super().tearDownClass()

    def test_nap_dung_phien_ban_va_dien_bien(self):
        with override_settings(AI_PROMPTS_DIR=self.thu_muc_tam):
            he_thong, nguoi_dung = nap_prompt('demo', 'v1', ten='An')
            self.assertEqual(he_thong, 'He thong phien ban 1')
            self.assertEqual(nguoi_dung, 'Xin chao An')

            he_thong_v2, nguoi_dung_v2 = nap_prompt('demo', 'v2', ten='An')
            self.assertEqual(he_thong_v2, 'He thong phien ban 2 vi du JSON {"a": 1} khong can escape')
            self.assertEqual(nguoi_dung_v2, 'Chao ban An')

    def test_khong_tim_thay_phien_ban_bao_loi(self):
        with override_settings(AI_PROMPTS_DIR=self.thu_muc_tam):
            with self.assertRaises(KhongTimThayPrompt):
                nap_prompt('demo', 'v3')

    def test_nap_prompt_that_kiem_tra_ket_noi(self):
        he_thong, nguoi_dung = nap_prompt('kiem_tra_ket_noi', 'v1')
        self.assertIn('kiểm tra kết nối', he_thong.lower())
        self.assertTrue(nguoi_dung.strip())

    def test_nap_prompt_that_hoi_dap_quy_che_v2(self):
        he_thong, nguoi_dung = nap_prompt(
            'hoi_dap_quy_che', 'v2',
            cau_hoi='Câu hỏi mẫu?', doan_trich='[Nguồn: Tài liệu, Điều 1]\nNội dung mẫu.',
        )
        self.assertIn('120 từ', he_thong)
        self.assertIn('Câu hỏi mẫu?', nguoi_dung)
        self.assertIn('[Nguồn: Tài liệu, Điều 1]', nguoi_dung)

    def test_nap_prompt_that_hoi_dap_quy_che_v1_khong_bi_doi(self):
        # v2 thêm ràng buộc ~120 từ; v1 không được có ràng buộc này (chưa từng sửa v1).
        he_thong, _ = nap_prompt('hoi_dap_quy_che', 'v1', cau_hoi='x', doan_trich='y')
        self.assertNotIn('120 từ', he_thong)


class KiemTraAiCommandTest(KiemThuCoDinhCauHinhAI):
    @override_settings(AI_BACKEND='gia')
    def test_thanh_cong_voi_client_gia_khong_goi_mang(self):
        out = StringIO()
        call_command('kiem_tra_ai', stdout=out)
        noi_dung = out.getvalue()
        self.assertIn('thành công', noi_dung)

    @override_settings(AI_BACKEND='gemini', GEMINI_API_KEY='')
    def test_bao_loi_de_hieu_khi_thieu_khoa_khong_lo_khoa(self):
        out = StringIO()
        err = StringIO()
        call_command('kiem_tra_ai', stdout=out, stderr=err)
        self.assertIn('Chưa cấu hình khóa', err.getvalue())

    @override_settings(AI_BACKEND='gemini', GEMINI_API_KEY='')
    def test_khong_chi_tiet_thi_khong_in_them_dong_chi_tiet(self):
        err = StringIO()
        call_command('kiem_tra_ai', stdout=StringIO(), stderr=err)
        self.assertNotIn('Mã HTTP', err.getvalue())

    @override_settings(AI_BACKEND='gemini', GEMINI_API_KEY='')
    def test_chi_tiet_bao_khong_co_them_thong_tin_cho_loi_thieu_khoa(self):
        # ChuaCauHinhKhoaAI không có chi_tiet (không phải lỗi từ phía API), nên
        # --chi_tiet chỉ báo "không có thêm chi tiết", không suy diễn hay bịa dữ liệu.
        err = StringIO()
        call_command('kiem_tra_ai', '--chi_tiet', stdout=StringIO(), stderr=err)
        self.assertIn('Không có thêm chi tiết', err.getvalue())

    @override_settings(AI_BACKEND='gia')
    def test_chi_tiet_in_dung_thong_tin_khi_client_gia_bao_loi_mo_hinh(self):
        from unittest.mock import patch

        loi = LoiMoHinhAI({'loai': 'ServerError', 'ma_http': 503, 'thong_diep': 'server busy'})
        err = StringIO()
        with patch('ai_core.clients.ClientAIGia.sinh_noi_dung', side_effect=loi):
            call_command('kiem_tra_ai', '--chi_tiet', stdout=StringIO(), stderr=err)
        noi_dung = err.getvalue()
        self.assertIn('ServerError', noi_dung)
        self.assertIn('503', noi_dung)
        self.assertIn('server busy', noi_dung)


class GioiHanTanSuatDungChungTest(KiemThuCoDinhCauHinhAI):
    """Hàm giới hạn tần suất dùng chung cho tu_van_dang_ky/tom_tat_ket_qua (hoi_dap_quy_che
    có bản riêng tương đương — xem hoi_dap_quy_che/gioi_han_tan_suat.py)."""

    def setUp(self):
        cache.clear()

    def test_duoc_phep_toi_da_mac_dinh_lan(self):
        khoa = 'test_khoa_1'
        for _ in range(SO_LAN_TOI_DA_MOI_PHUT_MAC_DINH):
            duoc_phep, _ = kiem_tra_va_dem(khoa)
            self.assertTrue(duoc_phep)
        duoc_phep, thong_bao = kiem_tra_va_dem(khoa)
        self.assertFalse(duoc_phep)
        self.assertTrue(thong_bao)

    def test_moi_khoa_dem_rieng(self):
        for _ in range(SO_LAN_TOI_DA_MOI_PHUT_MAC_DINH):
            kiem_tra_va_dem('khoa_a')
        duoc_phep, _ = kiem_tra_va_dem('khoa_b')
        self.assertTrue(duoc_phep)

    def test_co_the_ghi_de_so_toi_da_va_cua_so(self):
        khoa = 'test_khoa_gioi_han_rieng'
        for _ in range(3):
            duoc_phep, _ = kiem_tra_va_dem(khoa, so_toi_da=3, cua_so_giay=30)
            self.assertTrue(duoc_phep)
        duoc_phep, _ = kiem_tra_va_dem(khoa, so_toi_da=3, cua_so_giay=30)
        self.assertFalse(duoc_phep)


class DocPhamViTest(TestCase):
    """Code tự đọc học kỳ/năm học/toàn khóa từ câu gõ trong khung chat (không gửi câu gõ cho AI để hiểu)."""

    def _doc(self, cau):
        from .phan_tich_cau_hoi import doc_pham_vi
        return doc_pham_vi(cau)

    def test_ky_va_nam_hoc_nhieu_cach_viet(self):
        for cau in ('tóm tắt kỳ 1 năm 2024-2025', 'Tóm tắt học kì 1 năm học 2024 - 2025', 'tom tat hk1 2024/2025'):
            pham_vi = self._doc(cau)
            self.assertEqual((pham_vi.hoc_ky, pham_vi.nam_hoc), ('1', '2024-2025'), cau)

    def test_chi_co_ky_hoac_chi_co_nam(self):
        self.assertEqual((self._doc('tóm tắt học tập của kì 2').hoc_ky, self._doc('tóm tắt học tập của kì 2').nam_hoc), ('2', ''))
        pham_vi = self._doc('kết quả năm học 2025-2026 thế nào')
        self.assertEqual((pham_vi.hoc_ky, pham_vi.nam_hoc), ('', '2025-2026'))

    def test_so_trong_nam_hoc_khong_bi_hieu_nham_la_hoc_ky(self):
        self.assertEqual(self._doc('năm 2021-2022').hoc_ky, '')

    def test_nam_hoc_khong_lien_tiep_bi_bo_qua(self):
        self.assertEqual(self._doc('năm 2024-2026').nam_hoc, '')

    def test_toan_khoa_va_gan_nhat(self):
        self.assertTrue(self._doc('Tóm tắt toàn khóa giúp em').toan_khoa)
        self.assertTrue(self._doc('điểm tích lũy của em').toan_khoa)
        self.assertTrue(self._doc('tóm tắt học kỳ gần nhất').gan_nhat)
        self.assertFalse(self._doc('xin chào').co_noi_toi)

    def test_bo_dau(self):
        from .phan_tich_cau_hoi import bo_dau
        self.assertEqual(bo_dau('  Học  KỲ Đầu '), 'hoc ky dau')


class LichSuChatTest(TestCase):
    def _request(self):
        from django.contrib.sessions.backends.signed_cookies import SessionStore
        from django.test import RequestFactory
        request = RequestFactory().post('/', {'cau_hoi': ' câu gõ '})
        request.session = SessionStore()
        return request

    def test_them_doc_xoa_va_gioi_han_so_luot(self):
        from . import lich_su_chat
        request = self._request()
        for i in range(lich_su_chat.SO_LUOT_TOI_DA + 3):
            lich_su_chat.them(request, 'thu', f'câu {i}', {'noi_dung': str(i)})
        lich_su = lich_su_chat.doc(request, 'thu')
        self.assertEqual(len(lich_su), lich_su_chat.SO_LUOT_TOI_DA)
        self.assertEqual(lich_su[-1], {'cau_hoi': f'câu {lich_su_chat.SO_LUOT_TOI_DA + 2}', 'tra_loi': {'noi_dung': str(lich_su_chat.SO_LUOT_TOI_DA + 2)}})
        self.assertEqual(lich_su_chat.doc(request, 'khoa_khac'), [])
        lich_su_chat.xoa(request, 'thu')
        self.assertEqual(lich_su_chat.doc(request, 'thu'), [])

    def test_cau_gui_len_lay_o_nhap_bo_khoang_trang(self):
        from django.contrib.sessions.backends.signed_cookies import SessionStore
        from django.test import RequestFactory

        from . import lich_su_chat
        self.assertEqual(lich_su_chat.cau_gui_len(self._request()), 'câu gõ')
        request = RequestFactory().post('/', {})
        request.session = SessionStore()
        self.assertEqual(lich_su_chat.cau_gui_len(request), '')
