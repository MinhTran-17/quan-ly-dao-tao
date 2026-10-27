import os
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.db.utils import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings, tag
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


def _view_loi_500_thu(request):
    raise RuntimeError('loi thu nghiem chi tiet noi bo')


# urlconf riêng cho test trang 500: toàn bộ URL thật cộng một URL cố ý ném lỗi.
from django.urls import path as _path  # noqa: E402

from qldt.urls import urlpatterns as _urlpatterns_that  # noqa: E402

urlpatterns = [_path('loi-500-thu/', _view_loi_500_thu)] + _urlpatterns_that


@tag('tich_hop')
@override_settings(DEBUG=False)
class TrangLoiKhiTatDebugTest(TestCase):
    """Khi DJANGO_DEBUG=False, trang 403/404/500 dùng templates/403.html, 404.html, 500.html, không lộ traceback."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        from accounts.models import VaiTro
        self.sinh_vien = get_user_model().objects.create_user(
            ten_dang_nhap='sv_loi', vai_tro=VaiTro.SINH_VIEN, password='MatKhauManh123',
        )

    def test_404_khi_chua_dang_nhap_va_da_dang_nhap(self):
        response = self.client.get('/khong-co-trang-nay/')
        self.assertContains(response, 'Không tìm thấy trang', status_code=404)
        self.client.force_login(self.sinh_vien)
        response = self.client.get('/khong-co-trang-nay/')
        self.assertContains(response, 'Không tìm thấy trang', status_code=404)
        self.assertNotContains(response, 'Page not found', status_code=404)
        self.assertNotContains(response, 'urlpatterns', status_code=404)

    def test_403_khi_sinh_vien_vao_trang_cua_phong_dao_tao(self):
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('accounts:tai_khoan_danh_sach'))
        self.assertContains(response, 'Không có quyền truy cập', status_code=403)
        self.assertTemplateUsed(response, '403.html')

    @override_settings(ROOT_URLCONF='qldt.tests')
    def test_500_hien_trang_loi_chung_khong_lo_chi_tiet(self):
        self.client.raise_request_exception = False
        with self.assertLogs('django.request', level='ERROR'):
            response = self.client.get('/loi-500-thu/')
        self.assertContains(response, 'Lỗi hệ thống', status_code=500)
        self.assertTemplateUsed(response, '500.html')
        for an in ('loi thu nghiem chi tiet noi bo', 'Traceback', 'RuntimeError'):
            self.assertNotContains(response, an, status_code=500)


@tag('don_vi')
class CauHinhProxyHttpsTest(SimpleTestCase):
    """CSRF_TRUSTED_ORIGINS đọc từ .env và SECURE_PROXY_SSL_HEADER (truy cập qua Cloudflare Tunnel)."""

    def _doc_csrf(self, gia_tri):
        moi_truong = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'qldt.settings', 'PYTHONIOENCODING': 'utf-8',
                      'CSRF_TRUSTED_ORIGINS': gia_tri}
        ket_qua = subprocess.run(
            [sys.executable, '-c', 'from django.conf import settings; print(repr(settings.CSRF_TRUSTED_ORIGINS))'],
            cwd=settings.BASE_DIR, env=moi_truong, capture_output=True, encoding='utf-8', errors='replace', timeout=60,
        )
        self.assertEqual(ket_qua.returncode, 0, ket_qua.stderr)
        return ket_qua.stdout.strip()

    def test_doc_danh_sach_bo_khoang_trang_va_gia_tri_rong(self):
        from qldt.settings import doc_danh_sach
        self.assertEqual(doc_danh_sach(' https://*.trycloudflare.com , ,https://a.vn,'),
                         ['https://*.trycloudflare.com', 'https://a.vn'])
        self.assertEqual(doc_danh_sach(''), [])
        self.assertEqual(doc_danh_sach(None), [])

    def test_csrf_trusted_origins_doc_tu_bien_moi_truong_mac_dinh_rong(self):
        self.assertEqual(self._doc_csrf(''), '[]')
        self.assertEqual(self._doc_csrf('https://*.trycloudflare.com, https://a.vn'),
                         "['https://*.trycloudflare.com', 'https://a.vn']")

    def test_secure_proxy_ssl_header(self):
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ('HTTP_X_FORWARDED_PROTO', 'https'))


@tag('tich_hop')
@override_settings(ALLOWED_HOSTS=['.trycloudflare.com', 'testserver'])
class TruyCapQuaCloudflareTunnelTest(TestCase):
    HOST = 'abc-xyz.trycloudflare.com'
    QUA_TUNNEL = {'HTTP_HOST': HOST, 'HTTP_X_FORWARDED_PROTO': 'https'}

    def _gui_form_dang_nhap(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:dang_nhap'), **self.QUA_TUNNEL)
        return client.post(reverse('accounts:dang_nhap'), {
            'username': 'khong_co', 'password': 'sai', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        }, HTTP_ORIGIN=f'https://{self.HOST}', **self.QUA_TUNNEL)

    @override_settings(CSRF_TRUSTED_ORIGINS=[], SECURE_PROXY_SSL_HEADER=None)
    def test_thieu_ca_hai_cau_hinh_thi_403_origin_checking_failed(self):
        # Tái hiện lỗi: Django thấy request là http nhưng Origin là https -> không cùng origin.
        self.assertEqual(self._gui_form_dang_nhap().status_code, 403)

    @override_settings(CSRF_TRUSTED_ORIGINS=['https://*.trycloudflare.com'], SECURE_PROXY_SSL_HEADER=None)
    def test_khai_bao_csrf_trusted_origins_thi_gui_form_duoc(self):
        response = self._gui_form_dang_nhap()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tên đăng nhập hoặc mật khẩu không đúng.')

    @override_settings(CSRF_TRUSTED_ORIGINS=[])
    def test_secure_proxy_ssl_header_thi_origin_https_khop_may_chu(self):
        self.assertContains(self._gui_form_dang_nhap(), 'Tên đăng nhập hoặc mật khẩu không đúng.')

    def test_request_qua_tunnel_la_https_va_link_dat_lai_mat_khau_dung_https(self):
        from django.contrib.auth import get_user_model
        from django.core import mail
        from django.core.cache import cache

        from accounts.models import VaiTro
        from people.models import GiangVien
        cache.clear()
        self.addCleanup(cache.clear)
        tk = get_user_model().objects.create_user(ten_dang_nhap='gv_tunnel', vai_tro=VaiTro.GIANG_VIEN,
                                                  password='MatKhauManh123')
        GiangVien.objects.create(ma_giang_vien='GVTUNNEL', ho_ten='GV', email='gv.tunnel@gmail.com',
                                 so_dien_thoai='0919600001', ma_tai_khoan=tk)
        response = self.client.post(reverse('accounts:quen_mat_khau'), {'email': 'gv.tunnel@gmail.com'},
                                    **self.QUA_TUNNEL)
        self.assertTrue(response.wsgi_request.is_secure())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f'https://{self.HOST}/dat-lai-mat-khau/', mail.outbox[0].body)
