from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from academics.models import HocPhan, LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from classes.models import LopHocPhan
from diem_danh.models import DiemDanh
from enrollment.models import DangKyHocPhan, TrangThaiDangKy

from .models import CoVanHocTap, GiangVien, SinhVien

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


def _tao_lop_hanh_chinh(ma_lop='CNTT1'):
    nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
    tk_co_van = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'cv_{ma_lop}', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
    )
    co_van = CoVanHocTap.objects.create(
        ma_co_van=f'CV_{ma_lop}', ho_ten='Cố vấn Test', email='cv@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk_co_van,
    )
    return LopHanhChinh.objects.create(ma_lop=ma_lop, ten_lop=f'Lớp {ma_lop}', ma_nganh=nganh, ma_co_van=co_van)


class SinhVienCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.sinh_vien_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv001', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
        )
        self.lop = _tao_lop_hanh_chinh('CNTT1')
        self.client.force_login(self.phong_dao_tao)

    def test_tao_sinh_vien(self):
        response = self.client.post(reverse('people:sinh_vien_tao'), {
            'ma_sinh_vien': 'SV001',
            'ho_ten': 'Nguyễn Văn A',
            'ngay_sinh': '2004-01-01',
            'email': 'a@test.local',
            'so_dien_thoai': '0900000001',
            'ma_lop': self.lop.pk,
            'ma_tai_khoan': self.sinh_vien_tk.pk,
        })
        self.assertRedirects(response, reverse('people:sinh_vien_danh_sach'))
        self.assertTrue(SinhVien.objects.filter(pk='SV001').exists())

    def test_khong_the_gan_tai_khoan_da_dung_cho_sinh_vien_khac(self):
        SinhVien.objects.create(
            ma_sinh_vien='SV002', ho_ten='B', ngay_sinh='2004-01-01', email='b@test.local',
            so_dien_thoai='0900000002', ma_lop=self.lop, ma_tai_khoan=self.sinh_vien_tk,
        )
        response = self.client.post(reverse('people:sinh_vien_tao'), {
            'ma_sinh_vien': 'SV003',
            'ho_ten': 'C',
            'ngay_sinh': '2004-01-01',
            'email': 'c@test.local',
            'so_dien_thoai': '0900000003',
            'ma_lop': self.lop.pk,
            'ma_tai_khoan': self.sinh_vien_tk.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SinhVien.objects.filter(pk='SV003').exists())

    def test_khong_the_chon_tai_khoan_sai_vai_tro(self):
        response = self.client.post(reverse('people:sinh_vien_tao'), {
            'ma_sinh_vien': 'SV004',
            'ho_ten': 'D',
            'ngay_sinh': '2004-01-01',
            'email': 'd@test.local',
            'so_dien_thoai': '0900000004',
            'ma_lop': self.lop.pk,
            'ma_tai_khoan': self.phong_dao_tao.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SinhVien.objects.filter(pk='SV004').exists())

    def test_tim_kiem_theo_ma_va_ho_ten(self):
        SinhVien.objects.create(
            ma_sinh_vien='SV005', ho_ten='Trần Thị E', ngay_sinh='2004-01-01', email='e@test.local',
            so_dien_thoai='0900000005', ma_lop=self.lop, ma_tai_khoan=self.sinh_vien_tk,
        )
        response = self.client.get(reverse('people:sinh_vien_danh_sach'), {'q': 'Thị E'})
        self.assertContains(response, 'SV005')

    def test_loc_theo_lop_hanh_chinh(self):
        lop_khac = _tao_lop_hanh_chinh('CNTT2')
        SinhVien.objects.create(
            ma_sinh_vien='SV006', ho_ten='F', ngay_sinh='2004-01-01', email='f@test.local',
            so_dien_thoai='0900000006', ma_lop=lop_khac, ma_tai_khoan=self.sinh_vien_tk,
        )
        response = self.client.get(reverse('people:sinh_vien_danh_sach'), {'ma_lop': self.lop.pk})
        self.assertNotContains(response, 'SV006')


def _tao_file_excel(cac_dong):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(['Mã sinh viên', 'Họ tên', 'Ngày sinh', 'Email', 'Số điện thoại', 'Mã lớp hành chính', 'Tên đăng nhập'])
    for dong in cac_dong:
        sheet.append(dong)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        'sinh_vien.xlsx', buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


class XoaHoSoTest(TestCase):
    """Xóa hồ sơ sinh viên/giảng viên/cố vấn: chỉ khi chưa có dữ liệu đi kèm; tài khoản đăng nhập vẫn còn."""

    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_xhs', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU)
        self.client.force_login(self.phong_dao_tao)
        self.lop = _tao_lop_hanh_chinh('XHS')  # đã có cố vấn CV_XHS đang phụ trách lớp này

        self.tk_sv = TaiKhoan.objects.create_user(ten_dang_nhap='sv_xhs', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU)
        self.sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='SV_XHS', ho_ten='Sinh viên XHS', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=self.lop, ma_tai_khoan=self.tk_sv,
        )
        self.tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_xhs', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_XHS', ho_ten='Giảng viên XHS', email='gv@test.local', so_dien_thoai='0900000000',
            ma_tai_khoan=self.tk_gv,
        )
        self.tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_tu_do', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van_tu_do = CoVanHocTap.objects.create(
            ma_co_van='CV_TU_DO', ho_ten='Cố vấn chưa có lớp', email='cv@test.local', so_dien_thoai='0900000000',
            ma_tai_khoan=self.tk_cv,
        )
        self.url_sv = reverse('people:sinh_vien_xoa', args=['SV_XHS'])
        self.url_gv = reverse('people:giang_vien_xoa', args=['GV_XHS'])
        self.url_cv = reverse('people:co_van_xoa', args=['CV_TU_DO'])

    def _lop_hoc_phan(self):
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_XHS', ten_hoc_phan='HP', so_tin_chi=3)
        return LopHocPhan.objects.create(
            ma_lop_hoc_phan='LHP_XHS', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=10,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )

    def test_cac_danh_sach_co_nut_xoa(self):
        for ten_url, url in (
            ('people:sinh_vien_danh_sach', self.url_sv), ('people:giang_vien_danh_sach', self.url_gv),
            ('people:co_van_danh_sach', self.url_cv),
        ):
            self.assertContains(self.client.get(reverse(ten_url)), f'href="{url}"', msg_prefix=ten_url)

    def test_trang_xac_nhan_khong_xoa_va_neu_ro_tai_khoan_con_lai(self):
        for url, ma, tai_khoan in ((self.url_sv, 'SV_XHS', 'sv_xhs'), (self.url_gv, 'GV_XHS', 'gv_xhs'), (self.url_cv, 'CV_TU_DO', 'cv_tu_do')):
            response = self.client.get(url)
            self.assertContains(response, ma)
            self.assertContains(response, f'tài khoản đăng nhập "{tai_khoan}" vẫn còn')
            self.assertNotContains(response, 'chưa thể xóa')
        self.assertTrue(SinhVien.objects.filter(pk='SV_XHS').exists())

    def test_xoa_sinh_vien_chua_dung_giu_lai_tai_khoan(self):
        response = self.client.post(self.url_sv, follow=True)
        self.assertRedirects(response, reverse('people:sinh_vien_danh_sach'))
        self.assertContains(response, 'Đã xóa hồ sơ sinh viên')
        self.assertFalse(SinhVien.objects.filter(pk='SV_XHS').exists())
        self.assertTrue(TaiKhoan.objects.filter(ten_dang_nhap='sv_xhs').exists())

    def test_chan_xoa_sinh_vien_co_dang_ky_ke_ca_da_huy(self):
        lop = self._lop_hoc_phan()
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(), trang_thai=TrangThaiDangKy.DA_HUY,
        )
        response = self.client.post(self.url_sv, follow=True)
        self.assertRedirects(response, reverse('people:sinh_vien_danh_sach'))
        self.assertContains(response, '1 bản đăng ký học phần')
        self.assertContains(response, 'khóa tài khoản')
        self.assertTrue(SinhVien.objects.filter(pk='SV_XHS').exists())
        self.assertContains(self.client.get(self.url_sv), 'chưa thể xóa')

    def test_chan_xoa_sinh_vien_co_diem_danh(self):
        lop = self._lop_hoc_phan()
        DiemDanh.objects.create(lop_hoc_phan=lop, sinh_vien=self.sinh_vien, ngay_diem_danh=timezone.localdate())
        response = self.client.post(self.url_sv, follow=True)
        self.assertContains(response, '1 bản ghi điểm danh')
        self.assertTrue(SinhVien.objects.filter(pk='SV_XHS').exists())

    def test_xoa_giang_vien_chua_dung_va_chan_khi_co_lop_hoc_phan(self):
        self._lop_hoc_phan()
        response = self.client.post(self.url_gv, follow=True)
        self.assertContains(response, '1 lớp học phần đang phụ trách')
        self.assertTrue(GiangVien.objects.filter(pk='GV_XHS').exists())
        LopHocPhan.objects.all().delete()
        response = self.client.post(self.url_gv, follow=True)
        self.assertRedirects(response, reverse('people:giang_vien_danh_sach'))
        self.assertContains(response, 'Đã xóa hồ sơ giảng viên')
        self.assertFalse(GiangVien.objects.filter(pk='GV_XHS').exists())
        self.assertTrue(TaiKhoan.objects.filter(ten_dang_nhap='gv_xhs').exists())

    def test_xoa_co_van_chua_dung_va_chan_khi_dang_phu_trach_lop_hanh_chinh(self):
        LopHanhChinh.objects.filter(pk=self.lop.pk).update(ma_co_van=self.co_van_tu_do)
        response = self.client.post(self.url_cv, follow=True)
        self.assertContains(response, '1 lớp hành chính đang phụ trách')
        self.assertTrue(CoVanHocTap.objects.filter(pk='CV_TU_DO').exists())
        LopHanhChinh.objects.filter(pk=self.lop.pk).update(ma_co_van=CoVanHocTap.objects.get(pk='CV_XHS'))
        response = self.client.post(self.url_cv, follow=True)
        self.assertRedirects(response, reverse('people:co_van_danh_sach'))
        self.assertFalse(CoVanHocTap.objects.filter(pk='CV_TU_DO').exists())
        self.assertTrue(TaiKhoan.objects.filter(ten_dang_nhap='cv_tu_do').exists())

    def test_sau_khi_xoa_tai_khoan_khong_gan_ho_so_van_gan_lai_duoc(self):
        self.client.post(self.url_sv)
        response = self.client.post(reverse('people:sinh_vien_tao'), {
            'ma_sinh_vien': 'SV_MOI', 'ho_ten': 'Sinh viên mới', 'ngay_sinh': '2004-02-02', 'email': 'moi@test.local',
            'so_dien_thoai': '0900000001', 'ma_lop': self.lop.pk, 'ma_tai_khoan': self.tk_sv.pk,
        })
        self.assertRedirects(response, reverse('people:sinh_vien_danh_sach'))
        self.assertTrue(SinhVien.objects.filter(pk='SV_MOI', ma_tai_khoan=self.tk_sv).exists())

    def test_ho_so_khong_ton_tai_tra_ve_404(self):
        for ten_url in ('people:sinh_vien_xoa', 'people:giang_vien_xoa', 'people:co_van_xoa'):
            self.assertEqual(self.client.post(reverse(ten_url, args=['KHONG_CO'])).status_code, 404, ten_url)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        cac_url = (self.url_sv, self.url_gv, self.url_cv)
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            self.client.force_login(TaiKhoan.objects.create_user(ten_dang_nhap=f'q_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU))
            for url in cac_url:
                self.assertEqual(self.client.post(url).status_code, 403, (vai_tro, url))
        self.client.logout()
        for url in cac_url:
            self.assertEqual(self.client.post(url).status_code, 302, url)
        self.assertTrue(SinhVien.objects.filter(pk='SV_XHS').exists())
        self.assertTrue(GiangVien.objects.filter(pk='GV_XHS').exists())
        self.assertTrue(CoVanHocTap.objects.filter(pk='CV_TU_DO').exists())


class NhapSinhVienExcelTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_excel', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.lop = _tao_lop_hanh_chinh('CNTT_EXCEL1')
        self.client.force_login(self.phong_dao_tao)

    def test_nhap_du_lieu_hop_le_tao_ca_tai_khoan(self):
        file_excel = _tao_file_excel([
            ['SVE001', 'Nguyễn Văn X', '2004-05-01', 'x@test.local', '0911111111', self.lop.pk, ''],
        ])
        response = self.client.post(reverse('people:sinh_vien_nhap_excel'), {'file_excel': file_excel})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ket_qua']['so_thanh_cong'], 1)
        self.assertEqual(response.context['ket_qua']['loi'], [])

        sinh_vien = SinhVien.objects.get(pk='SVE001')
        self.assertEqual(sinh_vien.ma_tai_khoan.ten_dang_nhap, 'sve001')
        self.assertTrue(sinh_vien.ma_tai_khoan.phai_doi_mat_khau)

    def test_dong_thieu_cot_bat_buoc_bi_bao_loi(self):
        file_excel = _tao_file_excel([
            ['SVE002', '', '2004-05-01', 'y@test.local', '0911111112', self.lop.pk, ''],
        ])
        response = self.client.post(reverse('people:sinh_vien_nhap_excel'), {'file_excel': file_excel})
        self.assertFalse(SinhVien.objects.filter(pk='SVE002').exists())
        self.assertEqual(len(response.context['ket_qua']['loi']), 1)
        self.assertIn('Thiếu cột bắt buộc', response.context['ket_qua']['loi'][0]['loi'])
        self.assertEqual(response.context['ket_qua']['loi'][0]['dong'], 2)

    def test_dong_ma_lop_khong_ton_tai_bi_bao_loi(self):
        file_excel = _tao_file_excel([
            ['SVE003', 'Z', '2004-05-01', 'z@test.local', '0911111113', 'LOP_KHONG_CO', ''],
        ])
        response = self.client.post(reverse('people:sinh_vien_nhap_excel'), {'file_excel': file_excel})
        self.assertFalse(SinhVien.objects.filter(pk='SVE003').exists())
        self.assertIn('không tồn tại', response.context['ket_qua']['loi'][0]['loi'])

    def test_dong_ma_sinh_vien_trung_bi_loi_dong_khac_van_thanh_cong(self):
        SinhVien.objects.create(
            ma_sinh_vien='SVE004', ho_ten='Đã có', ngay_sinh='2004-01-01', email='old@test.local',
            so_dien_thoai='0900000000', ma_lop=self.lop,
            ma_tai_khoan=TaiKhoan.objects.create_user(
                ten_dang_nhap='sve004_cu', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU,
            ),
        )
        file_excel = _tao_file_excel([
            ['SVE004', 'Trùng', '2004-05-01', 'trung@test.local', '0911111114', self.lop.pk, ''],
            ['SVE005', 'Hợp lệ', '2004-05-01', 'hople@test.local', '0911111115', self.lop.pk, ''],
        ])
        response = self.client.post(reverse('people:sinh_vien_nhap_excel'), {'file_excel': file_excel})
        self.assertEqual(response.context['ket_qua']['so_thanh_cong'], 1)
        self.assertIn('đã tồn tại', response.context['ket_qua']['loi'][0]['loi'])
        self.assertTrue(SinhVien.objects.filter(pk='SVE005').exists())

    def test_dong_ten_dang_nhap_chi_dinh_duoc_su_dung(self):
        file_excel = _tao_file_excel([
            ['SVE006', 'Có tên đăng nhập', '2004-05-01', 'w@test.local', '0911111116', self.lop.pk, 'nguoidung_w'],
        ])
        self.client.post(reverse('people:sinh_vien_nhap_excel'), {'file_excel': file_excel})
        sinh_vien = SinhVien.objects.get(pk='SVE006')
        self.assertEqual(sinh_vien.ma_tai_khoan.ten_dang_nhap, 'nguoidung_w')

    def test_tai_mau_excel(self):
        response = self.client.get(reverse('people:sinh_vien_mau_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_sinh_vien_khong_vao_duoc_trang_nhap_excel(self):
        sinh_vien = TaiKhoan.objects.create_user(ten_dang_nhap='sv_excel', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU)
        self.client.force_login(sinh_vien)
        response = self.client.get(reverse('people:sinh_vien_nhap_excel'))
        self.assertEqual(response.status_code, 403)


class PhanQuyenNguoiDungTest(TestCase):
    def setUp(self):
        self.sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv999', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
        )

    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('people:sinh_vien_danh_sach'))
        self.assertEqual(response.status_code, 302)

    def test_sinh_vien_khong_vao_duoc_danh_sach_sinh_vien(self):
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('people:sinh_vien_danh_sach'))
        self.assertEqual(response.status_code, 403)
