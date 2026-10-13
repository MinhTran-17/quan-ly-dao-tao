import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import ChiTietChuongTrinh, ChuongTrinhDaoTao, HocPhan, LopHanhChinh, NganhHoc
from accounts.models import VaiTro
from accounts.tests import kiem_tra_can_bang_the
from classes.models import LopHocPhan
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from grades.models import Diem
from people.models import CoVanHocTap, GiangVien, SinhVien

from .services import tinh_tien_do

TaiKhoan = get_user_model()
MAT_KHAU = 'MatKhauManh123'


def tao_sinh_vien(ma, ma_lop):
    tk = TaiKhoan.objects.create_user(ten_dang_nhap=f'tk_{ma}', vai_tro=VaiTro.SINH_VIEN, password=MAT_KHAU)
    return SinhVien.objects.create(
        ma_sinh_vien=ma, ho_ten=f'Sinh viên {ma}', ngay_sinh='2004-01-01',
        email=f'{ma}@test.local', so_dien_thoai='0900000000', ma_lop=ma_lop, ma_tai_khoan=tk,
    )


def tao_giang_vien(ma):
    tk = TaiKhoan.objects.create_user(ten_dang_nhap=f'tk_{ma}', vai_tro=VaiTro.GIANG_VIEN, password=MAT_KHAU)
    return GiangVien.objects.create(
        ma_giang_vien=ma, ho_ten=f'Giảng viên {ma}', email=f'{ma}@test.local',
        so_dien_thoai='0900000000', ma_tai_khoan=tk,
    )


def dang_ky_va_cham_diem(sinh_vien, lop_hoc_phan, diem_qua_trinh, diem_thi):
    dang_ky = DangKyHocPhan.objects.create(
        ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
    )
    Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=diem_qua_trinh, diem_thi=diem_thi)
    return dang_ky


class TinhTienDoTest(TestCase):
    def setUp(self):
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_td', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_TD', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        self.giang_vien = tao_giang_vien('GV_TD')
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)
        self.tu_chon = HocPhan.objects.create(ma_hoc_phan='TUCHON', ten_hoc_phan='Học phần tự chọn', so_tin_chi=2)

    def test_chua_gan_chuong_trinh_dao_tao(self):
        lop = LopHanhChinh.objects.create(ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=self.nganh, ma_co_van=self.co_van)
        sinh_vien = tao_sinh_vien('SV001', lop)
        ket_qua = tinh_tien_do(sinh_vien)
        self.assertFalse(ket_qua['co_chuong_trinh'])

    def test_da_dat_het_bat_buoc(self):
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=1, bat_buoc=True)
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.ctdl, hoc_ky_du_kien=1, bat_buoc=True)
        lop = LopHanhChinh.objects.create(
            ma_lop='CNTT2', ten_lop='CNTT K2', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=chuong_trinh,
        )
        sinh_vien = tao_sinh_vien('SV002', lop)
        lop_csdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.csdl, ma_giang_vien=self.giang_vien,
        )
        lop_ctdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDL_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.ctdl, ma_giang_vien=self.giang_vien,
        )
        dang_ky_va_cham_diem(sinh_vien, lop_csdl, Decimal('8'), Decimal('8'))
        dang_ky_va_cham_diem(sinh_vien, lop_ctdl, Decimal('7'), Decimal('7'))

        ket_qua = tinh_tien_do(sinh_vien)
        self.assertTrue(ket_qua['co_chuong_trinh'])
        self.assertEqual(ket_qua['so_bat_buoc_da_dat'], 2)
        self.assertEqual(ket_qua['tong_so_bat_buoc'], 2)
        self.assertEqual(ket_qua['phan_tram_hoan_thanh'], 100)
        self.assertEqual(ket_qua['con_thieu_bat_buoc'], [])

    def test_con_thieu_mot_so_hoc_phan(self):
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=1, bat_buoc=True)
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.ctdl, hoc_ky_du_kien=2, bat_buoc=True)
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.tu_chon, hoc_ky_du_kien=3, bat_buoc=False)
        lop = LopHanhChinh.objects.create(
            ma_lop='CNTT3', ten_lop='CNTT K3', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=chuong_trinh,
        )
        sinh_vien = tao_sinh_vien('SV003', lop)
        lop_csdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_02', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.csdl, ma_giang_vien=self.giang_vien,
        )
        dang_ky_va_cham_diem(sinh_vien, lop_csdl, Decimal('8'), Decimal('8'))

        ket_qua = tinh_tien_do(sinh_vien)
        self.assertEqual(ket_qua['so_bat_buoc_da_dat'], 1)
        self.assertEqual(ket_qua['tong_so_bat_buoc'], 2)
        self.assertEqual(ket_qua['phan_tram_hoan_thanh'], 50)
        self.assertEqual([ct.hoc_phan_id for ct in ket_qua['con_thieu_bat_buoc']], ['CTDL'])
        self.assertEqual([ct.hoc_phan_id for ct in ket_qua['con_thieu_tu_chon']], ['TUCHON'])
        self.assertEqual([ct.hoc_phan_id for ct in ket_qua['da_dat_bat_buoc']], ['CSDL'])

    def test_thanh_tien_do_dung_dau_cham_khi_phan_tram_khong_tron(self):
        # LANGUAGE_CODE='vi' in số thập phân bằng dấu phẩy ("33,3"), không hợp lệ trong CSS
        # "width: ...%" — phải dùng |unlocalize để thanh tiến độ không bị rỗng.
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        for hoc_ky, hoc_phan in enumerate((self.csdl, self.ctdl, self.tu_chon), start=1):
            ChiTietChuongTrinh.objects.create(
                chuong_trinh=chuong_trinh, hoc_phan=hoc_phan, hoc_ky_du_kien=hoc_ky, bat_buoc=True,
            )
        lop = LopHanhChinh.objects.create(
            ma_lop='CNTT_UL', ten_lop='CNTT UL', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=chuong_trinh,
        )
        sinh_vien = tao_sinh_vien('SV_UL', lop)
        lop_csdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_UL', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.csdl, ma_giang_vien=self.giang_vien,
        )
        dang_ky_va_cham_diem(sinh_vien, lop_csdl, Decimal('8'), Decimal('8'))

        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:co_van'), {'ma_sinh_vien': sinh_vien.pk})
        self.assertEqual(response.context['ket_qua']['phan_tram_hoan_thanh'], 33.3)
        self.assertContains(response, 'style="width: 33.3%;"')
        self.assertNotContains(response, 'width: 33,3%')
        # Chữ hiển thị cho người đọc vẫn theo kiểu Việt Nam (dấu phẩy).
        self.assertContains(response, '33,3%')

    def test_chi_tinh_dang_ky_con_hieu_luc(self):
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        ChiTietChuongTrinh.objects.create(chuong_trinh=chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=1, bat_buoc=True)
        lop = LopHanhChinh.objects.create(
            ma_lop='CNTT4', ten_lop='CNTT K4', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=chuong_trinh,
        )
        sinh_vien = tao_sinh_vien('SV004', lop)
        lop_csdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_03', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.csdl, ma_giang_vien=self.giang_vien,
        )
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_csdl, thoi_gian_dang_ky=timezone.now(),
            trang_thai=TrangThaiDangKy.DA_HUY,
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=9, diem_thi=9)

        ket_qua = tinh_tien_do(sinh_vien)
        self.assertEqual(ket_qua['so_bat_buoc_da_dat'], 0)
        self.assertEqual([ct.hoc_phan_id for ct in ket_qua['con_thieu_bat_buoc']], ['CSDL'])


class TienDoViewTest(TestCase):
    def setUp(self):
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_view', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_VIEW', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        tk_cv_khac = TaiKhoan.objects.create_user(ten_dang_nhap='cv_khac', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van_khac = CoVanHocTap.objects.create(
            ma_co_van='CV_KHAC', ho_ten='Cố vấn khác', email='cv2@test.local', so_dien_thoai='0900000000',
            ma_tai_khoan=tk_cv_khac,
        )
        self.lop = LopHanhChinh.objects.create(ma_lop='CNTT1', ten_lop='CNTT K1', ma_nganh=self.nganh, ma_co_van=self.co_van)
        self.lop_khac = LopHanhChinh.objects.create(
            ma_lop='CNTT2', ten_lop='CNTT K2', ma_nganh=self.nganh, ma_co_van=self.co_van_khac,
        )
        self.sinh_vien = tao_sinh_vien('SV010', self.lop)
        self.sinh_vien_khac = tao_sinh_vien('SV011', self.lop_khac)

    def test_sinh_vien_xem_duoc_tien_do_cua_minh(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:cua_toi'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['ket_qua']['co_chuong_trinh'])

    def test_giang_vien_khong_vao_duoc_trang_sinh_vien(self):
        giang_vien = tao_giang_vien('GV_VIEW')
        self.client.force_login(giang_vien.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:cua_toi'))
        self.assertEqual(response.status_code, 403)

    def test_co_van_xem_duoc_tien_do_sinh_vien_phu_trach(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:co_van'), {'ma_sinh_vien': self.sinh_vien.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['ket_qua'])

    def test_co_van_khong_xem_duoc_sinh_vien_ngoai_pham_vi(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:co_van'), {'ma_sinh_vien': self.sinh_vien_khac.pk})
        self.assertEqual(response.status_code, 403)

    def test_chua_dang_nhap_bi_chuyen_huong(self):
        response = self.client.get(reverse('tien_do_hoc_tap:cua_toi'))
        self.assertEqual(response.status_code, 302)


class TienDoChiDiemDaCongBoTest(TestCase):
    """Phần C: điểm chưa công bố không được coi là 'đã đạt' ở trang tiến độ học tập của
    chính sinh viên, nhưng Cố vấn học tập vẫn thấy tiến độ thật (điểm thật)."""

    def setUp(self):
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_cb', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_CB', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        self.giang_vien = tao_giang_vien('GV_CB')
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        self.chuong_trinh = ChuongTrinhDaoTao.objects.create(
            nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1',
        )
        ChiTietChuongTrinh.objects.create(
            chuong_trinh=self.chuong_trinh, hoc_phan=self.csdl, hoc_ky_du_kien=1, bat_buoc=True,
        )
        self.lop = LopHanhChinh.objects.create(
            ma_lop='CNTT_CB', ten_lop='CNTT K_CB', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=self.chuong_trinh,
        )
        self.sinh_vien = tao_sinh_vien('SV_CB', self.lop)
        lop_csdl = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_CB', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.csdl, ma_giang_vien=self.giang_vien,
        )
        # Điểm đạt nhưng CHƯA công bố (da_cong_bo mặc định False).
        dang_ky_va_cham_diem(self.sinh_vien, lop_csdl, Decimal('8'), Decimal('8'))

    def test_sinh_vien_tu_xem_khong_tinh_diem_chua_cong_bo_la_da_dat(self):
        ket_qua = tinh_tien_do(self.sinh_vien, chi_diem_da_cong_bo=True)
        self.assertEqual(ket_qua['so_bat_buoc_da_dat'], 0)
        self.assertEqual([ct.hoc_phan_id for ct in ket_qua['con_thieu_bat_buoc']], ['CSDL'])

    def test_co_van_van_thay_diem_that_du_chua_cong_bo(self):
        ket_qua = tinh_tien_do(self.sinh_vien)
        self.assertEqual(ket_qua['so_bat_buoc_da_dat'], 1)
        self.assertEqual(ket_qua['con_thieu_bat_buoc'], [])

    def test_view_sinh_vien_tu_xem_khong_tinh_da_dat(self):
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:cua_toi'))
        self.assertEqual(response.context['ket_qua']['so_bat_buoc_da_dat'], 0)

    def test_view_co_van_thay_da_dat_that(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:co_van'), {'ma_sinh_vien': self.sinh_vien.pk})
        self.assertEqual(response.context['ket_qua']['so_bat_buoc_da_dat'], 1)


class TienDoGiaoDienTest(TestCase):
    """Giao diện trang Tiến độ học tập (lượt giao diện 3/3): thanh tiến độ tổng, hai nhóm
    "Đã đạt"/"Còn thiếu" gom theo học kỳ dự kiến, nhãn Bắt buộc/Tự chọn."""

    def setUp(self):
        self.nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        tk_cv = TaiKhoan.objects.create_user(ten_dang_nhap='cv_gd', vai_tro=VaiTro.CO_VAN_HOC_TAP, password=MAT_KHAU)
        self.co_van = CoVanHocTap.objects.create(
            ma_co_van='CV_GD', ho_ten='Cố vấn', email='cv@test.local', so_dien_thoai='0900000000', ma_tai_khoan=tk_cv,
        )
        self.giang_vien = tao_giang_vien('GV_GD')
        self.hp = {
            ma: HocPhan.objects.create(ma_hoc_phan=ma, ten_hoc_phan=f'Học phần {ma}', so_tin_chi=3)
            for ma in ('DAT', 'THIEU1', 'THIEU2', 'THIEU3')
        }
        chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=self.nganh, ten_chuong_trinh='CNTT chuẩn', khoa_hoc='Khóa 1')
        # (học phần, học kỳ dự kiến, bắt buộc): cố ý tạo lộn xộn để kiểm tra việc sắp theo học kỳ.
        for ma, hoc_ky, bat_buoc in (
            ('THIEU3', 2, False), ('DAT', 2, True), ('THIEU2', 1, False), ('THIEU1', 1, True),
        ):
            ChiTietChuongTrinh.objects.create(
                chuong_trinh=chuong_trinh, hoc_phan=self.hp[ma], hoc_ky_du_kien=hoc_ky, bat_buoc=bat_buoc,
            )
        self.lop = LopHanhChinh.objects.create(
            ma_lop='CNTT_GD', ten_lop='CNTT GD', ma_nganh=self.nganh, ma_co_van=self.co_van,
            chuong_trinh_dao_tao=chuong_trinh,
        )
        self.sinh_vien = tao_sinh_vien('SV_GD', self.lop)
        lop_dat = LopHocPhan.objects.create(
            ma_lop_hoc_phan='DAT_01', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=self.hp['DAT'], ma_giang_vien=self.giang_vien,
        )
        dang_ky = dang_ky_va_cham_diem(self.sinh_vien, lop_dat, Decimal('8'), Decimal('8'))
        Diem.objects.filter(ma_dang_ky=dang_ky).update(da_cong_bo=True)
        self.client.force_login(self.sinh_vien.ma_tai_khoan)
        self.url = reverse('tien_do_hoc_tap:cua_toi')

    def test_ba_o_tong_hop_va_thanh_tien_do(self):
        response = self.client.get(self.url)
        noi_dung = response.content.decode()
        self.assertEqual(noi_dung.count('<div class="o-tong-hop">'), 3)
        self.assertContains(response, '<div class="o-tong-hop__gia-tri">50,0%</div>')
        self.assertContains(response, 'style="width: 50.0%;"')
        self.assertContains(response, '1 <small>/ 2</small>')

    def test_hai_nhom_da_dat_con_thieu_voi_chip_dung_mau(self):
        response = self.client.get(self.url)
        self.assertContains(response, '<h2>Đã đạt</h2>')
        self.assertContains(response, '<span class="chip chip--du_dieu_kien">1 học phần</span>')
        self.assertContains(response, '<h2>Còn thiếu</h2>')
        self.assertContains(response, '<span class="chip chip--thieu_tien_quyet">3 học phần</span>')

    def test_con_thieu_sap_theo_hoc_ky_du_kien_va_co_nhan_bat_buoc_tu_chon(self):
        noi_dung = self.client.get(self.url).content.decode()
        bang_con_thieu = noi_dung.split('<h2>Còn thiếu</h2>')[1]
        vi_tri = [
            bang_con_thieu.index('Học kỳ dự kiến 1'), bang_con_thieu.index('<td>THIEU1</td>'),
            bang_con_thieu.index('<td>THIEU2</td>'), bang_con_thieu.index('Học kỳ dự kiến 2'),
            bang_con_thieu.index('<td>THIEU3</td>'),
        ]
        self.assertEqual(vi_tri, sorted(vi_tri))
        dong_thieu1 = re.search(r'<tr class="hang-diem">\s*<td>THIEU1</td>.*?</tr>', bang_con_thieu, re.S).group(0)
        dong_thieu2 = re.search(r'<tr class="hang-diem">\s*<td>THIEU2</td>.*?</tr>', bang_con_thieu, re.S).group(0)
        self.assertIn('<span class="chip chip--con_hieu_luc">Bắt buộc</span>', dong_thieu1)
        self.assertIn('<span class="chip chip--da_day">Tự chọn</span>', dong_thieu2)

    def test_nhom_da_dat_gom_theo_hoc_ky_du_kien(self):
        noi_dung = self.client.get(self.url).content.decode()
        bang_da_dat = noi_dung.split('<h2>Đã đạt</h2>')[1].split('<h2>Còn thiếu</h2>')[0]
        self.assertIn('Học kỳ dự kiến 2', bang_da_dat)
        self.assertIn('<td>DAT</td>', bang_da_dat)
        self.assertNotIn('THIEU', bang_da_dat)

    def test_chua_gan_chuong_trinh_hien_thong_bao_ro_rang(self):
        lop_khong_ct = LopHanhChinh.objects.create(
            ma_lop='KHONG_CT', ten_lop='Không chương trình', ma_nganh=self.nganh, ma_co_van=self.co_van,
        )
        sinh_vien = tao_sinh_vien('SV_KCT', lop_khong_ct)
        self.client.force_login(sinh_vien.ma_tai_khoan)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<strong>Chưa có chương trình đào tạo.</strong>')
        self.assertContains(response, 'chưa được gán chương trình đào tạo')
        self.assertNotContains(response, '<h2>Đã đạt</h2>')

    def test_trang_co_van_dung_chung_giao_dien_moi(self):
        self.client.force_login(self.co_van.ma_tai_khoan)
        response = self.client.get(reverse('tien_do_hoc_tap:co_van'), {'ma_sinh_vien': self.sinh_vien.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2>Còn thiếu</h2>')

    def test_khong_gach_chan_va_html_can_bang(self):
        noi_dung = self.client.get(self.url).content.decode()
        self.assertNotIn('underline', noi_dung)
        loi, con_mo = kiem_tra_can_bang_the(noi_dung)
        self.assertEqual((loi, con_mo), ([], []))
