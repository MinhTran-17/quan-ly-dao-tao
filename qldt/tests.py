import os
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.db.utils import OperationalError
from django.test import SimpleTestCase, TestCase, tag
from django.urls import reverse


@tag('tich_hop')
class KiemTraSucKhoeTest(TestCase):
    def test_tra_json_ok_khi_csdl_ket_noi_duoc_va_khong_can_dang_nhap(self):
        response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'trang_thai': 'ok', 'ung_dung': 'ok', 'csdl': 'ok'})
        self.assertIn('no-cache', response['Cache-Control'])

    def test_tra_503_khi_csdl_loi_va_khong_lo_chi_tiet_loi(self):
        with patch('qldt.views.connection.cursor', side_effect=OperationalError('mat ket noi toi may chu bi mat')):
            response = self.client.get(reverse('health'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'trang_thai': 'loi', 'ung_dung': 'ok', 'csdl': 'loi'})
        self.assertNotContains(response, 'bi mat', status_code=503)

    def test_chi_nhan_get(self):
        self.assertEqual(self.client.post(reverse('health')).status_code, 405)


@tag('don_vi')
class KhoaBiMatKhiChayThatTest(SimpleTestCase):
    """Nạp settings trong tiến trình con với biến môi trường cố định (load_dotenv không ghi đè
    biến đã có), để không phụ thuộc .env của máy chạy test."""

    def _nap_settings(self, **bien):
        moi_truong = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'qldt.settings', 'PYTHONIOENCODING': 'utf-8', **bien}
        return subprocess.run(
            [sys.executable, '-c', 'from django.conf import settings; print(len(settings.SECRET_KEY))'],
            cwd=settings.BASE_DIR, env=moi_truong, capture_output=True, encoding='utf-8', errors='replace', timeout=60,
        )

    def test_debug_false_thieu_khoa_thi_bao_loi(self):
        ket_qua = self._nap_settings(DJANGO_DEBUG='False', DJANGO_SECRET_KEY='')
        self.assertNotEqual(ket_qua.returncode, 0)
        self.assertIn('ImproperlyConfigured', ket_qua.stderr)
        self.assertIn('DJANGO_SECRET_KEY', ket_qua.stderr)

    def test_debug_false_co_khoa_thi_chay_duoc(self):
        ket_qua = self._nap_settings(DJANGO_DEBUG='False', DJANGO_SECRET_KEY='k' * 50)
        self.assertEqual(ket_qua.returncode, 0, ket_qua.stderr)
        self.assertEqual(ket_qua.stdout.strip(), '50')

    def test_debug_true_thieu_khoa_dung_khoa_phat_trien(self):
        ket_qua = self._nap_settings(DJANGO_DEBUG='True', DJANGO_SECRET_KEY='')
        self.assertEqual(ket_qua.returncode, 0, ket_qua.stderr)


@tag('don_vi')
class CauHinhLogTest(SimpleTestCase):
    def test_log_ghi_ra_tep_xoay_vong_trong_thu_muc_logs(self):
        handler = settings.LOGGING['handlers']['tep_xoay_vong']
        self.assertEqual(handler['class'], 'logging.handlers.RotatingFileHandler')
        self.assertEqual(handler['filename'], settings.LOG_DIR / 'app.log')
        self.assertGreater(handler['backupCount'], 0)
        self.assertIn('tep_xoay_vong', settings.LOGGING['loggers']['qldt']['handlers'])
