from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from academics.models import DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc
from accounts.models import TaiKhoan, VaiTro
from classes.models import LichHoc, LopHocPhan
from enrollment.models import DangKyHocPhan
from grades.models import Diem
from people.models import CoVanHocTap, GiangVien, SinhVien

MAT_KHAU_MAU = 'MatKhauDemo123'


class Command(BaseCommand):
    help = (
        'Nạp dữ liệu mẫu để demo: 4 vai trò, ngành, lớp hành chính, học phần có '
        'điều kiện tiên quyết, lớp học phần có lịch học, đăng ký, điểm. '
        'CHỈ dùng để demo/phát triển, KHÔNG chạy trên môi trường thật.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Ép chạy dù DEBUG=False (không khuyến khích, chỉ dùng khi chắc chắn đây là môi trường demo).',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'CẢNH BÁO: Lệnh này tạo các tài khoản demo với MỘT mật khẩu cố định, ai biết '
            'tên đăng nhập cũng đăng nhập được. Không chạy lệnh này trên môi trường thật.'
        ))
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'DJANGO_DEBUG=False (có vẻ đây là môi trường thật) nên lệnh bị chặn. '
                'Nếu chắc chắn đây là môi trường demo, chạy lại với --force.'
            )
        if NganhHoc.objects.filter(pk='CNTT').exists():
            raise CommandError('Dữ liệu mẫu dường như đã được nạp trước đó (đã có ngành CNTT). Dừng lại.')

        self._tao_du_lieu()
        self.stdout.write(self.style.SUCCESS(f'Đã nạp xong dữ liệu mẫu. Mật khẩu demo: "{MAT_KHAU_MAU}".'))

    def _tao_tai_khoan(self, ten_dang_nhap, vai_tro):
        return TaiKhoan.objects.create_user(ten_dang_nhap=ten_dang_nhap, vai_tro=vai_tro, password=MAT_KHAU_MAU)

    def _dang_ky_va_cham_diem(self, sinh_vien, lop_hoc_phan, diem_qua_trinh, diem_thi):
        dang_ky = DangKyHocPhan.objects.create(
            ma_sinh_vien=sinh_vien, ma_lop_hoc_phan=lop_hoc_phan, thoi_gian_dang_ky=timezone.now(),
        )
        Diem.objects.create(ma_dang_ky=dang_ky, diem_qua_trinh=diem_qua_trinh, diem_thi=diem_thi)
        return dang_ky

    def _tao_du_lieu(self):
        # Phòng Đào tạo
        self._tao_tai_khoan('pdt_demo', VaiTro.PHONG_DAO_TAO)

        # Giảng viên
        gv1 = GiangVien.objects.create(
            ma_giang_vien='GV001', ho_ten='Nguyễn Văn Giảng', email='gv001@demo.local',
            so_dien_thoai='0900000001', ma_tai_khoan=self._tao_tai_khoan('gv001', VaiTro.GIANG_VIEN),
        )
        gv2 = GiangVien.objects.create(
            ma_giang_vien='GV002', ho_ten='Trần Thị Dạy', email='gv002@demo.local',
            so_dien_thoai='0900000002', ma_tai_khoan=self._tao_tai_khoan('gv002', VaiTro.GIANG_VIEN),
        )

        # Cố vấn học tập
        co_van = CoVanHocTap.objects.create(
            ma_co_van='CV001', ho_ten='Lê Thị Vấn', email='cv001@demo.local',
            so_dien_thoai='0900000003', ma_tai_khoan=self._tao_tai_khoan('cv001', VaiTro.CO_VAN_HOC_TAP),
        )

        # Ngành, lớp hành chính
        nganh = NganhHoc.objects.create(ma_nganh='CNTT', ten_nganh='Công nghệ thông tin')
        lop_hanh_chinh = LopHanhChinh.objects.create(
            ma_lop='CNTT_K1', ten_lop='Công nghệ thông tin - Khóa 1', ma_nganh=nganh, ma_co_van=co_van,
        )

        # Sinh viên
        sv001 = SinhVien.objects.create(
            ma_sinh_vien='SV001', ho_ten='Phạm Văn An', ngay_sinh='2004-05-10', email='sv001@demo.local',
            so_dien_thoai='0911000001', ma_lop=lop_hanh_chinh, ma_tai_khoan=self._tao_tai_khoan('sv001', VaiTro.SINH_VIEN),
        )
        sv002 = SinhVien.objects.create(
            ma_sinh_vien='SV002', ho_ten='Nguyễn Thị Bình', ngay_sinh='2004-06-15', email='sv002@demo.local',
            so_dien_thoai='0911000002', ma_lop=lop_hanh_chinh, ma_tai_khoan=self._tao_tai_khoan('sv002', VaiTro.SINH_VIEN),
        )
        sv003 = SinhVien.objects.create(
            ma_sinh_vien='SV003', ho_ten='Trần Văn Cường', ngay_sinh='2004-07-20', email='sv003@demo.local',
            so_dien_thoai='0911000003', ma_lop=lop_hanh_chinh, ma_tai_khoan=self._tao_tai_khoan('sv003', VaiTro.SINH_VIEN),
        )
        SinhVien.objects.create(
            ma_sinh_vien='SV004', ho_ten='Lê Thị Dung', ngay_sinh='2004-08-25', email='sv004@demo.local',
            so_dien_thoai='0911000004', ma_lop=lop_hanh_chinh, ma_tai_khoan=self._tao_tai_khoan('sv004', VaiTro.SINH_VIEN),
        )
        SinhVien.objects.create(
            ma_sinh_vien='SV005', ho_ten='Hoàng Văn Em', ngay_sinh='2004-09-30', email='sv005@demo.local',
            so_dien_thoai='0911000005', ma_lop=lop_hanh_chinh, ma_tai_khoan=self._tao_tai_khoan('sv005', VaiTro.SINH_VIEN),
        )

        # Học phần và điều kiện tiên quyết
        csdl = HocPhan.objects.create(ma_hoc_phan='CSDL', ten_hoc_phan='Cơ sở dữ liệu', so_tin_chi=3)
        ctdlgt = HocPhan.objects.create(
            ma_hoc_phan='CTDLGT', ten_hoc_phan='Cấu trúc dữ liệu và giải thuật', so_tin_chi=4,
        )
        cnpm = HocPhan.objects.create(ma_hoc_phan='CNPM', ten_hoc_phan='Công nghệ phần mềm', so_tin_chi=3)
        aiud = HocPhan.objects.create(ma_hoc_phan='AIUD', ten_hoc_phan='AI ứng dụng', so_tin_chi=3)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=cnpm, ma_hoc_phan_tien_quyet=ctdlgt)
        DieuKienTienQuyet.objects.create(ma_hoc_phan=aiud, ma_hoc_phan_tien_quyet=csdl)

        # Lớp học phần kỳ trước (2024-2025), để tạo điểm "đã đạt" cho sinh viên
        csdl_2024 = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CSDL_2024', hoc_ky='1', nam_hoc='2024-2025', si_so_toi_da=40,
            ma_hoc_phan=csdl, ma_giang_vien=gv1,
        )
        ctdlgt_2024 = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDLGT_2024', hoc_ky='1', nam_hoc='2024-2025', si_so_toi_da=40,
            ma_hoc_phan=ctdlgt, ma_giang_vien=gv1,
        )
        LichHoc.objects.create(ma_lop_hoc_phan=csdl_2024, thu=3, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101')
        LichHoc.objects.create(ma_lop_hoc_phan=ctdlgt_2024, thu=5, tiet_bat_dau=1, so_tiet=4, phong_hoc='A102')

        # Đợt đăng ký đang mở cho học kỳ hiện tại (2025-2026), để đăng ký học phần qua
        # giao diện web hoạt động được ngay sau khi nạp dữ liệu mẫu (xem academics.DotDangKy).
        hoc_ky_hien_tai = HocKy.objects.create(
            hoc_ky=1, nam_hoc='2025-2026',
            ngay_bat_dau=timezone.localdate(), ngay_ket_thuc=timezone.localdate() + timedelta(days=120),
        )
        DotDangKy.objects.create(
            hoc_ky=hoc_ky_hien_tai,
            ngay_mo=timezone.now() - timedelta(days=1), ngay_dong=timezone.now() + timedelta(days=30),
        )

        # Lớp học phần kỳ hiện tại (2025-2026)
        ctdlgt_2025 = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CTDLGT_2025', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=1,
            ma_hoc_phan=ctdlgt, ma_giang_vien=gv1,
        )
        cnpm_2025 = LopHocPhan.objects.create(
            ma_lop_hoc_phan='CNPM_2025', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=cnpm, ma_giang_vien=gv2,
        )
        aiud_2025 = LopHocPhan.objects.create(
            ma_lop_hoc_phan='AIUD_2025', hoc_ky='1', nam_hoc='2025-2026', si_so_toi_da=40,
            ma_hoc_phan=aiud, ma_giang_vien=gv2,
        )
        # Thứ 2 tiết 1-3 và Thứ 2 tiết 2-4 giao nhau -> dùng để demo trùng lịch.
        LichHoc.objects.create(ma_lop_hoc_phan=ctdlgt_2025, thu=2, tiet_bat_dau=1, so_tiet=3, phong_hoc='A101')
        LichHoc.objects.create(ma_lop_hoc_phan=cnpm_2025, thu=4, tiet_bat_dau=1, so_tiet=3, phong_hoc='B201')
        LichHoc.objects.create(ma_lop_hoc_phan=aiud_2025, thu=2, tiet_bat_dau=2, so_tiet=3, phong_hoc='B202')

        # SV001 đã đạt CSDL và CTDLGT (đúng ví dụ trong đề bài), sẵn sàng đăng ký CNPM/AI ứng dụng.
        self._dang_ky_va_cham_diem(sv001, csdl_2024, Decimal('8'), Decimal('8'))
        self._dang_ky_va_cham_diem(sv001, ctdlgt_2024, Decimal('7'), Decimal('8'))
        # SV003 đã đạt CSDL (đủ điều kiện tiên quyết AI ứng dụng) nhưng chưa đạt CTDLGT.
        self._dang_ky_va_cham_diem(sv003, csdl_2024, Decimal('6'), Decimal('6'))
        # SV003 đã đăng ký CTDLGT_2025 kỳ này (chiếm hết sĩ số tối đa = 1).
        DangKyHocPhan.objects.create(
            ma_sinh_vien=sv003, ma_lop_hoc_phan=ctdlgt_2025, thoi_gian_dang_ky=timezone.now(),
        )
        # SV002, SV004, SV005: chưa đăng ký/chưa có điểm gì, để trống cho việc demo.

        self.stdout.write('')
        self.stdout.write('Gợi ý demo đăng ký học phần (đăng nhập bằng mật khẩu demo ở trên):')
        self.stdout.write('  - sv001: đăng ký CNPM_2025 và AIUD_2025 -> thành công (đã đạt tiên quyết).')
        self.stdout.write('  - sv002: đăng ký CNPM_2025 hoặc AIUD_2025 -> báo thiếu học phần tiên quyết.')
        self.stdout.write('  - sv003: đăng ký AIUD_2025 -> báo trùng lịch với CTDLGT_2025 (cùng Thứ 2).')
        self.stdout.write('  - sv005: đăng ký CTDLGT_2025 -> báo lớp đã đủ sĩ số (SV003 đã chiếm chỗ duy nhất).')
        self.stdout.write('Cần bộ dữ liệu đầy đủ hơn (90 sinh viên, điểm, điểm danh, lịch thi, thông báo)? '
                          'Chạy tiếp: python manage.py nap_du_lieu_day_du')
