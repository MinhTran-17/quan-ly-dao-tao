import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, tag
from django.urls import reverse
from django.utils import timezone

from academics.models import HocPhan, LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from accounts.tests import kiem_tra_can_bang_the
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan
from people.models import CoVanHocTap, GiangVien, SinhVien

from .models import Diem
from .services import (
    bang_diem_chi_tiet, canh_bao_hoc_vu, diem_trung_binh_hoc_ky, diem_trung_binh_tich_luy,
    hoc_ky_gan_nhat_co_du_diem, xep_loai_hoc_luc,
)
from .tinh_diem import tinh_diem_tong_ket

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


def tao_lop_hanh_chinh(ma_lop='CNTT1'):
    nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
    tk_cv = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_cv_{ma_lop}', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
    )
    co_van = CoVanHocTap.objects.create(
        ma_co_van=f'CV_{ma_lop}', ho_ten='Cố vấn Test', email='cv@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
    )
    lop = LopHanhChinh.objects.create(ma_lop=ma_lop, ten_lop=f'Lớp {ma_lop}', ma_nganh=nganh, ma_co_van=co_van)
    return lop, co_van


def tao_sinh_vien(ma_sinh_vien, ma_lop):
    tk = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_{ma_sinh_vien}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU
    )
    return SinhVien.objects.create(
        ma_sinh_vien=ma_sinh_vien, ho_ten=f'Sinh viên {ma_sinh_vien}', ngay_sinh='2004-01-01',
        email=f'{ma_sinh_vien}@test.local', so_dien_thoai='0900000000', ma_lop=ma_lop, ma_tai_khoan=tk,
    )


def tao_giang_vien(ma_giang_vien):
    tk = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_{ma_giang_vien}', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU
    )
    return GiangVien.objects.create(
        ma_giang_vien=ma_giang_vien, ho_ten=f'Giảng viên {ma_giang_vien}', email=f'{ma_giang_vien}@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk,
    )


@tag('don_vi')
class TinhDiemTongKetTest(TestCase):
    def test_8_0_va_7_5_ra_7_7(self):
        ket_qua = tinh_diem_tong_ket(Decimal('8.0'), Decimal('7.5'))
        self.assertEqual(ket_qua, Decimal('7.7'))

    def test_9_0_va_8_5_ra_8_7(self):
        ket_qua = tinh_diem_tong_ket(Decimal('9.0'), Decimal('8.5'))
        self.assertEqual(ket_qua, Decimal('8.7'))

    def test_thieu_diem_qua_trinh_tra_ve_none(self):
        self.assertIsNone(tinh_diem_tong_ket(None, Decimal('8.0')))

    def test_thieu_diem_thi_tra_ve_none(self):
        self.assertIsNone(tinh_diem_tong_ket(Decimal('8.0'), None))


@tag('tich_hop')
class NhapSuaDiemTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT1')
        self.sinh_vien = tao_sinh_vien('SV001', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV001')
        self.giang_vien_khac = tao_giang_vien('GV002')
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )

    def test_giang_vien_nhap_diem_moi(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[self.dang_ky.pk]), {
            'diem_qua_trinh': '8.0', 'diem_thi': '7.5',
        })
        self.assertRedirects(response, reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        diem = Diem.objects.get(ma_dang_ky=self.dang_ky)
        self.assertEqual(diem.tinh_diem_tong_ket(), Decimal('7.7'))

    def test_khong_the_nhap_diem_ngoai_khoang(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[self.dang_ky.pk]), {
            'diem_qua_trinh': '11', 'diem_thi': '5',
        })
        self.assertEqual(response.status_code, 200)
        # get_or_create có thể đã tạo sẵn dòng điểm rỗng, nhưng giá trị 11 không hợp lệ
        # không được lưu vào đó.
        diem = Diem.objects.filter(ma_dang_ky=self.dang_ky).first()
        self.assertTrue(diem is None or diem.diem_qua_trinh is None)

    def test_giang_vien_khong_phu_trach_khong_duoc_nhap_diem(self):
        self.client.force_login(self.giang_vien_khac.ma_tai_khoan)
        response = self.client.get(reverse('grades:nhap_diem', args=[self.dang_ky.pk]))
        self.assertEqual(response.status_code, 403)

    def test_phong_dao_tao_sua_duoc_diem_da_co(self):
        Diem.objects.create(ma_dang_ky=self.dang_ky, diem_qua_trinh=8, diem_thi=8)
        self.client.force_login(self.phong_dao_tao)
        response = self.client.post(reverse('grades:sua_diem', args=[self.dang_ky.pk]), {
            'diem_qua_trinh': '9.0', 'diem_thi': '8.5',
        })
        self.assertRedirects(
            response, reverse('grades:bang_diem_lop_phong_dao_tao', args=[self.lop_hoc_phan.pk])
        )
        diem = Diem.objects.get(ma_dang_ky=self.dang_ky)
        self.assertEqual(diem.tinh_diem_tong_ket(), Decimal('8.7'))

    def test_phong_dao_tao_khong_the_tao_diem_moi(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(reverse('grades:sua_diem', args=[self.dang_ky.pk]))
        self.assertEqual(response.status_code, 404)


@tag('tich_hop')
class XemBangDiemTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT1')
        self.lop_hanh_chinh_khac, self.co_van_khac = tao_lop_hanh_chinh('CNTT2')
        self.sinh_vien = tao_sinh_vien('SV010', self.lop_hanh_chinh)
        self.sinh_vien_khac = tao_sinh_vien('SV011', self.lop_hanh_chinh_khac)
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt2', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )

    def test_sinh_vien_xem_duoc_bang_diem_cua_minh(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertEqual(response.status_code, 200)

    def test_sinh_vien_khong_xem_duoc_bang_diem_nguoi_khac(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien_khac.pk]))
        self.assertEqual(response.status_code, 403)

    def test_co_van_xem_duoc_diem_sinh_vien_lop_minh(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertEqual(response.status_code, 200)

    def test_co_van_khong_xem_duoc_diem_sinh_vien_lop_khac(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien_khac.pk]))
        self.assertEqual(response.status_code, 403)

    def test_phong_dao_tao_xem_duoc_bat_ky_sinh_vien_nao(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien_khac.pk]))
        self.assertEqual(response.status_code, 200)

    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertEqual(response.status_code, 302)


@tag('don_vi')
class BangDiemChiTietTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, _ = tao_lop_hanh_chinh('CNTT1')
        self.sinh_vien = tao_sinh_vien('SV001', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV001')
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)

    def _tao_lop_va_diem(self, ma_lop_hoc_phan, hoc_ky, nam_hoc, diem_qua_trinh, diem_thi, hoc_phan=None):
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan=ma_lop_hoc_phan, hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=40,
            ma_hoc_phan=hoc_phan or self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=diem_qua_trinh, diem_thi=diem_thi)
        return lop

    def test_bo_qua_dang_ky_chua_co_diem(self):
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(),
        )
        self.assertEqual(bang_diem_chi_tiet(self.sinh_vien), [])

    def test_tinh_dung_diem_tong_ket_va_trang_thai_dat(self):
        self._tao_lop_va_diem('CSDL_01', '1', '2025-2026', Decimal('8'), Decimal('7.5'))
        ket_qua = bang_diem_chi_tiet(self.sinh_vien)
        self.assertEqual(len(ket_qua), 1)
        self.assertEqual(ket_qua[0]['diem_tong_ket'], Decimal('7.7'))
        self.assertTrue(ket_qua[0]['dat'])

    def test_hoc_lai_giu_diem_cao_nhat(self):
        self._tao_lop_va_diem('CSDL_01', '1', '2024-2025', Decimal('2'), Decimal('2'))
        self._tao_lop_va_diem('CSDL_02', '1', '2025-2026', Decimal('9'), Decimal('9'))
        ket_qua = bang_diem_chi_tiet(self.sinh_vien)
        self.assertEqual(len(ket_qua), 1)
        self.assertEqual(ket_qua[0]['diem_tong_ket'], Decimal('9.0'))
        self.assertEqual(ket_qua[0]['nam_hoc'], '2025-2026')


@tag('don_vi')
class XepLoaiHocLucTest(TestCase):
    def test_xuat_sac(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('9.0')), 'Xuất sắc')
        self.assertEqual(xep_loai_hoc_luc(Decimal('10')), 'Xuất sắc')

    def test_gioi(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('8.0')), 'Giỏi')
        self.assertEqual(xep_loai_hoc_luc(Decimal('8.99')), 'Giỏi')

    def test_kha(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('7.0')), 'Khá')
        self.assertEqual(xep_loai_hoc_luc(Decimal('7.99')), 'Khá')

    def test_trung_binh(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('5.0')), 'Trung bình')
        self.assertEqual(xep_loai_hoc_luc(Decimal('6.99')), 'Trung bình')

    def test_yeu(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('4.0')), 'Yếu')
        self.assertEqual(xep_loai_hoc_luc(Decimal('4.99')), 'Yếu')

    def test_kem(self):
        self.assertEqual(xep_loai_hoc_luc(Decimal('3.99')), 'Kém')
        self.assertEqual(xep_loai_hoc_luc(Decimal('0')), 'Kém')

    def test_none_tra_ve_none(self):
        self.assertIsNone(xep_loai_hoc_luc(None))


@tag('don_vi')
class DiemTrungBinhTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, _ = tao_lop_hanh_chinh('CNTT_TB')
        self.sinh_vien = tao_sinh_vien('SV_TB', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_TB')

    def _tao_lop_va_diem(self, ma, hoc_ky, nam_hoc, so_tin_chi, dqt, dt, cong_bo=True):
        hoc_phan = HocPhan.objects.create(ma_hoc_phan=ma, ten_hoc_phan=ma, so_tin_chi=so_tin_chi)
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan=f'{ma}_L', hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=dqt, diem_thi=dt, da_cong_bo=cong_bo)
        return lop

    def test_trung_binh_co_trong_so_tin_chi(self):
        # HP1: 3 tín chỉ, điểm tổng kết 8.0; HP2: 1 tín chỉ, điểm tổng kết 4.0.
        # TB = (8.0*3 + 4.0*1) / 4 = 28/4 = 7.0
        self._tao_lop_va_diem('HP1', '1', '2025-2026', 3, Decimal('8'), Decimal('8'))
        self._tao_lop_va_diem('HP2', '1', '2025-2026', 1, Decimal('4'), Decimal('4'))
        tb = diem_trung_binh_hoc_ky(self.sinh_vien, '1', '2025-2026')
        self.assertEqual(tb, Decimal('7.00'))

    def test_tich_luy_gom_nhieu_hoc_ky(self):
        self._tao_lop_va_diem('HP3', '1', '2024-2025', 3, Decimal('6'), Decimal('6'))
        self._tao_lop_va_diem('HP4', '1', '2025-2026', 3, Decimal('8'), Decimal('8'))
        tb = diem_trung_binh_tich_luy(self.sinh_vien)
        self.assertEqual(tb, Decimal('7.00'))

    def test_khong_du_diem_tra_ve_none(self):
        self.assertIsNone(diem_trung_binh_hoc_ky(self.sinh_vien, '1', '2025-2026'))
        self.assertIsNone(diem_trung_binh_tich_luy(self.sinh_vien))

    def test_chi_tinh_dang_ky_con_hieu_luc(self):
        from enrollment.models import TrangThaiDangKy

        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HP5', ten_hoc_phan='HP5', so_tin_chi=3)
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan='HP5_L', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(),
            trang_thai=TrangThaiDangKy.DA_HUY,
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=9, diem_thi=9, da_cong_bo=True)
        self.assertIsNone(diem_trung_binh_hoc_ky(self.sinh_vien, '1', '2025-2026'))

    def test_chi_diem_da_cong_bo_loai_diem_chua_cong_bo(self):
        self._tao_lop_va_diem('HP6', '1', '2025-2026', 3, Decimal('9'), Decimal('9'), cong_bo=False)
        tb_that = diem_trung_binh_hoc_ky(self.sinh_vien, '1', '2025-2026')
        tb_cong_bo = diem_trung_binh_hoc_ky(self.sinh_vien, '1', '2025-2026', chi_diem_da_cong_bo=True)
        self.assertIsNotNone(tb_that)
        self.assertIsNone(tb_cong_bo)


@tag('don_vi')
class CanhBaoHocVuServiceTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, _ = tao_lop_hanh_chinh('CNTT_CB')
        self.sinh_vien = tao_sinh_vien('SV_CB', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_CB')

    def _tao_lop_va_diem(self, ma, so_tin_chi, dqt, dt):
        hoc_phan = HocPhan.objects.create(ma_hoc_phan=ma, ten_hoc_phan=ma, so_tin_chi=so_tin_chi)
        lop = LopHocPhan.objects.create(
            ma_lop_hoc_phan=f'{ma}_L', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=dqt, diem_thi=dt, da_cong_bo=True)

    def test_khong_canh_bao_khi_diem_tot(self):
        self._tao_lop_va_diem('HPA', 3, Decimal('8'), Decimal('8'))
        ket_qua = canh_bao_hoc_vu(self.sinh_vien, '1', '2025-2026')
        self.assertFalse(ket_qua['canh_bao'])

    def test_canh_bao_diem_trung_binh_duoi_5(self):
        self._tao_lop_va_diem('HPB', 3, Decimal('3'), Decimal('3'))
        ket_qua = canh_bao_hoc_vu(self.sinh_vien, '1', '2025-2026')
        self.assertTrue(ket_qua['canh_bao'])
        self.assertTrue(any('dưới 5.0' in ly_do for ly_do in ket_qua['ly_do']))

    def test_canh_bao_hai_hoc_phan_chua_dat(self):
        self._tao_lop_va_diem('HPC', 3, Decimal('9'), Decimal('9'))
        self._tao_lop_va_diem('HPD', 1, Decimal('3'), Decimal('3'))
        self._tao_lop_va_diem('HPE', 1, Decimal('3'), Decimal('3'))
        ket_qua = canh_bao_hoc_vu(self.sinh_vien, '1', '2025-2026')
        self.assertTrue(ket_qua['canh_bao'])
        self.assertTrue(any('2 học phần chưa đạt' in ly_do for ly_do in ket_qua['ly_do']))

    def test_mot_hoc_phan_chua_dat_khong_canh_bao_neu_tb_van_tren_5(self):
        self._tao_lop_va_diem('HPF', 3, Decimal('8'), Decimal('8'))
        self._tao_lop_va_diem('HPG', 1, Decimal('3'), Decimal('3'))
        ket_qua = canh_bao_hoc_vu(self.sinh_vien, '1', '2025-2026')
        self.assertFalse(ket_qua['canh_bao'])

    def test_chua_co_diem_khong_canh_bao(self):
        ket_qua = canh_bao_hoc_vu(self.sinh_vien, '1', '2025-2026')
        self.assertFalse(ket_qua['canh_bao'])


@tag('tich_hop')
class CongBoDiemTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT_CB2')
        self.sinh_vien = tao_sinh_vien('SV_CB2', self.lop_hanh_chinh)
        self.sinh_vien2 = tao_sinh_vien('SV_CB3', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_CB2')
        self.giang_vien_khac = tao_giang_vien('GV_CB3')
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL2', ten_hoc_phan='CSDL2', so_tin_chi=3)
        self.lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL2_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.dang_ky1 = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        self.dang_ky2 = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien2, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        self.diem1 = Diem.objects.create(ma_dang_ky=self.dang_ky1, diem_qua_trinh=8, diem_thi=8)
        # sinh_vien2 chưa đủ điểm (chỉ có điểm quá trình) -> không được công bố khi bấm "cả lớp".
        self.diem2 = Diem.objects.create(ma_dang_ky=self.dang_ky2, diem_qua_trinh=7, diem_thi=None)

    def test_giang_vien_cong_bo_ca_lop(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:cong_bo_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.assertRedirects(response, reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.diem1.refresh_from_db()
        self.diem2.refresh_from_db()
        self.assertTrue(self.diem1.da_cong_bo)
        self.assertFalse(self.diem2.da_cong_bo)

    def test_giang_vien_khac_khong_duoc_cong_bo(self):
        self.client.force_login(self.giang_vien_khac.ma_tai_khoan)
        response = self.client.post(reverse('grades:cong_bo_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.assertEqual(response.status_code, 403)

    def test_sua_diem_sau_cong_bo_tu_dat_lai_chua_cong_bo(self):
        self.diem1.da_cong_bo = True
        self.diem1.save(update_fields=['da_cong_bo'])
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[self.dang_ky1.pk]), {
            'diem_qua_trinh': '9.0', 'diem_thi': '9.0',
        })
        self.assertRedirects(response, reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.diem1.refresh_from_db()
        self.assertFalse(self.diem1.da_cong_bo)

    def test_luu_diem_khong_doi_gia_tri_giu_nguyen_trang_thai_cong_bo(self):
        self.diem1.da_cong_bo = True
        self.diem1.save(update_fields=['da_cong_bo'])
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[self.dang_ky1.pk]), {
            'diem_qua_trinh': '8.0', 'diem_thi': '8.0',
        })
        self.assertRedirects(response, reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.diem1.refresh_from_db()
        self.assertTrue(self.diem1.da_cong_bo)

    def test_sinh_vien_khong_thay_diem_chua_cong_bo(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertContains(response, 'Đang chờ công bố')

    def test_sinh_vien_thay_diem_sau_khi_cong_bo(self):
        self.diem1.da_cong_bo = True
        self.diem1.save(update_fields=['da_cong_bo'])
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertNotContains(response, 'Đang chờ công bố')
        # LANGUAGE_CODE='vi' -> số hiển thị theo kiểu Việt Nam (dấu phẩy thập phân), xem
        # docs/thiet_ke_giao_dien.md.
        self.assertContains(response, '8,0')

    def test_giang_vien_van_thay_diem_that_du_chua_cong_bo(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_lop', args=[self.lop_hoc_phan.pk]))
        self.assertContains(response, '8,00')
        self.assertContains(response, 'Chưa công bố')

    def test_co_van_van_thay_diem_that_du_chua_cong_bo(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk]))
        self.assertNotContains(response, 'Đang chờ công bố')


@tag('tich_hop')
class XuatBangDiemPdfTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT_PDF1')
        self.sinh_vien = tao_sinh_vien('SV_PDF1', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_PDF1')
        self.hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL3', ten_hoc_phan='CSDL3', so_tin_chi=3)
        self.lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL3_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=self.dang_ky, diem_qua_trinh=8, diem_thi=8, da_cong_bo=True)
        self.client.force_login(self.sinh_vien.ma_tai_khoan)

    def test_xuat_pdf_chay_khong_loi(self):
        response = self.client.get(reverse('grades:xuat_bang_diem_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        noi_dung = b''.join(response.streaming_content)
        self.assertTrue(noi_dung.startswith(b'%PDF'))

    def test_giang_vien_khong_xuat_duoc_bang_diem_sinh_vien(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:xuat_bang_diem_pdf'))
        self.assertEqual(response.status_code, 403)


@tag('tich_hop')
class CanhBaoHocVuViewTest(TestCase):
    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT_CB4')
        self.lop_hanh_chinh_khac, self.co_van_khac = tao_lop_hanh_chinh('CNTT_CB5')
        self.sinh_vien = tao_sinh_vien('SV_CB4', self.lop_hanh_chinh)
        self.sinh_vien_khac = tao_sinh_vien('SV_CB5', self.lop_hanh_chinh_khac)
        self.giang_vien = tao_giang_vien('GV_CB4')
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_cb', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='HPX', ten_hoc_phan='HPX', so_tin_chi=3)
        lop_hp = LopHocPhan.objects.create(
            ma_lop_hoc_phan='HPX_L', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien_khac, ma_lop_hoc_phan=lop_hp, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=Decimal('2'), diem_thi=Decimal('2'), da_cong_bo=True)

    def test_co_van_khong_thay_sinh_vien_ngoai_lop_minh(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('grades:canh_bao_co_van'))
        self.assertNotContains(response, 'SV_CB5')

    def test_co_van_thay_sinh_vien_lop_minh_bi_canh_bao(self):
        self.client.force_login(self.co_van_khac.ma_tai_khoan)
        response = self.client.get(reverse('grades:canh_bao_co_van'))
        self.assertContains(response, 'SV_CB5')

    def test_giang_vien_khong_vao_duoc_trang_canh_bao_co_van(self):
        self.client.force_login(self.giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('grades:canh_bao_co_van'))
        self.assertEqual(response.status_code, 403)

    def test_phong_dao_tao_xem_duoc_toan_truong_theo_bo_loc(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(
            reverse('grades:canh_bao_phong_dao_tao'), {'hoc_ky': '1', 'nam_hoc': '2025-2026'}
        )
        self.assertContains(response, 'SV_CB5')

    def test_phong_dao_tao_chua_loc_khong_hien_danh_sach(self):
        self.client.force_login(self.phong_dao_tao)
        response = self.client.get(reverse('grades:canh_bao_phong_dao_tao'))
        self.assertNotContains(response, 'SV_CB5')

    def test_co_van_khong_vao_duoc_trang_pdt(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('grades:canh_bao_phong_dao_tao'))
        self.assertEqual(response.status_code, 403)


@tag('tich_hop')
class GiaoDienBangDiemSinhVienTest(TestCase):
    """Giao diện trang bảng điểm (lượt giao diện 2/3): khối tổng hợp, bảng nhóm theo học kỳ,
    chip trạng thái, nút thay cho liên kết chữ. Chỉ đổi template, không đổi view."""

    def setUp(self):
        self.lop_hanh_chinh, self.co_van = tao_lop_hanh_chinh('CNTT_GD')
        self.sinh_vien = tao_sinh_vien('SV_GD1', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_GD1')
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='pdt_gd', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU
        )
        self.hoc_phan = {
            ma: HocPhan.objects.create(ma_hoc_phan=ma, ten_hoc_phan=f'Học phần {ma}', so_tin_chi=tin_chi)
            for ma, tin_chi in (('HPA', 3), ('HPB', 4), ('HPC', 2), ('HPD', 3), ('HPE', 2), ('HPF', 2))
        }
        self.url = reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk])
        self.client.force_login(self.sinh_vien.ma_tai_khoan)

    def _dang_ky(self, ma_hoc_phan, hoc_ky, nam_hoc, diem=None, da_cong_bo=True):
        lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan=f'{ma_hoc_phan}_{hoc_ky}_{nam_hoc}', hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=40,
            ma_hoc_phan=self.hoc_phan[ma_hoc_phan], ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        if diem is not None:
            Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=diem[0], diem_thi=diem[1], da_cong_bo=da_cong_bo)
        return dang_ky

    def _trang(self, **tham_so):
        return self.client.get(self.url, tham_so)

    def test_nhom_theo_hoc_ky_dung_thu_tu_va_tieu_de_nhom(self):
        # Xem cả năm học: mỗi học kỳ của năm là một nhóm, học kỳ 1 trước học kỳ 2; năm khác không hiện.
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self._dang_ky('HPB', '1', '2025-2026', diem=(7, 7))
        self._dang_ky('HPC', '2', '2025-2026', diem=(9, 9))
        self._dang_ky('HPD', '1', '2024-2025', diem=(6, 6))
        noi_dung = self._trang(nam_hoc='2025-2026', hoc_ky='').content.decode()
        self.assertEqual(noi_dung.count('<tr class="hang-nhom">'), 2)
        nhom_1, nhom_2 = noi_dung.index('Học kỳ 1 - 2025-2026'), noi_dung.index('Học kỳ 2 - 2025-2026')
        self.assertTrue(nhom_1 < noi_dung.index('<td>HPA</td>') < nhom_2)
        self.assertTrue(nhom_1 < noi_dung.index('<td>HPB</td>') < nhom_2)
        self.assertTrue(nhom_2 < noi_dung.index('<td>HPC</td>'))
        self.assertNotIn('<td>HPD</td>', noi_dung)
        self.assertIn('<td colspan="7">Học kỳ 1 - 2025-2026</td>', noi_dung)

    def test_chon_nam_va_ky_chi_hien_hoc_ky_do(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self._dang_ky('HPC', '2', '2025-2026', diem=(9, 9))
        self._dang_ky('HPD', '1', '2024-2025', diem=(6, 6))
        response = self._trang(nam_hoc='2025-2026', hoc_ky='2')
        noi_dung = response.content.decode()
        self.assertIn('<td>HPC</td>', noi_dung)
        self.assertNotIn('<td>HPA</td>', noi_dung)
        self.assertNotIn('<td>HPD</td>', noi_dung)
        self.assertEqual(noi_dung.count('<tr class="hang-nhom">'), 1)
        self.assertIn('Điểm trung bình học kỳ 2 - 2025-2026', noi_dung)
        self.assertEqual(response.context['diem_tb_hoc_ky'], Decimal('9.00'))

    def test_chon_ca_nam_tinh_diem_trung_binh_nam_hoc(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))  # 3 tín chỉ, tổng kết 8.0
        self._dang_ky('HPC', '2', '2025-2026', diem=(5, 5))  # 2 tín chỉ, tổng kết 5.0
        self._dang_ky('HPD', '1', '2024-2025', diem=(2, 2))  # năm khác, không tính
        response = self._trang(nam_hoc='2025-2026', hoc_ky='')
        self.assertTrue(response.context['ca_nam'])
        # (8.0*3 + 5.0*2) / 5 = 6.80
        self.assertEqual(response.context['diem_tb_hoc_ky'], Decimal('6.80'))
        self.assertContains(response, 'Điểm trung bình năm học 2025-2026')
        self.assertContains(response, 'Xếp loại năm học')
        self.assertContains(response, '<option value="" selected>Cả năm</option>')
        self.assertIsNone(response.context['canh_bao'])

    def test_nam_moi_co_mot_ky_thi_khong_xem_ca_nam_ma_xem_ky_do(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self._dang_ky('HPD', '1', '2024-2025', diem=(6, 6))
        self._dang_ky('HPE', '2', '2024-2025', diem=(7, 7))
        response = self._trang(nam_hoc='2025-2026', hoc_ky='')
        self.assertFalse(response.context['ca_nam'])
        self.assertTrue(response.context['chi_mot_ky'])
        self.assertEqual(response.context['hoc_ky_loc'], '1')
        self.assertContains(response, 'Năm học 2025-2026 mới có học kỳ 1 nên chưa xem được cả năm')
        self.assertContains(response, '<option value="1" selected>Học kỳ 1</option>')
        self.assertContains(response, 'Điểm trung bình học kỳ 1 - 2025-2026')
        self.assertNotContains(response, '<td>HPD</td>')

    def test_mac_dinh_chua_chon_hien_moi_hoc_ky_va_bo_loc_chi_gom_ky_cua_sinh_vien(self):
        self._dang_ky('HPA', '1', '2025-2026')
        self._dang_ky('HPD', '2', '2024-2025', diem=(6, 6))
        response = self._trang()
        self.assertTrue(response.context['tat_ca'])
        self.assertEqual((response.context['hoc_ky_loc'], response.context['nam_hoc_loc']), ('', ''))
        self.assertContains(response, '<td>HPD</td>')
        self.assertContains(response, '<td>HPA</td>')
        self.assertEqual(response.content.decode().count('<tr class="hang-nhom">'), 2)
        self.assertContains(response, '<option value="" selected>-- Chọn năm học --</option>')
        self.assertContains(response, '<option value="" selected>-- Chọn học kỳ --</option>')
        self.assertNotContains(response, 'Xem tất cả')
        self.assertIsNone(response.context['canh_bao'])
        self.assertEqual(response.context['cac_nam_hoc'], ['2025-2026', '2024-2025'])
        self.assertEqual(response.context['cac_hoc_ky'], ['1', '2'])
        # Đã chọn thì có nút quay về xem tất cả.
        self.assertContains(self._trang(nam_hoc='2024-2025', hoc_ky='2'), 'Xem tất cả')

    def test_nam_hoc_khong_hop_le_hien_tat_ca(self):
        self._dang_ky('HPD', '2', '2024-2025', diem=(6, 6))
        response = self._trang(nam_hoc='1999-2000', hoc_ky='1')
        self.assertTrue(response.context['tat_ca'])
        self.assertEqual((response.context['hoc_ky_loc'], response.context['nam_hoc_loc']), ('', ''))
        self.assertContains(response, '<td>HPD</td>')

    def test_cac_cot_dung_thu_tu_va_khong_co_cot_diem_chu(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        response = self._trang()
        phan_dau_bang = re.search(r'<thead>.*?</thead>', response.content.decode(), re.S).group(0)
        cac_cot = [re.sub(r'<[^>]+>', '', cot).strip() for cot in re.findall(r'<th[^>]*>.*?</th>', phan_dau_bang, re.S)]
        self.assertEqual(cac_cot, [
            'Mã học phần', 'Tên học phần', 'Số tín chỉ', 'Điểm quá trình', 'Điểm thi', 'Điểm tổng kết', 'Trạng thái',
        ])
        self.assertNotContains(response, 'Điểm chữ')

    def test_hang_diem_co_ma_ten_tin_chi_diem_va_chip_da_cong_bo(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        response = self._trang()
        self.assertContains(response, '<td>HPA</td>')
        self.assertContains(response, '<td>Học phần HPA</td>')
        self.assertContains(response, '<td class="so">3</td>')
        self.assertContains(response, '8,00')
        self.assertContains(response, '<strong>8,0</strong>')
        self.assertContains(response, '<span class="chip chip--con_hieu_luc">Đã công bố</span>')

    def test_sinh_vien_diem_chua_cong_bo_bi_an_va_hien_chip_cho_cong_bo(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(6.75, 6.75), da_cong_bo=False)
        response = self._trang()
        self.assertContains(response, '<span class="chip chip--thieu_tien_quyet">Đang chờ công bố</span>')
        self.assertNotContains(response, '6,75')

    def test_hoc_phan_chua_co_diem_hien_chip_chua_nhap(self):
        self._dang_ky('HPA', '1', '2025-2026')
        self.assertContains(self._trang(), '<span class="chip chip--da_huy">Chưa nhập điểm</span>')

    def test_co_van_thay_diem_that_va_chip_chua_cong_bo(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(6.75, 6.75), da_cong_bo=False)
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self._trang()
        self.assertContains(response, '6,75')
        self.assertContains(response, '<span class="chip chip--da_huy">Chưa công bố</span>')
        self.assertNotContains(response, 'Đang chờ công bố')

    def test_diem_bang_khong_khong_bi_hieu_nham_la_chua_nhap(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(0, 0))
        response = self._trang()
        self.assertContains(response, '0,00')
        self.assertContains(response, '<strong>0,0</strong>')
        self.assertNotContains(response, 'Chưa đủ điểm')

    def test_chua_co_du_lieu_diem(self):
        response = self._trang()
        self.assertContains(response, '<td colspan="7">Chưa có dữ liệu điểm.</td>')

    def test_khoi_tong_hop_co_bon_o_dung_nhan_va_gia_tri(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self._dang_ky('HPB', '1', '2025-2026', diem=(5, 6))
        # Mới vào (chưa chọn): chỉ hai ô tích lũy.
        mac_dinh = self._trang().content.decode()
        self.assertIn('<div class="luoi-tong-hop luoi-tong-hop--2">', mac_dinh)
        self.assertEqual(mac_dinh.count('<div class="o-tong-hop">'), 2)
        self.assertNotIn('Xếp loại học kỳ', mac_dinh)
        # Chọn học kỳ: thêm hai ô của học kỳ.
        response = self._trang(nam_hoc='2025-2026', hoc_ky='1')
        noi_dung = response.content.decode()
        self.assertIn('<div class="luoi-tong-hop luoi-tong-hop--4">', noi_dung)
        self.assertEqual(noi_dung.count('<div class="o-tong-hop">'), 4)
        for nhan in ('Điểm trung bình học kỳ 1 - 2025-2026', 'Xếp loại học kỳ', 'Điểm trung bình tích lũy', 'Xếp loại tích lũy'):
            self.assertIn(f'<div class="o-tong-hop__nhan">{nhan}</div>', noi_dung)
        diem_tb = str(response.context['diem_tb_tich_luy']).replace('.', ',')
        self.assertContains(response, f'<div class="o-tong-hop__gia-tri">{diem_tb}</div>')
        self.assertContains(response, f'<div class="o-tong-hop__gia-tri o-tong-hop__gia-tri--den">{response.context["xep_loai_tich_luy"]}</div>')

    def test_khoi_tong_hop_bao_chua_co_diem_thay_vi_so(self):
        response = self._trang()
        self.assertContains(response, 'Chưa có học phần nào đủ điểm.')
        self.assertContains(response, 'Chưa có điểm để xếp loại.', count=1)
        self._dang_ky('HPA', '1', '2025-2026')
        response = self._trang(nam_hoc='2025-2026', hoc_ky='1')
        self.assertContains(response, 'Chưa có học phần nào đủ điểm trong học kỳ này.')
        self.assertContains(response, 'Chưa có điểm để xếp loại.', count=2)

    def test_canh_bao_mau_vang_khi_mot_ly_do_va_mau_do_khi_hai_ly_do(self):
        self._dang_ky('HPE', '3', '2026-2027', diem=(2, 2))
        response = self._trang(hoc_ky='3', nam_hoc='2026-2027')
        self.assertContains(response, '<div class="thong-bao--warning canh-bao-khoi">')
        self.assertNotContains(response, '<div class="thong-bao--error canh-bao-khoi">')

        self._dang_ky('HPF', '3', '2026-2027', diem=(2, 2))
        response = self._trang(hoc_ky='3', nam_hoc='2026-2027')
        self.assertContains(response, '<div class="thong-bao--error canh-bao-khoi">')
        self.assertContains(response, 'Cảnh báo học vụ &mdash; Học kỳ 3, năm học 2026-2027')

    def test_khong_canh_bao_khi_diem_tot(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self.assertNotContains(self._trang(), 'canh-bao-khoi">')

    def test_sinh_vien_co_nut_xuat_pdf_va_nut_ai_khong_phai_lien_ket_chu(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        response = self._trang()
        self.assertContains(response, f'<a class="nut nut-chinh" href="{reverse("grades:xuat_bang_diem_pdf")}">Xuất PDF</a>')
        self.assertContains(
            response,
            f'<a class="nut nut-nhe" href="{reverse("tom_tat_ket_qua:toi")}">Nhờ AI tóm tắt kết quả học tập</a>',
        )
        phan_main = re.search(r'<main>.*?</main>', response.content.decode(), re.S).group(0)
        for the in re.findall(r'<a [^>]*>', phan_main):
            self.assertIn('class="nut', the)

    def test_co_van_co_nut_ai_rieng_va_khong_co_nut_pdf(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self._trang()
        self.assertContains(response, f'<a class="nut nut-nhe" href="{reverse("tom_tat_ket_qua:co_van")}">')
        self.assertNotContains(response, 'Xuất PDF')

    def test_phong_dao_tao_khong_co_nut_pdf_hay_ai(self):
        self.client.force_login(self.phong_dao_tao)
        response = self._trang()
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Xuất PDF')
        self.assertNotContains(response, 'Nhờ AI')

    def test_khong_dung_chu_gach_chan(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self.assertNotIn('underline', self._trang().content.decode())

    def test_html_can_bang_the_voi_moi_vai_tro_xem(self):
        self._dang_ky('HPA', '1', '2025-2026', diem=(8, 8))
        self._dang_ky('HPB', '2', '2025-2026', diem=(2, 2), da_cong_bo=False)
        self._dang_ky('HPC', '2', '2025-2026')
        for tai_khoan in (self.sinh_vien.ma_tai_khoan, self.co_van.ma_tai_khoan, self.phong_dao_tao):
            self.client.force_login(tai_khoan)
            loi, con_mo = kiem_tra_can_bang_the(self._trang().content.decode())
            self.assertEqual(loi, [])
            self.assertEqual(con_mo, [])
