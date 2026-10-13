import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import VaiTro

from .models import TaiLieuQuyChe

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'
MEDIA_ROOT_TEST = tempfile.mkdtemp(prefix='qldt_media_test_')


def tep_pdf(ten='quy_che.pdf', noi_dung=b'%PDF-1.4 noi dung gia lap'):
    return SimpleUploadedFile(ten, noi_dung, content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TEST)
class TaiLenTaiLieuTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT_TEST, ignore_errors=True)

    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tai_len_hop_le(self):
        response = self.client.post(reverse('regulations:tao'), {
            'ten_tai_lieu': 'Quy chế đào tạo 2025', 'duong_dan_file': tep_pdf(),
        })
        self.assertRedirects(response, reverse('regulations:danh_sach'))
        tai_lieu = TaiLieuQuyChe.objects.get(ten_tai_lieu='Quy chế đào tạo 2025')
        self.assertTrue(tai_lieu.duong_dan_file.storage.exists(tai_lieu.duong_dan_file.name))
        self.assertEqual(tai_lieu.ngay_tai_len, tai_lieu.ngay_cap_nhat)

    def test_tu_choi_duoi_tep_khong_hop_le(self):
        tep_txt = SimpleUploadedFile('quy_che.txt', b'noi dung', content_type='text/plain')
        response = self.client.post(reverse('regulations:tao'), {
            'ten_tai_lieu': 'Quy chế sai đuôi', 'duong_dan_file': tep_txt,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaiLieuQuyChe.objects.filter(ten_tai_lieu='Quy chế sai đuôi').exists())

    def test_tu_choi_tep_qua_10mb(self):
        tep_lon = SimpleUploadedFile(
            'qua_lon.pdf', b'a' * (10 * 1024 * 1024 + 1), content_type='application/pdf'
        )
        response = self.client.post(reverse('regulations:tao'), {
            'ten_tai_lieu': 'Quy chế quá lớn', 'duong_dan_file': tep_lon,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaiLieuQuyChe.objects.filter(ten_tai_lieu='Quy chế quá lớn').exists())

    def test_tu_choi_tep_doi_duoi_gia_mao_khong_dung_pdf_that(self):
        # Đuôi .pdf hợp lệ nhưng nội dung thật không phải PDF (vd. đổi đuôi tệp khác) ->
        # phải bị từ chối bằng kiểm tra magic bytes, không chỉ dựa vào đuôi tên tệp.
        tep_gia = SimpleUploadedFile('gia_mao.pdf', b'noi dung khong phai PDF that', content_type='application/pdf')
        response = self.client.post(reverse('regulations:tao'), {
            'ten_tai_lieu': 'Quy chế giả mạo đuôi', 'duong_dan_file': tep_gia,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaiLieuQuyChe.objects.filter(ten_tai_lieu='Quy chế giả mạo đuôi').exists())

    def test_tu_choi_tep_docx_gia_mao(self):
        tep_gia = SimpleUploadedFile(
            'gia_mao.docx', b'khong phai zip/docx that',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response = self.client.post(reverse('regulations:tao'), {
            'ten_tai_lieu': 'Quy chế docx giả mạo', 'duong_dan_file': tep_gia,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TaiLieuQuyChe.objects.filter(ten_tai_lieu='Quy chế docx giả mạo').exists())

    def test_khong_phai_phong_dao_tao_khong_duoc_tai_len(self):
        sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv001', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
        )
        self.client.force_login(sinh_vien)
        response = self.client.get(reverse('regulations:danh_sach'))
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TEST)
class CapNhatXoaTaiLieuTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT_TEST, ignore_errors=True)

    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.tai_lieu = TaiLieuQuyChe.objects.create(
            ten_tai_lieu='Quy chế cũ', duong_dan_file=tep_pdf('cu.pdf'),
            ngay_tai_len='2025-01-01', ngay_cap_nhat='2025-01-01',
        )

    def test_cap_nhat_thay_tep_xoa_tep_cu(self):
        duong_dan_cu = self.tai_lieu.duong_dan_file.name
        storage = self.tai_lieu.duong_dan_file.storage
        self.assertTrue(storage.exists(duong_dan_cu))

        response = self.client.post(reverse('regulations:sua', args=[self.tai_lieu.pk]), {
            'ten_tai_lieu': 'Quy chế mới', 'duong_dan_file': tep_pdf('moi.pdf'),
        })
        self.assertRedirects(response, reverse('regulations:danh_sach'))
        self.tai_lieu.refresh_from_db()
        self.assertEqual(self.tai_lieu.ten_tai_lieu, 'Quy chế mới')
        self.assertFalse(storage.exists(duong_dan_cu))
        self.assertTrue(storage.exists(self.tai_lieu.duong_dan_file.name))

    def test_cap_nhat_khong_thay_tep_van_giu_tep_cu(self):
        duong_dan_cu = self.tai_lieu.duong_dan_file.name
        response = self.client.post(reverse('regulations:sua', args=[self.tai_lieu.pk]), {
            'ten_tai_lieu': 'Quy chế đổi tên', 'duong_dan_file': '',
        })
        self.assertRedirects(response, reverse('regulations:danh_sach'))
        self.tai_lieu.refresh_from_db()
        self.assertEqual(self.tai_lieu.ten_tai_lieu, 'Quy chế đổi tên')
        self.assertEqual(self.tai_lieu.duong_dan_file.name, duong_dan_cu)
        self.assertTrue(self.tai_lieu.duong_dan_file.storage.exists(duong_dan_cu))

    def test_xoa_tai_lieu_xoa_ca_tep_tren_dia(self):
        duong_dan = self.tai_lieu.duong_dan_file.name
        storage = self.tai_lieu.duong_dan_file.storage
        self.assertTrue(storage.exists(duong_dan))

        response = self.client.post(reverse('regulations:xoa', args=[self.tai_lieu.pk]))
        self.assertRedirects(response, reverse('regulations:danh_sach'))
        self.assertFalse(TaiLieuQuyChe.objects.filter(pk=self.tai_lieu.pk).exists())
        self.assertFalse(storage.exists(duong_dan))

    def test_tim_kiem_theo_ten(self):
        response = self.client.get(reverse('regulations:danh_sach'), {'q': 'cũ'})
        self.assertContains(response, 'Quy chế cũ')


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TEST)
class TaiVeTaiLieuTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT_TEST, ignore_errors=True)

    def setUp(self):
        self.tai_lieu = TaiLieuQuyChe.objects.create(
            ten_tai_lieu='Quy chế công khai', duong_dan_file=tep_pdf('cong_khai.pdf'),
            ngay_tai_len='2025-01-01', ngay_cap_nhat='2025-01-01',
        )

    def test_chua_dang_nhap_khong_tai_ve_duoc(self):
        response = self.client.get(reverse('regulations:tai_ve', args=[self.tai_lieu.pk]))
        self.assertEqual(response.status_code, 302)

    def test_phong_dao_tao_tai_ve_duoc(self):
        phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt3', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(phong_dao_tao)
        response = self.client.get(reverse('regulations:tai_ve', args=[self.tai_lieu.pk]))
        self.assertEqual(response.status_code, 200)

    def test_sinh_vien_khong_tai_ve_duoc(self):
        sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv002', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
        )
        self.client.force_login(sinh_vien)
        response = self.client.get(reverse('regulations:tai_ve', args=[self.tai_lieu.pk]))
        self.assertEqual(response.status_code, 403)

    def test_co_van_khong_tai_ve_duoc(self):
        co_van = TaiKhoan.objects.create_user(
            ten_dang_nhap='cv003', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
        )
        self.client.force_login(co_van)
        response = self.client.get(reverse('regulations:tai_ve', args=[self.tai_lieu.pk]))
        self.assertEqual(response.status_code, 403)
