from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import VaiTro
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan
from people.models import CoVanHocTap, GiangVien, SinhVien

from .models import ChiTietChuongTrinh, ChuongTrinhDaoTao, DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


class NganhHocHocPhanCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_nganh_hoc(self):
        response = self.client.post(reverse('academics:nganh_hoc_tao'), {
            'ma_nganh': 'CNTT', 'ten_nganh': 'Công nghệ thông tin',
        })
        self.assertRedirects(response, reverse('academics:nganh_hoc_danh_sach'))
        self.assertTrue(NganhHoc.objects.filter(pk='CNTT').exists())

    def test_tao_hoc_phan_hop_le(self):
        response = self.client.post(reverse('academics:hoc_phan_tao'), {
            'ma_hoc_phan': 'CSDL', 'ten_hoc_phan': 'Cơ sở dữ liệu', 'so_tin_chi': 3,
        })
        self.assertRedirects(response, reverse('academics:hoc_phan_danh_sach'))
        self.assertTrue(HocPhan.objects.filter(pk='CSDL').exists())

    def test_khong_the_tao_hoc_phan_so_tin_chi_khong_duong(self):
        response = self.client.post(reverse('academics:hoc_phan_tao'), {
            'ma_hoc_phan': 'CSDL2', 'ten_hoc_phan': 'Cơ sở dữ liệu 2', 'so_tin_chi': 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HocPhan.objects.filter(pk='CSDL2').exists())


class XoaHocPhanTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_xoa_hp', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_XOA', ten_hoc_phan='Học phần cần xóa', so_tin_chi=3)
        self.khac = HocPhan.objects.create(ma_hoc_phan='HP_KHAC', ten_hoc_phan='Học phần khác', so_tin_chi=3)
        self.url = reverse('academics:hoc_phan_xoa', args=[self.hoc_phan.pk])

    def _bi_chan(self, phan_mo_ta):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('academics:hoc_phan_danh_sach'))
        self.assertContains(response, phan_mo_ta)
        self.assertTrue(HocPhan.objects.filter(pk='HP_XOA').exists())

    def test_danh_sach_co_nut_xoa(self):
        response = self.client.get(reverse('academics:hoc_phan_danh_sach'))
        self.assertContains(response, self.url)

    def test_get_chi_hien_xac_nhan_khong_xoa(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Học phần cần xóa')
        self.assertNotContains(response, 'chưa thể xóa')
        self.assertTrue(HocPhan.objects.filter(pk='HP_XOA').exists())

    def test_xoa_hoc_phan_chua_dung(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('academics:hoc_phan_danh_sach'))
        self.assertContains(response, 'Đã xóa học phần')
        self.assertFalse(HocPhan.objects.filter(pk='HP_XOA').exists())
        self.assertTrue(HocPhan.objects.filter(pk='HP_KHAC').exists())

    def test_chan_xoa_khi_co_lop_hoc_phan(self):
        tk = TaiKhoan.objects.create_user(ten_dang_nhap='gv_xoa_hp', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_XHP', ho_ten='GV', email='gv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk,
        )
        LopHocPhan.objects.create(
            ma_lop_hoc_phan='LHP_XHP', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=10,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=giang_vien,
        )
        self._bi_chan('1 lớp học phần')
        self.assertContains(self.client.get(self.url), 'chưa thể xóa')

    def test_chan_xoa_khi_la_hoc_phan_co_tien_quyet(self):
        DieuKienTienQuyet.objects.create(ma_hoc_phan=self.hoc_phan, ma_hoc_phan_tien_quyet=self.khac)
        self._bi_chan('1 điều kiện tiên quyết')

    def test_chan_xoa_khi_la_hoc_phan_tien_quyet_cua_mon_khac(self):
        DieuKienTienQuyet.objects.create(ma_hoc_phan=self.khac, ma_hoc_phan_tien_quyet=self.hoc_phan)
        self._bi_chan('1 điều kiện tiên quyết')

    def test_chan_xoa_khi_nam_trong_chuong_trinh_dao_tao(self):
        nganh = NganhHoc.objects.create(ma_nganh='N_XHP', ten_nganh='Ngành')
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=nganh, ten_chuong_trinh='CT', khoa_hoc='Khóa 1')
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.hoc_phan, hoc_ky_du_kien=1)
        self._bi_chan('1 mục trong chương trình đào tạo')

    def test_xoa_hoc_phan_khong_ton_tai_tra_ve_404(self):
        self.assertEqual(self.client.post(reverse('academics:hoc_phan_xoa', args=['KHONG_CO'])).status_code, 404)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap=f'hp_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU)
            self.client.force_login(tai_khoan)
            self.assertEqual(self.client.post(self.url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(HocPhan.objects.filter(pk='HP_XOA').exists())


class XoaNganhHocTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_xoa_nganh', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='NGANH_XOA', ten_nganh='Ngành cần xóa')

    def _tao_lop_hanh_chinh(self):
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_xoa_nganh', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_XN', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        return LopHanhChinh.objects.create(ma_lop='LXN1', ten_lop='LXN1', ma_nganh=self.nganh, ma_co_van=co_van)

    def test_danh_sach_co_nut_xoa(self):
        response = self.client.get(reverse('academics:nganh_hoc_danh_sach'))
        self.assertContains(response, reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]))

    def test_trang_xac_nhan_hien_ten_nganh(self):
        response = self.client.get(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]))
        self.assertContains(response, 'Ngành cần xóa')

    def test_xoa_nganh_chua_dung(self):
        response = self.client.post(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]))
        self.assertRedirects(response, reverse('academics:nganh_hoc_danh_sach'))
        self.assertFalse(NganhHoc.objects.filter(pk='NGANH_XOA').exists())

    def test_chan_xoa_khi_con_lop_hanh_chinh(self):
        self._tao_lop_hanh_chinh()
        response = self.client.post(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]), follow=True)
        self.assertRedirects(response, reverse('academics:nganh_hoc_danh_sach'))
        self.assertContains(response, 'còn 1 lớp hành chính')
        self.assertTrue(NganhHoc.objects.filter(pk='NGANH_XOA').exists())

    def test_chan_xoa_khi_con_chuong_trinh_dao_tao(self):
        ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CT', khoa_hoc='Khóa 1')
        response = self.client.post(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]), follow=True)
        self.assertContains(response, 'còn 0 lớp hành chính và 1 chương trình')
        self.assertTrue(NganhHoc.objects.filter(pk='NGANH_XOA').exists())

    def test_trang_xac_nhan_canh_bao_khi_dang_dung(self):
        self._tao_lop_hanh_chinh()
        response = self.client.get(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]))
        self.assertContains(response, 'chưa thể xóa')

    def test_get_khong_xoa(self):
        self.client.get(reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk]))
        self.assertTrue(NganhHoc.objects.filter(pk='NGANH_XOA').exists())

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        url = reverse('academics:nganh_hoc_xoa', args=[self.nganh.pk])
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap=f'x_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU)
            self.client.force_login(tai_khoan)
            self.assertEqual(self.client.post(url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(NganhHoc.objects.filter(pk='NGANH_XOA').exists())


class DieuKienTienQuyetTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)

    def test_tao_dieu_kien_tien_quyet_hop_le(self):
        response = self.client.post(reverse('academics:dieu_kien_tien_quyet_tao'), {
            'ma_hoc_phan': self.csdl.pk, 'ma_hoc_phan_tien_quyet': self.ctdl.pk,
        })
        self.assertRedirects(response, reverse('academics:dieu_kien_tien_quyet_danh_sach'))
        self.assertTrue(DieuKienTienQuyet.objects.filter(
            ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl
        ).exists())

    def test_khong_the_hoc_phan_tien_quyet_cua_chinh_no(self):
        response = self.client.post(reverse('academics:dieu_kien_tien_quyet_tao'), {
            'ma_hoc_phan': self.csdl.pk, 'ma_hoc_phan_tien_quyet': self.csdl.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DieuKienTienQuyet.objects.filter(
            ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.csdl
        ).exists())

    def test_khong_the_trung_lap_dieu_kien_tien_quyet(self):
        DieuKienTienQuyet.objects.create(ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl)
        response = self.client.post(reverse('academics:dieu_kien_tien_quyet_tao'), {
            'ma_hoc_phan': self.csdl.pk, 'ma_hoc_phan_tien_quyet': self.ctdl.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            DieuKienTienQuyet.objects.filter(ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl).count(), 1
        )

    def test_tim_kiem_theo_ma_va_ten_hoc_phan_khong_loi(self):
        """Hồi quy: tìm theo mã học phần từng làm trang báo lỗi 500 (icontains trực tiếp trên khóa ngoại)."""
        attt = HocPhan.objects.create(ma_hoc_phan='ATTT', ten_hoc_phan='An toàn thông tin', so_tin_chi=3)
        mmt = HocPhan.objects.create(ma_hoc_phan='MMT', ten_hoc_phan='Mạng máy tính', so_tin_chi=3)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=attt, ma_hoc_phan_tien_quyet=mmt)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl)
        url = reverse('academics:dieu_kien_tien_quyet_danh_sach')

        def tim(tu_khoa):
            response = self.client.get(url, {'q': tu_khoa})
            self.assertEqual(response.status_code, 200, tu_khoa)
            return [(dk.ma_hoc_phan_id, dk.ma_hoc_phan_tien_quyet_id) for dk in response.context['danh_sach']]

        self.assertEqual(tim('ATTT'), [('ATTT', 'MMT')])
        self.assertEqual(tim('attt'), [('ATTT', 'MMT')])
        self.assertEqual(tim('MMT'), [('ATTT', 'MMT')])  # khớp cả học phần tiên quyết
        self.assertEqual(tim('toàn thông'), [('ATTT', 'MMT')])  # theo tên
        self.assertEqual(tim('CSDL'), [('CSDL', 'CTDL')])
        self.assertEqual(tim('khong-co'), [])
        self.assertEqual(len(tim('')), 2)


class XoaDieuKienTienQuyetTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_xoa_tq', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)
        self.dieu_kien = DieuKienTienQuyet.objects.create(ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl)

    def test_danh_sach_co_nut_xoa(self):
        response = self.client.get(reverse('academics:dieu_kien_tien_quyet_danh_sach'))
        self.assertContains(response, reverse('academics:dieu_kien_tien_quyet_xoa', args=[self.dieu_kien.pk]))

    def test_trang_xac_nhan_hien_ten_hai_hoc_phan_va_khong_xoa_khi_get(self):
        response = self.client.get(reverse('academics:dieu_kien_tien_quyet_xoa', args=[self.dieu_kien.pk]))
        self.assertContains(response, 'Cơ sở dữ liệu')
        self.assertContains(response, 'Cấu trúc dữ liệu')
        self.assertTrue(DieuKienTienQuyet.objects.filter(pk=self.dieu_kien.pk).exists())

    def test_xoa_dieu_kien_tien_quyet(self):
        response = self.client.post(reverse('academics:dieu_kien_tien_quyet_xoa', args=[self.dieu_kien.pk]), follow=True)
        self.assertRedirects(response, reverse('academics:dieu_kien_tien_quyet_danh_sach'))
        self.assertContains(response, 'Đã xóa điều kiện tiên quyết')
        self.assertFalse(DieuKienTienQuyet.objects.filter(pk=self.dieu_kien.pk).exists())
        # Hai học phần vẫn còn nguyên.
        self.assertTrue(HocPhan.objects.filter(pk__in=['CSDL', 'CTDL']).count() == 2)

    def test_sau_khi_xoa_co_the_tao_lai_dieu_kien_do(self):
        self.client.post(reverse('academics:dieu_kien_tien_quyet_xoa', args=[self.dieu_kien.pk]))
        response = self.client.post(reverse('academics:dieu_kien_tien_quyet_tao'), {
            'ma_hoc_phan': self.csdl.pk, 'ma_hoc_phan_tien_quyet': self.ctdl.pk,
        })
        self.assertRedirects(response, reverse('academics:dieu_kien_tien_quyet_danh_sach'))
        self.assertEqual(DieuKienTienQuyet.objects.count(), 1)

    def test_xoa_dieu_kien_khong_ton_tai_tra_ve_404(self):
        self.assertEqual(self.client.post(reverse('academics:dieu_kien_tien_quyet_xoa', args=[999999])).status_code, 404)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        url = reverse('academics:dieu_kien_tien_quyet_xoa', args=[self.dieu_kien.pk])
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap=f'tq_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU)
            self.client.force_login(tai_khoan)
            self.assertEqual(self.client.post(url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertTrue(DieuKienTienQuyet.objects.filter(pk=self.dieu_kien.pk).exists())


class LopHanhChinhTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt3', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_co_van = TaiKhoan.objects.create_user(
            ten_dang_nhap='cv01', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
        )
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV01', ho_ten='Cố vấn A', email='cv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_co_van,
        )

    def test_tao_lop_hanh_chinh(self):
        response = self.client.post(reverse('academics:lop_hanh_chinh_tao'), {
            'ma_lop': 'CNTT1', 'ten_lop': 'CNTT Khóa 1',
            'ma_nganh': self.nganh.pk, 'ma_co_van': self.co_van.pk,
        })
        self.assertRedirects(response, reverse('academics:lop_hanh_chinh_danh_sach'))
        self.assertTrue(LopHanhChinh.objects.filter(pk='CNTT1').exists())

    def test_loc_theo_nganh(self):
        LopHanhChinh.objects.create(ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=self.nganh, ma_co_van=self.co_van)
        nganh_khac = NganhHoc.objects.create(ma_nganh='KTPM', ten_nganh='Kỹ thuật phần mềm')
        LopHanhChinh.objects.create(ma_lop='KTPM1', ten_lop='KTPM K1', ma_nganh=nganh_khac, ma_co_van=self.co_van)
        response = self.client.get(reverse('academics:lop_hanh_chinh_danh_sach'), {'ma_nganh': self.nganh.pk})
        self.assertContains(response, 'CNTT1')
        self.assertNotContains(response, 'KTPM1')


class HocKyCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt4', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_hoc_ky_hop_le(self):
        response = self.client.post(reverse('academics:hoc_ky_tao'), {
            'hoc_ky': 1, 'nam_hoc': '2025-2026',
            'ngay_bat_dau': '2025-09-01', 'ngay_ket_thuc': '2026-01-15',
        })
        self.assertRedirects(response, reverse('academics:hoc_ky_danh_sach'))
        self.assertTrue(HocKy.objects.filter(hoc_ky=1, nam_hoc='2025-2026').exists())

    def test_khong_the_tao_trung_hoc_ky_nam_hoc(self):
        HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )
        response = self.client.post(reverse('academics:hoc_ky_tao'), {
            'hoc_ky': 1, 'nam_hoc': '2025-2026',
            'ngay_bat_dau': '2025-09-05', 'ngay_ket_thuc': '2026-01-20',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(HocKy.objects.filter(hoc_ky=1, nam_hoc='2025-2026').count(), 1)

    def test_khong_the_tao_nam_hoc_sai_dinh_dang(self):
        response = self.client.post(reverse('academics:hoc_ky_tao'), {
            'hoc_ky': 1, 'nam_hoc': '2025',
            'ngay_bat_dau': '2025-09-01', 'ngay_ket_thuc': '2026-01-15',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HocKy.objects.filter(hoc_ky=1).exists())

    def test_khong_the_tao_ngay_ket_thuc_truoc_ngay_bat_dau(self):
        response = self.client.post(reverse('academics:hoc_ky_tao'), {
            'hoc_ky': 1, 'nam_hoc': '2025-2026',
            'ngay_bat_dau': '2026-01-15', 'ngay_ket_thuc': '2025-09-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HocKy.objects.filter(hoc_ky=1, nam_hoc='2025-2026').exists())

    def test_sua_hoc_ky(self):
        hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )
        response = self.client.post(reverse('academics:hoc_ky_sua', args=[hoc_ky.pk]), {
            'hoc_ky': 1, 'nam_hoc': '2025-2026',
            'ngay_bat_dau': '2025-09-05', 'ngay_ket_thuc': '2026-01-20',
        })
        self.assertRedirects(response, reverse('academics:hoc_ky_danh_sach'))
        hoc_ky.refresh_from_db()
        self.assertEqual(str(hoc_ky.ngay_bat_dau), '2025-09-05')

    def test_xoa_hoc_ky_khong_dung_thi_xoa_duoc(self):
        hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )
        response = self.client.post(reverse('academics:hoc_ky_xoa', args=[hoc_ky.pk]))
        self.assertRedirects(response, reverse('academics:hoc_ky_danh_sach'))
        self.assertFalse(HocKy.objects.filter(pk=hoc_ky.pk).exists())

    def test_khong_the_xoa_hoc_ky_dang_duoc_lop_hoc_phan_su_dung(self):
        hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_hk', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_HK', ho_ten='Giảng viên A', email='gv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_HK', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=giang_vien,
        )
        response = self.client.post(reverse('academics:hoc_ky_xoa', args=[hoc_ky.pk]))
        self.assertRedirects(response, reverse('academics:hoc_ky_danh_sach'))
        self.assertTrue(HocKy.objects.filter(pk=hoc_ky.pk).exists())


def _ngay_gio(chuoi):
    """'YYYY-MM-DD HH:MM' -> giá trị datetime-local mà form DotDangKyForm chấp nhận."""
    return chuoi.replace(' ', 'T')


def _ngay_gio_aware(chuoi):
    """'YYYY-MM-DD HH:MM' -> datetime có timezone, để tạo DotDangKy thẳng qua ORM trong
    test (không qua form) mà không bị cảnh báo naive datetime khi USE_TZ=True."""
    return timezone.make_aware(datetime.strptime(chuoi, '%Y-%m-%d %H:%M'))


class DotDangKyCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt5', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )

    def test_tao_dot_dang_ky_hop_le(self):
        response = self.client.post(reverse('academics:dot_dang_ky_tao'), {
            'hoc_ky': self.hoc_ky.pk,
            'ngay_mo': _ngay_gio('2025-09-01 08:00'),
            'ngay_dong': _ngay_gio('2025-09-15 17:00'),
        })
        self.assertRedirects(response, reverse('academics:dot_dang_ky_danh_sach'))
        self.assertTrue(DotDangKy.objects.filter(hoc_ky=self.hoc_ky).exists())

    def test_khong_the_tao_ngay_dong_truoc_ngay_mo(self):
        response = self.client.post(reverse('academics:dot_dang_ky_tao'), {
            'hoc_ky': self.hoc_ky.pk,
            'ngay_mo': _ngay_gio('2025-09-15 08:00'),
            'ngay_dong': _ngay_gio('2025-09-01 17:00'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DotDangKy.objects.filter(hoc_ky=self.hoc_ky).exists())

    def test_khong_the_tao_hai_dot_chong_lap_cung_hoc_ky(self):
        DotDangKy.objects.create(
            hoc_ky=self.hoc_ky, ngay_mo=_ngay_gio_aware('2025-09-01 08:00'), ngay_dong=_ngay_gio_aware('2025-09-15 17:00'),
        )
        response = self.client.post(reverse('academics:dot_dang_ky_tao'), {
            'hoc_ky': self.hoc_ky.pk,
            'ngay_mo': _ngay_gio('2025-09-10 08:00'),
            'ngay_dong': _ngay_gio('2025-09-20 17:00'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DotDangKy.objects.filter(hoc_ky=self.hoc_ky).count(), 1)

    def test_hai_dot_khong_chong_lap_van_tao_duoc(self):
        DotDangKy.objects.create(
            hoc_ky=self.hoc_ky, ngay_mo=_ngay_gio_aware('2025-09-01 08:00'), ngay_dong=_ngay_gio_aware('2025-09-15 17:00'),
        )
        response = self.client.post(reverse('academics:dot_dang_ky_tao'), {
            'hoc_ky': self.hoc_ky.pk,
            'ngay_mo': _ngay_gio('2025-09-16 08:00'),
            'ngay_dong': _ngay_gio('2025-09-30 17:00'),
        })
        self.assertRedirects(response, reverse('academics:dot_dang_ky_danh_sach'))
        self.assertEqual(DotDangKy.objects.filter(hoc_ky=self.hoc_ky).count(), 2)

    def test_sua_dot_khong_tu_bao_chong_lap_voi_chinh_no(self):
        dot = DotDangKy.objects.create(
            hoc_ky=self.hoc_ky, ngay_mo=_ngay_gio_aware('2025-09-01 08:00'), ngay_dong=_ngay_gio_aware('2025-09-15 17:00'),
        )
        response = self.client.post(reverse('academics:dot_dang_ky_sua', args=[dot.pk]), {
            'hoc_ky': self.hoc_ky.pk,
            'ngay_mo': _ngay_gio('2025-09-02 08:00'),
            'ngay_dong': _ngay_gio('2025-09-16 17:00'),
        })
        self.assertRedirects(response, reverse('academics:dot_dang_ky_danh_sach'))
        dot.refresh_from_db()
        self.assertEqual(str(dot.ngay_mo.date()), '2025-09-02')

    def test_xoa_dot_khong_dung_thi_xoa_duoc(self):
        dot = DotDangKy.objects.create(
            hoc_ky=self.hoc_ky, ngay_mo=_ngay_gio_aware('2025-09-01 08:00'), ngay_dong=_ngay_gio_aware('2025-09-15 17:00'),
        )
        response = self.client.post(reverse('academics:dot_dang_ky_xoa', args=[dot.pk]))
        self.assertRedirects(response, reverse('academics:dot_dang_ky_danh_sach'))
        self.assertFalse(DotDangKy.objects.filter(pk=dot.pk).exists())

    def test_khong_the_xoa_dot_da_co_sinh_vien_dang_ky_trong_do(self):
        dot = DotDangKy.objects.create(
            hoc_ky=self.hoc_ky, ngay_mo=timezone.now() - timedelta(days=5), ngay_dong=timezone.now() + timedelta(days=5),
        )
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_dot', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_DOT', ho_ten='Giảng viên A', email='gv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_DOT', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=giang_vien,
        )
        tk_sv = TaiKhoan.objects.create_user(ten_dang_nhap='sv_dot', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU)
        nganh = NganhHoc.objects.create(ma_nganh='CNTT_DOT', ten_nganh='CNTT')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_dot', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_DOT', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        lop_hanh_chinh = LopHanhChinh.objects.create(ma_lop='DOT1', ten_lop='DOT1', ma_nganh=nganh, ma_co_van=co_van)
        sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='SV_DOT', ho_ten='Sinh viên', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=lop_hanh_chinh, ma_tai_khoan=tk_sv,
        )
        DangKyHocPhan.objects.create(ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now())

        response = self.client.post(reverse('academics:dot_dang_ky_xoa', args=[dot.pk]))
        self.assertRedirects(response, reverse('academics:dot_dang_ky_danh_sach'))
        self.assertTrue(DotDangKy.objects.filter(pk=dot.pk).exists())


class PhanQuyenAcademicsTest(TestCase):
    def setUp(self):
        self.giang_vien_tk = TaiKhoan.objects.create_user(
            ten_dang_nhap='gv01', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU
        )

    def test_giang_vien_khong_vao_duoc_danh_sach_hoc_phan(self):
        self.client.force_login(self.giang_vien_tk)
        response = self.client.get(reverse('academics:hoc_phan_danh_sach'))
        self.assertEqual(response.status_code, 403)

    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('academics:hoc_phan_danh_sach'))
        self.assertEqual(response.status_code, 302)

    def test_giang_vien_khong_vao_duoc_danh_sach_hoc_ky(self):
        self.client.force_login(self.giang_vien_tk)
        response = self.client.get(reverse('academics:hoc_ky_danh_sach'))
        self.assertEqual(response.status_code, 403)

    def test_giang_vien_khong_vao_duoc_danh_sach_dot_dang_ky(self):
        self.client.force_login(self.giang_vien_tk)
        response = self.client.get(reverse('academics:dot_dang_ky_danh_sach'))
        self.assertEqual(response.status_code, 403)

    def test_giang_vien_khong_vao_duoc_danh_sach_chuong_trinh(self):
        self.client.force_login(self.giang_vien_tk)
        response = self.client.get(reverse('academics:chuong_trinh_danh_sach'))
        self.assertEqual(response.status_code, 403)


class XoaChuongTrinhDaoTaoTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_xoa_ct', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='N_XCT', ten_nganh='Ngành XCT')
        self.chuong_trinh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh, ten_chuong_trinh='Chương trình cần xóa', khoa_hoc='Khóa 1',
        )
        self.url = reverse('academics:chuong_trinh_xoa', args=[self.chuong_trinh.pk])

    def _them_hoc_phan(self):
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_XCT', ten_hoc_phan='Học phần XCT', so_tin_chi=3)
        ChiTietChuongTrinh.objects.create(chuong_trinh=self.chuong_trinh, hoc_phan=hoc_phan, hoc_ky_du_kien=1)
        return hoc_phan

    def _gan_cho_lop_hanh_chinh(self):
        tk = TaiKhoan.objects.create_user(ten_dang_nhap='cv_xoa_ct', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_XCT', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk,
        )
        return LopHanhChinh.objects.create(
            ma_lop='L_XCT', ten_lop='L_XCT', ma_nganh=self.nganh, ma_co_van=co_van,
            chuong_trinh_dao_tao=self.chuong_trinh,
        )

    def test_danh_sach_co_nut_xoa(self):
        response = self.client.get(reverse('academics:chuong_trinh_danh_sach'))
        self.assertContains(response, self.url)

    def test_get_chi_hien_xac_nhan_va_bao_so_hoc_phan_se_bi_xoa(self):
        self._them_hoc_phan()
        response = self.client.get(self.url)
        self.assertContains(response, 'Chương trình cần xóa')
        self.assertContains(response, '1 học phần trong lộ trình')
        self.assertTrue(ChuongTrinhDaoTao.objects.filter(pk=self.chuong_trinh.pk).exists())

    def test_xoa_chuong_trinh_xoa_ca_lo_trinh_nhung_giu_hoc_phan(self):
        hoc_phan = self._them_hoc_phan()
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('academics:chuong_trinh_danh_sach'))
        self.assertContains(response, 'Đã xóa chương trình')
        self.assertFalse(ChuongTrinhDaoTao.objects.filter(pk=self.chuong_trinh.pk).exists())
        self.assertFalse(ChiTietChuongTrinh.objects.filter(hoc_phan=hoc_phan).exists())
        self.assertTrue(HocPhan.objects.filter(pk=hoc_phan.pk).exists())

    def test_chan_xoa_khi_dang_gan_cho_lop_hanh_chinh_va_khong_mat_lo_trinh(self):
        self._them_hoc_phan()
        self._gan_cho_lop_hanh_chinh()
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('academics:chuong_trinh_danh_sach'))
        self.assertContains(response, 'còn 1 lớp hành chính')
        self.assertTrue(ChuongTrinhDaoTao.objects.filter(pk=self.chuong_trinh.pk).exists())
        self.assertEqual(ChiTietChuongTrinh.objects.filter(chuong_trinh=self.chuong_trinh).count(), 1)
        self.assertContains(self.client.get(self.url), 'chưa thể xóa')

    def test_sau_khi_bo_gan_lop_hanh_chinh_thi_xoa_duoc(self):
        lop = self._gan_cho_lop_hanh_chinh()
        lop.chuong_trinh_dao_tao = None
        lop.save(update_fields=['chuong_trinh_dao_tao'])
        self.client.post(self.url)
        self.assertFalse(ChuongTrinhDaoTao.objects.filter(pk=self.chuong_trinh.pk).exists())

    def test_xoa_chuong_trinh_khong_ton_tai_tra_ve_404(self):
        self.assertEqual(self.client.post(reverse('academics:chuong_trinh_xoa', args=[999999])).status_code, 404)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap=f'ct_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU)
            self.client.force_login(tai_khoan)
            self.assertEqual(self.client.post(self.url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(ChuongTrinhDaoTao.objects.filter(pk=self.chuong_trinh.pk).exists())


class ChuongTrinhDaoTaoCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt6', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')

    def test_tao_chuong_trinh_hop_le(self):
        response = self.client.post(reverse('academics:chuong_trinh_tao'), {
            'nganh': self.nganh.pk, 'ten_chuong_trinh': 'CNTT chuẩn', 'khoa_hoc': 'Khóa 1',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_danh_sach'))
        self.assertTrue(ChuongTrinhDaoTao.objects.filter(nganh=self.nganh, khoa_hoc='Khóa 1').exists())

    def test_khong_the_tao_trung_nganh_va_khoa(self):
        ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        response = self.client.post(reverse('academics:chuong_trinh_tao'), {
            'nganh': self.nganh.pk, 'ten_chuong_trinh': 'CNTT chất lượng cao', 'khoa_hoc': 'Khóa 1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChuongTrinhDaoTao.objects.filter(nganh=self.nganh, khoa_hoc='Khóa 1').count(), 1)

    def test_sua_chuong_trinh(self):
        ct = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        response = self.client.post(reverse('academics:chuong_trinh_sua', args=[ct.pk]), {
            'nganh': self.nganh.pk, 'ten_chuong_trinh': 'CNTT chuẩn (đã cập nhật)', 'khoa_hoc': 'Khóa 1',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_danh_sach'))
        ct.refresh_from_db()
        self.assertEqual(ct.ten_chuong_trinh, 'CNTT chuẩn (đã cập nhật)')


class ChiTietChuongTrinhCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt7', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        self.chuong_trinh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1',
        )
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)

    def test_them_hoc_phan_vao_chuong_trinh(self):
        response = self.client.post(reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]), {
            'hoc_phan': self.csdl.pk, 'hoc_ky_du_kien': 3, 'bat_buoc': 'on',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        self.assertTrue(
            ChiTietChuongTrinh.objects.filter(chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl).exists()
        )

    def test_khong_the_them_trung_hoc_phan(self):
        ChiTietChuongTrinh.objects.create(
            chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=3, bat_buoc=True,
        )
        response = self.client.post(reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]), {
            'hoc_phan': self.csdl.pk, 'hoc_ky_du_kien': 4, 'bat_buoc': 'on',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        self.assertEqual(
            ChiTietChuongTrinh.objects.filter(chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl).count(), 1,
        )

    def test_hoc_ky_du_kien_ngoai_khoang_bi_tu_choi(self):
        response = self.client.post(reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]), {
            'hoc_phan': self.csdl.pk, 'hoc_ky_du_kien': 9, 'bat_buoc': 'on',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        self.assertFalse(
            ChiTietChuongTrinh.objects.filter(chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl).exists()
        )

    def test_hoc_phan_da_co_khong_hien_trong_danh_sach_kha_dung(self):
        ChiTietChuongTrinh.objects.create(
            chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=3, bat_buoc=True,
        )
        response = self.client.get(reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        ma_kha_dung = {hp.pk for hp in response.context['hoc_phan_kha_dung']}
        self.assertNotIn('CSDL', ma_kha_dung)
        self.assertIn('CTDL', ma_kha_dung)

    def test_tim_kiem_loc_hoc_phan_kha_dung(self):
        response = self.client.get(reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]), {'q': 'Cấu trúc'})
        ma_kha_dung = {hp.pk for hp in response.context['hoc_phan_kha_dung']}
        self.assertEqual(ma_kha_dung, {'CTDL'})

    def test_sua_chi_tiet_chuong_trinh(self):
        ct = ChiTietChuongTrinh.objects.create(
            chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=3, bat_buoc=True,
        )
        response = self.client.post(reverse('academics:chuong_trinh_chi_tiet_sua', args=[ct.pk]), {
            'hoc_phan': self.csdl.pk, 'hoc_ky_du_kien': 4, 'bat_buoc': '',
        })
        self.assertRedirects(response, reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        ct.refresh_from_db()
        self.assertEqual(ct.hoc_ky_du_kien, 4)
        self.assertFalse(ct.bat_buoc)

    def test_xoa_chi_tiet_chuong_trinh(self):
        ct = ChiTietChuongTrinh.objects.create(
            chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=3, bat_buoc=True,
        )
        response = self.client.post(reverse('academics:chuong_trinh_chi_tiet_xoa', args=[ct.pk]))
        self.assertRedirects(response, reverse('academics:chuong_trinh_chi_tiet', args=[self.chuong_trinh.pk]))
        self.assertFalse(ChiTietChuongTrinh.objects.filter(pk=ct.pk).exists())


class GanChuongTrinhChoLopHanhChinhTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt8', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        self.nganh_khac = NganhHoc.objects.create(ma_nganh='KTPM', ten_nganh='Kỹ thuật phần mềm')
        self.chuong_trinh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1',
        )
        self.chuong_trinh_khac_nganh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh_khac, ten_chuong_trinh='KTPM chuẩn', khoa_hoc='Khóa 1',
        )
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_ct', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_CT', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        self.lop = LopHanhChinh.objects.create(
            ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=self.nganh, ma_co_van=self.co_van,
        )

    def test_gan_chuong_trinh_dung_nganh_thanh_cong(self):
        response = self.client.post(reverse('academics:lop_hanh_chinh_sua', args=[self.lop.pk]), {
            'ten_lop': self.lop.ten_lop, 'ma_nganh': self.nganh.pk, 'ma_co_van': self.co_van.pk,
            'chuong_trinh_dao_tao': self.chuong_trinh.pk,
        })
        self.assertRedirects(response, reverse('academics:lop_hanh_chinh_danh_sach'))
        self.lop.refresh_from_db()
        self.assertEqual(self.lop.chuong_trinh_dao_tao, self.chuong_trinh)

    def test_khong_the_gan_chuong_trinh_khac_nganh(self):
        response = self.client.post(reverse('academics:lop_hanh_chinh_sua', args=[self.lop.pk]), {
            'ten_lop': self.lop.ten_lop, 'ma_nganh': self.nganh.pk, 'ma_co_van': self.co_van.pk,
            'chuong_trinh_dao_tao': self.chuong_trinh_khac_nganh.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.lop.refresh_from_db()
        self.assertIsNone(self.lop.chuong_trinh_dao_tao)

    def test_khong_bat_buoc_gan_chuong_trinh(self):
        response = self.client.post(reverse('academics:lop_hanh_chinh_sua', args=[self.lop.pk]), {
            'ten_lop': self.lop.ten_lop, 'ma_nganh': self.nganh.pk, 'ma_co_van': self.co_van.pk,
            'chuong_trinh_dao_tao': '',
        })
        self.assertRedirects(response, reverse('academics:lop_hanh_chinh_danh_sach'))
        self.lop.refresh_from_db()
        self.assertIsNone(self.lop.chuong_trinh_dao_tao)
