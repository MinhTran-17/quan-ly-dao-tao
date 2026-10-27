"""Test tích hợp xuyên luồng: đi qua URL, view, phân quyền, form, service, template như người dùng thật.

Mỗi test nối nhiều vai trò trong một kịch bản (Phòng Đào tạo → Sinh viên → Giảng viên → Sinh viên),
khác với test trong tests.py của từng app (kiểm tra một view hoặc một hàm). Chức năng AI dùng
client giả (ClientAIGia), không gọi Gemini thật.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.test import TestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone

from academics.models import DieuKienTienQuyet, HocPhan
from accounts.models import VaiTro
from ai_core.clients import ClientAIGia
from classes.models import LopHocPhan
from grades.models import Diem

from .models import DangKyHocPhan, TrangThaiDangKy
from .services import dang_ky_hoc_phan
from .tests import MAT_KHAU, tao_dot_dang_ky_mo, tao_giang_vien, tao_lop_hanh_chinh, tao_sinh_vien

TaiKhoan = get_user_model()

_LAY_CLIENT_AI_TU_VAN = 'tu_van_dang_ky.services.lay_client_ai'
_JSON_TU_VAN_RONG = '{"goi_y": [], "chua_nen_dang_ky": [], "luu_y": ""}'


@tag('tich_hop')
class LuongDaoTaoXuyenVaiTroTest(TestCase):
    def setUp(self):
        cache.clear()
        self.hoc_ky = tao_dot_dang_ky_mo('1', '2025-2026').hoc_ky
        lop_hanh_chinh = tao_lop_hanh_chinh('CNTT_LT')
        self.sinh_vien = tao_sinh_vien('SV101', lop_hanh_chinh)
        self.sinh_vien_khac = tao_sinh_vien('SV102', lop_hanh_chinh)
        self.giang_vien = tao_giang_vien('GV101')
        self.giang_vien_khac = tao_giang_vien('GV102')
        self.phong_dao_tao = TaiKhoan.objects.create_user(
            ten_dang_nhap='tk_pdt_lt', vai_tro=VaiTro.PHONG_DAO_TAO, password=MAT_KHAU,
        )
        self.ctdl = HocPhan.objects.create(ma_hoc_phan='CTDL', ten_hoc_phan='Cấu trúc dữ liệu', so_tin_chi=3)
        self.csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=self.csdl, ma_hoc_phan_tien_quyet=self.ctdl)

    def _dang_nhap(self, tai_khoan):
        self.client.force_login(tai_khoan)

    def _tao_lop_qua_phong_dao_tao(self, ma_lop, hoc_phan, giang_vien):
        self._dang_nhap(self.phong_dao_tao)
        response = self.client.post(reverse('classes:lop_hoc_phan_tao'), {
            'ma_lop_hoc_phan': ma_lop, 'hoc_ky_chon': self.hoc_ky.pk, 'si_so_toi_da': 30,
            'ma_hoc_phan': hoc_phan.pk, 'ma_giang_vien': giang_vien.pk,
        })
        self.assertRedirects(response, reverse('classes:lop_hoc_phan_danh_sach'))
        return LopHocPhan.objects.get(pk=ma_lop)

    def _thong_bao(self, response):
        return [str(tb) for tb in get_messages(response.wsgi_request)]

    def test_tao_lop_dang_ky_nhap_diem_cong_bo_xem_bang_diem_va_chan_sinh_vien_khac(self):
        # 1. Phòng Đào tạo tạo lớp học phần qua form.
        lop = self._tao_lop_qua_phong_dao_tao('CTDL_LT01', self.ctdl, self.giang_vien)
        self.assertEqual((lop.hoc_ky, lop.nam_hoc), ('1', '2025-2026'))

        # 2. Sinh viên đăng ký lớp đó.
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        response = self.client.post(reverse('enrollment:dang_ky', args=[lop.pk]))
        self.assertRedirects(response, reverse('enrollment:lop_dang_mo'))
        dang_ky = DangKyHocPhan.objects.get(ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop)
        self.assertEqual(dang_ky.trang_thai, TrangThaiDangKy.CON_HIEU_LUC)

        # 3. Giảng viên phụ trách nhập điểm.
        self._dang_nhap(self.giang_vien.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[dang_ky.pk]), {
            'diem_qua_trinh': '8', 'diem_thi': '7',
        })
        self.assertRedirects(response, reverse('grades:bang_diem_lop', args=[lop.pk]))
        diem = Diem.objects.get(ma_dang_ky=dang_ky)
        self.assertEqual((diem.diem_qua_trinh, diem.diem_thi), (Decimal('8'), Decimal('7')))

        # 4. Chưa công bố: sinh viên chỉ thấy "Đang chờ công bố", không thấy điểm.
        url_bang_diem = reverse('grades:bang_diem_sinh_vien', args=[self.sinh_vien.pk])
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(url_bang_diem)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['danh_sach'][0].cho_cong_bo)
        self.assertContains(response, 'Đang chờ công bố')

        # 5. Giảng viên công bố, sinh viên thấy điểm tổng kết do code tính (0.3*8 + 0.7*7 = 7.3).
        self._dang_nhap(self.giang_vien.ma_tai_khoan)
        self.client.post(reverse('grades:cong_bo_diem_lop', args=[lop.pk]))
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        response = self.client.get(url_bang_diem)
        dong = response.context['danh_sach'][0]
        self.assertFalse(dong.cho_cong_bo)
        self.assertEqual(dong.diem.tinh_diem_tong_ket(), Decimal('7.3'))

        # 6. Sinh viên khác không xem được bảng điểm này.
        self._dang_nhap(self.sinh_vien_khac.ma_tai_khoan)
        self.assertEqual(self.client.get(url_bang_diem).status_code, 403)

    def test_dang_ky_qua_view_bi_chan_khi_chua_dat_tien_quyet(self):
        lop_csdl = self._tao_lop_qua_phong_dao_tao('CSDL_LT01', self.csdl, self.giang_vien)
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        response = self.client.post(reverse('enrollment:dang_ky', args=[lop_csdl.pk]))
        self.assertRedirects(response, reverse('enrollment:lop_dang_mo'))
        self.assertFalse(DangKyHocPhan.objects.filter(ma_lop_hoc_phan=lop_csdl).exists())
        self.assertTrue(any('tiên quyết' in tb for tb in self._thong_bao(response)))

    def test_giang_vien_khong_phu_trach_khong_nhap_duoc_diem(self):
        lop = self._tao_lop_qua_phong_dao_tao('CTDL_LT02', self.ctdl, self.giang_vien)
        dang_ky = dang_ky_hoc_phan(self.sinh_vien, lop)
        self._dang_nhap(self.giang_vien_khac.ma_tai_khoan)
        response = self.client.post(reverse('grades:nhap_diem', args=[dang_ky.pk]), {
            'diem_qua_trinh': '10', 'diem_thi': '10',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Diem.objects.filter(ma_dang_ky=dang_ky).exists())

    def test_vai_tro_khac_khong_dung_duoc_chuc_nang_cua_sinh_vien_va_phong_dao_tao(self):
        lop = self._tao_lop_qua_phong_dao_tao('CTDL_LT03', self.ctdl, self.giang_vien)
        # Giảng viên không đăng ký học phần được.
        self._dang_nhap(self.giang_vien.ma_tai_khoan)
        self.assertEqual(self.client.post(reverse('enrollment:dang_ky', args=[lop.pk])).status_code, 403)
        self.assertFalse(DangKyHocPhan.objects.filter(ma_lop_hoc_phan=lop).exists())
        # Sinh viên không tạo lớp học phần được.
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        response = self.client.post(reverse('classes:lop_hoc_phan_tao'), {
            'ma_lop_hoc_phan': 'LOP_TRAI_PHEP', 'hoc_ky_chon': self.hoc_ky.pk, 'si_so_toi_da': 30,
            'ma_hoc_phan': self.ctdl.pk, 'ma_giang_vien': self.giang_vien.pk,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(LopHocPhan.objects.filter(pk='LOP_TRAI_PHEP').exists())

    @override_settings(AI_PHIEN_BAN_TU_VAN='v1', AI_GIOI_HAN_KY_TU=8000)
    def test_luong_ai_tu_van_dung_du_lieu_da_hoc_khong_gui_dinh_danh_va_chan_vai_tro_khac(self):
        # Sinh viên đã đạt CTDL ở năm trước (điểm đã công bố) → đủ điều kiện lớp CSDL đang mở.
        lop_cu = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDL_CU', hoc_ky='1', nam_hoc='2024-2025', si_so_toi_da=40,
            ma_hoc_phan=self.ctdl, ma_giang_vien=self.giang_vien,
        )
        dang_ky_cu = DangKyHocPhan.objects.create(
            ma_sinh_vien=self.sinh_vien, ma_lop_hoc_phan=lop_cu, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky_cu, diem_qua_trinh=8, diem_thi=8, da_cong_bo=True)
        self._tao_lop_qua_phong_dao_tao('CSDL_LT02', self.csdl, self.giang_vien)

        url = reverse('tu_van_dang_ky:trang_tu_van')
        self._dang_nhap(self.sinh_vien.ma_tai_khoan)
        client_gia = ClientAIGia(phan_hoi=_JSON_TU_VAN_RONG)
        with patch(_LAY_CLIENT_AI_TU_VAN, return_value=client_gia):
            response = self.client.post(url, {'cau_hoi': 'Tư vấn học kỳ 1 năm học 2025-2026'})
        self.assertRedirects(response, url)

        self.assertEqual(len(client_gia.cac_lan_goi), 1)
        prompt = client_gia.cac_lan_goi[0]['nguoi_dung']
        dau, cuoi = prompt.index('<<<DU_LIEU>>>'), prompt.index('<<<HET_DU_LIEU>>>')
        self.assertTrue(dau < prompt.index('CSDL_LT02') < cuoi)
        # Không gửi định danh: mã sinh viên (có trong họ tên mẫu), email, tên đăng nhập.
        for dinh_danh in ('SV101', self.sinh_vien.email, self.sinh_vien.ma_tai_khoan.ten_dang_nhap):
            self.assertNotIn(dinh_danh, prompt)
        self.assertEqual(self.client.get(url).status_code, 200)

        # Giảng viên không dùng được chức năng tư vấn của sinh viên.
        self._dang_nhap(self.giang_vien.ma_tai_khoan)
        self.assertEqual(self.client.get(url).status_code, 403)
