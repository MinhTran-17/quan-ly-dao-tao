from django.contrib.auth import get_user_model
from django.test import TestCase, tag
from django.urls import reverse
from django.utils import timezone

from academics.models import HocPhan, LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from people.models import CoVanHocTap, GiangVien, SinhVien

from .models import DaDocThongBao, DoiTuongThongBao, ThongBao
from .services import so_luong_chua_doc, thong_bao_lien_quan

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


def tao_co_van(ma_co_van):
    tk = TaiKhoan.objects.create_user(
        ten_dang_nhap=f'tk_{ma_co_van}', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU
    )
    return CoVanHocTap.objects.create(
        ma_co_van=ma_co_van, ho_ten='Cố vấn Test', email=f'{ma_co_van}@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk,
    )


def tao_lop_hanh_chinh(ma_lop, co_van):
    nganh, _ = NganhHoc.objects.get_or_create(ma_nganh='CNTT', defaults={'ten_nganh': 'Công nghệ thông tin'})
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
class ThongBaoPhongDaoTaoTest(TestCase):
    def setUp(self):
        self.pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_tb', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU)
        self.co_van = tao_co_van('CV_TB01')
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_TB1', self.co_van)
        self.sinh_vien = tao_sinh_vien('SV_TB01', self.lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV_TB01')
        self.client.force_login(self.pdt)

    def test_gui_tat_ca_moi_vai_tro_deu_thay(self):
        self.client.post(reverse('thong_bao:gui_phong_dao_tao'), {
            'tieu_de': 'Nghỉ lễ', 'noi_dung': 'Trường nghỉ lễ.', 'doi_tuong': DoiTuongThongBao.TAT_CA,
        })
        thong_bao = ThongBao.objects.get(tieu_de='Nghỉ lễ')

        for tai_khoan in (self.sinh_vien.ma_tai_khoan, self.giang_vien.ma_tai_khoan, self.co_van.ma_tai_khoan, self.pdt):
            self.assertIn(thong_bao, thong_bao_lien_quan(tai_khoan))

    def test_gui_theo_vai_tro_chi_vai_tro_do_thay(self):
        self.client.post(reverse('thong_bao:gui_phong_dao_tao'), {
            'tieu_de': 'Họp giảng viên', 'noi_dung': 'Mời họp.', 'doi_tuong': DoiTuongThongBao.GIANG_VIEN,
        })
        thong_bao = ThongBao.objects.get(tieu_de='Họp giảng viên')

        self.assertIn(thong_bao, thong_bao_lien_quan(self.giang_vien.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.sinh_vien.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.co_van.ma_tai_khoan))

    def test_sinh_vien_khong_gui_duoc_thong_bao_phong_dao_tao(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('thong_bao:gui_phong_dao_tao'))
        self.assertEqual(response.status_code, 403)


@tag('tich_hop')
class ThongBaoLopHocPhanTest(TestCase):
    def setUp(self):
        self.co_van = tao_co_van('CV_TB02')
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_TB2', self.co_van)
        self.giang_vien = tao_giang_vien('GV_TB02')
        self.giang_vien_khac = tao_giang_vien('GV_TB03')
        hoc_phan = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.lop_hoc_phan = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_TB01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=hoc_phan, ma_giang_vien=self.giang_vien,
        )
        self.sv_con_hieu_luc = tao_sinh_vien('SV_TB02', self.lop_hanh_chinh)
        self.sv_da_huy = tao_sinh_vien('SV_TB03', self.lop_hanh_chinh)
        self.sv_khong_dang_ky = tao_sinh_vien('SV_TB04', self.lop_hanh_chinh)
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sv_con_hieu_luc, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sv_da_huy, ma_lop_hoc_phan=self.lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
            trang_thai=TrangThaiDangKy.DA_HUY,
        )
        self.client.force_login(self.giang_vien.ma_tai_khoan)

    def test_chi_hien_lop_phu_trach_trong_form(self):
        response = self.client.get(reverse('thong_bao:gui_giang_vien'))
        self.assertContains(response, 'CSDL_TB01')

    def test_gui_thong_bao_lop_hoc_phan(self):
        response = self.client.post(reverse('thong_bao:gui_giang_vien'), {
            'lop_hoc_phan': self.lop_hoc_phan.pk, 'tieu_de': 'Đổi lịch học', 'noi_dung': 'Chuyển sang thứ 4.',
        })
        self.assertRedirects(response, reverse('thong_bao:gui_giang_vien'))
        thong_bao = ThongBao.objects.get(tieu_de='Đổi lịch học')
        self.assertEqual(thong_bao.doi_tuong, DoiTuongThongBao.LOP_HOC_PHAN)

        self.assertIn(thong_bao, thong_bao_lien_quan(self.sv_con_hieu_luc.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.sv_da_huy.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.sv_khong_dang_ky.ma_tai_khoan))
        self.assertIn(thong_bao, thong_bao_lien_quan(self.giang_vien.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.giang_vien_khac.ma_tai_khoan))

    def test_khong_gui_duoc_cho_lop_khong_phu_trach(self):
        lop_khac = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_TB02', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.lop_hoc_phan.ma_hoc_phan, ma_giang_vien=self.giang_vien_khac,
        )
        response = self.client.post(reverse('thong_bao:gui_giang_vien'), {
            'lop_hoc_phan': lop_khac.pk, 'tieu_de': 'X', 'noi_dung': 'Y',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ThongBao.objects.filter(tieu_de='X').exists())


@tag('tich_hop')
class ThongBaoLopHanhChinhTest(TestCase):
    def setUp(self):
        self.co_van = tao_co_van('CV_TB04')
        self.co_van_khac = tao_co_van('CV_TB05')
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_TB3', self.co_van)
        self.sv_trong_lop = tao_sinh_vien('SV_TB05', self.lop_hanh_chinh)
        lop_khac = tao_lop_hanh_chinh('CNTT_TB4', self.co_van_khac)
        self.sv_lop_khac = tao_sinh_vien('SV_TB06', lop_khac)
        self.client.force_login(self.co_van.ma_tai_khoan)

    def test_gui_thong_bao_lop_hanh_chinh(self):
        response = self.client.post(reverse('thong_bao:gui_co_van'), {
            'lop_hanh_chinh': self.lop_hanh_chinh.pk, 'tieu_de': 'Sinh hoạt lớp', 'noi_dung': 'Họp lớp chiều thứ 6.',
        })
        self.assertRedirects(response, reverse('thong_bao:gui_co_van'))
        thong_bao = ThongBao.objects.get(tieu_de='Sinh hoạt lớp')
        self.assertEqual(thong_bao.doi_tuong, DoiTuongThongBao.LOP_HANH_CHINH)

        self.assertIn(thong_bao, thong_bao_lien_quan(self.sv_trong_lop.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.sv_lop_khac.ma_tai_khoan))
        self.assertIn(thong_bao, thong_bao_lien_quan(self.co_van.ma_tai_khoan))
        self.assertNotIn(thong_bao, thong_bao_lien_quan(self.co_van_khac.ma_tai_khoan))


@tag('tich_hop')
class DanhDauDaDocTest(TestCase):
    def setUp(self):
        self.pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_dd', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU)
        self.co_van = tao_co_van('CV_DD01')
        self.lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_DD5', self.co_van)
        self.sinh_vien = tao_sinh_vien('SV_DD10', self.lop_hanh_chinh)
        self.thong_bao = ThongBao.objects.create(
            tieu_de='Thông báo chung', noi_dung='Nội dung.', nguoi_gui=self.pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )

    def test_so_chua_doc_giam_sau_khi_xem_chi_tiet(self):
        self.assertEqual(so_luong_chua_doc(self.sinh_vien.ma_tai_khoan), 1)
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('thong_bao:chi_tiet', args=[self.thong_bao.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(so_luong_chua_doc(self.sinh_vien.ma_tai_khoan), 0)
        self.assertTrue(DaDocThongBao.objects.filter(thong_bao=self.thong_bao, tai_khoan=self.sinh_vien.ma_tai_khoan).exists())

    def test_mo_lai_khong_tao_trung_ban_ghi_da_doc(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        self.client.get(reverse('thong_bao:chi_tiet', args=[self.thong_bao.pk]))
        self.client.get(reverse('thong_bao:chi_tiet', args=[self.thong_bao.pk]))
        self.assertEqual(
            DaDocThongBao.objects.filter(thong_bao=self.thong_bao, tai_khoan=self.sinh_vien.ma_tai_khoan).count(), 1
        )

    def test_chip_chua_doc_hien_tren_menu(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('accounts:trang_chu'))
        self.assertContains(response, 'chip-thong-bao')

    def test_khong_xem_duoc_thong_bao_ngoai_pham_vi(self):
        giang_vien = tao_giang_vien('GV_DD10')
        lop_hanh_chinh_khac = tao_lop_hanh_chinh('CNTT_DD6', self.co_van)
        thong_bao_lop = ThongBao.objects.create(
            tieu_de='Chỉ lớp X', noi_dung='...', nguoi_gui=self.co_van.ma_tai_khoan,
            doi_tuong=DoiTuongThongBao.LOP_HANH_CHINH, lop_hanh_chinh=lop_hanh_chinh_khac,
        )
        self.client.force_login(giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('thong_bao:chi_tiet', args=[thong_bao_lop.pk]))
        self.assertEqual(response.status_code, 404)


@tag('tich_hop')
class DanhSachThongBaoTest(TestCase):
    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('thong_bao:danh_sach'))
        self.assertEqual(response.status_code, 302)

    def test_trang_danh_sach_hien_moi_va_da_doc(self):
        pdt = TaiKhoan.objects.create_user(ten_dang_nhap='pdt_ds', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU)
        co_van = tao_co_van('CV_DS01')
        sinh_vien = tao_sinh_vien('SV_DS01', tao_lop_hanh_chinh('CNTT_DS1', co_van))
        da_doc = ThongBao.objects.create(
            tieu_de='Đã xem rồi', noi_dung='...', nguoi_gui=pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        ThongBao.objects.create(
            tieu_de='Chưa xem', noi_dung='...', nguoi_gui=pdt, doi_tuong=DoiTuongThongBao.TAT_CA,
        )
        DaDocThongBao.objects.create(thong_bao=da_doc, tai_khoan=sinh_vien.ma_tai_khoan)

        self.client.force_login(sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('thong_bao:danh_sach'))
        self.assertEqual(response.status_code, 200)
        trang_thai = {tb.tieu_de: tb.da_doc_boi_toi for tb in response.context['danh_sach']}
        self.assertEqual(trang_thai, {'Đã xem rồi': True, 'Chưa xem': False})
        self.assertContains(response, 'Đã đọc')
        self.assertContains(response, 'Mới')
        self.assertContains(response, '<table class="bang-sv">')
        self.assertContains(response, '<tr class="hang-diem">', count=2)
