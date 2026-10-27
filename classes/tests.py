from django.contrib.auth import get_user_model
from django.test import TestCase, tag
from django.urls import reverse

from datetime import date, time

from academics.models import HocKy, HocPhan
from accounts.models import VaiTro
from people.models import GiangVien

from .models import LichHoc, LichThi, LopHocPhan

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


@tag('tich_hop')
class LopHocPhanCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv01', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV01', ho_ten='Giảng viên A', email='gv@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        self.hoc_ky = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026', ngay_bat_dau='2025-09-01', ngay_ket_thuc='2026-01-15',
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_lop_hoc_phan_hop_le(self):
        response = self.client.post(reverse('classes:lop_hoc_phan_tao'), {
            'ma_lop_hoc_phan': 'CSDL_01', 'hoc_ky_chon': self.hoc_ky.pk,
            'si_so_toi_da': 40, 'ma_hoc_phan': self.hoc_phan.pk, 'ma_giang_vien': self.giang_vien.pk,
        })
        self.assertRedirects(response, reverse('classes:lop_hoc_phan_danh_sach'))
        lop = LopHocPhan.objects.filter(pk='CSDL_01').first()
        self.assertIsNotNone(lop)
        self.assertEqual(lop.hoc_ky, '1')
        self.assertEqual(lop.nam_hoc, '2025-2026')

    def test_khong_the_tao_lop_hoc_phan_si_so_khong_duong(self):
        response = self.client.post(reverse('classes:lop_hoc_phan_tao'), {
            'ma_lop_hoc_phan': 'CSDL_02', 'hoc_ky_chon': self.hoc_ky.pk,
            'si_so_toi_da': 0, 'ma_hoc_phan': self.hoc_phan.pk, 'ma_giang_vien': self.giang_vien.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LopHocPhan.objects.filter(pk='CSDL_02').exists())

    def test_khong_the_tao_lop_hoc_phan_khi_chua_chon_hoc_ky(self):
        response = self.client.post(reverse('classes:lop_hoc_phan_tao'), {
            'ma_lop_hoc_phan': 'CSDL_03', 'hoc_ky_chon': '',
            'si_so_toi_da': 40, 'ma_hoc_phan': self.hoc_phan.pk, 'ma_giang_vien': self.giang_vien.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LopHocPhan.objects.filter(pk='CSDL_03').exists())

    def test_sua_lop_hoc_phan_giu_dung_hoc_ky_da_chon(self):
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_04', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        hoc_ky_moi = HocKy.objects.create(
            hoc_ky=2, nam_hoc='2025-2026', ngay_bat_dau='2026-02-01', ngay_ket_thuc='2026-06-15',
        )
        response = self.client.post(reverse('classes:lop_hoc_phan_sua', args=[lop.pk]), {
            'hoc_ky_chon': hoc_ky_moi.pk,
            'si_so_toi_da': 40, 'ma_hoc_phan': self.hoc_phan.pk, 'ma_giang_vien': self.giang_vien.pk,
        })
        self.assertRedirects(response, reverse('classes:lop_hoc_phan_danh_sach'))
        lop.refresh_from_db()
        self.assertEqual(lop.hoc_ky, '2')

    def test_loc_theo_hoc_ky_va_nam_hoc(self):
        LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_HK1', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_HK2', hoc_ky='2', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        response = self.client.get(reverse('classes:lop_hoc_phan_danh_sach'), {'hoc_ky': '1'})
        self.assertContains(response, 'CSDL_HK1')
        self.assertNotContains(response, 'CSDL_HK2')


@tag('tich_hop')
class LichHocTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv02', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV02', ho_ten='Giảng viên B', email='gv2@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_lich_hoc_hop_le(self):
        response = self.client.post(reverse('classes:lich_hoc_tao'), {
            'ma_lop_hoc_phan': self.lop.pk, 'thu': 2, 'tiet_bat_dau': 1, 'so_tiet': 3, 'phong_hoc': 'A101',
        })
        self.assertRedirects(response, reverse('classes:lich_hoc_danh_sach'))
        self.assertTrue(LichHoc.objects.filter(ma_lop_hoc_phan=self.lop, phong_hoc='A101').exists())

    def test_khong_the_tao_lich_hoc_thu_khong_hop_le(self):
        response = self.client.post(reverse('classes:lich_hoc_tao'), {
            'ma_lop_hoc_phan': self.lop.pk, 'thu': 9, 'tiet_bat_dau': 1, 'so_tiet': 3, 'phong_hoc': 'A102',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LichHoc.objects.filter(phong_hoc='A102').exists())


@tag('tich_hop')
class XoaLichHocTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_xoa_lh', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.client.force_login(self.phong_dao_tao)
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP_XLH', ten_hoc_phan='HP XLH', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_xoa_lh', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_XLH', ho_ten='GV', email='gv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='LHP_XLH', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=30,
            ma_hoc_phan=hoc_phan, ma_giang_vien=giang_vien,
        )
        self.lich = LichHoc.objects.create(
            ma_lop_hoc_phan=self.lop, thu=2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101',
        )
        self.lich_khac = LichHoc.objects.create(
            ma_lop_hoc_phan=self.lop, thu=4, tiet_bat_dau=1, so_tiet=3, phong_hoc='A102',
        )
        self.url = reverse('classes:lich_hoc_xoa', args=[self.lich.pk])

    def _dang_ky_mot_sinh_vien(self, trang_thai=None):
        from django.utils import timezone

        from academics.models import LopHanhChinh, NganhHoc
        from enrollment.models import DangKyHocPhan
        from people.models import CoVanHocTap, SinhVien

        nganh = NganhHoc.objects.create(ma_nganh='N_XLH', ten_nganh='N')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_xoa_lh', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_XLH', ho_ten='CV', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        lop_hc = LopHanhChinh.objects.create(ma_lop='L_XLH', ten_lop='L', ma_nganh=nganh, ma_co_van=co_van)
        tk_sv = TaiKhoan.objects.create_user(ten_dang_nhap='sv_xoa_lh', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU)
        sinh_vien = SinhVien.objects.create(
            ma_sinh_vien='SV_XLH', ho_ten='SV', ngay_sinh='2004-01-01', email='sv@test.local',
            so_dien_thoai='0900000000', ma_lop=lop_hc, ma_tai_khoan=tk_sv,
        )
        du_lieu = {'ma_sinh_vien': sinh_vien, 'ma_lop_hoc_phan': self.lop, 'thoi_gian_dang_ky': timezone.now()}
        if trang_thai:
            du_lieu['trang_thai'] = trang_thai
        return DangKyHocPhan.objects.create(**du_lieu)

    def test_danh_sach_co_nut_xoa(self):
        response = self.client.get(reverse('classes:lich_hoc_danh_sach'))
        self.assertContains(response, self.url)

    def test_get_chi_hien_xac_nhan_khong_xoa_va_khong_canh_bao_khi_chua_co_ai_dang_ky(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'LHP_XLH')
        self.assertContains(response, 'phòng A101')
        self.assertNotContains(response, 'sinh viên đăng ký')
        self.assertTrue(LichHoc.objects.filter(pk=self.lich.pk).exists())

    def test_xoa_lich_hoc_chi_xoa_dung_dong_do(self):
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse('classes:lich_hoc_danh_sach'))
        self.assertContains(response, 'Đã xóa lịch học')
        self.assertFalse(LichHoc.objects.filter(pk=self.lich.pk).exists())
        self.assertTrue(LichHoc.objects.filter(pk=self.lich_khac.pk).exists())
        self.assertTrue(LopHocPhan.objects.filter(pk='LHP_XLH').exists())

    def test_canh_bao_so_sinh_vien_dang_ky_nhung_van_xoa_duoc(self):
        self._dang_ky_mot_sinh_vien()
        self.assertContains(self.client.get(self.url), '1 sinh viên đăng ký')
        self.client.post(self.url)
        self.assertFalse(LichHoc.objects.filter(pk=self.lich.pk).exists())

    def test_khong_dem_dang_ky_da_huy(self):
        from enrollment.models import TrangThaiDangKy

        self._dang_ky_mot_sinh_vien(trang_thai=TrangThaiDangKy.DA_HUY)
        self.assertNotContains(self.client.get(self.url), 'sinh viên đăng ký')

    def test_xoa_lich_hoc_khong_ton_tai_tra_ve_404(self):
        self.assertEqual(self.client.post(reverse('classes:lich_hoc_xoa', args=[999999])).status_code, 404)

    def test_vai_tro_khac_va_chua_dang_nhap_khong_xoa_duoc(self):
        for vai_tro in (VaiTro.GIANG_VIEN, VaiTro.SINH_VIEN, VaiTro.CO_VAN_HOC_TAP):
            tai_khoan = TaiKhoan.objects.create_user(ten_dang_nhap=f'lh_{vai_tro}', vai_tro=vai_tro, password=MAT_KHAU)
            self.client.force_login(tai_khoan)
            self.assertEqual(self.client.post(self.url).status_code, 403, vai_tro)
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertTrue(LichHoc.objects.filter(pk=self.lich.pk).exists())


@tag('tich_hop')
class GiangVienXemLopTest(TestCase):
    def setUp(self):
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv03', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV03', ho_ten='Giảng viên C', email='gv3@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=self.tk_gv,
        )
        tk_gv_khac = TaiKhoan.objects.create_user(ten_dang_nhap='gv04', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        giang_vien_khac = GiangVien.objects.create(
            ma_giang_vien='GV04', ho_ten='Giảng viên D', email='gv4@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv_khac,
        )
        self.lop_cua_toi = LopHocPhan.objects.create(
            ma_lop_hoc_phan='LOP_TOI', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.lop_khac = LopHocPhan.objects.create(
            ma_lop_hoc_phan='LOP_KHAC', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=giang_vien_khac,
        )
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_cua_toi, thu=2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101')
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop_khac, thu=3, tiet_bat_dau=1, so_tiet=3, phong_hoc='A102')
        self.client.force_login(self.tk_gv)

    def test_chi_thay_lop_phu_trach_cua_minh(self):
        response = self.client.get(reverse('classes:lop_phu_trach'))
        self.assertContains(response, 'LOP_TOI')
        self.assertNotContains(response, 'LOP_KHAC')

    def test_chi_thay_lich_giang_day_cua_minh(self):
        response = self.client.get(reverse('classes:lich_giang_day'))
        self.assertContains(response, 'A101')
        self.assertNotContains(response, 'A102')

    def test_giang_vien_khong_vao_duoc_crud_lop_hoc_phan(self):
        response = self.client.get(reverse('classes:lop_hoc_phan_danh_sach'))
        self.assertEqual(response.status_code, 403)


@tag('tich_hop')
class PhanQuyenClassesTest(TestCase):
    def setUp(self):
        self.sinh_vien = TaiKhoan.objects.create_user(
            ten_dang_nhap='sv01', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
        )

    def test_sinh_vien_khong_vao_duoc_lop_phu_trach(self):
        self.client.force_login(self.sinh_vien)
        response = self.client.get(reverse('classes:lop_phu_trach'))
        self.assertEqual(response.status_code, 403)

    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('classes:lop_hoc_phan_danh_sach'))
        self.assertEqual(response.status_code, 302)


@tag('tich_hop')
class LuoiTuanGiangVienTest(TestCase):
    def setUp(self):
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_luoi', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_LUOI', ho_ten='Giảng viên Lưới', email='gv_luoi@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=self.tk_gv,
        )
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_LUOI', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        LichHoc.objects.create(ma_lop_hoc_phan=self.lop, thu=2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101')
        self.client.force_login(self.tk_gv)

    def test_xem_dang_luoi_tuan_hien_dung_lop_va_phong(self):
        response = self.client.get(reverse('classes:lich_giang_day'), {'xem': 'luoi'})
        self.assertContains(response, 'CSDL_LUOI')
        self.assertContains(response, 'A101')

    def test_mac_dinh_van_la_dang_danh_sach(self):
        response = self.client.get(reverse('classes:lich_giang_day'))
        self.assertNotContains(response, '<table class="bang-luoi-tuan">')


@tag('tich_hop')
class LichThiCrudTest(TestCase):
    def setUp(self):
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_lt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        tk_gv = TaiKhoan.objects.create_user(ten_dang_nhap='gv_lt', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
        self.giang_vien = GiangVien.objects.create(
            ma_giang_vien='GV_LT', ho_ten='Giảng viên LT', email='gv_lt@test.local',
            so_dien_thoai='0900000000', ma_tai_khoan=tk_gv,
        )
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_LT01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.lop_khac = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_LT02', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.client.force_login(self.phong_dao_tao)

    def test_tao_lich_thi_hop_le(self):
        response = self.client.post(reverse('classes:lich_thi_tao'), {
            'lop_hoc_phan': self.lop.pk, 'ngay_thi': '2026-01-10', 'gio_bat_dau': '08:00',
            'thoi_luong_phut': 60, 'phong_thi': 'A201',
        })
        self.assertRedirects(response, reverse('classes:lich_thi_danh_sach'))
        self.assertTrue(LichThi.objects.filter(lop_hoc_phan=self.lop).exists())

    def test_khong_the_tao_hai_lich_thi_cho_cung_mot_lop(self):
        LichThi.objects.create(
            lop_hoc_phan=self.lop, ngay_thi=date(2026, 1, 10), gio_bat_dau=time(8, 0),
            thoi_luong_phut=60, phong_thi='A201',
        )
        # Lớp đã có lịch thi không còn xuất hiện trong lựa chọn khi tạo mới.
        response = self.client.get(reverse('classes:lich_thi_tao'))
        self.assertNotContains(response, 'CSDL_LT01')

        response = self.client.post(reverse('classes:lich_thi_tao'), {
            'lop_hoc_phan': self.lop.pk, 'ngay_thi': '2026-01-11', 'gio_bat_dau': '09:00',
            'thoi_luong_phut': 60, 'phong_thi': 'A202',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LichThi.objects.filter(lop_hoc_phan=self.lop).count(), 1)

    def test_khong_the_tao_lich_thi_thoi_luong_khong_duong(self):
        response = self.client.post(reverse('classes:lich_thi_tao'), {
            'lop_hoc_phan': self.lop.pk, 'ngay_thi': '2026-01-10', 'gio_bat_dau': '08:00',
            'thoi_luong_phut': 0, 'phong_thi': 'A201',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LichThi.objects.filter(lop_hoc_phan=self.lop).exists())

    def test_sua_lich_thi(self):
        lich_thi = LichThi.objects.create(
            lop_hoc_phan=self.lop, ngay_thi=date(2026, 1, 10), gio_bat_dau=time(8, 0),
            thoi_luong_phut=60, phong_thi='A201',
        )
        response = self.client.post(reverse('classes:lich_thi_sua', args=[lich_thi.pk]), {
            'ngay_thi': '2026-01-15', 'gio_bat_dau': '10:00', 'thoi_luong_phut': 90, 'phong_thi': 'B301',
        })
        self.assertRedirects(response, reverse('classes:lich_thi_danh_sach'))
        lich_thi.refresh_from_db()
        self.assertEqual(lich_thi.phong_thi, 'B301')
        self.assertEqual(lich_thi.thoi_luong_phut, 90)

    def test_xoa_lich_thi(self):
        lich_thi = LichThi.objects.create(
            lop_hoc_phan=self.lop, ngay_thi=date(2026, 1, 10), gio_bat_dau=time(8, 0),
            thoi_luong_phut=60, phong_thi='A201',
        )
        response = self.client.post(reverse('classes:lich_thi_xoa', args=[lich_thi.pk]))
        self.assertRedirects(response, reverse('classes:lich_thi_danh_sach'))
        self.assertFalse(LichThi.objects.filter(pk=lich_thi.pk).exists())

    def test_giang_vien_khong_vao_duoc_crud_lich_thi(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('classes:lich_thi_danh_sach'))
        self.assertEqual(response.status_code, 403)
