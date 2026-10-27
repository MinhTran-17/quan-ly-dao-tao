from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, tag
from django.urls import reverse
from django.utils import timezone

from academics.models import HocPhan, LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from people.models import CoVanHocTap, GiangVien, SinhVien

from .models import DiemDanh

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


def tao_giang_vien(ma_giang_vien):
    tk = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_{ma_giang_vien}', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU
    )
    return GiangVien.objects.create(
        ma_giang_vien=ma_giang_vien, ho_ten=f'Giảng viên {ma_giang_vien}', email=f'{ma_giang_vien}@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk,
    )


def tao_lop_hanh_chinh(ma_lop):
    nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
    tk_cv = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_cv_{ma_lop}', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
    )
    co_van = CoVanHocTap.objects.create(
        ma_co_van=f'CV_{ma_lop}', ho_ten='Cố vấn Test', email='cv@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
    )
    return LopHanhChinh.objects.create(ma_lop=ma_lop, ten_lop=f'Lớp {ma_lop}', ma_nganh=nganh, ma_co_van=co_van)


def tao_sinh_vien(ma_sinh_vien, ma_lop):
    tk = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_{ma_sinh_vien}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
    )
    return SinhVien.objects.create(
        ma_sinh_vien=ma_sinh_vien, ho_ten=f'Sinh viên {ma_sinh_vien}', ngay_sinh='2004-01-01',
        email=f'{ma_sinh_vien}@test.local', so_dien_thoai='0900000000', ma_lop=ma_lop, ma_tai_khoan=tk,
    )


@tag('tich_hop')
class DiemDanhLopTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_DD1')
        self.giang_vien = tao_giang_vien('GV_DD01')
        self.giang_vien_khac = tao_giang_vien('GV_DD02')
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_DD01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.sv1 = tao_sinh_vien('SV_DD01', self.lop_hanh_chinh)
        self.sv2 = tao_sinh_vien('SV_DD02', self.lop_hanh_chinh)
        sv_da_huy = tao_sinh_vien('SV_DD03', self.lop_hanh_chinh)
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sv1, ma_lop_hoc_phan=self.lop, thoi_gian_dang_ky=timezone.now(),
        )
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sv2, ma_lop_hoc_phan=self.lop, thoi_gian_dang_ky=timezone.now(),
        )
        DangKyHocPhan.objects.create(
            ma_sinh_vien=sv_da_huy, ma_lop_hoc_phan=self.lop, thoi_gian_dang_ky=timezone.now(),
            trang_thai=TrangThaiDangKy.DA_HUY,
        )
        self.client.force_login(self.giang_vien.ma_tai_khoan)

    def test_danh_sach_diem_danh_chi_gom_sinh_vien_con_hieu_luc(self):
        response = self.client.get(reverse('diem_danh:diem_danh_lop', args=[self.lop.pk]))
        self.assertContains(response, 'SV_DD01')
        self.assertContains(response, 'SV_DD02')
        self.assertNotContains(response, 'SV_DD03')

    def test_luu_diem_danh(self):
        ngay = timezone.localdate()
        url = reverse('diem_danh:diem_danh_lop', args=[self.lop.pk])
        response = self.client.post(url, {'ngay': ngay.isoformat(), f'co_mat_{self.sv1.pk}': 'on'})
        self.assertRedirects(response, f'{url}?ngay={ngay.isoformat()}')
        self.assertTrue(
            DiemDanh.objects.filter(
                lop_hoc_phan=self.lop, sinh_vien=self.sv1, ngay_diem_danh=ngay, co_mat=True,
            ).exists()
        )
        self.assertTrue(
            DiemDanh.objects.filter(
                lop_hoc_phan=self.lop, sinh_vien=self.sv2, ngay_diem_danh=ngay, co_mat=False,
            ).exists()
        )

    def test_sua_lai_diem_danh_ngay_da_diem_danh_khong_tao_dong_moi(self):
        ngay = timezone.localdate()
        DiemDanh.objects.create(lop_hoc_phan=self.lop, sinh_vien=self.sv1, ngay_diem_danh=ngay, co_mat=True)
        DiemDanh.objects.create(lop_hoc_phan=self.lop, sinh_vien=self.sv2, ngay_diem_danh=ngay, co_mat=True)

        url = reverse('diem_danh:diem_danh_lop', args=[self.lop.pk])
        # Điểm danh lại: sv1 chuyển sang vắng (bỏ tick), sv2 vẫn có mặt.
        self.client.post(url, {'ngay': ngay.isoformat(), f'co_mat_{self.sv2.pk}': 'on'})

        self.assertEqual(DiemDanh.objects.filter(lop_hoc_phan=self.lop, ngay_diem_danh=ngay).count(), 2)
        sv1_dd = DiemDanh.objects.get(lop_hoc_phan=self.lop, sinh_vien=self.sv1, ngay_diem_danh=ngay)
        self.assertFalse(sv1_dd.co_mat)

    def test_giang_vien_khac_khong_diem_danh_duoc_lop_khong_phu_trach(self):
        self.client.force_login(self.giang_vien_khac.ma_tai_khoan)
        response = self.client.get(reverse('diem_danh:diem_danh_lop', args=[self.lop.pk]))
        self.assertEqual(response.status_code, 403)

    def test_sinh_vien_khong_vao_duoc_trang_diem_danh_giang_vien(self):
        self.client.force_login(self.sv1.ma_tai_khoan)
        response = self.client.get(reverse('diem_danh:diem_danh_lop', args=[self.lop.pk]))
        self.assertEqual(response.status_code, 403)


@tag('tich_hop')
class LichSuDiemDanhTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_DD2')
        self.giang_vien = tao_giang_vien('GV_DD03')
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)
        self.lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDL_DD01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.sinh_vien = tao_sinh_vien('SV_LS01', self.lop_hanh_chinh)
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=self.lop, thoi_gian_dang_ky=timezone.now(),
        )
        DiemDanh.objects.create(
            lop_hoc_phan=self.lop, sinh_vien=self.sinh_vien, ngay_diem_danh=date(2025, 9, 1), co_mat=True,
        )
        DiemDanh.objects.create(
            lop_hoc_phan=self.lop, sinh_vien=self.sinh_vien, ngay_diem_danh=date(2025, 9, 8), co_mat=False,
        )

    def test_giang_vien_xem_lich_su_theo_ngay_va_ty_le(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('diem_danh:lich_su_diem_danh_lop', args=[self.lop.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '01/09/2025')
        self.assertContains(response, '08/09/2025')

    def test_sinh_vien_xem_lich_su_diem_danh_cua_minh(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('diem_danh:lich_su_cua_toi'))
        self.assertContains(response, 'CTDL_DD01')
        self.assertContains(response, '50,0')
        # Header bảng đồng bộ với các trang Sinh viên khác (xanh nhạt, dòng xen kẽ).
        self.assertContains(response, '<table class="bang-sv">')
        self.assertContains(response, '<tr class="hang-diem">', count=2)

    def test_sinh_vien_khac_khong_thay_lich_su_cua_nguoi_khac(self):
        sinh_vien_khac = tao_sinh_vien('SV_LS02', self.lop_hanh_chinh)
        self.client.force_login(sinh_vien_khac.ma_tai_khoan)
        response = self.client.get(reverse('diem_danh:lich_su_cua_toi'))
        self.assertNotContains(response, 'CTDL_DD01')
