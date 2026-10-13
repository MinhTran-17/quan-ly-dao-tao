import io
import re
import shutil
import tempfile
from datetime import time, timedelta
from html.parser import HTMLParser
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from academics.models import (
    ChiTietChuongTrinh, ChuongTrinhDaoTao, DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc,
)
from classes.models import LichHoc, LichThi, LopHocPhan
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from diem_danh.models import DiemDanh
from enrollment.services import LoiDangKyHocPhan, dang_ky_hoc_phan, tim_hoc_phan_tien_quyet_con_thieu
from grades.models import Diem
from grades.services import canh_bao_hoc_vu, hoc_ky_gan_nhat_co_du_diem
from people.models import CoVanHocTap, GiangVien, SinhVien
from regulations.models import TaiLieuQuyChe
from thong_bao.models import DaDocThongBao, DoiTuongThongBao, ThongBao
from thong_bao.services import so_luong_chua_doc

from .models import VaiTro

TaiKhoan = get_user_model()

MAT_KHAU_HOP_LE = 'MatKhauManh123'
MEDIA_ROOT_TEST = tempfile.mkdtemp(prefix='qldt_media_test_')


class _KiemTraThe(HTMLParser):
    THE_THEO_DOI = {
        'div', 'nav', 'header', 'footer', 'main', 'button', 'form', 'a', 'ul', 'li', 'span', 'svg',
        'symbol', 'defs', 'h2', 'h3', 'h4', 'p', 'section', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
        'strong', 'small', 'script', 'style',
    }

    def __init__(self):
        super().__init__()
        self.ngan_xep = []
        self.loi = []

    def handle_starttag(self, tag, attrs):
        if tag in self.THE_THEO_DOI:
            self.ngan_xep.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag not in self.THE_THEO_DOI:
            return
        if not self.ngan_xep or self.ngan_xep[-1] != tag:
            self.loi.append(f'</{tag}> không khớp (ngăn xếp: {self.ngan_xep[-3:]})')
        else:
            self.ngan_xep.pop()


def kiem_tra_can_bang_the(html):
    """Trả về (danh sách lỗi đóng thẻ sai, danh sách thẻ còn mở) của các thẻ khối chính — dùng
    chung cho test giao diện (accounts, grades) vì chưa có trình duyệt trong bộ test."""
    bo_kiem_tra = _KiemTraThe()
    bo_kiem_tra.feed(html)
    return bo_kiem_tra.loi, bo_kiem_tra.ngan_xep


class DangNhapTest(TestCase):
    def setUp(self):
        self.tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv001', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )

    def test_dang_nhap_dung_tai_khoan_va_mat_khau(self):
        response = self.client.post(reverse('accounts:dang_nhap'), {
            'username': 'sv001',
            'password': MAT_KHAU_HOP_LE,
        })
        self.assertRedirects(response, reverse('accounts:trang_chu'))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_dang_nhap_sai_mat_khau(self):
        response = self.client.post(reverse('accounts:dang_nhap'), {
            'username': 'sv001',
            'password': 'mat_khau_sai',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)

    def test_tai_khoan_bi_khoa_khong_dang_nhap_duoc(self):
        self.tai_khoan.is_active = False
        self.tai_khoan.save(update_fields=['is_active'])
        response = self.client.post(reverse('accounts:dang_nhap'), {
            'username': 'sv001',
            'password': MAT_KHAU_HOP_LE,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)


class MoKhoaVaXoaTaiKhoanTest(TestCase):
    def setUp(self):
        self.pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_mk', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.client.force_login(self.pdt)
        self.tk = TaiKhoan.objects.create_user(ten_dang_nhap='tk_mk', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
        self.url_danh_sach = reverse('accounts:tai_khoan_danh_sach')
        self.url_mo_khoa = reverse('accounts:tai_khoan_mo_khoa', args=[self.tk.pk])
        self.url_xoa = reverse('accounts:tai_khoan_xoa', args=[self.tk.pk])

    def _khoa(self):
        TaiKhoan.objects.filter(pk=self.tk.pk).update(is_active=False)

    # ---- mở khóa ----
    def test_danh_sach_chi_hien_mo_khoa_cho_tai_khoan_da_khoa(self):
        response = self.client.get(self.url_danh_sach)
        self.assertContains(response, reverse('accounts:tai_khoan_khoa', args=[self.tk.pk]))
        self.assertNotContains(response, self.url_mo_khoa)
        self._khoa()
        response = self.client.get(self.url_danh_sach)
        self.assertContains(response, self.url_mo_khoa)
        self.assertContains(response, 'Mở khóa')
        self.assertNotContains(response, reverse('accounts:tai_khoan_khoa', args=[self.tk.pk]))

    def test_mo_khoa_cho_phep_dang_nhap_lai(self):
        self._khoa()
        client = self.client_class()
        self.assertFalse(client.login(username='tk_mk', password=MAT_KHAU_HOP_LE))
        response = self.client.post(self.url_mo_khoa, follow=True)
        self.assertRedirects(response, self.url_danh_sach)
        self.assertContains(response, 'Đã mở khóa tài khoản')
        self.tk.refresh_from_db()
        self.assertTrue(self.tk.is_active)
        self.assertTrue(client.login(username='tk_mk', password=MAT_KHAU_HOP_LE))

    def test_mo_khoa_chi_nhan_post_va_tai_khoan_khong_ton_tai_tra_ve_404(self):
        self._khoa()
        self.assertEqual(self.client.get(self.url_mo_khoa).status_code, 405)
        self.tk.refresh_from_db()
        self.assertFalse(self.tk.is_active)
        self.assertEqual(self.client.post(reverse('accounts:tai_khoan_mo_khoa', args=[999999])).status_code, 404)

    # ---- xóa ----
    def test_danh_sach_co_nut_xoa_tru_tai_khoan_dang_dang_nhap(self):
        response = self.client.get(self.url_danh_sach)
        self.assertContains(response, self.url_xoa)
        self.assertNotContains(response, reverse('accounts:tai_khoan_xoa', args=[self.pdt.pk]))

    def test_get_chi_hien_xac_nhan_khong_xoa(self):
        response = self.client.get(self.url_xoa)
        self.assertContains(response, 'tk_mk')
        self.assertNotContains(response, 'chưa thể xóa')
        self.assertTrue(TaiKhoan.objects.filter(pk=self.tk.pk).exists())

    def test_xoa_tai_khoan_chua_dung(self):
        response = self.client.post(self.url_xoa, follow=True)
        self.assertRedirects(response, self.url_danh_sach)
        self.assertContains(response, 'Đã xóa tài khoản')
        self.assertFalse(TaiKhoan.objects.filter(pk=self.tk.pk).exists())

    def test_xoa_tai_khoan_phong_dao_tao_khac_duoc(self):
        khac = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_khac', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.client.post(reverse('accounts:tai_khoan_xoa', args=[khac.pk]))
        self.assertFalse(TaiKhoan.objects.filter(pk=khac.pk).exists())

    def test_chan_xoa_tai_khoan_dang_gan_ho_so(self):
        nganh = NganhHoc.objects.create(ma_nganh='N_MK', ten_nganh='N')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_mk', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        co_van = CoVanHocTap.objects.create(ma_co_van='CV_MK', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv)
        lop = LopHanhChinh.objects.create(ma_lop='L_MK', ten_lop='L', ma_nganh=nganh, ma_co_van=co_van)
        SinhVien.objects.create(
            ma_sinh_vien='SV_MK', ho_ten='SV', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=lop, ma_tai_khoan=self.tk,
        )
        for tai_khoan, nhan in ((self.tk, 'hồ sơ sinh viên'), (tk_cv, 'hồ sơ cố vấn học tập')):
            url = reverse('accounts:tai_khoan_xoa', args=[tai_khoan.pk])
            response = self.client.post(url, follow=True)
            self.assertRedirects(response, self.url_danh_sach)
            self.assertContains(response, f'đang gắn {nhan}')
            self.assertContains(response, 'khóa tài khoản')
            self.assertTrue(TaiKhoan.objects.filter(pk=tai_khoan.pk).exists())
            self.assertContains(self.client.get(url), 'chưa thể xóa')

    def test_chan_xoa_tai_khoan_da_gui_hoac_da_doc_thong_bao(self):
        thong_bao = ThongBao.objects.create(tieu_de='TB', noi_dung='x', nguoi_gui=self.pdt, doi_tuong=DoiTuongThongBao.TAT_CA)
        response = self.client.post(self.url_xoa, follow=True)
        self.assertNotContains(response, 'Không thể xóa tài khoản')  # tk_mk chưa gửi hay đọc gì -> xóa được
        tai_khoan_da_doc = TaiKhoan.objects.create_user(ten_dang_nhap='da_doc_mk', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
        DaDocThongBao.objects.create(thong_bao=thong_bao, tai_khoan=tai_khoan_da_doc)
        response = self.client.post(reverse('accounts:tai_khoan_xoa', args=[tai_khoan_da_doc.pk]), follow=True)
        self.assertContains(response, 'có 1 lượt đã đọc thông báo')
        self.assertTrue(TaiKhoan.objects.filter(pk=tai_khoan_da_doc.pk).exists())
        tk_gui = TaiKhoan.objects.create_user(ten_dang_nhap='da_gui_mk', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        ThongBao.objects.create(tieu_de='TB2', noi_dung='x', nguoi_gui=tk_gui, doi_tuong=DoiTuongThongBao.TAT_CA)
        response = self.client.post(reverse('accounts:tai_khoan_xoa', args=[tk_gui.pk]), follow=True)
        self.assertContains(response, 'đã gửi 1 thông báo')
        self.assertTrue(TaiKhoan.objects.filter(pk=tk_gui.pk).exists())

    def test_khong_tu_xoa_tai_khoan_dang_dang_nhap(self):
        url = reverse('accounts:tai_khoan_xoa', args=[self.pdt.pk])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, self.url_danh_sach)
        self.assertContains(response, 'Không thể tự xóa tài khoản đang đăng nhập.')
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Không thể tự xóa tài khoản đang đăng nhập.')
        self.assertTrue(TaiKhoan.objects.filter(pk=self.pdt.pk).exists())

    def test_xoa_tai_khoan_khong_ton_tai_tra_ve_404(self):
        self.assertEqual(self.client.post(reverse('accounts:tai_khoan_xoa', args=[999999])).status_code, 404)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_mo_khoa_hay_xoa_duoc(self):
        self._khoa()
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=f'mk_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU_HOP_LE))
            self.assertEqual(self.client.post(self.url_mo_khoa).status_code, 403, vai_tro)
            self.assertEqual(self.client.post(self.url_xoa).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(self.url_mo_khoa).status_code, 302)
        self.assertEqual(self.client.post(self.url_xoa).status_code, 302)
        self.tk.refresh_from_db()
        self.assertFalse(self.tk.is_active)
        self.assertTrue(TaiKhoan.objects.filter(pk=self.tk.pk).exists())


class TaoTaiKhoanCoVanTest(TestCase):
    """Tạo tài khoản cố vấn (và gắn hồ sơ), thông báo lỗi luôn bằng tiếng Việt."""

    def setUp(self):
        self.pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_cvtk', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.client.force_login(self.pdt)
        self.url = reverse('accounts:tai_khoan_tao')

    def _tao(self, ten='cv_moi_tk', mat_khau=MAT_KHAU_HOP_LE, vai_tro=VaiTro.CO_VAN_HOC_TAP):
        return self.client.post(self.url, {'ten_dang_nhap': ten, 'vai_tro': vai_tro, 'mat_khau': mat_khau, 'is_active': 'on'})

    def _loi(self, response, truong):
        self.assertEqual(response.status_code, 200)
        return [str(m) for m in response.context['form'].errors[truong]]

    def test_tao_tai_khoan_co_van_thanh_cong_va_gan_duoc_ho_so(self):
        response = self._tao()
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        tai_khoan = TaiKhoan.objects.get(ten_dang_nhap='cv_moi_tk')
        self.assertEqual(tai_khoan.vai_tro, VaiTro.CO_VAN_HOC_TAP)
        self.assertTrue(tai_khoan.check_password(MAT_KHAU_HOP_LE))
        response = self.client.post(reverse('people:co_van_tao'), {
            'ma_co_van': 'CV_MOI_TK', 'ho_ten': 'Cố vấn mới', 'email': 'cv@test.local',
            'so_dien_thoai': '0912345678', 'ma_tai_khoan': tai_khoan.pk,
        })
        self.assertRedirects(response, reverse('people:co_van_danh_sach'))
        self.assertTrue(CoVanHocTap.objects.filter(pk='CV_MOI_TK', ma_tai_khoan=tai_khoan).exists())

    def test_ten_dang_nhap_co_dau_va_khoang_trang_van_tao_duoc(self):
        self.assertRedirects(self._tao(ten='Cố vấn 1'), reverse('accounts:tai_khoan_danh_sach'))

    def test_mat_khau_yeu_bao_loi_bang_tieng_viet(self):
        loi = self._loi(self._tao(mat_khau='123456'), 'mat_khau')
        self.assertIn('Mật khẩu quá ngắn, cần có ít nhất 8 ký tự.', loi)
        self.assertIn('Mật khẩu này quá phổ biến, hãy chọn mật khẩu khó đoán hơn.', loi)
        self.assertIn('Mật khẩu không được chỉ gồm chữ số.', loi)
        for thong_diep in loi:
            self.assertNotIn('This password', thong_diep)
            self.assertNotIn('must contain', thong_diep)
        self.assertFalse(TaiKhoan.objects.filter(ten_dang_nhap='cv_moi_tk').exists())

    def test_ten_dang_nhap_trung_bao_loi_bang_tieng_viet(self):
        self._tao()
        loi = self._loi(self._tao(), 'ten_dang_nhap')
        self.assertEqual(loi, ['Tên đăng nhập này đã tồn tại.'])

    def test_cap_nhat_tai_khoan_trung_ten_cung_bao_tieng_viet(self):
        self._tao()
        khac = TaiKhoan.objects.create_user(ten_dang_nhap='tk_khac_cv', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
        response = self.client.post(reverse('accounts:tai_khoan_sua', args=[khac.pk]), {
            'ten_dang_nhap': 'cv_moi_tk', 'vai_tro': VaiTro.SINH_VIEN, 'is_active': 'on',
        })
        self.assertEqual([str(m) for m in response.context['form'].errors['ten_dang_nhap']], ['Tên đăng nhập này đã tồn tại.'])

    def test_doi_mat_khau_bao_loi_yeu_bang_tieng_viet(self):
        tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap='cv_doi_mk', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        self.client.force_login(tai_khoan)
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': MAT_KHAU_HOP_LE, 'mat_khau_moi': '12345678', 'mat_khau_moi_xac_nhan': '12345678',
        })
        noi_dung = response.content.decode()
        self.assertIn('Mật khẩu này quá phổ biến', noi_dung)
        self.assertNotIn('This password', noi_dung)


class PhanQuyenTest(TestCase):
    def setUp(self):
        self.sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv002', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt001', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )

    def test_chua_dang_nhap_bi_chuyen_huong_toi_trang_dang_nhap(self):
        response = self.client.get(reverse('accounts:tai_khoan_danh_sach'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:dang_nhap'), response.url)

    def test_sinh_vien_khong_duoc_vao_danh_sach_tai_khoan(self):
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('accounts:tai_khoan_danh_sach'))
        self.assertEqual(response.status_code, 403)

    def test_phong_dao_tao_vao_duoc_danh_sach_tai_khoan(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(reverse('accounts:tai_khoan_danh_sach'))
        self.assertEqual(response.status_code, 200)


class QuanLyTaiKhoanTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt002', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_tai_khoan_moi(self):
        response = self.client.post(reverse('accounts:tai_khoan_tao'), {
            'ten_dang_nhap': 'gv001',
            'vai_tro': VaiTro.GIANG_VIEN,
            'is_active': 'on',
            'mat_khau': MAT_KHAU_HOP_LE,
        })
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        self.assertTrue(
            TaiKhoan.objects.filter(ten_dang_nhap='gv001', vai_tro=VaiTro.GIANG_VIEN).exists()
        )

    def test_khoa_tai_khoan(self):
        tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='gv002', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE
        )
        response = self.client.post(reverse('accounts:tai_khoan_khoa', args=[tai_khoan.pk]))
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        tai_khoan.refresh_from_db()
        self.assertFalse(tai_khoan.is_active)

    def test_khong_the_tu_khoa_tai_khoan_dang_dang_nhap(self):
        response = self.client.post(reverse('accounts:tai_khoan_khoa', args=[self.phong_dao_tao.pk]))
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        self.phong_dao_tao.refresh_from_db()
        self.assertTrue(self.phong_dao_tao.is_active)

    def test_khong_the_doi_vai_tro_tai_khoan_da_gan_ho_so_sinh_vien(self):
        tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv_da_gan', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_cv = TaiKhoan.objects.create_user(
            ten_dang_nhap='cv_phu', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_PHU', ho_ten='Cố vấn', email='cv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        lop = LopHanhChinh.objects.create(ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=nganh, ma_co_van=co_van)
        SinhVien.objects.create(
            ma_sinh_vien='SV_DA_GAN', ho_ten='Sinh viên đã gắn', ngay_sinh='2004-01-01',
            email='sv@test.local', so_dien_thoai='0900000000', ma_lop=lop, ma_tai_khoan=tai_khoan,
        )

        response = self.client.post(reverse('accounts:tai_khoan_sua', args=[tai_khoan.pk]), {
            'ten_dang_nhap': tai_khoan.ten_dang_nhap,
            'vai_tro': VaiTro.GIANG_VIEN,
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 200)
        tai_khoan.refresh_from_db()
        self.assertEqual(tai_khoan.vai_tro, VaiTro.SINH_VIEN)

    def test_van_cap_nhat_duoc_cac_truong_khac_khi_giu_nguyen_vai_tro(self):
        tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='gv_giu_vai_tro', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE
        )
        GiangVien.objects.create(
            ma_giang_vien='GV_GIU', ho_ten='Giảng viên giữ vai trò', email='gv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tai_khoan,
        )

        response = self.client.post(reverse('accounts:tai_khoan_sua', args=[tai_khoan.pk]), {
            'ten_dang_nhap': 'gv_giu_vai_tro_moi',
            'vai_tro': VaiTro.GIANG_VIEN,
            'is_active': 'on',
        })
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        tai_khoan.refresh_from_db()
        self.assertEqual(tai_khoan.ten_dang_nhap, 'gv_giu_vai_tro_moi')

    def test_doi_vai_tro_binh_thuong_khi_chua_gan_ho_so(self):
        tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='tk_chua_gan', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        response = self.client.post(reverse('accounts:tai_khoan_sua', args=[tai_khoan.pk]), {
            'ten_dang_nhap': tai_khoan.ten_dang_nhap,
            'vai_tro': VaiTro.GIANG_VIEN,
            'is_active': 'on',
        })
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        tai_khoan.refresh_from_db()
        self.assertEqual(tai_khoan.vai_tro, VaiTro.GIANG_VIEN)


class DoiMatKhauTest(TestCase):
    def setUp(self):
        self.tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='dmk_sv', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.client.force_login(self.tai_khoan)

    def test_doi_mat_khau_dung(self):
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': MAT_KHAU_HOP_LE,
            'mat_khau_moi': 'MatKhauMoi456',
            'mat_khau_moi_xac_nhan': 'MatKhauMoi456',
        })
        self.assertRedirects(response, reverse('accounts:trang_chu'))
        self.tai_khoan.refresh_from_db()
        self.assertTrue(self.tai_khoan.check_password('MatKhauMoi456'))
        self.assertFalse(self.tai_khoan.phai_doi_mat_khau)
        # update_session_auth_hash phải giữ nguyên phiên đăng nhập sau khi đổi mật khẩu.
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertEqual(response.status_code, 200)

    def test_doi_mat_khau_sai_mat_khau_cu(self):
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': 'mat_khau_sai',
            'mat_khau_moi': 'MatKhauMoi456',
            'mat_khau_moi_xac_nhan': 'MatKhauMoi456',
        })
        self.assertEqual(response.status_code, 200)
        self.tai_khoan.refresh_from_db()
        self.assertTrue(self.tai_khoan.check_password(MAT_KHAU_HOP_LE))

    def test_doi_mat_khau_xac_nhan_khong_khop(self):
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': MAT_KHAU_HOP_LE,
            'mat_khau_moi': 'MatKhauMoi456',
            'mat_khau_moi_xac_nhan': 'KhacHoanToan789',
        })
        self.assertEqual(response.status_code, 200)
        self.tai_khoan.refresh_from_db()
        self.assertTrue(self.tai_khoan.check_password(MAT_KHAU_HOP_LE))

    def test_khong_the_dat_mat_khau_moi_qua_ngan(self):
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': MAT_KHAU_HOP_LE,
            'mat_khau_moi': '123',
            'mat_khau_moi_xac_nhan': '123',
        })
        self.assertEqual(response.status_code, 200)
        self.tai_khoan.refresh_from_db()
        self.assertTrue(self.tai_khoan.check_password(MAT_KHAU_HOP_LE))


class DatLaiMatKhauTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='dlmk_pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )
        self.sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='dlmk_sv', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.client.force_login(self.phong_dao_tao)

    def test_sinh_vien_khong_duoc_dat_lai_mat_khau(self):
        self.client.force_login(self.sinh_vien)
        response = self.client.post(reverse('accounts:tai_khoan_dat_lai_mat_khau', args=[self.phong_dao_tao.pk]))
        self.assertEqual(response.status_code, 403)

    def test_khong_the_tu_dat_lai_mat_khau_chinh_minh(self):
        response = self.client.post(reverse('accounts:tai_khoan_dat_lai_mat_khau', args=[self.phong_dao_tao.pk]))
        self.assertRedirects(response, reverse('accounts:tai_khoan_danh_sach'))
        self.phong_dao_tao.refresh_from_db()
        self.assertFalse(self.phong_dao_tao.phai_doi_mat_khau)

    def test_dat_lai_mat_khau_hien_mot_lan_va_bat_co_buoc_doi(self):
        response = self.client.post(reverse('accounts:tai_khoan_dat_lai_mat_khau', args=[self.sinh_vien.pk]))
        self.assertEqual(response.status_code, 200)
        mat_khau_tam = response.context['mat_khau_tam']
        self.assertContains(response, mat_khau_tam)
        self.sinh_vien.refresh_from_db()
        self.assertTrue(self.sinh_vien.phai_doi_mat_khau)
        self.assertTrue(self.sinh_vien.check_password(mat_khau_tam))
        self.assertFalse(self.sinh_vien.check_password(MAT_KHAU_HOP_LE))

    def test_tai_khoan_bi_buoc_doi_mat_khau_khong_vao_duoc_trang_khac(self):
        self.sinh_vien.phai_doi_mat_khau = True
        self.sinh_vien.save(update_fields=['phai_doi_mat_khau'])
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertRedirects(response, reverse('accounts:doi_mat_khau'))

    def test_tai_khoan_bi_buoc_doi_mat_khau_van_vao_duoc_trang_doi_mat_khau_va_dang_xuat(self):
        self.sinh_vien.phai_doi_mat_khau = True
        self.sinh_vien.save(update_fields=['phai_doi_mat_khau'])
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('accounts:doi_mat_khau'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('accounts:dang_xuat'))
        self.assertRedirects(response, reverse('accounts:dang_nhap'))

    def test_sau_khi_tu_doi_mat_khau_het_bi_chan(self):
        self.sinh_vien.phai_doi_mat_khau = True
        self.sinh_vien.save(update_fields=['phai_doi_mat_khau'])
        self.client.force_login(self.sinh_vien)
        response = self.client.post(reverse('accounts:doi_mat_khau'), {
            'mat_khau_cu': MAT_KHAU_HOP_LE,
            'mat_khau_moi': 'MatKhauMoi456',
            'mat_khau_moi_xac_nhan': 'MatKhauMoi456',
        })
        self.assertRedirects(response, reverse('accounts:trang_chu'))
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertEqual(response.status_code, 200)


class ThongTinCaNhanTest(TestCase):
    def setUp(self):
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        self.tk_sv = TaiKhoan.objects.create_user(
            ten_dang_nhap='ttcn_sv', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        tk_cv = TaiKhoan.objects.create_user(
            ten_dang_nhap='ttcn_cv', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='TTCN_CV', ho_ten='Cố vấn TTCN', email='cv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        self.lop = LopHanhChinh.objects.create(
            ma_lop='TTCN1', ten_lop='TTCN K1', ma_nganh=self.nganh, ma_co_van=self.co_van,
        )
        self.sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='TTCN_SV', ho_ten='Sinh viên TTCN', ngay_sinh='2004-01-01',
            email='sv_cu@test.local', so_dien_thoai='0900000001', ma_lop=self.lop, ma_tai_khoan=self.tk_sv,
        )
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='ttcn_pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )

    def test_sinh_vien_xem_duoc_ho_ten_ma_va_form_lien_he(self):
        self.client.force_login(self.tk_sv)
        response = self.client.get(reverse('accounts:thong_tin_ca_nhan'))
        self.assertContains(response, 'Sinh viên TTCN')
        self.assertContains(response, 'TTCN_SV')
        self.assertContains(response, 'sv_cu@test.local')

    def test_phong_dao_tao_khong_thay_form_lien_he(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(reverse('accounts:thong_tin_ca_nhan'))
        self.assertContains(response, 'ttcn_pdt')
        self.assertNotContains(response, 'Cập nhật thông tin liên hệ')

    def test_cap_nhat_thong_tin_lien_he_hop_le(self):
        self.client.force_login(self.tk_sv)
        response = self.client.post(reverse('accounts:thong_tin_ca_nhan'), {
            'email': 'sv_moi@test.local', 'so_dien_thoai': '0912345678',
        })
        self.assertRedirects(response, reverse('accounts:thong_tin_ca_nhan'))
        self.sinh_vien.refresh_from_db()
        self.assertEqual(self.sinh_vien.email, 'sv_moi@test.local')
        self.assertEqual(self.sinh_vien.so_dien_thoai, '0912345678')

    def test_khong_cap_nhat_duoc_email_sai_dinh_dang(self):
        self.client.force_login(self.tk_sv)
        response = self.client.post(reverse('accounts:thong_tin_ca_nhan'), {
            'email': 'khong-phai-email', 'so_dien_thoai': '0912345678',
        })
        self.assertEqual(response.status_code, 200)
        self.sinh_vien.refresh_from_db()
        self.assertEqual(self.sinh_vien.email, 'sv_cu@test.local')

    def test_khong_cap_nhat_duoc_so_dien_thoai_sai_dinh_dang(self):
        self.client.force_login(self.tk_sv)
        response = self.client.post(reverse('accounts:thong_tin_ca_nhan'), {
            'email': 'sv_moi@test.local', 'so_dien_thoai': '12345',
        })
        self.assertEqual(response.status_code, 200)
        self.sinh_vien.refresh_from_db()
        self.assertEqual(self.sinh_vien.so_dien_thoai, '0900000001')


def tep_pdf_test(ten='qc.pdf'):
    return SimpleUploadedFile(ten, b'%PDF-1.4 noi dung gia lap', content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA_ROOT_TEST)
class PhanQuyenToanHeThongTest(TestCase):
    """Rà soát phân quyền toàn hệ thống: mỗi URL chính thử với cả 4 vai trò và
    người chưa đăng nhập (bước 11). Dữ liệu dựng đủ hai bộ (của "tôi" và của
    "người khác") để phát hiện lỗ hổng truy cập chéo đối tượng, không chỉ chéo vai trò.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT_TEST, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )
        cls.giang_vien_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_gv', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE
        )
        cls.sinh_vien_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_sv', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        cls.co_van_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_cv', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )

        cls.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        cls.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV01', ho_ten='Cố vấn A', email='cv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=cls.co_van_tk,
        )
        cls.lop_hanh_chinh = LopHanhChinh.objects.create(
            ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=cls.nganh, ma_co_van=cls.co_van,
        )
        cls.sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='SV001', ho_ten='Sinh viên A', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=cls.lop_hanh_chinh, ma_tai_khoan=cls.sinh_vien_tk,
        )
        cls.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV01', ho_ten='Giảng viên A', email='gv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=cls.giang_vien_tk,
        )
        cls.hoc_phan_a = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)
        cls.hoc_phan_b = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=cls.hoc_phan_b, ma_hoc_phan_tien_quyet=cls.hoc_phan_a)
        cls.lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=cls.hoc_phan_a, ma_giang_vien=cls.giang_vien,
        )
        LichHoc.objects.create(
            ma_lop_hoc_phan=cls.lop_hoc_phan, thu=2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101',
        )
        cls.dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=cls.sinh_vien, ma_lop_hoc_phan=cls.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=cls.dang_ky, diem_qua_trinh=8, diem_thi=8)
        cls.tai_lieu = TaiLieuQuyChe.objects.create(
            ten_tai_lieu='Quy chế test', duong_dan_file=tep_pdf_test(),
            ngay_tai_len='2025-01-01', ngay_cap_nhat='2025-01-01',
        )

        # Bộ dữ liệu "của người khác" để kiểm tra không truy cập chéo đối tượng.
        cls.giang_vien_khac_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_gv2', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE
        )
        cls.giang_vien_khac = GiangVien.objects.create(
            ma_giang_vien='GV02', ho_ten='Giảng viên B', email='gv2@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=cls.giang_vien_khac_tk,
        )
        cls.nganh_khac = NganhHoc.objects.create(ma_nganh='KTPM', ten_nganh='Kỹ thuật phần mềm')
        cls.co_van_khac_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_cv2', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )
        cls.co_van_khac = CoVanHocTap.objects.create(
            ma_co_van='CV02', ho_ten='Cố vấn B', email='cv2@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=cls.co_van_khac_tk,
        )
        cls.lop_hanh_chinh_khac = LopHanhChinh.objects.create(
            ma_lop='KTPM1', ten_lop='KTPM K1', ma_nganh=cls.nganh_khac, ma_co_van=cls.co_van_khac,
        )
        cls.sinh_vien_khac_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='pq_sv2', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        cls.sinh_vien_khac = SinhVien.objects.create(
            ma_sinh_vien='SV002', ho_ten='Sinh viên B', ngay_sinh='2004-01-01', email='sv2@test.local',
            so_dien_thoai='0900000000', ma_lop=cls.lop_hanh_chinh_khac, ma_tai_khoan=cls.sinh_vien_khac_tk,
        )

    def _tai_khoan_theo_vai_tro(self):
        return {
            VaiTro.PHONG_DAO_TAO: self.phong_dao_tao,
            VaiTro.GIANG_VIEN: self.giang_vien_tk,
            VaiTro.SINH_VIEN: self.sinh_vien_tk,
            VaiTro.CO_VAN_HOC_TAP: self.co_van_tk,
        }

    def _thu_get_voi_moi_vai_tro(self, ten_url, kwargs, vai_tro_hop_le):
        url = reverse(ten_url, kwargs=kwargs or {})
        for vai_tro, tai_khoan in self._tai_khoan_theo_vai_tro().items():
            self.client.force_login(tai_khoan)
            response = self.client.get(url)
            if vai_tro in vai_tro_hop_le:
                self.assertIn(
                    response.status_code, (200, 302),
                    f'{ten_url}: vai trò {vai_tro} phải truy cập được, nhưng trả về {response.status_code}',
                )
            else:
                self.assertEqual(
                    response.status_code, 403,
                    f'{ten_url}: vai trò {vai_tro} phải bị chặn (403), nhưng trả về {response.status_code}',
                )
            self.client.logout()

        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 302,
            f'{ten_url}: người chưa đăng nhập phải bị chuyển hướng, nhưng trả về {response.status_code}',
        )

    def test_ma_tran_phan_quyen_cac_url_chinh(self):
        PDT, GV, SV, CV = (
            VaiTro.PHONG_DAO_TAO, VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP,
        )
        cac_url = [
            ('accounts:trang_chu', {}, (PDT, GV, SV, CV)),
            ('accounts:tai_khoan_danh_sach', {}, (PDT,)),
            ('accounts:tai_khoan_tao', {}, (PDT,)),
            ('accounts:tai_khoan_sua', {'pk': self.sinh_vien_tk.pk}, (PDT,)),
            ('accounts:thong_tin_ca_nhan', {}, (PDT, GV, SV, CV)),
            ('accounts:doi_mat_khau', {}, (PDT, GV, SV, CV)),

            ('people:sinh_vien_danh_sach', {}, (PDT,)),
            ('people:sinh_vien_sua', {'pk': self.sinh_vien.pk}, (PDT,)),
            ('people:giang_vien_danh_sach', {}, (PDT,)),
            ('people:co_van_danh_sach', {}, (PDT,)),

            ('academics:nganh_hoc_danh_sach', {}, (PDT,)),
            ('academics:lop_hanh_chinh_danh_sach', {}, (PDT,)),
            ('academics:hoc_phan_danh_sach', {}, (PDT,)),
            ('academics:dieu_kien_tien_quyet_danh_sach', {}, (PDT,)),
            ('academics:hoc_ky_danh_sach', {}, (PDT,)),
            ('academics:dot_dang_ky_danh_sach', {}, (PDT,)),

            ('classes:lop_hoc_phan_danh_sach', {}, (PDT,)),
            ('classes:lich_hoc_danh_sach', {}, (PDT,)),
            ('classes:lop_phu_trach', {}, (GV,)),
            ('classes:lich_giang_day', {}, (GV,)),

            ('enrollment:lop_dang_mo', {}, (SV,)),
            ('enrollment:thoi_khoa_bieu', {}, (SV,)),
            ('enrollment:lich_su_dang_ky', {}, (SV,)),
            ('enrollment:danh_sach_sinh_vien_lop', {'ma_lop_hoc_phan': self.lop_hoc_phan.pk}, (PDT, GV)),
            ('enrollment:tra_cuu_lich_su', {}, (PDT,)),
            ('enrollment:sinh_vien_phu_trach', {}, (CV,)),

            ('grades:bang_diem_lop', {'ma_lop_hoc_phan': self.lop_hoc_phan.pk}, (GV,)),
            ('grades:bang_diem_lop_phong_dao_tao', {'ma_lop_hoc_phan': self.lop_hoc_phan.pk}, (PDT,)),
            ('grades:bang_diem_sinh_vien', {'ma_sinh_vien': self.sinh_vien.pk}, (PDT, CV, SV)),

            ('regulations:danh_sach', {}, (PDT,)),
            ('regulations:tai_ve', {'pk': self.tai_lieu.pk}, (PDT,)),

            ('reports:si_so_theo_lop', {}, (PDT,)),
            ('reports:hoc_phan_nhieu_dang_ky', {}, (PDT,)),
            ('reports:ket_qua_hoc_tap', {}, (PDT,)),
        ]
        for ten_url, kwargs, vai_tro_hop_le in cac_url:
            with self.subTest(url=ten_url):
                self._thu_get_voi_moi_vai_tro(ten_url, kwargs, vai_tro_hop_le)

    def test_bang_diem_cua_toi_dieu_huong_dung_theo_vai_tro(self):
        # Không bị chặn theo vai trò (chỉ login_required), nhưng luôn điều hướng đi nơi khác.
        for tai_khoan in self._tai_khoan_theo_vai_tro().values():
            self.client.force_login(tai_khoan)
            response = self.client.get(reverse('grades:bang_diem_cua_toi'))
            self.assertEqual(response.status_code, 302)
            self.client.logout()

        response = self.client.get(reverse('grades:bang_diem_cua_toi'))
        self.assertRedirects(response, f"{reverse('accounts:dang_nhap')}?next={reverse('grades:bang_diem_cua_toi')}")

    def test_sinh_vien_khong_xem_duoc_diem_sinh_vien_khac(self):
        self.client.force_login(self.sinh_vien_tk)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien_khac.pk]))
        self.assertEqual(response.status_code, 403)

    def test_giang_vien_khong_nhap_diem_lop_giang_vien_khac(self):
        self.client.force_login(self.giang_vien_khac_tk)
        response = self.client.get(reverse('grades:nhap_diem', args=[self.dang_ky.pk]))
        self.assertEqual(response.status_code, 403)
        # Cũng không xem được bảng điểm lớp của giảng viên khác.
        response = self.client.get(reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_giang_vien_khong_xem_duoc_danh_sach_sinh_vien_lop_giang_vien_khac(self):
        self.client.force_login(self.giang_vien_khac_tk)
        response = self.client.get(
            reverse('enrollment:danh_sach_sinh_vien_lop', args=[self.lop_hoc_phan.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_co_van_khong_xem_duoc_sinh_vien_ngoai_lop_phu_trach(self):
        self.client.force_login(self.co_van_tk)
        # Danh sách phụ trách của co_van_tk chỉ gồm sinh_vien (lớp CNTT1), không có sinh_vien_khac (lớp KTPM1).
        response = self.client.get(reverse('enrollment:sinh_vien_phu_trach'))
        self.assertContains(response, self.sinh_vien.ma_sinh_vien)
        self.assertNotContains(response, self.sinh_vien_khac.ma_sinh_vien)
        # Cũng không xem được bảng điểm của sinh viên ngoài lớp phụ trách.
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien_khac.pk]))
        self.assertEqual(response.status_code, 403)


class NapDuLieuMauTest(TestCase):
    def test_lenh_chay_thanh_cong_va_tao_du_lieu(self):
        call_command('nap_du_lieu_mau', '--force')
        self.assertTrue(SinhVien.objects.filter(pk='SV001').exists())
        self.assertTrue(HocPhan.objects.filter(pk='CNPM').exists())
        self.assertTrue(LopHocPhan.objects.filter(pk='AIUD_2025').exists())
        self.assertEqual(TaiKhoan.objects.filter(vai_tro=VaiTro.PHONG_DAO_TAO).count(), 1)
        self.assertEqual(SinhVien.objects.count(), 5)

    def test_khong_the_chay_lai_lan_hai(self):
        call_command('nap_du_lieu_mau', '--force')
        with self.assertRaises(CommandError):
            call_command('nap_du_lieu_mau', '--force')

    def test_chan_khi_khong_debug_va_khong_co_force(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command('nap_du_lieu_mau')

    def test_du_lieu_mau_dung_voi_vi_du_trong_de_bai(self):
        """SV001 đã đạt CSDL, CTDLGT nên đăng ký được CNPM/AI ứng dụng; SV002 thì không."""
        call_command('nap_du_lieu_mau', '--force')
        sv001 = SinhVien.objects.get(pk='SV001')
        sv002 = SinhVien.objects.get(pk='SV002')
        sv003 = SinhVien.objects.get(pk='SV003')
        sv005 = SinhVien.objects.get(pk='SV005')
        cnpm_2025 = LopHocPhan.objects.get(pk='CNPM_2025')
        aiud_2025 = LopHocPhan.objects.get(pk='AIUD_2025')
        ctdlgt_2025 = LopHocPhan.objects.get(pk='CTDLGT_2025')

        dang_ky_hoc_phan(sv001, cnpm_2025)
        dang_ky_hoc_phan(sv001, aiud_2025)

        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv002, cnpm_2025)
        self.assertIn('tiên quyết', str(ngu_canh.exception))

        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv003, aiud_2025)
        self.assertIn('trùng', str(ngu_canh.exception))

        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv005, ctdlgt_2025)
        self.assertIn('sĩ số', str(ngu_canh.exception))


def _nap_day_du():
    call_command('nap_du_lieu_day_du', '--force', stdout=io.StringIO())


class NapDuLieuDayDuTest(TestCase):
    """Bộ dữ liệu đầy đủ trên CSDL trống. Lệnh chạy khoảng 10-20 giây nên chỉ chạy MỘT lần cho cả lớp
    (setUpTestData); mỗi test chỉ đọc hoặc ghi trong transaction của chính nó rồi được hoàn tác."""

    @classmethod
    def setUpTestData(cls):
        _nap_day_du()

    def test_so_luong_theo_thiet_ke(self):
        self.assertEqual(SinhVien.objects.count(), 90)
        self.assertEqual(GiangVien.objects.count(), 5)
        self.assertEqual(CoVanHocTap.objects.count(), 3)
        self.assertEqual(LopHanhChinh.objects.count(), 3)
        self.assertEqual(HocPhan.objects.count(), 13)
        self.assertEqual(DieuKienTienQuyet.objects.count(), 7)
        self.assertEqual(LopHocPhan.objects.count(), 22)
        self.assertEqual(ChuongTrinhDaoTao.objects.count(), 3)
        self.assertEqual(HocKy.objects.count(), 3)
        self.assertEqual(TaiKhoan.objects.filter(vai_tro=VaiTro.SINH_VIEN).count(), 90)
        self.assertEqual(ThongBao.objects.count(), 10)
        for ma_lop in ('CNTT_K1', 'CNTT_K2', 'ATTT_K1'):
            lop = LopHanhChinh.objects.get(pk=ma_lop)
            self.assertEqual(SinhVien.objects.filter(ma_lop=lop).count(), 30)
            self.assertIsNotNone(lop.chuong_trinh_dao_tao)
        # Mỗi cố vấn phụ trách đúng một lớp.
        self.assertEqual(set(LopHanhChinh.objects.values_list('ma_co_van_id', flat=True)), {'CV001', 'CV002', 'CV003'})
        # Mỗi giảng viên có nhiều lớp học phần.
        for gv in GiangVien.objects.all():
            self.assertGreaterEqual(LopHocPhan.objects.filter(ma_giang_vien=gv).count(), 4)

    def test_ten_sinh_vien_khong_trung_va_dang_nhap_bang_mat_khau_demo(self):
        ho_ten = list(SinhVien.objects.values_list('ho_ten', flat=True))
        self.assertEqual(len(ho_ten), len(set(ho_ten)))
        self.assertTrue(self.client.login(username='sv050', password='MatKhauDemo123'))
        self.assertEqual(self.client.get(reverse('accounts:trang_chu')).status_code, 200)

    def test_ma_sinh_vien_ten_dang_nhap_va_lop(self):
        self.assertTrue(SinhVien.objects.filter(pk='SV090', ma_tai_khoan__ten_dang_nhap='sv090').exists())
        self.assertEqual(SinhVien.objects.get(pk='SV045').ma_lop_id, 'CNTT_K2')
        self.assertEqual(SinhVien.objects.get(pk='SV075').ma_lop_id, 'ATTT_K1')

    def test_dang_ky_ky_dang_mo_dung_tien_quyet_trung_lich_va_si_so(self):
        dang_ky = DangKyHocPhan.objects.filter(
            ma_lop_hoc_phan__nam_hoc='2025-2026', trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        )
        so_theo_sinh_vien = {}
        for ma_sv in dang_ky.values_list('ma_sinh_vien_id', flat=True):
            so_theo_sinh_vien[ma_sv] = so_theo_sinh_vien.get(ma_sv, 0) + 1
        # Phần lớn sinh viên mới đăng ký 3-5 lớp, không ai quá 5 lớp.
        moi = [ma for ma in so_theo_sinh_vien if ma != 'SV003']
        self.assertGreaterEqual(sum(1 for ma in moi if 3 <= so_theo_sinh_vien[ma] <= 5), 60)
        self.assertLessEqual(max(so_theo_sinh_vien.values()), 5)
        for lop in LopHocPhan.objects.all():
            so = DangKyHocPhan.objects.filter(ma_lop_hoc_phan=lop, trang_thai=TrangThaiDangKy.CON_HIEU_LUC).count()
            self.assertLessEqual(so, lop.si_so_toi_da, lop.pk)
        # Lớp nhỏ đã đầy để demo "đủ sĩ số".
        self.assertEqual(DangKyHocPhan.objects.filter(ma_lop_hoc_phan_id='HQTCSDL_2025').count(), 18)
        for dk in dang_ky.select_related('ma_sinh_vien', 'ma_lop_hoc_phan__ma_hoc_phan'):
            self.assertEqual(tim_hoc_phan_tien_quyet_con_thieu(dk.ma_sinh_vien, dk.ma_lop_hoc_phan.ma_hoc_phan), [])
        # Không có hai lớp trùng giờ trong cùng một kỳ của cùng một sinh viên (kiểm tra bằng số liệu thô).
        lich_theo_sinh_vien = {}
        for ma_sv, thu, tiet, so_tiet in LichHoc.objects.filter(
            ma_lop_hoc_phan__dang_ky__trang_thai=TrangThaiDangKy.CON_HIEU_LUC, ma_lop_hoc_phan__nam_hoc='2025-2026',
        ).values_list('ma_lop_hoc_phan__dang_ky__ma_sinh_vien_id', 'thu', 'tiet_bat_dau', 'so_tiet'):
            lich_theo_sinh_vien.setdefault(ma_sv, []).append((thu, tiet, tiet + so_tiet - 1))
        for ma_sv, cac_lich in lich_theo_sinh_vien.items():
            for i, (thu_a, dau_a, cuoi_a) in enumerate(cac_lich):
                for thu_b, dau_b, cuoi_b in cac_lich[i + 1:]:
                    self.assertFalse(thu_a == thu_b and dau_a <= cuoi_b and dau_b <= cuoi_a, ma_sv)

    def test_diem_ky_da_qua(self):
        diem = list(Diem.objects.select_related('ma_dang_ky__ma_lop_hoc_phan'))
        self.assertGreater(len(diem), 300)
        # Chỉ điểm của các lớp kỳ đã qua.
        self.assertFalse(any(d.ma_dang_ky.ma_lop_hoc_phan.nam_hoc == '2025-2026' for d in diem))
        chua_dat = sum(
            1 for d in diem if d.tinh_diem_tong_ket() is not None and d.tinh_diem_tong_ket() < settings.DIEM_DAT_TOI_THIEU
        )
        self.assertGreaterEqual(chua_dat, 15)
        self.assertLessEqual(chua_dat / len(diem), 0.20)
        chua_cong_bo = sum(1 for d in diem if not d.da_cong_bo)
        self.assertGreater(chua_cong_bo, 5)
        self.assertLess(chua_cong_bo / len(diem), 0.20)
        for d in diem:
            self.assertTrue(0 <= d.diem_qua_trinh <= 10 and 0 <= d.diem_thi <= 10)

    def test_co_sinh_vien_bi_canh_bao_hoc_vu_va_moi_co_van_thay_nhieu_hon_mot(self):
        do, vang = [], []
        for sv in SinhVien.objects.all():
            hoc_ky = hoc_ky_gan_nhat_co_du_diem(sv, chi_diem_da_cong_bo=True)
            if hoc_ky is None:
                continue
            ket_qua = canh_bao_hoc_vu(sv, hoc_ky[0], hoc_ky[1], chi_diem_da_cong_bo=True)
            if ket_qua['canh_bao']:
                (do if len(ket_qua['ly_do']) == 2 else vang).append(sv.pk)
        self.assertEqual(sorted(do), ['SV010', 'SV036', 'SV052', 'SV066'])
        self.assertEqual(sorted(vang), ['SV018', 'SV025', 'SV045', 'SV080'])
        lop_cua = {sv.pk: sv.ma_lop.ma_co_van_id for sv in SinhVien.objects.filter(pk__in=do + vang).select_related('ma_lop')}
        for ma_co_van, so_toi_thieu in (('CV001', 3), ('CV002', 3), ('CV003', 2)):
            self.client.force_login(TaiKhoan.objects.get(ho_so_co_van__pk=ma_co_van))
            response = self.client.get(reverse('grades:canh_bao_co_van'))
            self.assertEqual(response.status_code, 200)
            self.assertGreaterEqual(sum(1 for ma in lop_cua.values() if ma == ma_co_van), so_toi_thieu)
            for ma_sv, ma_cv_cua_sv in lop_cua.items():
                if ma_cv_cua_sv == ma_co_van:
                    self.assertContains(response, ma_sv)
                else:
                    self.assertNotContains(response, ma_sv)

    def test_co_van_chi_thay_sinh_vien_lop_minh(self):
        self.client.force_login(TaiKhoan.objects.get(ho_so_co_van__pk='CV002'))
        response = self.client.get(reverse('enrollment:sinh_vien_phu_trach'))
        self.assertContains(response, 'SV031')
        self.assertNotContains(response, 'SV030')
        self.assertNotContains(response, 'SV061')

    def test_diem_chua_cong_bo_hien_dang_cho_cong_bo_cho_sinh_vien(self):
        diem = Diem.objects.filter(da_cong_bo=False).select_related('ma_dang_ky__ma_sinh_vien__ma_tai_khoan').last()
        self.client.force_login(diem.ma_dang_ky.ma_sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_cua_toi'), follow=True)
        self.assertContains(response, 'Đang chờ công bố')

    def test_diem_danh_lich_thi_va_thong_bao(self):
        lop_mo = LopHocPhan.objects.filter(nam_hoc='2025-2026')
        self.assertEqual(lop_mo.count(), 13)
        hoc_ky = HocKy.objects.get(hoc_ky=1, nam_hoc='2025-2026')
        for lop in lop_mo.filter(dang_ky__isnull=False).distinct():
            so_buoi = DiemDanh.objects.filter(lop_hoc_phan=lop).values('ngay_diem_danh').distinct().count()
            self.assertEqual(so_buoi, 4, lop.pk)
        for ngay in DiemDanh.objects.values_list('ngay_diem_danh', flat=True).distinct():
            self.assertTrue(hoc_ky.ngay_bat_dau <= ngay < timezone.localdate(), ngay)
        self.assertEqual(LichThi.objects.count(), 10)
        self.assertFalse(LichThi.objects.filter(lop_hoc_phan_id__in=['CNPM_2025', 'AIUD_2025', 'CNPM_2025_2']).exists())
        for lich in LichThi.objects.all():
            self.assertTrue(hoc_ky.ngay_bat_dau < lich.ngay_thi <= hoc_ky.ngay_ket_thuc)
        self.assertEqual(set(ThongBao.objects.values_list('doi_tuong', flat=True)), {
            DoiTuongThongBao.TAT_CA, DoiTuongThongBao.SINH_VIEN, DoiTuongThongBao.GIANG_VIEN,
            DoiTuongThongBao.LOP_HOC_PHAN, DoiTuongThongBao.LOP_HANH_CHINH,
        })
        # Số thông báo chưa đọc khác nhau giữa các sinh viên (không phải ai cũng cùng một số).
        so_chua_doc = {so_luong_chua_doc(sv.ma_tai_khoan) for sv in SinhVien.objects.select_related('ma_tai_khoan')}
        self.assertGreaterEqual(len(so_chua_doc), 3)

    def test_bon_ca_loi_dang_ky_goc_van_dung(self):
        sv001, sv002, sv003, sv005 = (SinhVien.objects.get(pk=f'SV00{i}') for i in (1, 2, 3, 5))
        cnpm_2025 = LopHocPhan.objects.get(pk='CNPM_2025')
        aiud_2025 = LopHocPhan.objects.get(pk='AIUD_2025')
        ctdlgt_2025 = LopHocPhan.objects.get(pk='CTDLGT_2025')
        dang_ky_hoc_phan(sv001, cnpm_2025)
        dang_ky_hoc_phan(sv001, aiud_2025)
        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv002, cnpm_2025)
        self.assertIn('tiên quyết', str(ngu_canh.exception))
        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv003, aiud_2025)
        self.assertIn('trùng', str(ngu_canh.exception))
        with self.assertRaises(LoiDangKyHocPhan) as ngu_canh:
            dang_ky_hoc_phan(sv005, ctdlgt_2025)
        self.assertIn('sĩ số', str(ngu_canh.exception))

    def test_trang_chinh_cua_bon_vai_tro_tra_ve_200(self):
        trang_theo_vai_tro = {
            'pdt_demo': [
                'accounts:trang_chu', 'people:sinh_vien_danh_sach', 'classes:lop_hoc_phan_danh_sach',
                'classes:lich_thi_danh_sach', 'grades:canh_bao_phong_dao_tao', 'thong_bao:danh_sach',
            ],
            'gv003': ['accounts:trang_chu', 'classes:lop_phu_trach', 'classes:lich_giang_day', 'thong_bao:danh_sach'],
            'cv003': [
                'accounts:trang_chu', 'enrollment:sinh_vien_phu_trach', 'grades:canh_bao_co_van', 'thong_bao:danh_sach',
            ],
            'sv020': [
                'accounts:trang_chu', 'enrollment:lop_dang_mo', 'enrollment:thoi_khoa_bieu', 'enrollment:lich_su_dang_ky',
                'enrollment:lich_thi', 'grades:bang_diem_cua_toi', 'tien_do_hoc_tap:cua_toi', 'diem_danh:lich_su_cua_toi',
                'thong_bao:danh_sach',
            ],
        }
        for ten_dang_nhap, cac_trang in trang_theo_vai_tro.items():
            self.client.force_login(TaiKhoan.objects.get(ten_dang_nhap=ten_dang_nhap))
            for ten_trang in cac_trang:
                with self.subTest(tai_khoan=ten_dang_nhap, trang=ten_trang):
                    self.assertEqual(self.client.get(reverse(ten_trang), follow=True).status_code, 200)

    def test_chan_chay_lai_lan_hai_va_khong_thay_doi_du_lieu(self):
        so_sinh_vien, so_dang_ky = SinhVien.objects.count(), DangKyHocPhan.objects.count()
        with self.assertRaises(CommandError):
            _nap_day_du()
        self.assertEqual(SinhVien.objects.count(), so_sinh_vien)
        self.assertEqual(DangKyHocPhan.objects.count(), so_dang_ky)


class NapDuLieuDayDuChayRiengTest(TestCase):
    def test_chay_sau_nap_du_lieu_mau_chi_bo_sung_khong_trung(self):
        call_command('nap_du_lieu_mau', '--force', stdout=io.StringIO())
        self.assertEqual(SinhVien.objects.count(), 5)
        _nap_day_du()
        self.assertEqual(SinhVien.objects.count(), 90)
        self.assertEqual(NganhHoc.objects.count(), 2)
        self.assertEqual(GiangVien.objects.count(), 5)
        self.assertEqual(TaiKhoan.objects.filter(vai_tro=VaiTro.PHONG_DAO_TAO).count(), 1)
        # Sinh viên gốc không bị sinh thêm dữ liệu ngẫu nhiên.
        self.assertEqual(DangKyHocPhan.objects.filter(ma_sinh_vien_id__in=['SV002', 'SV004', 'SV005']).count(), 0)
        self.assertEqual(DangKyHocPhan.objects.filter(ma_sinh_vien_id='SV001').count(), 2)
        self.assertEqual(DangKyHocPhan.objects.filter(ma_sinh_vien_id='SV003').count(), 2)

    def test_chay_khi_csdl_da_co_hoc_ky_cu_khong_con_dot_dang_ky_va_ky_het_han(self):
        """Tình huống CSDL thật: người dùng đã tự tạo HK1 2024-2025, đã xóa đợt đăng ký, và HK1 2025-2026
        đã kết thúc. Lệnh phải giữ học kỳ tự tạo, mở lại một đợt đăng ký và vẫn đăng ký được cho sinh viên."""
        call_command('nap_du_lieu_mau', '--force', stdout=io.StringIO())
        DotDangKy.objects.all().delete()
        HocKy.objects.filter(nam_hoc='2025-2026').update(
            ngay_bat_dau=timezone.localdate() - timedelta(days=400), ngay_ket_thuc=timezone.localdate() - timedelta(days=300),
        )
        HocKy.objects.create(hoc_ky=1, nam_hoc='2024-2025', ngay_bat_dau='2024-09-01', ngay_ket_thuc='2024-12-31')
        _nap_day_du()
        self.assertEqual(str(HocKy.objects.get(hoc_ky=1, nam_hoc='2024-2025').ngay_bat_dau), '2024-09-01')
        self.assertEqual(HocKy.objects.count(), 3)
        self.assertEqual(DotDangKy.objects.count(), 1)
        self.assertGreater(
            DangKyHocPhan.objects.filter(ma_lop_hoc_phan__nam_hoc='2025-2026').count(), 250,
        )

    def test_chan_khi_khong_debug_va_khong_co_force(self):
        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command('nap_du_lieu_day_du', stdout=io.StringIO())
        self.assertEqual(SinhVien.objects.count(), 0)

    def test_loi_giua_chung_thi_hoan_tac_toan_bo(self):
        with mock.patch(
            'accounts.management.commands.nap_du_lieu_day_du.Command._tao_thong_bao', side_effect=RuntimeError('lỗi giả'),
        ):
            with self.assertRaises(RuntimeError):
                _nap_day_du()
        for mo_hinh in (SinhVien, TaiKhoan, DangKyHocPhan, Diem, NganhHoc, HocPhan, LopHocPhan, HocKy):
            self.assertEqual(mo_hinh.objects.count(), 0, mo_hinh.__name__)
        # Sau khi lỗi, chạy lại bình thường vẫn được.
        _nap_day_du()
        self.assertEqual(SinhVien.objects.count(), 90)


class LayoutSinhVienTest(TestCase):
    """Layout riêng của vai trò Sinh viên (banner, menu, breadcrumb, footer) — chỉ đổi giao
    diện, xem templates/sinh_vien/ và docs/thiet_ke_giao_dien.md."""

    def setUp(self):
        self.tk_sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv_layout', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.tk_pdt = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_layout', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )
        self.client.force_login(self.tk_sinh_vien)

    def _khoi(self, response, mau):
        khop = re.search(mau, response.content.decode(), re.S)
        self.assertIsNotNone(khop, f'Không thấy khối {mau!r} trong trang.')
        return khop.group(0)

    def _khoi_menu(self, response):
        return self._khoi(response, r'<nav class="sv-menu".*?</nav>')

    def _khoi_breadcrumb(self, response):
        return self._khoi(response, r'<nav class="sv-breadcrumb".*?</nav>')

    def _tao_ho_so_sinh_vien(self):
        nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
        tk_cv = TaiKhoan.objects.create_user(
            ten_dang_nhap='cv_layout', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_LAYOUT', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000',
            ma_tai_khoan=tk_cv,
        )
        lop = LopHanhChinh.objects.create(ma_lop='CNTT_LAYOUT', ten_lop='Lớp layout', ma_nganh=nganh, ma_co_van=co_van)
        return SinhVien.objects.create(
            ma_sinh_vien='SV_LAYOUT', ho_ten='Sinh viên layout', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=lop, ma_tai_khoan=self.tk_sinh_vien,
        )

    def test_banner_co_logo_ten_truong_va_ten_he_thong(self):
        banner = self._khoi(self.client.get(reverse('accounts:trang_chu')), r'<header class="sv-banner">.*?</header>')
        self.assertIn('logo__icon', banner)
        self.assertIn(settings.TEN_TRUONG, banner)
        self.assertIn(settings.TEN_HE_THONG, banner)

    def test_menu_chi_chua_cac_trang_sinh_vien_da_co_that(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        ten_url = set()
        for duong_dan in re.findall(r'<a [^>]*href="([^"]+)"', self._khoi_menu(response)):
            khop = resolve(duong_dan)
            ten_url.add(f'{khop.app_name}:{khop.url_name}')
        self.assertEqual(ten_url, {
            'accounts:trang_chu',
            'enrollment:lop_dang_mo', 'enrollment:thoi_khoa_bieu', 'enrollment:lich_su_dang_ky',
            'tien_do_hoc_tap:cua_toi', 'grades:bang_diem_cua_toi', 'enrollment:lich_thi', 'diem_danh:lich_su_cua_toi',
            'tu_van_dang_ky:trang_tu_van', 'tom_tat_ket_qua:toi', 'hoi_dap_quy_che:trang_chat',
        })

    def test_menu_co_bon_muc_chinh_dung_ten(self):
        khoi = self._khoi_menu(self.client.get(reverse('accounts:trang_chu')))
        for nhan in ('Trang chủ', 'Đăng ký học phần', 'Học tập', 'Trợ lý AI'):
            self.assertIn(f'<span>{nhan}</span>', khoi)
        self.assertEqual(khoi.count('sv-nhom__nut'), 3)

    def test_trang_chu_sang_muc_trang_chu_va_khong_sang_nhom_nao(self):
        khoi = self._khoi_menu(self.client.get(reverse('accounts:trang_chu')))
        self.assertIn(f'sv-menu__muc sv-menu__muc--chon" href="{reverse("accounts:trang_chu")}"', khoi)
        self.assertEqual(khoi.count('sv-nhom--chon'), 0)

    def test_thoi_khoa_bieu_sang_dung_nhom_va_muc(self):
        khoi = self._khoi_menu(self.client.get(reverse('enrollment:thoi_khoa_bieu')))
        self.assertEqual(khoi.count('sv-nhom--chon'), 1)
        self.assertIn(f'sv-nhom__muc sv-nhom__muc--chon" href="{reverse("enrollment:thoi_khoa_bieu")}"', khoi)

    def test_lich_thi_thuoc_nhom_hoc_tap_khong_phai_nhom_dang_ky(self):
        khoi = self._khoi_menu(self.client.get(reverse('enrollment:lich_thi')))
        self.assertEqual(khoi.count('sv-nhom--chon'), 1)
        self.assertIn(f'sv-nhom__muc sv-nhom__muc--chon" href="{reverse("enrollment:lich_thi")}"', khoi)
        dau_nhom_dang_ky = re.search(r'<div class="sv-nhom[^"]*">\s*<button[^>]*>.*?Đăng ký học phần</span>', khoi, re.S)
        self.assertNotIn('sv-nhom--chon', dau_nhom_dang_ky.group(0))

    def test_bang_diem_sang_sau_khi_chuyen_huong(self):
        # Trước đây tab "Bảng điểm" không bao giờ sáng vì view redirect sang bang_diem_sinh_vien.
        self._tao_ho_so_sinh_vien()
        response = self.client.get(reverse('grades:bang_diem_cua_toi'), follow=True)
        self.assertEqual(response.status_code, 200)
        khoi = self._khoi_menu(response)
        self.assertEqual(khoi.count('sv-nhom--chon'), 1)
        self.assertIn(f'sv-nhom__muc sv-nhom__muc--chon" href="{reverse("grades:bang_diem_cua_toi")}"', khoi)

    def test_tro_ly_ai_sang_dung_muc(self):
        khoi = self._khoi_menu(self.client.get(reverse('hoi_dap_quy_che:trang_chat')))
        self.assertEqual(khoi.count('sv-nhom--chon'), 1)
        self.assertIn(f'sv-nhom__muc sv-nhom__muc--chon" href="{reverse("hoi_dap_quy_che:trang_chat")}"', khoi)

    def test_breadcrumb_trang_chu_chi_co_chu_trang_chu(self):
        khoi = self._khoi_breadcrumb(self.client.get(reverse('accounts:trang_chu')))
        self.assertIn('aria-current="page">Trang chủ</span>', khoi)
        self.assertNotIn('sv-breadcrumb__buoc', khoi)

    def test_breadcrumb_trang_con_co_dang_trang_chu_va_ten_trang(self):
        khoi = self._khoi_breadcrumb(self.client.get(reverse('enrollment:thoi_khoa_bieu')))
        self.assertIn(f'<a href="{reverse("accounts:trang_chu")}">Trang chủ</a>', khoi)
        self.assertIn('aria-current="page">Thời khóa biểu</span>', khoi)

    def test_breadcrumb_trang_khong_nam_trong_menu(self):
        khoi = self._khoi_breadcrumb(self.client.get(reverse('accounts:doi_mat_khau')))
        self.assertIn('aria-current="page">Đổi mật khẩu</span>', khoi)
        khoi = self._khoi_breadcrumb(self.client.get(reverse('accounts:thong_tin_ca_nhan')))
        self.assertIn('aria-current="page">Thông tin cá nhân</span>', khoi)

    def test_breadcrumb_chi_tiet_thong_bao_co_ba_cap(self):
        thong_bao = ThongBao.objects.create(
            tieu_de='Nghỉ lễ', noi_dung='Nội dung.', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        khoi = self._khoi_breadcrumb(self.client.get(reverse('thong_bao:chi_tiet', args=[thong_bao.pk])))
        self.assertIn(f'href="{reverse("thong_bao:danh_sach")}">Thông báo</a>', khoi)
        self.assertIn('aria-current="page">Chi tiết</span>', khoi)

    def test_chip_thong_bao_dung_so_chua_doc_that(self):
        for so in range(3):
            ThongBao.objects.create(
                tieu_de=f'Thông báo {so}', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
            )
        # Thông báo dành cho vai trò khác không được tính vào số chưa đọc của Sinh viên.
        ThongBao.objects.create(
            tieu_de='Chỉ giảng viên', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.GIANG_VIEN,
        )
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(response, '<span class="chip-thong-bao">3</span>')
        self.assertContains(response, f'href="{reverse("thong_bao:danh_sach")}" aria-label="Thông báo, 3 chưa đọc"')

    def test_chip_thong_bao_giam_sau_khi_doc_va_an_khi_bang_khong(self):
        thong_bao = ThongBao.objects.create(
            tieu_de='Một thông báo', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        self.assertContains(self.client.get(reverse('accounts:trang_chu')), '<span class="chip-thong-bao">1</span>')
        self.client.get(reverse('thong_bao:chi_tiet', args=[thong_bao.pk]))
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertNotContains(response, '<span class="chip-thong-bao">')

    def test_menu_nguoi_dung_giu_dinh_dang_ten_va_co_ba_muc(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(response, 'sv_layout<span class="sv-chip__vai-tro"> · Sinh viên</span>')
        self.assertContains(response, f'href="{reverse("accounts:thong_tin_ca_nhan")}"><svg')
        self.assertContains(response, 'Thông tin cá nhân</a>')
        self.assertContains(response, f'href="{reverse("accounts:doi_mat_khau")}"><svg')
        self.assertContains(response, 'Đổi mật khẩu</a>')
        self.assertContains(response, f'<form method="post" action="{reverse("accounts:dang_xuat")}">')

    def test_co_nut_hamburger_va_css_thu_gon_cho_man_hinh_nho(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(response, 'id="sv-hamburger"')
        self.assertContains(response, '.sv-thanh-menu--mo .sv-menu { display: flex; }')

    def test_footer_co_ba_cot_va_ban_quyen(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(response, f'© {timezone.localdate().year} {settings.TEN_TRUONG}')
        self.assertContains(response, '<h4>Liên hệ</h4>')
        self.assertContains(response, '<h4>Liên kết nhanh</h4>')
        self.assertContains(response, 'Địa chỉ: (chưa cập nhật)')

    def test_khong_doi_bang_mau_goc_va_khong_them_bien_moi(self):
        noi_dung = self.client.get(reverse('accounts:trang_chu')).content.decode()
        self.assertIn('--mau-xanh-chinh: #1877F2;', noi_dung)
        self.assertIn('--mau-nen-trang: #F0F2F5;', noi_dung)
        khoi_css_sinh_vien = noi_dung.split('Layout Sinh viên: banner')[1].split('</style>')[0]
        self.assertIsNone(re.search(r'(^|[\s;{])--[a-z-]+\s*:', khoi_css_sinh_vien))

    def _quy_tac_css(self, bo_chon, response=None):
        """Nội dung khai báo của quy tắc CSS đầu tiên có bộ chọn `bo_chon` trong trang."""
        noi_dung = (response or self.client.get(reverse('accounts:trang_chu'))).content.decode()
        khop = re.search(re.escape(bo_chon) + r' \{(.*?)\}', noi_dung, re.S)
        self.assertIsNotNone(khop, f'Không thấy quy tắc CSS {bo_chon!r}.')
        return khop.group(1)

    def test_thanh_menu_va_chan_trang_nen_xanh_chu_trang(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertIn('background: var(--mau-xanh-chinh)', self._quy_tac_css('.sv-thanh-menu', response))
        self.assertIn('color: #fff;', self._quy_tac_css('.sv-menu__muc', response))
        chan_trang = self._quy_tac_css('.sv-chan-trang', response)
        self.assertIn('background: var(--mau-xanh-chinh)', chan_trang)
        self.assertIn('color: rgba(255, 255, 255, .85)', chan_trang)
        self.assertIn('color: #fff', self._quy_tac_css('.sv-chan-trang h4', response))
        # Chữ liên kết ở chân trang phải ghi đè "li a:hover" (nền xanh nhạt) của quy tắc chung.
        self.assertIn('background: rgba(255, 255, 255, .16)', self._quy_tac_css('.sv-chan-trang a:hover', response))

    def test_muc_dang_chon_phan_biet_bang_gach_chan_trang_khong_dung_xanh_dam_hon(self):
        quy_tac = self._quy_tac_css('.sv-menu__muc--chon, .sv-menu .sv-nhom--chon > .sv-nhom__nut')
        self.assertIn('border-bottom-color: #fff', quy_tac)
        self.assertIn('background: rgba(255, 255, 255, .12)', quy_tac)
        self.assertNotIn('--mau-xanh', quy_tac)
        # Viền focus bàn phím của thanh menu phải là trắng (xanh chìm vào nền xanh).
        self.assertIn('outline: 2px solid #fff', self._quy_tac_css('.sv-menu__muc:focus-visible, .sv-hamburger:focus-visible'))

    def test_dropdown_nen_xanh_dam_chu_trang_hover_dam_hon_va_duong_ke_mo(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        khung = self._quy_tac_css('.sv-nhom__xo', response)
        # Xanh đậm hơn thanh menu (#1877F2) để thấy ranh giới giữa menu chính và menu con.
        self.assertIn('background: #145DBF', khung)
        self.assertNotIn('var(--mau-xanh-chinh)', khung)
        self.assertIn('color: #fff;', self._quy_tac_css('.sv-nhom__muc', response))
        self.assertIn('background: #0D47A1', self._quy_tac_css('.sv-nhom__muc:hover', response))
        self.assertIn(
            'border-top: 1px solid rgba(255, 255, 255, .15)', self._quy_tac_css('.sv-nhom__xo > * + *', response),
        )
        # Mục đang chọn trong dropdown phân biệt bằng vạch trắng + nền trắng mờ, không dùng xanh.
        dang_chon = self._quy_tac_css('.sv-nhom__muc--chon', response)
        self.assertIn('box-shadow: inset 3px 0 0 #fff', dang_chon)
        self.assertNotIn('--mau-xanh', dang_chon)
        # Viền focus bàn phím trong dropdown phải là trắng (xanh chìm vào nền xanh đậm).
        self.assertIn('outline: 2px solid #fff', self._quy_tac_css('.sv-nhom__muc:focus-visible', response))

    def test_dropdown_tren_mobile_van_doc_duoc_vi_nam_trong_bang_menu_nen_trang(self):
        # Bảng menu sổ xuống của hamburger vẫn nền trắng, nên danh sách con trong đó phải trong suốt + chữ tối.
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(
            response,
            '.sv-menu__muc { width: 100%; height: 44px; border-bottom: none; border-radius: 6px; color: var(--mau-chu-phu); }',
        )
        self.assertContains(response, 'padding: 0 0 4px 16px; box-shadow: none; background: transparent; overflow: visible; }')
        self.assertContains(response, '.sv-menu .sv-nhom__muc { color: var(--mau-chu);')
        self.assertContains(response, '.sv-menu .sv-nhom__xo > * + * { border-top: 0; }')

    def test_chip_nen_trang_de_chu_den_va_badge_do_doc_ro_tren_nen_xanh(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        chip = self._quy_tac_css('.sv-chip', response)
        self.assertIn('background: var(--mau-the)', chip)
        self.assertIn('color: var(--mau-chu)', chip)
        self.assertIn('background: var(--mau-do)', self._quy_tac_css('.chip-thong-bao', response))

    def test_do_tuong_phan_toi_thieu_tren_nen_xanh_thuong_hieu(self):
        # Ghi lại tương phản thật (WCAG) của các tổ hợp chữ/nền mới để không bị hạ vô tình.
        # Trắng trên #1877F2 chỉ đạt ≈4,2:1 (đạt cho chữ đậm/thành phần giao diện, chưa đạt 4,5:1 của chữ
        # thường) — giới hạn của việc dùng chính màu thương hiệu làm nền, xem docs/thiet_ke_giao_dien.md.
        def do_sang(rgb):
            tuyen_tinh = [(c / 255 / 12.92) if c / 255 <= 0.03928 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in rgb]
            return 0.2126 * tuyen_tinh[0] + 0.7152 * tuyen_tinh[1] + 0.0722 * tuyen_tinh[2]

        def tuong_phan(a, b):
            sang, toi = sorted((do_sang(a), do_sang(b)), reverse=True)
            return (sang + 0.05) / (toi + 0.05)

        def tron_voi_trang(do_duc):
            return tuple(round(do_duc * 255 + (1 - do_duc) * c) for c in XANH)

        XANH, TRANG = (24, 119, 242), (255, 255, 255)
        self.assertGreaterEqual(tuong_phan(TRANG, XANH), 4.0)
        self.assertGreaterEqual(tuong_phan(tron_voi_trang(0.85), XANH), 3.4)
        self.assertGreaterEqual(tuong_phan(TRANG, tron_voi_trang(0.12)), 3.5)
        self.assertGreaterEqual(tuong_phan((228, 30, 63), TRANG), 4.5)
        # Dropdown xanh đậm: chữ trắng đạt AA đầy đủ và vẫn tách khỏi thanh menu #1877F2 cạnh nó.
        dropdown, dropdown_hover = (20, 93, 191), (13, 71, 161)
        self.assertGreaterEqual(tuong_phan(TRANG, dropdown), 4.5)
        self.assertGreaterEqual(tuong_phan(TRANG, dropdown_hover), 4.5)
        self.assertGreaterEqual(tuong_phan(dropdown, XANH), 1.3)
        self.assertGreaterEqual(tuong_phan(dropdown, dropdown_hover), 1.2)
        # Đỏ đặt thẳng lên nền xanh gần như không phân biệt được -> chip phải nền trắng.
        self.assertLess(tuong_phan((228, 30, 63), XANH), 1.5)

    def test_vai_tro_khac_dung_thanh_menu_xanh_giong_sinh_vien(self):
        """Phòng Đào tạo, Giảng viên, Cố vấn dùng cùng màu và kiểu dáng thanh menu với Sinh viên
        (khung riêng nhan_vien/_khung_dau.html, có kiểm thử chi tiết ở MenuNhanVienTest)."""
        tai_khoan_khac = [self.tk_pdt]
        for ten, vai_tro in (('gv_layout', VaiTro.GIANG_VIEN), ('cv_layout2', VaiTro.CO_VAN_HOC_TAP)):
            tai_khoan_khac.append(
                TaiKhoan.objects.create_user(ten_dang_nhap=ten, vai_tro=vai_tro, password=MAT_KHAU_HOP_LE)
            )
        for tai_khoan in tai_khoan_khac:
            self.client.force_login(tai_khoan)
            response = self.client.get(reverse('accounts:trang_chu'))
            self.assertContains(response, '<header class="sv-banner">')
            self.assertContains(response, 'sv-thanh-menu sv-thanh-menu--nv')
            self.assertNotContains(response, 'class="thanh-tren')
            self.assertNotContains(response, '<footer class="sv-chan-trang">')
            self.assertNotContains(response, '<nav class="sv-breadcrumb"')

    def test_sinh_vien_khong_dung_khung_nhan_vien(self):
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertNotContains(response, 'sv-thanh-menu--nv')

    def test_trang_loi_403_van_hien_layout_sinh_vien(self):
        response = self.client.get(reverse('people:sinh_vien_danh_sach'))
        self.assertContains(response, 'sv-banner', status_code=403)
        self.assertContains(response, 'sv-chan-trang', status_code=403)

    def test_chua_dang_nhap_khong_co_layout_sinh_vien(self):
        self.client.logout()
        response = self.client.get(reverse('accounts:dang_nhap'))
        self.assertNotContains(response, 'sv-banner')
        self.assertNotContains(response, 'sv-chan-trang')


class MenuNhanVienTest(TestCase):
    """Menu của Phòng Đào tạo, Giảng viên, Cố vấn học tập (templates/nhan_vien/_khung_dau.html): đủ liên kết tới
    mọi trang danh mục mà vai trò được vào, đúng nhóm dropdown, dùng chung kiểu dáng với menu Sinh viên."""

    NHOM_PDT = {
        'Người dùng': [
            ('people:sinh_vien_danh_sach', 'Sinh viên'), ('people:giang_vien_danh_sach', 'Giảng viên'),
            ('people:co_van_danh_sach', 'Cố vấn học tập'), ('people:sinh_vien_nhap_excel', 'Nhập sinh viên từ Excel'),
        ],
        'Học vụ': [
            ('academics:nganh_hoc_danh_sach', 'Ngành học'), ('academics:lop_hanh_chinh_danh_sach', 'Lớp hành chính'),
            ('academics:hoc_phan_danh_sach', 'Học phần'),
            ('academics:dieu_kien_tien_quyet_danh_sach', 'Điều kiện tiên quyết'),
            ('academics:chuong_trinh_danh_sach', 'Chương trình đào tạo'),
            ('academics:hoc_ky_danh_sach', 'Danh mục học kỳ'), ('academics:dot_dang_ky_danh_sach', 'Đợt đăng ký học phần'),
        ],
        'Lớp học phần': [
            ('classes:lop_hoc_phan_danh_sach', 'Lớp học phần'), ('classes:lich_hoc_danh_sach', 'Lịch học'),
            ('classes:lich_thi_danh_sach', 'Lịch thi'), ('enrollment:tra_cuu_lich_su', 'Tra cứu lịch sử đăng ký'),
        ],
        'Báo cáo': [
            ('reports:si_so_theo_lop', 'Sĩ số theo lớp'), ('reports:hoc_phan_nhieu_dang_ky', 'Học phần nhiều đăng ký'),
            ('reports:ket_qua_hoc_tap', 'Kết quả học tập'),
        ],
    }
    TAB_RIENG = {
        VaiTro.PHONG_DAO_TAO: [
            ('accounts:trang_chu', 'Trang chủ'), ('accounts:tai_khoan_danh_sach', 'Tài khoản'),
            ('regulations:danh_sach', 'Quy chế'), ('grades:canh_bao_phong_dao_tao', 'Cảnh báo học vụ'),
            ('thong_bao:gui_phong_dao_tao', 'Gửi thông báo'),
        ],
        VaiTro.GIANG_VIEN: [
            ('accounts:trang_chu', 'Trang chủ'), ('classes:lop_phu_trach', 'Lớp phụ trách'),
            ('classes:lich_giang_day', 'Lịch giảng dạy'), ('thong_bao:gui_giang_vien', 'Gửi thông báo'),
        ],
        VaiTro.CO_VAN_HOC_TAP: [
            ('accounts:trang_chu', 'Trang chủ'), ('enrollment:sinh_vien_phu_trach', 'Sinh viên phụ trách'),
            ('tien_do_hoc_tap:co_van', 'Tiến độ học tập'), ('grades:canh_bao_co_van', 'Cảnh báo học vụ'),
            ('tom_tat_ket_qua:co_van', 'Tóm tắt AI'), ('hoi_dap_quy_che:trang_chat', 'Hỏi đáp AI'),
            ('thong_bao:gui_co_van', 'Gửi thông báo'),
        ],
    }

    def setUp(self):
        self.tai_khoan = {
            vai_tro: TaiKhoan.objects.create_user(ten_dang_nhap=f'menu_{i}', vai_tro=vai_tro, password=MAT_KHAU_HOP_LE)
            for i, vai_tro in enumerate(self.TAB_RIENG)
        }

    def _trang(self, vai_tro, ten_url='accounts:trang_chu'):
        self.client.force_login(self.tai_khoan[vai_tro])
        return self.client.get(reverse(ten_url), follow=True)

    @staticmethod
    def _menu(response):
        return re.search(r'<nav class="sv-menu".*?</nav>', response.content.decode(), re.S).group(0)

    @staticmethod
    def _nhom(menu):
        """{tên nhóm: [(href, nhãn), ...]} của các dropdown trong menu chính."""
        ket_qua = {}
        for ten, noi_dung in re.findall(
            r'<div class="sv-nhom[^"]*">\s*<button[^>]*>.*?<span>([^<]+)</span>.*?<div class="sv-nhom__xo">(.*?)</div>\s*</div>',
            menu, re.S,
        ):
            ket_qua[ten] = re.findall(r'href="([^"]+)"[^>]*>.*?</svg>([^<]+)</a>', noi_dung, re.S)
        return ket_qua

    @staticmethod
    def _tab_rieng(menu):
        """Các liên kết nằm trực tiếp trên thanh (không thuộc dropdown)."""
        return re.findall(r'<a class="sv-menu__muc[^"]*" href="([^"]+)">.*?<span>([^<]+)</span></a>', menu, re.S)

    @staticmethod
    def _cap(danh_sach):
        return [(reverse(ten), nhan) for ten, nhan in danh_sach]

    def test_phong_dao_tao_du_nhom_va_du_lien_ket(self):
        menu = self._menu(self._trang(VaiTro.PHONG_DAO_TAO))
        self.assertEqual(self._tab_rieng(menu), self._cap(self.TAB_RIENG[VaiTro.PHONG_DAO_TAO]))
        nhom = self._nhom(menu)
        self.assertEqual(list(nhom), list(self.NHOM_PDT))
        for ten, muc in self.NHOM_PDT.items():
            self.assertEqual(nhom[ten], self._cap(muc), ten)

    def test_giang_vien_va_co_van_nhom_dung_so_chuc_nang_that(self):
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.CO_VAN_HOC_TAP):
            menu = self._menu(self._trang(vai_tro))
            self.assertEqual(self._tab_rieng(menu), self._cap(self.TAB_RIENG[vai_tro]), vai_tro)
            self.assertEqual(self._nhom(menu), {}, vai_tro)

    def test_moi_lien_ket_tren_menu_mo_duoc_bang_dung_vai_tro(self):
        for vai_tro in self.TAB_RIENG:
            noi_dung = self._trang(vai_tro).content.decode()
            khoi = re.search(r'<nav class="sv-menu".*?</nav>', noi_dung, re.S).group(0)
            khoi += re.search(r'<div class="sv-phai">.*', noi_dung, re.S).group(0)
            duong_dan = sorted(set(re.findall(r'href="(/[^"]*)"', khoi)))
            self.assertGreater(len(duong_dan), 6)
            for url in duong_dan:
                with self.subTest(vai_tro=vai_tro, url=url):
                    self.assertEqual(self.client.get(url, follow=True).status_code, 200)

    def test_menu_ca_nhan_co_thong_tin_doi_mat_khau_dang_xuat_va_chuong_thong_bao(self):
        for vai_tro in self.TAB_RIENG:
            noi_dung = self._trang(vai_tro).content.decode()
            phai = re.search(r'<div class="sv-phai">.*', noi_dung, re.S).group(0)
            for ten_url in ('accounts:thong_tin_ca_nhan', 'accounts:doi_mat_khau', 'thong_bao:danh_sach'):
                self.assertIn(f'href="{reverse(ten_url)}"', phai, (vai_tro, ten_url))
            self.assertIn(f'action="{reverse("accounts:dang_xuat")}"', phai)

    def test_muc_dang_chon_dung_nhom_va_dung_muc(self):
        menu = self._menu(self._trang(VaiTro.PHONG_DAO_TAO, 'academics:hoc_ky_danh_sach'))
        self.assertEqual(menu.count('sv-nhom--chon'), 1)
        self.assertRegex(menu, r'sv-nhom--chon">\s*<button[^>]*>.*?<span>Học vụ</span>')
        self.assertIn(f'sv-nhom__muc sv-nhom__muc--chon" href="{reverse("academics:hoc_ky_danh_sach")}"', menu)
        self.assertEqual(menu.count('sv-nhom__muc--chon'), 1)
        menu = self._menu(self._trang(VaiTro.PHONG_DAO_TAO, 'accounts:tai_khoan_danh_sach'))
        self.assertIn(f'sv-menu__muc sv-menu__muc--chon" href="{reverse("accounts:tai_khoan_danh_sach")}"', menu)
        self.assertEqual(menu.count('sv-nhom--chon'), 0)
        menu = self._menu(self._trang(VaiTro.GIANG_VIEN, 'classes:lich_giang_day'))
        self.assertIn(f'sv-menu__muc sv-menu__muc--chon" href="{reverse("classes:lich_giang_day")}"', menu)
        self.assertEqual(menu.count('sv-menu__muc--chon'), 1)

    def test_dung_kieu_dang_va_mau_cua_menu_sinh_vien(self):
        noi_dung = self._trang(VaiTro.PHONG_DAO_TAO).content.decode()
        self.assertIn('<header class="sv-banner">', noi_dung)
        self.assertIn('sv-thanh-menu sv-thanh-menu--nv sv-thanh-menu--nhieu', noi_dung)
        self.assertNotIn('class="thanh-tren', noi_dung)
        self.assertRegex(noi_dung, r'\.sv-thanh-menu \{[^}]*background: var\(--mau-xanh-chinh\)')
        self.assertRegex(noi_dung, r'\.sv-nhom__xo \{[^}]*background: #145DBF')
        self.assertIn('.sv-nhom__muc:hover { background: #0D47A1; color: #fff; }', noi_dung)
        self.assertRegex(
            noi_dung, r'\.sv-menu__muc--chon, \.sv-menu \.sv-nhom--chon > \.sv-nhom__nut \{[^}]*border-bottom-color: #fff',
        )
        # Bấm mở trên cảm ứng, hover trên máy tính: cùng quy tắc và cùng script với Sinh viên.
        self.assertIn('.sv-nhom:hover > .sv-nhom__xo, .sv-nhom:focus-within > .sv-nhom__xo { display: block; }', noi_dung)
        self.assertIn("nhom.classList.toggle('sv-nhom--mo', mo);", noi_dung)
        self.assertIn('sv-icon', noi_dung)

    def test_dieu_chinh_rieng_cho_nhieu_muc_va_man_hinh_hep(self):
        noi_dung = self._trang(VaiTro.PHONG_DAO_TAO).content.decode()
        self.assertIn('@media (max-width: 1100px)', noi_dung)
        self.assertIn('.sv-thanh-menu--nv.sv-thanh-menu--mo .sv-menu { display: flex; }', noi_dung)
        self.assertIn('@media (min-width: 1101px) and (max-width: 1439px)', noi_dung)
        # Giảng viên và Cố vấn không có lớp "nhiều mục".
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.CO_VAN_HOC_TAP):
            self.assertNotIn('sv-thanh-menu--nv sv-thanh-menu--nhieu', self._trang(vai_tro).content.decode())

    def test_khong_co_chan_trang_va_duong_dan_cua_sinh_vien(self):
        for vai_tro in self.TAB_RIENG:
            noi_dung = self._trang(vai_tro).content.decode()
            self.assertNotIn('<footer class="sv-chan-trang">', noi_dung)
            self.assertNotIn('<nav class="sv-breadcrumb"', noi_dung)

    def test_html_can_bang_the(self):
        for vai_tro in self.TAB_RIENG:
            loi, con_mo = kiem_tra_can_bang_the(self._trang(vai_tro).content.decode())
            self.assertEqual((loi, con_mo), ([], []), vai_tro)

    def test_trang_loi_403_van_hien_menu_dung_vai_tro(self):
        # Giảng viên vào trang của Phòng Đào tạo: 403 nhưng menu vẫn là của Giảng viên.
        self.client.force_login(self.tai_khoan[VaiTro.GIANG_VIEN])
        response = self.client.get(reverse('people:sinh_vien_danh_sach'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, '<nav class="sv-menu"', status_code=403)
        self.assertContains(response, 'Lịch giảng dạy', status_code=403)
        self.assertNotContains(response, 'Người dùng', status_code=403)


class TrangChuPhongDaoTaoTest(TestCase):
    """Ba khối đầu trang chủ Phòng Đào tạo: số liệu tổng quan, cảnh báo cần chú ý, thông báo đã gửi gần đây."""

    def setUp(self):
        self.tk_pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_tc', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.client.force_login(self.tk_pdt)
        bay_gio = timezone.now()
        hom_nay = timezone.localdate()
        self.hk_cu = HocKy.objects.create(hoc_ky=2, nam_hoc='2024-2025', ngay_bat_dau=hom_nay - timedelta(days=400), ngay_ket_thuc=hom_nay - timedelta(days=300))
        self.hk_nay = HocKy.objects.create(hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau=hom_nay - timedelta(days=30), ngay_ket_thuc=hom_nay + timedelta(days=90))
        # Đợt đăng ký đang hiệu lực và sắp đóng trong 2 ngày.
        self.dot = DotDangKy.objects.create(hoc_ky=self.hk_nay, ngay_mo=bay_gio - timedelta(days=1), ngay_dong=bay_gio + timedelta(days=2))

        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_tc', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_TC', ho_ten='GV', email='gv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_TC', ten_hoc_phan='HP TC', so_tin_chi=3)
        # Hai lớp của học kỳ đang xét: LHP_NAY1 sĩ số 1 (sẽ đầy), LHP_NAY2 sĩ số 5. Hai lớp kỳ cũ để có điểm.
        self.lop_day = LopHocPhan.objects.create(ma_lop_hoc_phan='LHP_NAY1', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=1, ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien)
        self.lop_con = LopHocPhan.objects.create(ma_lop_hoc_phan='LHP_NAY2', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=5, ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien)
        self.lop_cu = [
            LopHocPhan.objects.create(ma_lop_hoc_phan=f'LHP_CU{i}', hoc_ky='2', nam_hoc='2024-2025', si_so_toi_da=30, ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien)
            for i in (1, 2)
        ]

        nganh = NganhHoc.objects.create(ma_nganh='N_TC', ten_nganh='Ngành')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_tc', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        co_van = CoVanHocTap.objects.create(ma_co_van='CV_TC', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv)
        lop_hc = LopHanhChinh.objects.create(ma_lop='L_TC', ten_lop='L', ma_nganh=nganh, ma_co_van=co_van)

        def tao_sinh_vien(ma, hoat_dong=True):
            tk = TaiKhoan.objects.create_user(ten_dang_nhap=f'sv_{ma}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
            if not hoat_dong:
                tk.is_active = False
                tk.save(update_fields=['is_active'])
            return SinhVien.objects.create(
                ma_sinh_vien=ma, ho_ten=ma, ngay_sinh='2004-01-01', email=f'{ma}@test.local',
                so_dien_thoai='0900000000', ma_lop=lop_hc, ma_tai_khoan=tk,
            )

        def dang_ky(sinh_vien, lop, diem=None):
            dk = DangKyHocPhan.objects.create(ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=bay_gio)
            if diem is not None:
                Diem.objects.create(ma_dang_ky=dk, diem_qua_trinh=diem, diem_thi=diem)
            return dk

        self.sv_do = tao_sinh_vien('SV_DO')                    # 2 học phần rớt, TB 3.0 -> cảnh báo mức đỏ
        self.sv_thuong = tao_sinh_vien('SV_THUONG')            # không có điểm
        self.sv_khoa = tao_sinh_vien('SV_KHOA', hoat_dong=False)  # cùng điểm rớt nhưng tài khoản bị khóa
        for lop in self.lop_cu:
            dang_ky(self.sv_do, lop, diem=3)
            dang_ky(self.sv_khoa, lop, diem=3)
        dang_ky(self.sv_do, self.lop_day)
        dang_ky(self.sv_thuong, self.lop_con)
        self.url = reverse('accounts:trang_chu')

    def _trang(self):
        return self.client.get(self.url)

    def test_so_lieu_tong_quan(self):
        tt = self._trang().context['tong_hop']
        self.assertEqual(tt['so_sinh_vien_hoat_dong'], 2)  # không tính tài khoản bị khóa
        self.assertEqual(tt['so_lop_hoc_phan'], 2)         # chỉ lớp của học kỳ đang xét
        self.assertEqual(tt['so_dot_hieu_luc'], 1)
        self.assertEqual((tt['so_canh_bao'], tt['so_canh_bao_do']), (1, 1))
        self.assertEqual(tt['so_lop_day'], 1)
        self.assertEqual(tt['hoc_ky_xet'], {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'dot'})

    def test_nam_o_tong_quan_co_nhan_gia_tri_va_lien_ket_xem_chi_tiet(self):
        response = self._trang()
        for nhan in (
            'Sinh viên đang hoạt động', 'Lớp học phần của học kỳ đang xét', 'Đợt đăng ký đang hiệu lực',
            'Sinh viên bị cảnh báo học vụ', 'Lớp học phần đã đầy chỗ',
        ):
            self.assertContains(response, nhan)
        self.assertContains(response, 'luoi-tong-hop luoi-tong-hop--5')
        self.assertContains(response, 'Xem chi tiết', count=5)
        loc = '?hoc_ky=1&amp;nam_hoc=2025-2026'
        for url in (
            reverse('people:sinh_vien_danh_sach'), reverse('classes:lop_hoc_phan_danh_sach') + loc,
            reverse('academics:dot_dang_ky_danh_sach'), reverse('grades:canh_bao_phong_dao_tao') + loc,
            reverse('reports:si_so_theo_lop') + loc,
        ):
            self.assertContains(response, f'href="{url}"')

    def test_moi_lien_ket_xem_chi_tiet_mo_duoc(self):
        tt = self._trang().context['tong_hop']
        for khoa in ('url_sinh_vien', 'url_lop_hoc_phan', 'url_dot_dang_ky', 'url_canh_bao', 'url_si_so', 'url_thong_bao_da_gui'):
            self.assertEqual(self.client.get(tt[khoa]).status_code, 200, khoa)

    def test_o_canh_bao_hoc_vu_co_ghi_chu_xam_ve_hoc_ky_gan_nhat(self):
        response = self._trang()
        self.assertContains(
            response, '* tính theo học kỳ gần nhất của từng sinh viên, có thể khác trang chi tiết theo học kỳ',
        )
        self.assertContains(response, '(1 mức đỏ)')
        self.assertRegex(response.content.decode(), r'\.o-tong-hop__ghi-chu \{[^}]*color: var\(--mau-chu-phu\)')

    def test_khoi_canh_bao_moi_loai_mot_dong_dung_thu_tu_uu_tien(self):
        response = self._trang()
        dong = response.context['tong_hop']['dong_canh_bao']
        self.assertEqual([d['muc'] for d in dong], ['do', 'day', 'dot'])
        self.assertIn('1 sinh viên bị cảnh báo học vụ mức đỏ', dong[0]['noi_dung'])
        self.assertIn('1 lớp học phần đã đầy chỗ: LHP_NAY1.', dong[1]['noi_dung'])
        self.assertIn('Học kỳ 1 năm học 2025-2026 sắp đóng', dong[2]['noi_dung'])
        self.assertContains(response, 'Cảnh báo cần chú ý')
        self.assertContains(response, 'khoi-chu-y__dong--do')
        self.assertRegex(response.content.decode(), r'\.khoi-chu-y \{[^}]*background: var\(--mau-vang-nhat\)')
        for d in dong:
            self.assertContains(response, f'href="{d["url"].replace("&", "&amp;")}"')
            self.assertEqual(self.client.get(d['url']).status_code, 200, d['url'])

    def test_khoi_canh_bao_toi_da_5_dong_va_gop_lop_day(self):
        bay_gio = timezone.now()
        for i, nam_hoc in enumerate(('2020-2021', '2021-2022', '2022-2023', '2023-2024'), start=1):
            hoc_ky = HocKy.objects.create(hoc_ky=1, nam_hoc=nam_hoc, ngay_bat_dau=timezone.localdate(), ngay_ket_thuc=timezone.localdate() + timedelta(days=100))
            DotDangKy.objects.create(hoc_ky=hoc_ky, ngay_mo=bay_gio - timedelta(hours=1), ngay_dong=bay_gio + timedelta(hours=i))
        dong = self._trang().context['tong_hop']['dong_canh_bao']
        self.assertEqual(len(dong), 5)
        self.assertEqual([d['muc'] for d in dong], ['do', 'day', 'dot', 'dot', 'dot'])
        # Các đợt thêm thuộc học kỳ cũ hơn nên học kỳ đang xét vẫn là 2025-2026. Đợt đóng sớm nhất xếp trước
        # (các đợt thêm đóng sau 1, 2, 3, 4 giờ; đợt gốc đóng sau 2 ngày).
        for d, nam_hoc in zip(dong[2:], ('2020-2021', '2021-2022', '2022-2023')):
            self.assertIn(f'năm học {nam_hoc} sắp đóng', d['noi_dung'])

    def test_nhieu_lop_day_chi_hien_ba_ma_va_gop_so_con_lai(self):
        hoc_phan = HocPhan.objects.get(pk='HP_TC')
        for i in range(4):
            lop = LopHocPhan.objects.create(ma_lop_hoc_phan=f'LHP_DAY{i}', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=1, ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien)
            DangKyHocPhan.objects.create(ma_sinh_vien=self.sv_thuong, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now())
        noi_dung = self._trang().context['tong_hop']['dong_canh_bao'][1]['noi_dung']
        self.assertIn('5 lớp học phần đã đầy chỗ: LHP_DAY0, LHP_DAY1, LHP_DAY2 và 2 lớp khác.', noi_dung)

    def test_an_khoi_canh_bao_khi_khong_co_gi_dang_chu_y(self):
        Diem.objects.all().delete()
        DangKyHocPhan.objects.filter(ma_lop_hoc_phan=self.lop_day).delete()
        DotDangKy.objects.all().delete()
        response = self._trang()
        self.assertEqual(response.context['tong_hop']['dong_canh_bao'], [])
        self.assertNotContains(response, 'Cảnh báo cần chú ý')
        self.assertNotContains(response, '<section class="khoi-chu-y"')
        self.assertContains(response, 'Số liệu tổng quan')

    def test_chon_hoc_ky_dang_xet(self):
        from accounts.tong_hop_phong_dao_tao import hoc_ky_dang_xet

        bay_gio = timezone.now()
        # Có đợt đang hiệu lực: lấy học kỳ của đợt.
        self.assertEqual(hoc_ky_dang_xet(bay_gio), {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'dot'})
        # Không có đợt: học kỳ mới nhất trong danh mục (năm học lớn nhất rồi số học kỳ lớn nhất).
        DotDangKy.objects.all().delete()
        HocKy.objects.create(hoc_ky=1, nam_hoc='2024-2025', ngay_bat_dau=timezone.localdate(), ngay_ket_thuc=timezone.localdate() + timedelta(days=10))
        self.assertEqual(hoc_ky_dang_xet(bay_gio), {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'danh_muc'})
        self.hk_nay.delete()
        self.assertEqual(hoc_ky_dang_xet(bay_gio), {'hoc_ky': '2', 'nam_hoc': '2024-2025', 'nguon': 'danh_muc'})
        # Đợt đang hiệu lực của học kỳ cũ vẫn được ưu tiên hơn học kỳ mới nhất trong danh mục.
        HocKy.objects.create(hoc_ky=1, nam_hoc='2030-2031', ngay_bat_dau=timezone.localdate(), ngay_ket_thuc=timezone.localdate() + timedelta(days=10))
        DotDangKy.objects.create(hoc_ky=self.hk_cu, ngay_mo=bay_gio - timedelta(days=1), ngay_dong=bay_gio + timedelta(days=20))
        self.assertEqual(hoc_ky_dang_xet(bay_gio), {'hoc_ky': '2', 'nam_hoc': '2024-2025', 'nguon': 'dot'})

    def test_danh_muc_hoc_ky_trong_van_hien_trang(self):
        DotDangKy.objects.all().delete()
        HocKy.objects.all().delete()
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        tt = response.context['tong_hop']
        self.assertIsNone(tt['hoc_ky_xet'])
        self.assertIsNone(tt['so_lop_hoc_phan'])
        self.assertEqual(tt['so_lop_day'], 0)
        self.assertContains(response, 'Chưa có học kỳ nào trong danh mục.')

    def test_thong_bao_da_gui_gan_day_nam_dong_moi_nhat_cua_phong_dao_tao(self):
        goc = timezone.now() - timedelta(days=10)
        for i in range(7):
            thong_bao = ThongBao.objects.create(
                tieu_de=f'TB PDT {i}', noi_dung='nội dung', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
            )
            ThongBao.objects.filter(pk=thong_bao.pk).update(thoi_gian_gui=goc + timedelta(hours=i))
        tk_gv = TaiKhoan.objects.get(ten_dang_nhap='gv_tc')
        thong_bao_gv = ThongBao.objects.create(
            tieu_de='TB cua giang vien', noi_dung='x', nguoi_gui=tk_gv, doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN, lop_hoc_phan=self.lop_con,
        )
        ThongBao.objects.filter(pk=thong_bao_gv.pk).update(thoi_gian_gui=goc + timedelta(days=5))
        response = self._trang()
        noi_dung = response.content.decode()
        tieu_de = [tb.tieu_de for tb in response.context['tong_hop']['thong_bao_gan_day']]
        self.assertEqual(tieu_de, ['TB PDT 6', 'TB PDT 5', 'TB PDT 4', 'TB PDT 3', 'TB PDT 2'])
        self.assertNotIn('TB cua giang vien', noi_dung)
        self.assertNotIn('TB PDT 1<', noi_dung)
        vi_tri = [noi_dung.index(f'TB PDT {i}') for i in (6, 5, 4, 3, 2)]
        self.assertEqual(vi_tri, sorted(vi_tri))
        self.assertContains(response, 'Thông báo đã gửi gần đây')
        self.assertContains(response, f'href="{reverse("thong_bao:da_gui")}"')
        self.assertContains(response, 'Xem tất cả')
        self.assertContains(response, 'Gửi cho tất cả người dùng')

    def test_chua_co_thong_bao_nao_da_gui(self):
        self.assertContains(self._trang(), 'Chưa có thông báo nào được gửi.')

    def test_mo_ta_doi_tuong_lop_hoc_phan_va_lop_hanh_chinh(self):
        ThongBao.objects.create(
            tieu_de='Gửi lớp học phần', noi_dung='x', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN, lop_hoc_phan=self.lop_con,
        )
        ThongBao.objects.create(
            tieu_de='Gửi lớp hành chính', noi_dung='x', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH,
            lop_hanh_chinh=LopHanhChinh.objects.get(pk='L_TC'),
        )
        response = self._trang()
        self.assertContains(response, 'cho lớp học phần LHP_NAY2')
        self.assertContains(response, 'cho lớp hành chính L_TC')

    def test_mo_ta_doi_tuong_theo_vai_tro_co_dau_tieng_viet(self):
        for doi_tuong in (DoiTuongThongBao.SINH_VIEN, DoiTuongThongBao.GIANG_VIEN, DoiTuongThongBao.CO_VAN_HOC_TAP):
            ThongBao.objects.create(tieu_de=f'TB {doi_tuong}', noi_dung='x', nguoi_gui=self.tk_pdt, doi_tuong=doi_tuong)
        noi_dung = self._trang().content.decode()
        for mo_ta in ('Gửi cho sinh viên', 'Gửi cho giảng viên', 'Gửi cho cố vấn học tập'):
            self.assertIn(mo_ta, noi_dung)
        self.assertNotIn('Giang Vien', noi_dung)

    def test_chi_con_ba_khoi_va_khong_con_luoi_the_chuc_nang(self):
        noi_dung = self._trang().content.decode()
        for khoi in ('Số liệu tổng quan', 'Cảnh báo cần chú ý', 'Thông báo đã gửi gần đây'):
            self.assertIn(khoi, noi_dung)
        self.assertLess(noi_dung.index('Số liệu tổng quan'), noi_dung.index('Cảnh báo cần chú ý'))
        self.assertLess(noi_dung.index('Cảnh báo cần chú ý'), noi_dung.index('Thông báo đã gửi gần đây'))
        # Không còn nhóm thẻ nào (các thẻ liệt kê trang quản lý đã bỏ, menu trên thanh đã có đủ liên kết).
        for dau_hieu in ('<div class="nhom-chuc-nang', '<div class="luoi-the"', '<div class="the-chuc-nang"'):
            self.assertNotIn(dau_hieu, noi_dung)
        noi_dung_chinh = noi_dung[noi_dung.index('<main>'):noi_dung.index('</main>')]
        for the in ('Quản lý tài khoản', 'Nhập sinh viên từ Excel', 'Danh mục học kỳ', 'Tra cứu lịch sử đăng ký', 'Thông báo của tôi'):
            self.assertNotIn(the, noi_dung_chinh)
        # Lời chào vẫn còn.
        self.assertContains(self._trang(), 'Xin chào, pdt_tc')

    def test_moi_lien_ket_da_bo_khoi_trang_chu_van_co_tren_menu(self):
        noi_dung = self._trang().content.decode()
        menu = re.search(r'<nav class="sv-menu".*?</nav>', noi_dung, re.S).group(0)
        for ten_url in (
            'accounts:tai_khoan_danh_sach', 'people:sinh_vien_danh_sach', 'people:giang_vien_danh_sach',
            'people:co_van_danh_sach', 'people:sinh_vien_nhap_excel', 'academics:nganh_hoc_danh_sach',
            'academics:lop_hanh_chinh_danh_sach', 'academics:hoc_phan_danh_sach', 'academics:dieu_kien_tien_quyet_danh_sach',
            'academics:hoc_ky_danh_sach', 'academics:dot_dang_ky_danh_sach', 'academics:chuong_trinh_danh_sach',
            'classes:lop_hoc_phan_danh_sach', 'classes:lich_hoc_danh_sach', 'classes:lich_thi_danh_sach',
            'enrollment:tra_cuu_lich_su', 'regulations:danh_sach', 'reports:si_so_theo_lop', 'reports:hoc_phan_nhieu_dang_ky',
            'reports:ket_qua_hoc_tap', 'grades:canh_bao_phong_dao_tao', 'thong_bao:gui_phong_dao_tao',
        ):
            self.assertIn(f'href="{reverse(ten_url)}"', menu, ten_url)
        # "Thông báo của tôi" (trước là thẻ ở trang chủ) vẫn vào được qua chuông thông báo.
        self.assertIn(f'href="{reverse("thong_bao:danh_sach")}"', noi_dung)

    def test_khong_vai_tro_nao_con_luoi_the_chuc_nang(self):
        for ten, vai_tro in (('gv_tc3', VaiTro.GIANG_VIEN), ('cv_tc3', VaiTro.CO_VAN_HOC_TAP), ('sv_tc3', VaiTro.SINH_VIEN)):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=ten, vai_tro=vai_tro, password=MAT_KHAU_HOP_LE))
            noi_dung = self._trang().content.decode()
            for dau_hieu in ('<div class="nhom-chuc-nang', '<div class="luoi-the"', '<div class="the-chuc-nang"'):
                self.assertNotIn(dau_hieu, noi_dung, (vai_tro, dau_hieu))

    def test_moi_hanh_dong_trong_ba_khoi_la_nut_hoac_lien_ket_ro_rang(self):
        noi_dung = self._trang().content.decode()
        bat_dau = noi_dung.index('<section class="khoi-tong-quan"')
        ket_thuc = noi_dung.index('</main>')
        cac_lien_ket = re.findall(r'<a [^>]*>', noi_dung[bat_dau:ket_thuc])
        self.assertGreaterEqual(len(cac_lien_ket), 5 + 3 + 1)
        for the in cac_lien_ket:
            self.assertIn('class="nut ', the)
        self.assertNotIn('underline', self._quy_tac_khoi_chu_y(noi_dung))

    @staticmethod
    def _quy_tac_khoi_chu_y(noi_dung):
        return ''.join(re.findall(r'\.(?:khoi-chu-y|khoi-gan-day|khoi-tong-quan|o-tong-hop)[^{]*\{[^}]*\}', noi_dung))

    def test_vai_tro_khac_khong_thay_ba_khoi(self):
        for ten, vai_tro in (('sv_tc2', VaiTro.SINH_VIEN),):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=ten, vai_tro=vai_tro, password=MAT_KHAU_HOP_LE))
            response = self._trang()
            self.assertNotContains(response, 'Số liệu tổng quan')
            self.assertNotContains(response, 'Cảnh báo cần chú ý')
            self.assertNotContains(response, 'Thông báo đã gửi gần đây')

    def test_html_can_bang_the(self):
        ThongBao.objects.create(tieu_de='TB', noi_dung='x', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA)
        loi, con_mo = kiem_tra_can_bang_the(self._trang().content.decode())
        self.assertEqual((loi, con_mo), ([], []))


class DanhSachThongBaoDaGuiTest(TestCase):
    def setUp(self):
        self.tk_pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_dg', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.tk_pdt2 = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_dg2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.url = reverse('thong_bao:da_gui')

    def _gui(self, tieu_de, nguoi_gui, doi_tuong=DoiTuongThongBao.TAT_CA):
        return ThongBao.objects.create(tieu_de=tieu_de, noi_dung='Nội dung ' + tieu_de, nguoi_gui=nguoi_gui, doi_tuong=doi_tuong)

    def test_phong_dao_tao_thay_thong_bao_cua_moi_tai_khoan_phong_dao_tao(self):
        self._gui('Của tôi', self.tk_pdt)
        self._gui('Của đồng nghiệp', self.tk_pdt2, DoiTuongThongBao.SINH_VIEN)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_dg', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        self._gui('Của giảng viên', tk_gv, DoiTuongThongBao.SINH_VIEN)
        self.client.force_login(self.tk_pdt)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Của tôi')
        self.assertContains(response, 'Của đồng nghiệp')
        self.assertNotContains(response, 'Của giảng viên')
        self.assertContains(response, 'pdt_dg2')

    def test_moi_nhat_truoc_va_phan_trang(self):
        for i in range(25):
            tb = self._gui(f'Muc {i:02d}', self.tk_pdt)
            ThongBao.objects.filter(pk=tb.pk).update(thoi_gian_gui=timezone.now() - timedelta(minutes=25 - i))
        self.client.force_login(self.tk_pdt)
        trang_1 = self.client.get(self.url)
        self.assertEqual(len(trang_1.context['danh_sach']), 20)
        self.assertEqual(trang_1.context['danh_sach'][0].tieu_de, 'Muc 24')
        self.assertEqual(len(self.client.get(self.url, {'page': 2}).context['danh_sach']), 5)

    def test_khong_co_thong_bao_nao(self):
        self.client.force_login(self.tk_pdt)
        self.assertContains(self.client.get(self.url), 'Chưa có thông báo nào được gửi.')

    def test_vai_tro_khac_bi_chan_va_chua_dang_nhap_chuyen_ve_dang_nhap(self):
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=f'dg_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU_HOP_LE))
            self.assertEqual(self.client.get(self.url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_tab_gui_thong_bao_sang_o_trang_da_gui(self):
        self.client.force_login(self.tk_pdt)
        menu = re.search(r'<nav class="sv-menu".*?</nav>', self.client.get(self.url).content.decode(), re.S).group(0)
        self.assertIn(f'sv-menu__muc sv-menu__muc--chon" href="{reverse("thong_bao:gui_phong_dao_tao")}"', menu)


class TrangChuGiangVienTest(TestCase):
    """Trang chủ Giảng viên: số liệu tổng quan, cảnh báo cần chú ý, buổi dạy hôm nay, thông báo gần đây."""

    def setUp(self):
        self.hom_nay = timezone.localdate()
        self.hom_qua = self.hom_nay - timedelta(days=1)
        bay_gio = timezone.now()
        self.thu_hom_nay = self.hom_nay.weekday() + 2
        self.thu_hom_qua = self.hom_qua.weekday() + 2
        self.thu_mai = (self.hom_nay + timedelta(days=1)).weekday() + 2

        self.tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_gv', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        self.gv = GiangVien.objects.create(
            ma_giang_vien='GV_HOME', ho_ten='GV', email='gv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=self.tk_gv,
        )
        tk_khac = TaiKhoan.objects.create_user(ten_dang_nhap='gv_khac', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        self.gv_khac = GiangVien.objects.create(
            ma_giang_vien='GV_KHAC', ho_ten='GV khác', email='gv2@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_khac,
        )
        self.hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau=self.hom_nay - timedelta(days=30), ngay_ket_thuc=self.hom_nay + timedelta(days=60),
        )
        DotDangKy.objects.create(hoc_ky=self.hoc_ky, ngay_mo=bay_gio - timedelta(days=5), ngay_dong=bay_gio + timedelta(days=20))

        hoc_phan_a = HocPhan.objects.create(ma_hoc_phan='HP_GA', ten_hoc_phan='Học phần A', so_tin_chi=3)
        hoc_phan_b = HocPhan.objects.create(ma_hoc_phan='HP_GB', ten_hoc_phan='Học phần B', so_tin_chi=3)

        def tao_lop(ma, hoc_phan, giang_vien, hoc_ky='1', nam_hoc='2025-2026'):
            return LopHocPhan.objects.create(
                ma_lop_hoc_phan=ma, hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=30, ma_hoc_phan=hoc_phan, ma_giang_vien=giang_vien,
            )

        self.lop_a = tao_lop('L_GA', hoc_phan_a, self.gv)
        self.lop_b = tao_lop('L_GB', hoc_phan_b, self.gv)
        self.lop_cu = tao_lop('L_GCU', hoc_phan_a, self.gv, hoc_ky='2', nam_hoc='2024-2025')
        self.lop_khac = tao_lop('L_GKHAC', hoc_phan_a, self.gv_khac)

        nganh = NganhHoc.objects.create(ma_nganh='N_GV', ten_nganh='N')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_gv', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        co_van = CoVanHocTap.objects.create(ma_co_van='CV_GV', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv)
        lop_hc = LopHanhChinh.objects.create(ma_lop='L_HC_GV', ten_lop='L', ma_nganh=nganh, ma_co_van=co_van)

        def tao_sinh_vien(ma):
            tk = TaiKhoan.objects.create_user(ten_dang_nhap=f'sv_{ma}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
            return SinhVien.objects.create(
                ma_sinh_vien=ma, ho_ten=ma, ngay_sinh='2004-01-01', email=f'{ma}@test.local',
                so_dien_thoai='0900000000', ma_lop=lop_hc, ma_tai_khoan=tk,
            )

        self.sv1, self.sv2 = tao_sinh_vien('SV_G1'), tao_sinh_vien('SV_G2')
        for sv, lop in ((self.sv1, self.lop_a), (self.sv1, self.lop_b), (self.sv2, self.lop_a), (self.sv2, self.lop_khac)):
            DangKyHocPhan.objects.create(ma_sinh_vien=sv, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=bay_gio)
        dk_cu = DangKyHocPhan.objects.create(ma_sinh_vien=self.sv1, ma_lop_hoc_phan=self.lop_cu, thoi_gian_dang_ky=bay_gio)
        Diem.objects.create(ma_dang_ky=dk_cu, diem_qua_trinh=7, diem_thi=8, da_cong_bo=False)

        # Lịch học: L_GA có buổi hôm nay (tiết 1-3) và ngày mai; L_GB có buổi hôm qua; lớp của giảng viên khác cũng hôm nay.
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_a, thu=self.thu_hom_nay, tiet_bat_dau=1, so_tiet=3, phong_hoc='P_GA')
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_a, thu=self.thu_mai, tiet_bat_dau=1, so_tiet=3, phong_hoc='P_GA2')
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_b, thu=self.thu_hom_qua, tiet_bat_dau=4, so_tiet=3, phong_hoc='P_GB')
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_khac, thu=self.thu_hom_nay, tiet_bat_dau=1, so_tiet=3, phong_hoc='P_KHAC')
        LichThi.objects.create(
            lop_hoc_phan=self.lop_a, ngay_thi=self.hom_nay + timedelta(days=3), gio_bat_dau=time(9, 30), thoi_luong_phut=90, phong_thi='PT1',
        )
        LichThi.objects.create(
            lop_hoc_phan=self.lop_khac, ngay_thi=self.hom_nay + timedelta(days=3), gio_bat_dau=time(9, 30), thoi_luong_phut=90, phong_thi='PT2',
        )
        self.client.force_login(self.tk_gv)
        self.url = reverse('accounts:trang_chu')

    def _trang(self):
        return self.client.get(self.url)

    def test_so_lieu_tong_quan_chi_tinh_lop_cua_chinh_giang_vien(self):
        tt = self._trang().context['tong_hop']
        self.assertEqual(tt['so_lop'], 2)             # L_GA, L_GB (L_GCU khác học kỳ, L_GKHAC của người khác)
        self.assertEqual(tt['so_sinh_vien'], 2)       # SV_G1, SV_G2 (đếm sinh viên khác nhau)
        self.assertEqual(tt['so_buoi_hom_nay'], 1)
        self.assertEqual(tt['so_buoi_tuan'], 3)
        self.assertEqual(tt['so_lop_chua_cong_bo'], 1)
        self.assertEqual(tt['hoc_ky_xet'], {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'dot'})

    def test_nam_o_tong_quan_co_nhan_va_lien_ket_xem_chi_tiet_mo_duoc(self):
        response = self._trang()
        for nhan in (
            'Lớp học phần đang phụ trách', 'Sinh viên đang đăng ký', 'Buổi dạy hôm nay', 'Buổi dạy trong tuần', 'Lớp còn điểm chưa công bố',
        ):
            self.assertContains(response, nhan)
        self.assertContains(response, 'luoi-tong-hop luoi-tong-hop--5')
        self.assertContains(response, 'Xem chi tiết', count=5)
        tt = response.context['tong_hop']
        for khoa in ('url_lop_phu_trach', 'url_lich_giang_day', 'url_lich_giang_day_luoi', 'url_thong_bao'):
            self.assertContains(response, f'href="{tt[khoa]}"')
            self.assertEqual(self.client.get(tt[khoa]).status_code, 200, khoa)

    def test_giang_vien_khac_thay_du_lieu_cua_minh(self):
        self.client.force_login(TaiKhoan.objects.get(ten_dang_nhap='gv_khac'))
        tt = self._trang().context['tong_hop']
        self.assertEqual((tt['so_lop'], tt['so_sinh_vien'], tt['so_buoi_hom_nay'], tt['so_lop_chua_cong_bo']), (1, 1, 1, 0))
        self.assertEqual([d['muc'] for d in tt['dong_canh_bao']], ['thi'])

    def test_canh_bao_moi_loai_mot_dong_dung_thu_tu_va_lien_ket_mo_duoc(self):
        response = self._trang()
        dong = response.context['tong_hop']['dong_canh_bao']
        self.assertEqual([d['muc'] for d in dong], ['diem', 'diem_danh', 'thi'])
        self.assertIn('1 lớp còn điểm chưa công bố: L_GCU.', dong[0]['noi_dung'])
        self.assertIn(f'1 lớp có buổi dạy hôm qua ({self.hom_qua:%d/%m/%Y}) chưa điểm danh: L_GB.', dong[1]['noi_dung'])
        self.assertIn('1 lịch thi trong 7 ngày tới: L_GA', dong[2]['noi_dung'])
        self.assertIn('09:30', dong[2]['noi_dung'])
        self.assertEqual(dong[0]['url'], reverse('grades:bang_diem_lop', args=['L_GCU']))
        self.assertEqual(dong[1]['url'], reverse('diem_danh:diem_danh_lop', args=['L_GB']) + f'?ngay={self.hom_qua.isoformat()}')
        self.assertContains(response, 'Cảnh báo cần chú ý')
        self.assertRegex(response.content.decode(), r'\.khoi-chu-y \{[^}]*background: var\(--mau-vang-nhat\)')
        for d in dong:
            self.assertContains(response, f'href="{d["url"].replace("&", "&amp;")}"')
            self.assertEqual(self.client.get(d['url']).status_code, 200, d['url'])

    def test_nhieu_lop_chua_cong_bo_thi_gop_mot_dong_tro_ve_lop_phu_trach(self):
        for i in range(4):
            lop = LopHocPhan.objects.create(
                ma_lop_hoc_phan=f'L_GCB{i}', hoc_ky='1', nam_hoc='2024-2025', si_so_toi_da=30,
                ma_hoc_phan=HocPhan.objects.get(pk='HP_GA'), ma_giang_vien=self.gv,
            )
            dk = DangKyHocPhan.objects.create(ma_sinh_vien=self.sv2, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now())
            Diem.objects.create(ma_dang_ky=dk, diem_qua_trinh=5, diem_thi=5, da_cong_bo=False)
        dong = self._trang().context['tong_hop']['dong_canh_bao'][0]
        self.assertIn('5 lớp còn điểm chưa công bố: L_GCB0, L_GCB1, L_GCB2 và 2 lớp khác.', dong['noi_dung'])
        self.assertEqual(dong['url'], reverse('classes:lop_phu_trach'))

    def test_diem_da_cong_bo_hoac_chua_nhap_khong_bi_canh_bao(self):
        Diem.objects.filter(ma_dang_ky__ma_lop_hoc_phan=self.lop_cu).update(da_cong_bo=True)
        self.assertEqual(self._trang().context['tong_hop']['so_lop_chua_cong_bo'], 0)
        Diem.objects.filter(ma_dang_ky__ma_lop_hoc_phan=self.lop_cu).update(da_cong_bo=False, diem_qua_trinh=None, diem_thi=None)
        self.assertEqual(self._trang().context['tong_hop']['so_lop_chua_cong_bo'], 0)

    def test_het_canh_bao_diem_danh_khi_da_diem_danh_hoac_hom_qua_ngoai_hoc_ky(self):
        DiemDanh.objects.create(lop_hoc_phan=self.lop_b, sinh_vien=self.sv1, ngay_diem_danh=self.hom_qua)
        self.assertNotIn('diem_danh', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])
        DiemDanh.objects.all().delete()
        self.assertIn('diem_danh', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])
        HocKy.objects.filter(pk=self.hoc_ky.pk).update(ngay_bat_dau=self.hom_nay)  # hôm qua chưa thuộc học kỳ
        self.assertNotIn('diem_danh', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])

    def test_lop_khong_co_sinh_vien_khong_bi_nhac_diem_danh(self):
        DangKyHocPhan.objects.filter(ma_lop_hoc_phan=self.lop_b).delete()
        self.assertNotIn('diem_danh', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])

    def test_lich_thi_qua_7_ngay_hoac_da_qua_khong_bi_nhac(self):
        LichThi.objects.filter(lop_hoc_phan=self.lop_a).update(ngay_thi=self.hom_nay + timedelta(days=8))
        self.assertNotIn('thi', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])
        LichThi.objects.filter(lop_hoc_phan=self.lop_a).update(ngay_thi=self.hom_qua)
        self.assertNotIn('thi', [d['muc'] for d in self._trang().context['tong_hop']['dong_canh_bao']])

    def test_an_khoi_canh_bao_khi_khong_co_gi(self):
        Diem.objects.all().delete()
        LichThi.objects.all().delete()
        DiemDanh.objects.create(lop_hoc_phan=self.lop_b, sinh_vien=self.sv1, ngay_diem_danh=self.hom_qua)
        response = self._trang()
        self.assertEqual(response.context['tong_hop']['dong_canh_bao'], [])
        self.assertNotContains(response, 'Cảnh báo cần chú ý')
        self.assertNotContains(response, '<section class="khoi-chu-y"')
        self.assertContains(response, 'Số liệu tổng quan')

    def test_buoi_day_hom_nay_chi_gom_lop_cua_minh(self):
        response = self._trang()
        self.assertContains(response, 'Buổi dạy hôm nay')
        self.assertContains(response, 'Phòng P_GA')
        self.assertContains(response, 'Học phần A')
        self.assertContains(response, 'Tiết 1, 3 tiết')
        self.assertNotContains(response, 'P_KHAC')
        self.assertNotContains(response, 'P_GB')

    def test_khong_co_buoi_day_hom_nay(self):
        LichHoc.objects.filter(thu=self.thu_hom_nay).delete()
        response = self._trang()
        self.assertContains(response, 'bạn không có buổi dạy nào')
        self.assertEqual(response.context['tong_hop']['so_buoi_hom_nay'], 0)

    def test_thong_bao_gan_day_dung_pham_vi_va_danh_dau_moi(self):
        tk_pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_gvtb', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        chua_doc = ThongBao.objects.create(tieu_de='TB chưa đọc', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA)
        da_doc = ThongBao.objects.create(tieu_de='TB đã đọc', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.GIANG_VIEN)
        DaDocThongBao.objects.create(thong_bao=da_doc, tai_khoan=self.tk_gv)
        ThongBao.objects.create(tieu_de='TB cho sinh viên', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.SINH_VIEN)
        ThongBao.objects.create(
            tieu_de='TB lớp người khác', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN, lop_hoc_phan=self.lop_khac,
        )
        ThongBao.objects.create(
            tieu_de='TB lớp của tôi', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HOC_PHAN, lop_hoc_phan=self.lop_a,
        )
        response = self._trang()
        tieu_de = {tb.tieu_de: tb.da_doc_boi_toi for tb in response.context['tong_hop']['thong_bao_gan_day']}
        self.assertEqual(tieu_de, {'TB chưa đọc': False, 'TB đã đọc': True, 'TB lớp của tôi': False})
        self.assertContains(response, 'Thông báo gần đây')
        self.assertContains(response, f'href="{reverse("thong_bao:danh_sach")}"')
        self.assertContains(response, 'Xem tất cả')
        self.assertContains(response, 'chip chip--con_hieu_luc">Mới', count=2)
        self.assertNotContains(response, 'TB cho sinh viên')
        self.assertNotContains(response, 'TB lớp người khác')
        self.assertEqual(chua_doc.da_doc.count(), 0)  # chỉ hiển thị, không tự đánh dấu đã đọc

    def test_toi_da_5_thong_bao(self):
        tk_pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_gvtb2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        for i in range(8):
            ThongBao.objects.create(tieu_de=f'TB {i}', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA)
        self.assertEqual(len(self._trang().context['tong_hop']['thong_bao_gan_day']), 5)

    def test_chua_co_thong_bao_nao(self):
        self.assertContains(self._trang(), 'Chưa có thông báo nào.')

    def test_khong_con_luoi_the_chuc_nang(self):
        noi_dung = self._trang().content.decode()
        for dau_hieu in ('<div class="nhom-chuc-nang', '<div class="luoi-the"', '<div class="the-chuc-nang"'):
            self.assertNotIn(dau_hieu, noi_dung)
        noi_dung_chinh = noi_dung[noi_dung.index('<main>'):noi_dung.index('</main>')]
        self.assertNotIn('Gửi thông báo lớp học phần', noi_dung_chinh)
        self.assertContains(self._trang(), 'Xin chào, gv_gv')
        # Các liên kết đã bỏ khỏi trang chủ vẫn có trên menu.
        menu = re.search(r'<nav class="sv-menu".*?</nav>', noi_dung, re.S).group(0)
        for ten_url in ('classes:lop_phu_trach', 'classes:lich_giang_day', 'thong_bao:gui_giang_vien'):
            self.assertIn(f'href="{reverse(ten_url)}"', menu)

    def test_tai_khoan_chua_gan_ho_so_giang_vien(self):
        tk = TaiKhoan.objects.create_user(ten_dang_nhap='gv_chua_ho_so', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        self.client.force_login(tk)
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['tong_hop']['co_ho_so'])
        self.assertContains(response, 'chưa gắn hồ sơ giảng viên')
        self.assertNotContains(response, 'Số liệu tổng quan')

    def test_danh_muc_hoc_ky_trong_van_hien_trang(self):
        DotDangKy.objects.all().delete()
        HocKy.objects.all().delete()
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        tt = response.context['tong_hop']
        self.assertIsNone(tt['hoc_ky_xet'])
        self.assertIsNone(tt['so_lop'])
        self.assertEqual((tt['so_sinh_vien'], tt['so_buoi_hom_nay'], tt['so_buoi_tuan']), (0, 0, 0))
        self.assertContains(response, 'Chưa có học kỳ nào trong danh mục.')

    def test_moi_hanh_dong_trong_cac_khoi_la_nut_ro_rang(self):
        noi_dung = self._trang().content.decode()
        bat_dau = noi_dung.index('<section class="khoi-tong-quan"')
        ket_thuc = noi_dung.index('</main>')
        cac_lien_ket = re.findall(r'<a [^>]*>', noi_dung[bat_dau:ket_thuc])
        self.assertGreaterEqual(len(cac_lien_ket), 5 + 3 + 2)
        for the in cac_lien_ket:
            self.assertIn('class="nut ', the)

    def test_html_can_bang_the(self):
        loi, con_mo = kiem_tra_can_bang_the(self._trang().content.decode())
        self.assertEqual((loi, con_mo), ([], []))

    def test_vai_tro_khac_khong_thay_cac_khoi_cua_giang_vien(self):
        self.client.force_login(TaiKhoan.objects.get(ten_dang_nhap='cv_gv'))
        response = self._trang()
        self.assertNotContains(response, 'Buổi dạy hôm nay')  # Cố vấn có bộ khối riêng của mình


class TrangChuCoVanTest(TestCase):
    """Trang chủ Cố vấn học tập: số liệu tổng quan, cảnh báo cần chú ý, sinh viên cần quan tâm, thông báo gần đây."""

    def setUp(self):
        hom_nay = timezone.localdate()
        bay_gio = timezone.now()
        self.tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_home', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        self.cv = CoVanHocTap.objects.create(
            ma_co_van='CV_HOME', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=self.tk_cv,
        )
        tk_cv2 = TaiKhoan.objects.create_user(ten_dang_nhap='cv_home2', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        self.cv2 = CoVanHocTap.objects.create(
            ma_co_van='CV_HOME2', ho_ten='CV2', email='cv2@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv2,
        )
        nganh = NganhHoc.objects.create(ma_nganh='N_CV', ten_nganh='N')
        self.lop1 = LopHanhChinh.objects.create(ma_lop='L_CV1', ten_lop='L1', ma_nganh=nganh, ma_co_van=self.cv)
        self.lop2 = LopHanhChinh.objects.create(ma_lop='L_CV2', ten_lop='L2', ma_nganh=nganh, ma_co_van=self.cv)
        self.lop_khac = LopHanhChinh.objects.create(ma_lop='L_CVK', ten_lop='LK', ma_nganh=nganh, ma_co_van=self.cv2)

        hk = HocKy.objects.create(hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau=hom_nay - timedelta(days=30), ngay_ket_thuc=hom_nay + timedelta(days=60))
        self.dot = DotDangKy.objects.create(hoc_ky=hk, ngay_mo=bay_gio - timedelta(days=5), ngay_dong=bay_gio + timedelta(days=20))

        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_cvh', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE)
        gv = GiangVien.objects.create(ma_giang_vien='GV_CVH', ho_ten='GV', email='gv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_gv)
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_CVH', ten_hoc_phan='HP', so_tin_chi=3)

        def tao_lop(ma, hoc_ky, nam_hoc):
            return LopHocPhan.objects.create(
                ma_lop_hoc_phan=ma, hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=30, ma_hoc_phan=hoc_phan, ma_giang_vien=gv,
            )

        self.lop_nay = tao_lop('LHP_CVH_NAY', '1', '2025-2026')
        self.lop_cu = [tao_lop(f'LHP_CVH_CU{i}', '2', '2024-2025') for i in (1, 2, 3)]

        def tao_sinh_vien(ma, lop):
            tk = TaiKhoan.objects.create_user(ten_dang_nhap=f'sv_{ma}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE)
            return SinhVien.objects.create(
                ma_sinh_vien=ma, ho_ten=f'Họ tên {ma}', ngay_sinh='2004-01-01', email=f'{ma}@test.local',
                so_dien_thoai='0900000000', ma_lop=lop, ma_tai_khoan=tk,
            )

        def dang_ky(sv, lop, diem=None):
            dk = DangKyHocPhan.objects.create(ma_sinh_vien=sv, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=bay_gio)
            if diem is not None:
                Diem.objects.create(ma_dang_ky=dk, diem_qua_trinh=diem, diem_thi=diem)

        self.sv_do = tao_sinh_vien('SV_CV_DO', self.lop1)          # rớt 2 học phần, TB 3.0 -> mức đỏ
        self.sv_vang = tao_sinh_vien('SV_CV_VANG', self.lop1)      # rớt 2 học phần nhưng TB 5.33 -> mức vàng
        self.sv_thuong = tao_sinh_vien('SV_CV_THUONG', self.lop2)  # đã đăng ký kỳ này, không cảnh báo
        self.sv_moi = tao_sinh_vien('SV_CV_MOI', self.lop2)        # chưa có gì
        self.sv_khac = tao_sinh_vien('SV_CV_KHAC', self.lop_khac)  # lớp của cố vấn khác, cũng bị cảnh báo
        for lop in self.lop_cu[:2]:
            dang_ky(self.sv_do, lop, diem=3)
            dang_ky(self.sv_khac, lop, diem=3)
        for lop, diem in zip(self.lop_cu, (3, 3, 10)):
            dang_ky(self.sv_vang, lop, diem=diem)
        dang_ky(self.sv_thuong, self.lop_nay)
        self.client.force_login(self.tk_cv)
        self.url = reverse('accounts:trang_chu')

    def _trang(self):
        return self.client.get(self.url)

    def test_so_lieu_tong_quan_chi_tinh_sinh_vien_cua_chinh_co_van(self):
        tt = self._trang().context['tong_hop']
        self.assertEqual((tt['so_lop'], tt['ma_lop']), (2, ['L_CV1', 'L_CV2']))
        self.assertEqual(tt['so_sinh_vien'], 4)  # không có SV_CV_KHAC
        self.assertEqual((tt['so_canh_bao'], tt['so_canh_bao_do']), (2, 1))
        self.assertEqual(tt['so_chua_dang_ky'], 3)  # SV_CV_DO, SV_CV_VANG, SV_CV_MOI chưa đăng ký kỳ 2025-2026
        self.assertEqual(tt['hoc_ky_xet'], {'hoc_ky': '1', 'nam_hoc': '2025-2026', 'nguon': 'dot'})

    def test_khop_dung_so_dong_cua_trang_canh_bao_hoc_vu(self):
        tt = self._trang().context['tong_hop']
        danh_sach = self.client.get(reverse('grades:canh_bao_co_van')).context['danh_sach']
        self.assertEqual(tt['so_canh_bao'], len(danh_sach))

    def test_nam_o_tong_quan_co_nhan_va_lien_ket_xem_chi_tiet_mo_duoc(self):
        response = self._trang()
        for nhan in (
            'Lớp hành chính phụ trách', 'Sinh viên phụ trách', 'Sinh viên bị cảnh báo học vụ',
            'Chưa đăng ký học phần (học kỳ đang xét)', 'Thông báo chưa đọc',
        ):
            self.assertContains(response, nhan)
        self.assertContains(response, 'luoi-tong-hop luoi-tong-hop--5')
        self.assertContains(response, 'Xem chi tiết', count=5)
        self.assertContains(response, '(1 mức đỏ)')
        self.assertContains(response, 'L_CV1, L_CV2')
        tt = response.context['tong_hop']
        for khoa in ('url_sinh_vien_phu_trach', 'url_canh_bao', 'url_thong_bao'):
            self.assertContains(response, f'href="{tt[khoa]}"')
            self.assertEqual(self.client.get(tt[khoa]).status_code, 200, khoa)

    def test_canh_bao_moi_loai_mot_dong_dung_thu_tu(self):
        response = self._trang()
        dong = response.context['tong_hop']['dong_canh_bao']
        self.assertEqual([d['muc'] for d in dong], ['do', 'chua_dang_ky'])
        self.assertIn('1 sinh viên bị cảnh báo học vụ mức đỏ', dong[0]['noi_dung'])
        self.assertIn('SV_CV_DO', dong[0]['noi_dung'])
        self.assertNotIn('SV_CV_VANG', dong[0]['noi_dung'])  # mức vàng không nằm ở dòng mức đỏ
        self.assertIn('3 sinh viên chưa đăng ký học phần nào trong Học kỳ 1 năm học 2025-2026 (đang trong đợt đăng ký)', dong[1]['noi_dung'])
        self.assertIn('SV_CV_DO, SV_CV_MOI, SV_CV_VANG', dong[1]['noi_dung'])
        self.assertContains(response, 'Cảnh báo cần chú ý')
        for d in dong:
            self.assertContains(response, f'href="{d["url"]}"')
            self.assertEqual(self.client.get(d['url']).status_code, 200, d['url'])

    def test_dong_chua_dang_ky_chi_hien_khi_dang_trong_dot_dang_ky(self):
        DotDangKy.objects.all().delete()
        tt = self._trang().context['tong_hop']
        self.assertEqual(tt['hoc_ky_xet']['nguon'], 'danh_muc')
        self.assertEqual([d['muc'] for d in tt['dong_canh_bao']], ['do'])
        self.assertEqual(tt['so_chua_dang_ky'], 3)  # ô số liệu vẫn có

    def test_rut_gon_danh_sach_sinh_vien_trong_dong_canh_bao(self):
        for i in range(4):
            sv = SinhVien.objects.create(
                ma_sinh_vien=f'SV_CVX{i}', ho_ten='X', ngay_sinh='2004-01-01', email=f'x{i}@test.local', so_dien_thoai='0900000000',
                ma_lop=self.lop2, ma_tai_khoan=TaiKhoan.objects.create_user(ten_dang_nhap=f'sv_cvx{i}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE),
            )
            self.assertTrue(sv.pk)
        noi_dung = self._trang().context['tong_hop']['dong_canh_bao'][1]['noi_dung']
        self.assertIn('7 sinh viên chưa đăng ký', noi_dung)
        self.assertRegex(noi_dung, r': [\w, ]+ và 4 sinh viên khác\.$')

    def test_an_khoi_canh_bao_khi_khong_co_gi(self):
        Diem.objects.all().delete()
        for sv in (self.sv_do, self.sv_vang, self.sv_moi):
            DangKyHocPhan.objects.create(ma_sinh_vien=sv, ma_lop_hoc_phan=self.lop_nay, thoi_gian_dang_ky=timezone.now())
        response = self._trang()
        self.assertEqual(response.context['tong_hop']['dong_canh_bao'], [])
        self.assertNotContains(response, 'Cảnh báo cần chú ý')
        self.assertNotContains(response, '<section class="khoi-chu-y"')
        self.assertContains(response, 'Số liệu tổng quan')
        self.assertContains(response, 'Không có sinh viên nào bị cảnh báo học vụ.')

    def test_sinh_vien_can_quan_tam_muc_do_truoc_va_co_lien_ket_bang_diem(self):
        response = self._trang()
        can_quan_tam = response.context['tong_hop']['can_quan_tam']
        self.assertEqual([(d['sinh_vien'].pk, d['muc_do']) for d in can_quan_tam], [('SV_CV_DO', True), ('SV_CV_VANG', False)])
        self.assertContains(response, 'Sinh viên cần quan tâm')
        self.assertContains(response, 'Mức đỏ')
        self.assertContains(response, 'Mức vàng')
        self.assertContains(response, 'chip chip--muc-do')
        self.assertContains(response, 'Họ tên SV_CV_DO')
        self.assertContains(response, 'Lớp L_CV1')
        self.assertNotContains(response, 'SV_CV_KHAC')
        for d in can_quan_tam:
            url = reverse('grades:bang_diem_sinh_vien', args=[d['sinh_vien'].pk])
            self.assertContains(response, f'href="{url}"')
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_toi_da_5_sinh_vien_can_quan_tam(self):
        for i in range(6):
            sv = SinhVien.objects.create(
                ma_sinh_vien=f'SV_CVQ{i}', ho_ten='Q', ngay_sinh='2004-01-01', email=f'q{i}@test.local', so_dien_thoai='0900000000',
                ma_lop=self.lop2, ma_tai_khoan=TaiKhoan.objects.create_user(ten_dang_nhap=f'sv_cvq{i}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE),
            )
            for lop in self.lop_cu[:2]:
                DangKyHocPhan.objects.create(ma_sinh_vien=sv, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now())
                Diem.objects.create(ma_dang_ky=DangKyHocPhan.objects.get(ma_sinh_vien=sv, ma_lop_hoc_phan=lop), diem_qua_trinh=2, diem_thi=2)
        tt = self._trang().context['tong_hop']
        self.assertEqual(tt['so_canh_bao'], 8)
        self.assertEqual(len(tt['can_quan_tam']), 5)
        self.assertTrue(all(d['muc_do'] for d in tt['can_quan_tam']))  # mức đỏ xếp trước mức vàng

    def test_thong_bao_gan_day_dung_pham_vi_va_dem_chua_doc(self):
        tk_pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_cvtb', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        ThongBao.objects.create(tieu_de='TB chưa đọc', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA)
        da_doc = ThongBao.objects.create(tieu_de='TB đã đọc', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.CO_VAN_HOC_TAP)
        DaDocThongBao.objects.create(thong_bao=da_doc, tai_khoan=self.tk_cv)
        ThongBao.objects.create(tieu_de='TB cho sinh viên', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.SINH_VIEN)
        ThongBao.objects.create(
            tieu_de='TB lớp của tôi', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH, lop_hanh_chinh=self.lop1,
        )
        ThongBao.objects.create(
            tieu_de='TB lớp người khác', noi_dung='x', nguoi_gui=tk_pdt, doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH, lop_hanh_chinh=self.lop_khac,
        )
        response = self._trang()
        tt = response.context['tong_hop']
        tieu_de = {tb.tieu_de: tb.da_doc_boi_toi for tb in tt['thong_bao_gan_day']}
        self.assertEqual(tieu_de, {'TB chưa đọc': False, 'TB đã đọc': True, 'TB lớp của tôi': False})
        self.assertEqual(tt['so_thong_bao_chua_doc'], 2)
        self.assertContains(response, 'Thông báo gần đây')
        self.assertContains(response, 'chip chip--con_hieu_luc">Mới', count=2)
        self.assertNotContains(response, 'TB cho sinh viên')
        self.assertNotContains(response, 'TB lớp người khác')
        self.assertContains(response, f'href="{reverse("thong_bao:danh_sach")}"')

    def test_chua_co_thong_bao_nao(self):
        self.assertContains(self._trang(), 'Chưa có thông báo nào.')

    def test_co_van_khac_chi_thay_du_lieu_cua_minh(self):
        self.client.force_login(self.tk_cv.__class__.objects.get(ten_dang_nhap='cv_home2'))
        tt = self._trang().context['tong_hop']
        self.assertEqual((tt['so_lop'], tt['so_sinh_vien'], tt['so_canh_bao'], tt['so_canh_bao_do']), (1, 1, 1, 1))
        self.assertEqual([d['sinh_vien'].pk for d in tt['can_quan_tam']], ['SV_CV_KHAC'])

    def test_khong_con_luoi_the_chuc_nang_va_lien_ket_van_co_tren_menu(self):
        noi_dung = self._trang().content.decode()
        for dau_hieu in ('<div class="nhom-chuc-nang', '<div class="luoi-the"', '<div class="the-chuc-nang"'):
            self.assertNotIn(dau_hieu, noi_dung)
        noi_dung_chinh = noi_dung[noi_dung.index('<main>'):noi_dung.index('</main>')]
        for the in ('Trợ lý AI', 'Tóm tắt kết quả học tập sinh viên', 'Gửi thông báo lớp hành chính'):
            self.assertNotIn(the, noi_dung_chinh)
        self.assertContains(self._trang(), 'Xin chào, cv_home')
        menu = re.search(r'<nav class="sv-menu".*?</nav>', noi_dung, re.S).group(0)
        for ten_url in (
            'enrollment:sinh_vien_phu_trach', 'tien_do_hoc_tap:co_van', 'grades:canh_bao_co_van', 'tom_tat_ket_qua:co_van',
            'hoi_dap_quy_che:trang_chat', 'thong_bao:gui_co_van',
        ):
            self.assertIn(f'href="{reverse(ten_url)}"', menu, ten_url)

    def test_tai_khoan_chua_gan_ho_so_co_van(self):
        tk = TaiKhoan.objects.create_user(ten_dang_nhap='cv_chua_ho_so', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE)
        self.client.force_login(tk)
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['tong_hop']['co_ho_so'])
        self.assertContains(response, 'chưa gắn hồ sơ cố vấn học tập')
        self.assertNotContains(response, 'Số liệu tổng quan')

    def test_chua_phu_trach_lop_nao_va_danh_muc_hoc_ky_trong_van_hien_trang(self):
        LopHanhChinh.objects.filter(ma_co_van=self.cv).update(ma_co_van=self.cv2)
        DotDangKy.objects.all().delete()
        HocKy.objects.all().delete()
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        tt = response.context['tong_hop']
        self.assertEqual((tt['so_lop'], tt['so_sinh_vien'], tt['so_canh_bao']), (0, 0, 0))
        self.assertIsNone(tt['so_chua_dang_ky'])
        self.assertContains(response, 'Chưa có học kỳ nào trong danh mục.')

    def test_moi_hanh_dong_trong_cac_khoi_la_nut_ro_rang(self):
        noi_dung = self._trang().content.decode()
        bat_dau = noi_dung.index('<section class="khoi-tong-quan"')
        ket_thuc = noi_dung.index('</main>')
        cac_lien_ket = re.findall(r'<a [^>]*>', noi_dung[bat_dau:ket_thuc])
        self.assertGreaterEqual(len(cac_lien_ket), 5 + 2 + 2 + 2)
        for the in cac_lien_ket:
            self.assertIn('class="nut ', the)

    def test_html_can_bang_the(self):
        loi, con_mo = kiem_tra_can_bang_the(self._trang().content.decode())
        self.assertEqual((loi, con_mo), ([], []))


class TrangChuSinhVienTest(TestCase):
    """Trang chủ Sinh viên (lượt giao diện 2/3): tóm tắt học tập, cảnh báo, sắp diễn ra, thông báo."""

    def setUp(self):
        self.hom_nay = timezone.localdate()
        self.tk_pdt = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_tc', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE
        )
        tk_cv = TaiKhoan.objects.create_user(
            ten_dang_nhap='cv_tc', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU_HOP_LE
        )
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_TC', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        tk_gv = TaiKhoan.objects.create_user(
            ten_dang_nhap='gv_tc', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_TC', ho_ten='Giảng viên', email='gv@test.local', so_dien_thoai='0900000000',
            ma_tai_khoan=tk_gv,
        )
        self.nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
        self.lop = LopHanhChinh.objects.create(ma_lop='TC_LOP', ten_lop='Lớp trang chủ', ma_nganh=self.nganh, ma_co_van=co_van)
        self.tk_sv = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv_tc', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='SV_TC', ho_ten='Nguyễn Văn Trang', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=self.lop, ma_tai_khoan=self.tk_sv,
        )
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=4)
        self.client.force_login(self.tk_sv)

    def _gan_chuong_trinh(self):
        chuong_trinh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh, ten_chuong_trinh='Kỹ thuật phần mềm', khoa_hoc='Khóa 1',
        )
        for hoc_phan in (self.csdl, self.ctdl):
            ChiTietChuongTrinh.objects.create(
                chuong_trinh=chuong_trinh, hoc_phan=hoc_phan, hoc_ky_du_kien=1, bat_buoc=True,
            )
        self.lop.chuong_trinh_dao_tao = chuong_trinh
        self.lop.save(update_fields=['chuong_trinh_dao_tao'])

    def _dang_ky(self, ma_lop, hoc_phan, hoc_ky='1', nam_hoc='2025-2026', diem=None, da_cong_bo=True,
                 trang_thai=TrangThaiDangKy.CON_HIEU_LUC):
        lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan=ma_lop, hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
            trang_thai=trang_thai,
        )
        if diem is not None:
            Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=diem[0], diem_thi=diem[1], da_cong_bo=da_cong_bo)
        return lop_hoc_phan

    def _trang_chu(self):
        return self.client.get(reverse('accounts:trang_chu'))

    def test_chao_mung_co_ten_ma_so_va_lop(self):
        response = self._trang_chu()
        self.assertContains(response, 'Xin chào, Nguyễn Văn Trang')
        self.assertContains(response, 'SV_TC')
        self.assertContains(response, 'Lớp trang chủ')

    def test_khong_vai_tro_nao_con_luoi_the_chuc_nang_o_trang_chu(self):
        self.assertNotContains(self._trang_chu(), '<div class="the-chuc-nang">')
        # Phòng Đào tạo: menu trên thanh đã có đủ liên kết nên trang chủ chỉ còn 3 khối tổng hợp (xem TrangChuPhongDaoTaoTest).
        self.client.force_login(self.tk_pdt)
        self.assertNotContains(self._trang_chu(), '<div class="the-chuc-nang">')
        # Giảng viên và Cố vấn cũng đã chuyển sang các khối tổng hợp (xem TrangChuGiangVienTest, TrangChuCoVanTest).
        for ten, vai_tro in (('gv_the', VaiTro.GIANG_VIEN), ('cv_the', VaiTro.CO_VAN_HOC_TAP)):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=ten, vai_tro=vai_tro, password=MAT_KHAU_HOP_LE))
            self.assertNotContains(self._trang_chu(), '<div class="the-chuc-nang">')

    def test_o_tom_tat_co_so_lieu_va_chuong_trinh(self):
        self._gan_chuong_trinh()
        self._dang_ky('CSDL_TC', self.csdl, diem=(8, 8))
        response = self._trang_chu()
        tom_tat = response.context['tong_hop']['tom_tat']
        self.assertEqual(str(tom_tat['diem_tb_tich_luy']), '8.00')
        self.assertEqual(tom_tat['xep_loai'], 'Giỏi')
        self.assertEqual((tom_tat['tin_chi_tich_luy'], tom_tat['tong_tin_chi']), (3, 7))
        self.assertEqual(tom_tat['phan_tram_hoan_thanh'], 50.0)
        self.assertEqual((tom_tat['so_bat_buoc_da_dat'], tom_tat['tong_so_bat_buoc']), (1, 2))
        self.assertContains(response, '<div class="o-tong-hop__gia-tri">8,00</div>')
        self.assertContains(response, '3 <small>/ 7</small>')
        self.assertContains(response, '50,0%')
        self.assertContains(response, 'width: 50.0%;')

    def test_chua_co_diem_hien_thong_bao_ngan_thay_vi_so(self):
        self._gan_chuong_trinh()
        response = self._trang_chu()
        self.assertIsNone(response.context['tong_hop']['tom_tat']['diem_tb_tich_luy'])
        self.assertContains(response, 'Chưa có điểm đã công bố.')
        self.assertContains(response, 'Chưa có điểm để xếp loại.')
        self.assertContains(response, 'Chưa có học kỳ nào đủ điểm đã công bố.')

    def test_diem_chua_cong_bo_khong_duoc_tinh(self):
        self._dang_ky('CSDL_TC', self.csdl, diem=(8, 8), da_cong_bo=False)
        tom_tat = self._trang_chu().context['tong_hop']['tom_tat']
        self.assertIsNone(tom_tat['diem_tb_tich_luy'])
        self.assertIsNone(tom_tat['hoc_ky_gan_nhat'])

    def test_chua_gan_chuong_trinh_hien_thong_bao_thay_vi_so(self):
        self._dang_ky('CSDL_TC', self.csdl, diem=(8, 8))
        response = self._trang_chu()
        self.assertFalse(response.context['tong_hop']['tom_tat']['co_chuong_trinh'])
        self.assertContains(response, 'Lớp hành chính chưa được gán chương trình đào tạo.', count=3)
        self.assertNotContains(response, 'o-tong-hop__gia-tri">50')
        self.assertNotContains(response, 'thanh-tien-do__fill" style=')

    def test_diem_trung_binh_hoc_ky_gan_nhat(self):
        self._dang_ky('CSDL_TC', self.csdl, hoc_ky='1', diem=(8, 8))
        self._dang_ky('CTDL_TC', self.ctdl, hoc_ky='2', diem=(6, 6))
        gan_nhat = self._trang_chu().context['tong_hop']['tom_tat']['hoc_ky_gan_nhat']
        self.assertEqual((gan_nhat['hoc_ky'], gan_nhat['nam_hoc']), ('2', '2025-2026'))
        self.assertEqual(str(gan_nhat['diem_tb']), '6.00')

    def test_canh_bao_muc_nhe_nen_vang_co_nut_xem_chi_tiet(self):
        self._dang_ky('CSDL_TC', self.csdl, diem=(2, 2))
        response = self._trang_chu()
        canh_bao = response.context['tong_hop']['canh_bao']
        self.assertEqual(canh_bao['muc'], 'nhe')
        self.assertEqual(len(canh_bao['ly_do']), 1)
        self.assertContains(response, '<section class="thong-bao--warning sv-canh-bao">')
        self.assertNotContains(response, '<section class="thong-bao--error sv-canh-bao">')
        url_chi_tiet = reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk])
        self.assertContains(
            response,
            f'<a class="nut nut-phu nut-nho" href="{url_chi_tiet}?hoc_ky=1&amp;nam_hoc=2025-2026">Xem chi tiết</a>',
        )

    def test_canh_bao_muc_nang_nen_do_nhat(self):
        self._dang_ky('CSDL_TC', self.csdl, diem=(2, 2))
        self._dang_ky('CTDL_TC', self.ctdl, diem=(2, 2))
        response = self._trang_chu()
        canh_bao = response.context['tong_hop']['canh_bao']
        self.assertEqual(canh_bao['muc'], 'nang')
        self.assertEqual(len(canh_bao['ly_do']), 2)
        self.assertContains(response, '<section class="thong-bao--error sv-canh-bao">')

    def test_khong_canh_bao_khi_diem_tot_hoac_chua_cong_bo(self):
        self._dang_ky('CSDL_TC', self.csdl, diem=(8, 8))
        self._dang_ky('CTDL_TC', self.ctdl, hoc_ky='2', diem=(1, 1), da_cong_bo=False)
        response = self._trang_chu()
        self.assertIsNone(response.context['tong_hop']['canh_bao'])
        self.assertNotContains(response, 'Cảnh báo học vụ')

    def test_lich_thi_sap_toi_chi_gom_lop_con_hieu_luc_tu_hom_nay(self):
        lop_sap_thi = self._dang_ky('CSDL_TC', self.csdl)
        lop_da_thi = self._dang_ky('CTDL_TC', self.ctdl)
        lop_da_huy = self._dang_ky(
            'HUY_TC', HocPhan.objects.create(ma_hoc_phan='HUY', ten_hoc_phan='Học phần đã hủy', so_tin_chi=2),
            trang_thai=TrangThaiDangKy.DA_HUY,
        )
        LichThi.objects.create(
            lop_hoc_phan=lop_sap_thi, ngay_thi=self.hom_nay + timedelta(days=10), gio_bat_dau='08:00',
            thoi_luong_phut=90, phong_thi='C303',
        )
        LichThi.objects.create(
            lop_hoc_phan=lop_da_thi, ngay_thi=self.hom_nay - timedelta(days=1), gio_bat_dau='08:00',
            thoi_luong_phut=90, phong_thi='C101',
        )
        LichThi.objects.create(
            lop_hoc_phan=lop_da_huy, ngay_thi=self.hom_nay + timedelta(days=5), gio_bat_dau='08:00',
            thoi_luong_phut=90, phong_thi='C202',
        )
        response = self._trang_chu()
        self.assertEqual([lt.lop_hoc_phan_id for lt in response.context['tong_hop']['lich_thi']], ['CSDL_TC'])
        self.assertContains(response, '<h2>Sắp diễn ra</h2>')
        self.assertContains(response, 'Phòng C303')
        self.assertNotContains(response, 'Phòng C101')
        self.assertNotContains(response, 'Phòng C202')
        self.assertContains(response, f'href="{reverse("enrollment:lich_thi")}">Xem tất cả lịch thi</a>')

    def test_lich_thi_toi_da_3_dong_gan_nhat(self):
        for so in range(5):
            lop = self._dang_ky(
                f'LT{so}_TC', HocPhan.objects.create(ma_hoc_phan=f'HP{so}', ten_hoc_phan=f'Học phần {so}', so_tin_chi=2),
            )
            LichThi.objects.create(
                lop_hoc_phan=lop, ngay_thi=self.hom_nay + timedelta(days=5 - so), gio_bat_dau='08:00',
                thoi_luong_phut=60, phong_thi=f'P{so}',
            )
        ma_cac_lop = [lt.lop_hoc_phan_id for lt in self._trang_chu().context['tong_hop']['lich_thi']]
        self.assertEqual(ma_cac_lop, ['LT4_TC', 'LT3_TC', 'LT2_TC'])

    def test_khong_co_du_lieu_thi_va_hoc_thi_khong_hien_khoi_sap_dien_ra(self):
        self._dang_ky('CSDL_TC', self.csdl)
        response = self._trang_chu()
        self.assertFalse(response.context['tong_hop']['co_sap_dien_ra'])
        self.assertNotContains(response, '<h2>Sắp diễn ra</h2>')

    def _tao_hoc_ky_hien_tai(self):
        return HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau=self.hom_nay - timedelta(days=30),
            ngay_ket_thuc=self.hom_nay + timedelta(days=60),
        )

    def test_buoi_hoc_hom_nay_va_tuan_nay_trong_hoc_ky_hien_tai(self):
        self._tao_hoc_ky_hien_tai()
        thu_hom_nay = self.hom_nay.weekday() + 2
        thu_khac = thu_hom_nay % 7 + 2
        lop_hien_tai = self._dang_ky('CSDL_TC', self.csdl, hoc_ky='1', nam_hoc='2025-2026')
        LichHoc.objects.create(ma_lop_hoc_phan=lop_hien_tai, thu=thu_hom_nay, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101')
        LichHoc.objects.create(ma_lop_hoc_phan=lop_hien_tai, thu=thu_khac, tiet_bat_dau=4, so_tiet=2, phong_hoc='B202')
        # Lớp của học kỳ khác (không phải học kỳ đang diễn ra) không được tính dù cùng thứ.
        lop_ky_khac = self._dang_ky('CTDL_TC', self.ctdl, hoc_ky='2', nam_hoc='2025-2026')
        LichHoc.objects.create(ma_lop_hoc_phan=lop_ky_khac, thu=thu_hom_nay, tiet_bat_dau=6, so_tiet=2, phong_hoc='Z999')

        response = self._trang_chu()
        buoi_hoc = response.context['tong_hop']['buoi_hoc']
        self.assertEqual((buoi_hoc['so_hom_nay'], buoi_hoc['so_tuan_nay']), (1, 2))
        ten_thu = buoi_hoc['ten_thu']
        self.assertContains(response, f'Hôm nay ({ten_thu}): <strong>1</strong> buổi')
        self.assertContains(response, 'Tuần này: <strong>2</strong> buổi')
        self.assertContains(response, 'Phòng A101')
        self.assertNotContains(response, 'Z999')
        self.assertContains(response, f'href="{reverse("enrollment:thoi_khoa_bieu")}">Xem thời khóa biểu</a>')

    def test_khong_hien_buoi_hoc_khi_khong_co_hoc_ky_dang_dien_ra(self):
        lop = self._dang_ky('CSDL_TC', self.csdl, hoc_ky='1', nam_hoc='2025-2026')
        LichHoc.objects.create(
            ma_lop_hoc_phan=lop, thu=self.hom_nay.weekday() + 2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101',
        )
        HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau=self.hom_nay - timedelta(days=200),
            ngay_ket_thuc=self.hom_nay - timedelta(days=100),
        )
        response = self._trang_chu()
        self.assertIsNone(response.context['tong_hop']['buoi_hoc'])
        self.assertNotContains(response, 'Buổi học')

    def test_buoi_hoc_bo_qua_dang_ky_da_huy(self):
        self._tao_hoc_ky_hien_tai()
        lop = self._dang_ky('CSDL_TC', self.csdl, trang_thai=TrangThaiDangKy.DA_HUY)
        LichHoc.objects.create(
            ma_lop_hoc_phan=lop, thu=self.hom_nay.weekday() + 2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101',
        )
        self.assertIsNone(self._trang_chu().context['tong_hop']['buoi_hoc'])

    def test_thong_bao_moi_nhat_toi_da_3_va_chip_moi_cho_thong_bao_chua_doc(self):
        cac_thong_bao = []
        for so in range(4):
            thong_bao = ThongBao.objects.create(
                tieu_de=f'Thông báo số {so}', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
            )
            ThongBao.objects.filter(pk=thong_bao.pk).update(thoi_gian_gui=timezone.now() - timedelta(hours=4 - so))
            cac_thong_bao.append(thong_bao)
        ThongBao.objects.create(
            tieu_de='Chỉ dành cho giảng viên', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.GIANG_VIEN,
        )
        # Thông báo mới nhất (số 3) đã đọc -> không có chip "Mới".
        self.client.get(reverse('thong_bao:chi_tiet', args=[cac_thong_bao[3].pk]))

        response = self._trang_chu()
        tieu_de = [tb.tieu_de for tb in response.context['tong_hop']['thong_bao_moi']]
        self.assertEqual(tieu_de, ['Thông báo số 3', 'Thông báo số 2', 'Thông báo số 1'])
        self.assertNotContains(response, 'Thông báo số 0')
        self.assertNotContains(response, 'Chỉ dành cho giảng viên')
        self.assertContains(response, '<span class="chip chip--con_hieu_luc">Mới</span>', count=2)
        self.assertContains(response, f'href="{reverse("thong_bao:chi_tiet", args=[cac_thong_bao[2].pk])}">Xem</a>')
        self.assertContains(response, f'href="{reverse("thong_bao:danh_sach")}">Xem tất cả thông báo</a>')

    def test_chua_co_thong_bao(self):
        self.assertContains(self._trang_chu(), 'Chưa có thông báo nào.')

    def test_tai_khoan_chua_gan_ho_so_van_vao_duoc_trang_chu(self):
        tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv_khong_ho_so', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE
        )
        self.client.force_login(tk)
        response = self._trang_chu()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['tong_hop']['co_ho_so'])
        self.assertContains(response, 'Tài khoản của bạn chưa gắn hồ sơ sinh viên.')
        self.assertNotContains(response, 'Tóm tắt học tập')
        self.assertContains(response, 'Thông báo mới nhất')

    def test_moi_hanh_dong_trong_noi_dung_la_nut_khong_phai_lien_ket_chu(self):
        self._gan_chuong_trinh()
        self._dang_ky('CSDL_TC', self.csdl, diem=(2, 2))
        ThongBao.objects.create(
            tieu_de='Một thông báo', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        noi_dung = self._trang_chu().content.decode()
        phan_main = re.search(r'<main>.*?</main>', noi_dung, re.S).group(0)
        the_a = re.findall(r'<a [^>]*>', phan_main)
        self.assertGreaterEqual(len(the_a), 4)
        for the in the_a:
            self.assertIn('class="nut', the)

    def test_khong_dung_chu_gach_chan_o_giao_dien_moi(self):
        self.assertNotIn('underline', self._trang_chu().content.decode())

    def test_html_can_bang_the_khi_co_day_du_du_lieu(self):
        self._gan_chuong_trinh()
        self._tao_hoc_ky_hien_tai()
        lop = self._dang_ky('CSDL_TC', self.csdl, diem=(2, 2))
        LichHoc.objects.create(
            ma_lop_hoc_phan=lop, thu=self.hom_nay.weekday() + 2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101',
        )
        LichThi.objects.create(
            lop_hoc_phan=lop, ngay_thi=self.hom_nay + timedelta(days=3), gio_bat_dau='08:00',
            thoi_luong_phut=60, phong_thi='C303',
        )
        ThongBao.objects.create(
            tieu_de='Một thông báo', noi_dung='...', nguoi_gui=self.tk_pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        loi, con_mo = kiem_tra_can_bang_the(self._trang_chu().content.decode())
        self.assertEqual(loi, [])
        self.assertEqual(con_mo, [])

    def test_html_layout_sinh_vien_can_bang_the(self):
        loi, con_mo = kiem_tra_can_bang_the(self.client.get(reverse('accounts:trang_chu')).content.decode())
        self.assertEqual(loi, [])
        self.assertEqual(con_mo, [])


class ThongBaoTuAnTest(TestCase):
    """Thông báo (django messages) dùng chung ở templates/base.html: tự mờ dần rồi ẩn sau 4 giây, có
    nút × tắt tay. JS không chạy được trong test Django nên kiểm tra mã nguồn hiển thị (cấu trúc,
    mốc thời gian, tính độc lập) — hành vi thật đã thử bằng trình duyệt không giao diện."""

    def setUp(self):
        # Đăng nhập thành công (success) rồi bị buộc đổi mật khẩu (warning): hai thông báo cùng lúc.
        self.tai_khoan = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv_tb', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU_HOP_LE, phai_doi_mat_khau=True,
        )

    def _trang_co_hai_thong_bao(self):
        return self.client.post(
            reverse('accounts:dang_nhap'), {'username': 'sv_tb', 'password': MAT_KHAU_HOP_LE}, follow=True,
        )

    def test_moi_thong_bao_co_nut_dong_va_danh_sach_duoc_danh_dau_tu_an(self):
        response = self._trang_co_hai_thong_bao()
        noi_dung = response.content.decode()
        self.assertContains(response, '<ul class="thong-bao" data-thong-bao-tu-an>')
        self.assertEqual(noi_dung.count('<li class="thong-bao--'), 2)
        self.assertEqual(noi_dung.count('<button type="button" class="thong-bao__dong" aria-label="Đóng thông báo">&times;</button>'), 2)
        self.assertContains(response, '<span class="thong-bao__noi-dung">Xin chào, sv_tb.</span>')
        self.assertContains(response, 'Bạn cần đổi mật khẩu trước khi tiếp tục sử dụng hệ thống.')

    def test_script_tu_an_4_giay_doc_lap_tung_thong_bao_va_khong_dung_thu_vien_ngoai(self):
        noi_dung = self._trang_co_hai_thong_bao().content.decode()
        self.assertNotIn('<script src', noi_dung)
        script = re.search(r'<script>\s*\(function \(\) \{\s*var THOI_GIAN_HIEN_MS.*?</script>', noi_dung, re.S).group(0)
        self.assertIn('THOI_GIAN_HIEN_MS = 4000', script)
        self.assertIn('THOI_GIAN_MO_MS = 300', script)
        # 4 giây tính từ khi trang tải xong.
        self.assertIn("window.addEventListener('load', batDauDemGio)", script)
        # Mỗi thông báo có bộ hẹn giờ riêng; nút × hủy đúng bộ hẹn giờ của thông báo đó.
        self.assertIn('boHenGio[chiSo] = setTimeout(function () { an(muc); }, THOI_GIAN_HIEN_MS)', script)
        self.assertIn('clearTimeout(boHenGio[chiSo])', script)
        # Chỉ nhắm tới danh sách messages, không đụng các danh sách .thong-bao khác (ghi chú trang AI...).
        self.assertIn("document.querySelector('ul[data-thong-bao-tu-an]')", script)

    def test_css_mo_dan_0_3_giay_va_nut_dong_o_goc_phai(self):
        noi_dung = self._trang_co_hai_thong_bao().content.decode()
        muc = re.search(r'ul\.thong-bao\[data-thong-bao-tu-an\] > li \{(.*?)\}', noi_dung, re.S).group(1)
        self.assertIn('transition: opacity .3s ease', muc)
        self.assertIn('padding-right: 44px', muc)
        self.assertIn('opacity: 0;', re.search(r'li\.thong-bao--dang-an \{(.*?)\}', noi_dung, re.S).group(1))
        nut = re.search(r'\.thong-bao__dong \{(.*?)\}', noi_dung, re.S).group(1)
        self.assertIn('position: absolute', nut)
        self.assertIn('right: 8px', nut)
        self.assertIn('cursor: pointer', nut)

    def test_trang_khong_co_thong_bao_khong_them_danh_sach_hay_script(self):
        self.client.force_login(self.tai_khoan)
        noi_dung = self.client.get(reverse('accounts:doi_mat_khau')).content.decode()
        self.assertNotIn('<ul class="thong-bao" data-thong-bao-tu-an>', noi_dung)
        self.assertNotIn('THOI_GIAN_HIEN_MS', noi_dung)

    def test_ap_dung_cho_ca_layout_cu_cua_vai_tro_khac(self):
        TaiKhoan.objects.create_user(ten_dang_nhap='pdt_tb', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        response = self.client.post(
            reverse('accounts:dang_nhap'), {'username': 'pdt_tb', 'password': MAT_KHAU_HOP_LE}, follow=True,
        )
        self.assertContains(response, '<header class="sv-banner">')
        self.assertContains(response, '<ul class="thong-bao" data-thong-bao-tu-an>')
        self.assertContains(response, '<span class="thong-bao__noi-dung">Xin chào, pdt_tb.</span>')
        self.assertContains(response, 'class="thong-bao__dong"', count=1)

    def test_html_can_bang_the_khi_co_thong_bao(self):
        loi, con_mo = kiem_tra_can_bang_the(self._trang_co_hai_thong_bao().content.decode())
        self.assertEqual((loi, con_mo), ([], []))

    def test_noi_dung_thong_bao_do_nguoi_dung_nhap_van_duoc_escape(self):
        pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_esc', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU_HOP_LE)
        self.client.force_login(pdt)
        response = self.client.post(reverse('accounts:tai_khoan_tao'), {
            'ten_dang_nhap': '<i>x</i>', 'vai_tro': VaiTro.SINH_VIEN, 'is_active': 'on', 'mat_khau': MAT_KHAU_HOP_LE,
        }, follow=True)
        # Tên tài khoản (do người dùng nhập) nằm trong nội dung thông báo tự ẩn: phải bị escape.
        self.assertContains(
            response,
            '<span class="thong-bao__noi-dung">Đã tạo tài khoản &quot;&lt;i&gt;x&lt;/i&gt;&quot;.</span>',
        )
        self.assertNotContains(response, '<i>x</i>')
