import io
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import (
    ChiTietChuongTrinh, ChuongTrinhDaoTao, DieuKienTienQuyet, DotDangKy, HocKy, HocPhan, LopHanhChinh, NganhHoc,
)
from accounts.management.commands.nap_du_lieu_mau import MAT_KHAU_MAU, Command as LenhNapCoBan
from accounts.models import TaiKhoan, VaiTro
from classes.models import LichHoc, LichThi, LopHocPhan
from diem_danh.models import DiemDanh
from enrollment.models import DangKyHocPhan, TrangThaiDangKy
from enrollment.services import LoiDangKyHocPhan, dang_ky_hoc_phan
from grades.models import Diem
from grades.tinh_diem import tinh_diem_tong_ket
from people.models import CoVanHocTap, GiangVien, SinhVien
from thong_bao.models import DaDocThongBao, DoiTuongThongBao, ThongBao

# Seed cố định: chạy lại trên CSDL sạch cho ra đúng cùng bộ dữ liệu (họ tên, điểm, phân bổ đăng ký...).
SEED = 20250924

MA_LOP_DAU_TIEN_SV_MOI = 6  # SV001-SV005 là sinh viên gốc của nap_du_lieu_mau, giữ nguyên.
SO_SINH_VIEN_TOI_DA = 90
SO_SV_MOI_LOP = 30

HOC_KY_HIEN_TAI = ('1', '2025-2026')

# (mã, tên, số tín chỉ)
HOC_PHAN_MOI = [
    ('TOAN', 'Toán cao cấp', 3),
    ('NMLT', 'Nhập môn lập trình', 3),
    ('KTMT', 'Kiến trúc máy tính', 3),
    ('MMT', 'Mạng máy tính', 3),
    ('LTW', 'Lập trình web', 3),
    ('HDH', 'Hệ điều hành', 3),
    ('HQTCSDL', 'Hệ quản trị cơ sở dữ liệu', 3),
    ('ATTT', 'An toàn thông tin', 3),
    ('MMH', 'Mật mã học', 3),
]

# (học phần, học phần tiên quyết). CTDLGT/CSDL/CNPM/AIUD giữ nguyên: không thêm tiên quyết cho
# 4 học phần cũ, nếu không SV005 sẽ báo thiếu tiên quyết thay vì "đủ sĩ số" ở CTDLGT_2025.
TIEN_QUYET_MOI = [
    ('LTW', 'NMLT'), ('HDH', 'KTMT'), ('HQTCSDL', 'CSDL'), ('ATTT', 'MMT'), ('MMH', 'TOAN'),
]

# (mã lớp, học phần, học kỳ, năm học, giảng viên, sĩ số tối đa, thứ, tiết bắt đầu, số tiết, phòng)
LOP_HOC_PHAN_MOI = [
    # HK1 2024-2025 (đã qua)
    ('TOAN_2024', 'TOAN', '1', '2024-2025', 'GV003', 60, 2, 1, 3, 'C101'),
    ('NMLT_2024', 'NMLT', '1', '2024-2025', 'GV004', 60, 4, 1, 3, 'C102'),
    ('KTMT_2024', 'KTMT', '1', '2024-2025', 'GV005', 60, 6, 1, 3, 'C103'),
    # HK2 2024-2025 (đã qua)
    ('MMT_2024', 'MMT', '2', '2024-2025', 'GV005', 60, 2, 4, 3, 'C201'),
    ('LTW_2024', 'LTW', '2', '2024-2025', 'GV004', 50, 3, 4, 3, 'C202'),
    ('HDH_2024', 'HDH', '2', '2024-2025', 'GV003', 50, 5, 4, 3, 'C203'),
    ('MMH_2024', 'MMH', '2', '2024-2025', 'GV002', 50, 4, 4, 3, 'C204'),
    # HK1 2025-2026 (đang mở đăng ký)
    ('CNPM_2025_2', 'CNPM', '1', '2025-2026', 'GV002', 45, 6, 1, 3, 'B203'),
    ('AIUD_2025_2', 'AIUD', '1', '2025-2026', 'GV001', 25, 6, 4, 3, 'B204'),
    ('HQTCSDL_2025', 'HQTCSDL', '1', '2025-2026', 'GV004', 18, 3, 1, 3, 'D101'),
    ('ATTT_2025', 'ATTT', '1', '2025-2026', 'GV005', 20, 5, 1, 3, 'D102'),
    ('TOAN_2025', 'TOAN', '1', '2025-2026', 'GV003', 50, 2, 5, 3, 'C104'),
    ('NMLT_2025', 'NMLT', '1', '2025-2026', 'GV004', 50, 4, 4, 3, 'C105'),
    # KTMT_2025 (Thứ 3 tiết 3-5) giao HQTCSDL_2025 (Thứ 3 tiết 1-3) ở tiết 3;
    # MMT_2025 (Thứ 4 tiết 5-7) giao NMLT_2025 (Thứ 4 tiết 4-6) ở tiết 5-6 -> trùng lịch có chủ đích.
    ('KTMT_2025', 'KTMT', '1', '2025-2026', 'GV005', 45, 3, 3, 3, 'C106'),
    ('MMT_2025', 'MMT', '1', '2025-2026', 'GV003', 40, 4, 5, 3, 'C107'),
    ('CSDL_2025', 'CSDL', '1', '2025-2026', 'GV001', 30, 7, 1, 3, 'D103'),
    ('CTDLGT_2025_2', 'CTDLGT', '1', '2025-2026', 'GV002', 45, 5, 5, 3, 'B205'),
]

LOP_HK1_2024 = ['TOAN_2024', 'NMLT_2024', 'KTMT_2024', 'CSDL_2024', 'CTDLGT_2024']
LOP_HK2_2024 = ['MMT_2024', 'LTW_2024', 'HDH_2024', 'MMH_2024']
# Nhóm lớp kỳ đang mở dùng cho đăng ký ngẫu nhiên. CTDLGT_2025, CNPM_2025, AIUD_2025 (của
# nap_du_lieu_mau) bị loại để 4 ca lỗi gốc của sv001-sv005 luôn còn đúng.
LOP_DANG_KY_NGAU_NHIEN = [
    'CNPM_2025_2', 'AIUD_2025_2', 'HQTCSDL_2025', 'ATTT_2025', 'TOAN_2025', 'NMLT_2025', 'KTMT_2025',
    'MMT_2025', 'CSDL_2025', 'CTDLGT_2025_2',
]
LOP_KHONG_CO_LICH_THI = {'CNPM_2025', 'AIUD_2025', 'CNPM_2025_2'}

# 8 sinh viên bị cảnh báo học vụ ở HK2 2024-2025: 2 học phần chưa đạt.
# "Đỏ": điểm trung bình học kỳ < 5.0 (2 lý do); "vàng": còn lại chỉ có lý do 2 học phần chưa đạt (1 lý do).
SV_CANH_BAO_DO = ['SV010', 'SV036', 'SV052', 'SV066']
SV_CANH_BAO_VANG = ['SV018', 'SV025', 'SV045', 'SV080']

HO = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng', 'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý']
DEM_NAM = ['Văn', 'Minh', 'Quốc', 'Đức', 'Hữu', 'Anh', 'Thành', 'Gia', 'Công', 'Tuấn']
DEM_NU = ['Thị', 'Ngọc', 'Thu', 'Thanh', 'Kim', 'Mai', 'Phương', 'Bảo', 'Khánh', 'Diệu']
TEN_NAM = [
    'Anh', 'Bảo', 'Cường', 'Dũng', 'Đạt', 'Hải', 'Hiếu', 'Hoàng', 'Hùng', 'Huy', 'Khánh', 'Khoa', 'Kiên', 'Long',
    'Minh', 'Nam', 'Nghĩa', 'Phong', 'Phúc', 'Quân', 'Quang', 'Sơn', 'Thắng', 'Thành', 'Tuấn', 'Tùng', 'Việt',
    'Vinh', 'Đức', 'Trung',
]
TEN_NU = [
    'Anh', 'Chi', 'Dung', 'Giang', 'Hà', 'Hạnh', 'Hoa', 'Hương', 'Lan', 'Linh', 'Loan', 'Mai', 'My', 'Ngân',
    'Ngọc', 'Nhung', 'Oanh', 'Phương', 'Quyên', 'Thảo', 'Thủy', 'Trang', 'Trinh', 'Uyên', 'Vy', 'Yến', 'Hằng',
    'Thu', 'Diệp', 'Nhi',
]

GIANG_VIEN_MOI = [
    ('GV003', 'Vũ Minh Tuấn', '0900000004'),
    ('GV004', 'Đặng Thị Hạnh', '0900000005'),
    ('GV005', 'Bùi Quốc Khánh', '0900000006'),
]
CO_VAN_MOI = [
    ('CV002', 'Ngô Thị Lan', '0900000007', 'CNTT_K2'),
    ('CV003', 'Đỗ Văn Hưng', '0900000008', 'ATTT_K1'),
]

# (mã học phần, học kỳ dự kiến, bắt buộc)
CHUONG_TRINH_CNTT = [
    ('TOAN', 1, True), ('NMLT', 1, True), ('KTMT', 1, True),
    ('CSDL', 2, True), ('CTDLGT', 2, True), ('MMT', 2, True),
    ('LTW', 3, True), ('HDH', 3, True), ('HQTCSDL', 3, True),
    ('CNPM', 4, True), ('AIUD', 4, False), ('MMH', 4, False), ('ATTT', 4, False),
]
CHUONG_TRINH_ATTT = [
    ('TOAN', 1, True), ('NMLT', 1, True), ('KTMT', 1, True),
    ('MMT', 2, True), ('CSDL', 2, True), ('MMH', 2, True),
    ('HDH', 3, True), ('ATTT', 3, True), ('LTW', 4, False),
]


def _aware(nam, thang, ngay, gio=8, phut=0):
    return timezone.make_aware(datetime(nam, thang, ngay, gio, phut))


class Command(BaseCommand):
    help = (
        'Nạp bộ dữ liệu demo đầy đủ: 3 lớp hành chính (90 sinh viên), 5 giảng viên, 3 cố vấn, 13 học phần, '
        '22 lớp học phần qua 3 học kỳ, đăng ký, điểm, điểm danh, lịch thi, thông báo. Nếu CSDL chưa có dữ liệu '
        'của nap_du_lieu_mau thì tự nạp trước. CHỈ dùng để demo/phát triển, KHÔNG chạy trên môi trường thật.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Ép chạy dù DEBUG=False (không khuyến khích, chỉ dùng khi chắc chắn đây là môi trường demo).',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'CẢNH BÁO: Lệnh này tạo hàng trăm tài khoản demo với MỘT mật khẩu cố định, ai biết '
            'tên đăng nhập cũng đăng nhập được. Không chạy lệnh này trên môi trường thật.'
        ))
        if not settings.DEBUG and not options['force']:
            raise CommandError(
                'DJANGO_DEBUG=False (có vẻ đây là môi trường thật) nên lệnh bị chặn. '
                'Nếu chắc chắn đây là môi trường demo, chạy lại với --force.'
            )
        if LopHanhChinh.objects.filter(pk='ATTT_K1').exists():
            raise CommandError('Dữ liệu đầy đủ dường như đã được nạp trước đó (đã có lớp ATTT_K1). Dừng lại.')

        self.rng = random.Random(SEED)
        try:
            with transaction.atomic():
                if not NganhHoc.objects.filter(pk='CNTT').exists():
                    LenhNapCoBan(stdout=io.StringIO())._tao_du_lieu()
                thong_ke = self._nap_mo_rong()
        except ObjectDoesNotExist as loi:
            raise CommandError(
                f'Dữ liệu của nap_du_lieu_mau không còn đầy đủ nên không thể bổ sung ({loi}). '
                'Không có gì bị thay đổi.'
            )

        self._in_ket_qua(thong_ke)

    # ------------------------------------------------------------------ tổ chức đào tạo

    def _tao_tai_khoan_hang_loat(self, ten_dang_nhap_ds, vai_tro):
        """Tạo tài khoản hàng loạt với cùng một chuỗi băm mật khẩu (băm một lần thay vì mỗi tài khoản
        ~0,4 giây). Chấp nhận được vì đây là dữ liệu demo dùng chung một mật khẩu."""
        TaiKhoan.objects.bulk_create([
            TaiKhoan(ten_dang_nhap=ten, vai_tro=vai_tro, password=self.mat_khau_bam) for ten in ten_dang_nhap_ds
        ])
        return {tk.ten_dang_nhap: tk for tk in TaiKhoan.objects.filter(ten_dang_nhap__in=ten_dang_nhap_ds)}

    def _nap_mo_rong(self):
        self.mat_khau_bam = make_password(MAT_KHAU_MAU)
        self.hom_nay = timezone.localdate()

        self._tao_hoc_ky()
        giang_vien = self._tao_giang_vien()
        lop_hanh_chinh = self._tao_lop_hanh_chinh_va_co_van()
        sinh_vien_moi = self._tao_sinh_vien(lop_hanh_chinh)
        self._tao_hoc_phan()
        self._tao_chuong_trinh_dao_tao(lop_hanh_chinh)
        lop = self._tao_lop_hoc_phan(giang_vien)

        da_dat = self._tao_lich_su_ky_da_qua(sinh_vien_moi, lop)
        dang_ky_ky_moi = self._dang_ky_ky_dang_mo(sinh_vien_moi, lop, da_dat)
        so_diem_danh = self._tao_diem_danh()
        so_lich_thi = self._tao_lich_thi(lop)
        so_thong_bao = self._tao_thong_bao(lop_hanh_chinh, lop)

        return {
            'dang_ky_ky_moi': dang_ky_ky_moi, 'so_diem_danh': so_diem_danh,
            'so_lich_thi': so_lich_thi, 'so_thong_bao': so_thong_bao,
        }

    def _tao_hoc_ky(self):
        # Học kỳ hiện tại đã có (từ nap_du_lieu_mau): dời về khoảng [hôm nay - 28 ngày, hôm nay + 90 ngày]
        # để có sẵn các buổi điểm danh trong quá khứ thuộc đúng học kỳ, và để học kỳ đang diễn ra thật.
        hien_tai = HocKy.objects.get(hoc_ky=int(HOC_KY_HIEN_TAI[0]), nam_hoc=HOC_KY_HIEN_TAI[1])
        hien_tai.ngay_bat_dau = self.hom_nay - timedelta(days=28)
        hien_tai.ngay_ket_thuc = self.hom_nay + timedelta(days=90)
        hien_tai.save(update_fields=['ngay_bat_dau', 'ngay_ket_thuc'])
        # Học kỳ đã qua: giữ nguyên nếu người dùng đã tự tạo trước đó (danh mục có ràng buộc duy nhất).
        HocKy.objects.get_or_create(
            hoc_ky=1, nam_hoc='2024-2025', defaults={'ngay_bat_dau': date(2024, 9, 5), 'ngay_ket_thuc': date(2025, 1, 15)},
        )
        HocKy.objects.get_or_create(
            hoc_ky=2, nam_hoc='2024-2025', defaults={'ngay_bat_dau': date(2025, 2, 10), 'ngay_ket_thuc': date(2025, 6, 20)},
        )
        # Đăng ký học phần chỉ chạy được trong đợt đăng ký đang mở: nếu CSDL chưa có (hoặc đã xóa) thì mở một đợt.
        bay_gio = timezone.now()
        if not DotDangKy.objects.filter(hoc_ky=hien_tai, ngay_mo__lte=bay_gio, ngay_dong__gte=bay_gio).exists():
            DotDangKy.objects.create(
                hoc_ky=hien_tai, ngay_mo=bay_gio - timedelta(days=1), ngay_dong=bay_gio + timedelta(days=30),
            )

    def _tao_giang_vien(self):
        tai_khoan = self._tao_tai_khoan_hang_loat([ma.lower() for ma, _, _ in GIANG_VIEN_MOI], VaiTro.GIANG_VIEN)
        for ma, ho_ten, dien_thoai in GIANG_VIEN_MOI:
            GiangVien.objects.create(
                ma_giang_vien=ma, ho_ten=ho_ten, email=f'{ma.lower()}@demo.local',
                so_dien_thoai=dien_thoai, ma_tai_khoan=tai_khoan[ma.lower()],
            )
        return {gv.pk: gv for gv in GiangVien.objects.all()}

    def _tao_lop_hanh_chinh_va_co_van(self):
        nganh_attt = NganhHoc.objects.create(ma_nganh='ATTT', ten_nganh='An toàn thông tin')
        nganh_cntt = NganhHoc.objects.get(pk='CNTT')
        tai_khoan = self._tao_tai_khoan_hang_loat([ma.lower() for ma, _, _, _ in CO_VAN_MOI], VaiTro.CO_VAN_HOC_TAP)
        co_van = {}
        for ma, ho_ten, dien_thoai, _ in CO_VAN_MOI:
            co_van[ma] = CoVanHocTap.objects.create(
                ma_co_van=ma, ho_ten=ho_ten, email=f'{ma.lower()}@demo.local',
                so_dien_thoai=dien_thoai, ma_tai_khoan=tai_khoan[ma.lower()],
            )
        return {
            'CNTT_K1': LopHanhChinh.objects.get(pk='CNTT_K1'),
            'CNTT_K2': LopHanhChinh.objects.create(
                ma_lop='CNTT_K2', ten_lop='Công nghệ thông tin - Khóa 2', ma_nganh=nganh_cntt, ma_co_van=co_van['CV002'],
            ),
            'ATTT_K1': LopHanhChinh.objects.create(
                ma_lop='ATTT_K1', ten_lop='An toàn thông tin - Khóa 1', ma_nganh=nganh_attt, ma_co_van=co_van['CV003'],
            ),
        }

    def _tao_ten_sinh_vien(self, da_dung):
        while True:
            nam = self.rng.random() < 0.5
            ten = self.rng.choice(TEN_NAM if nam else TEN_NU)
            dem = self.rng.choice(DEM_NAM if nam else DEM_NU)
            ho_ten = f'{self.rng.choice(HO)} {dem} {ten}'
            if dem != ten and ho_ten not in da_dung:
                da_dung.add(ho_ten)
                return ho_ten

    def _tao_sinh_vien(self, lop_hanh_chinh):
        da_dung = set(SinhVien.objects.values_list('ho_ten', flat=True))
        thong_tin = []
        for so in range(MA_LOP_DAU_TIEN_SV_MOI, SO_SINH_VIEN_TOI_DA + 1):
            ma_lop = 'CNTT_K1' if so <= SO_SV_MOI_LOP else ('CNTT_K2' if so <= 2 * SO_SV_MOI_LOP else 'ATTT_K1')
            ho_ten = self._tao_ten_sinh_vien(da_dung)
            ngay_sinh = date(2003, 1, 1) + timedelta(days=self.rng.randint(0, 3 * 365 - 1))
            thong_tin.append((f'SV{so:03d}', ho_ten, ngay_sinh, lop_hanh_chinh[ma_lop], f'0912{so:06d}'))
        tai_khoan = self._tao_tai_khoan_hang_loat([ma.lower() for ma, *_ in thong_tin], VaiTro.SINH_VIEN)
        SinhVien.objects.bulk_create([
            SinhVien(
                ma_sinh_vien=ma, ho_ten=ho_ten, ngay_sinh=ngay_sinh, email=f'{ma.lower()}@demo.local',
                so_dien_thoai=dien_thoai, ma_lop=lop, ma_tai_khoan=tai_khoan[ma.lower()],
            )
            for ma, ho_ten, ngay_sinh, lop, dien_thoai in thong_tin
        ])
        return list(SinhVien.objects.filter(ma_sinh_vien__in=[ma for ma, *_ in thong_tin]).order_by('ma_sinh_vien'))

    # ------------------------------------------------------------------ học phần, chương trình, lớp học phần

    def _tao_hoc_phan(self):
        for ma, ten, tin_chi in HOC_PHAN_MOI:
            HocPhan.objects.create(ma_hoc_phan=ma, ten_hoc_phan=ten, so_tin_chi=tin_chi)
        for ma, tien_quyet in TIEN_QUYET_MOI:
            DieuKienTienQuyet.objects.create(ma_hoc_phan_id=ma, ma_hoc_phan_tien_quyet_id=tien_quyet)

    def _tao_chuong_trinh_dao_tao(self, lop_hanh_chinh):
        nganh_cntt = NganhHoc.objects.get(pk='CNTT')
        nganh_attt = NganhHoc.objects.get(pk='ATTT')
        cac_chuong_trinh = [
            ('CNTT_K1', nganh_cntt, 'Chương trình đào tạo ngành Công nghệ thông tin', 'Khóa 1', CHUONG_TRINH_CNTT),
            ('CNTT_K2', nganh_cntt, 'Chương trình đào tạo ngành Công nghệ thông tin', 'Khóa 2', CHUONG_TRINH_CNTT),
            ('ATTT_K1', nganh_attt, 'Chương trình đào tạo ngành An toàn thông tin', 'Khóa 1', CHUONG_TRINH_ATTT),
        ]
        for ma_lop, nganh, ten, khoa, chi_tiet in cac_chuong_trinh:
            co_san = lop_hanh_chinh[ma_lop].chuong_trinh_dao_tao
            if co_san is not None:
                # Lớp đã gắn chương trình đào tạo do người dùng tự tạo: giữ nguyên các dòng có sẵn, chỉ thêm
                # học phần còn thiếu để tiến độ học tập phản ánh được các học phần của bộ dữ liệu.
                da_co = set(co_san.chi_tiet.values_list('hoc_phan_id', flat=True))
                ChiTietChuongTrinh.objects.bulk_create([
                    ChiTietChuongTrinh(chuong_trinh=co_san, hoc_phan_id=ma_hp, hoc_ky_du_kien=hoc_ky, bat_buoc=bat_buoc)
                    for ma_hp, hoc_ky, bat_buoc in chi_tiet if ma_hp not in da_co
                ])
                continue
            chuong_trinh = ChuongTrinhDaoTao.objects.create(nganh=nganh, ten_chuong_trinh=ten, khoa_hoc=khoa)
            ChiTietChuongTrinh.objects.bulk_create([
                ChiTietChuongTrinh(chuong_trinh=chuong_trinh, hoc_phan_id=ma_hp, hoc_ky_du_kien=hoc_ky, bat_buoc=bat_buoc)
                for ma_hp, hoc_ky, bat_buoc in chi_tiet
            ])
            lop = lop_hanh_chinh[ma_lop]
            lop.chuong_trinh_dao_tao = chuong_trinh
            lop.save(update_fields=['chuong_trinh_dao_tao'])

    def _tao_lop_hoc_phan(self, giang_vien):
        lich = []
        for ma, hoc_phan, hoc_ky, nam_hoc, ma_gv, si_so, thu, tiet, so_tiet, phong in LOP_HOC_PHAN_MOI:
            lop = LopHocPhan.objects.create(
                ma_lop_hoc_phan=ma, hoc_ky=hoc_ky, nam_hoc=nam_hoc, si_so_toi_da=si_so,
                ma_hoc_phan_id=hoc_phan, ma_giang_vien=giang_vien[ma_gv],
            )
            lich.append(LichHoc(ma_lop_hoc_phan=lop, thu=thu, tiet_bat_dau=tiet, so_tiet=so_tiet, phong_hoc=phong))
        LichHoc.objects.bulk_create(lich)
        return {lop.pk: lop for lop in LopHocPhan.objects.select_related('ma_hoc_phan')}

    # ------------------------------------------------------------------ điểm các kỳ đã qua

    def _diem_tu_tong(self, tong):
        """(điểm quá trình, điểm thi) sao cho điểm tổng kết xấp xỉ `tong`."""
        ty_qt = float(settings.TY_LE_DIEM_QUA_TRINH)
        ty_thi = float(settings.TY_LE_DIEM_THI)
        qt = round(min(10.0, max(0.0, tong + self.rng.uniform(-1.0, 1.0))), 1)
        thi = round(min(10.0, max(0.0, (tong - ty_qt * qt) / ty_thi)), 1)
        return Decimal(str(qt)), Decimal(str(thi))

    def _tong_diem_ky(self, so_lop):
        """Điểm tổng kết mục tiêu cho các lớp một sinh viên học trong một kỳ. Khoảng 1/5 số kỳ có nhiều
        hơn 1 lớp có đúng một học phần chưa đạt (dưới 4), các lớp còn lại từ 7.0 trở lên nên điểm trung bình
        kỳ vẫn từ 5.0: sinh viên "rớt một môn" không bị cảnh báo học vụ ngoài 8 trường hợp cố ý."""
        if so_lop >= 2 and self.rng.random() < 0.23:
            tong = [min(9.6, max(7.0, self.rng.gauss(7.7, 0.8))) for _ in range(so_lop)]
            tong[self.rng.randrange(so_lop)] = self.rng.uniform(3.2, 3.7)
            return tong
        return [min(9.6, max(5.2, self.rng.gauss(7.0, 1.1))) for _ in range(so_lop)]

    def _ghi_diem(self, ke_hoach, da_dat, lop, ma_sv, ma_lop, tong, cong_bo):
        """Thêm một dòng đăng ký + điểm vào kế hoạch; "đã đạt" tính bằng đúng công thức và ngưỡng của hệ thống."""
        qt, thi = self._diem_tu_tong(tong)
        ke_hoach.append((ma_sv, ma_lop, qt, thi, cong_bo))
        if tinh_diem_tong_ket(qt, thi) >= settings.DIEM_DAT_TOI_THIEU:
            da_dat[ma_sv].add(lop[ma_lop].ma_hoc_phan_id)

    def _tao_lich_su_ky_da_qua(self, sinh_vien_moi, lop):
        """Đăng ký + điểm HK1/HK2 2024-2025 của 85 sinh viên mới, chèn thẳng (kỳ đã đóng đợt đăng ký
        nên không đi qua dịch vụ đăng ký). Trả về {mã sinh viên: tập mã học phần đã đạt}."""
        con_cho = {
            ma: lop[ma].si_so_toi_da - DangKyHocPhan.objects.filter(ma_lop_hoc_phan_id=ma).count()
            for ma in LOP_HK1_2024 + LOP_HK2_2024
        }
        dieu_kien_hk2 = {'LTW_2024': 'NMLT', 'HDH_2024': 'KTMT', 'MMH_2024': 'TOAN'}
        da_dat = {}
        ke_hoach = []  # (mã sv, mã lớp, điểm quá trình, điểm thi, đã công bố)

        for sv in sinh_vien_moi:
            ma_sv = sv.pk
            do = ma_sv in SV_CANH_BAO_DO
            canh_bao = do or ma_sv in SV_CANH_BAO_VANG
            da_dat[ma_sv] = set()

            # HK1 2024-2025: sinh viên bị cảnh báo học đủ 3 học phần nhập môn (để đủ tiên quyết cho HK2).
            if canh_bao:
                chon = ['TOAN_2024', 'NMLT_2024', 'KTMT_2024']
            else:
                # Ưu tiên một trong CSDL/CTDLGT (tiên quyết của nhiều lớp kỳ sau), còn lại là học phần nhập môn.
                nen_tang = [ma for ma in ('CSDL_2024', 'CTDLGT_2024') if con_cho[ma] > 0]
                nhap_mon = [ma for ma in ('TOAN_2024', 'NMLT_2024', 'KTMT_2024') if con_cho[ma] > 0]
                self.rng.shuffle(nen_tang)
                self.rng.shuffle(nhap_mon)
                chon = (nen_tang[:1] + nhap_mon)[:self.rng.choice((2, 2, 3))]
            # Công bố theo cả kỳ của từng sinh viên (không rải lẻ từng dòng): nếu chỉ ẩn môn đạt thì kỳ đó
            # chỉ còn môn rớt hiển thị và điểm trung bình bị kéo thấp, sinh ra cảnh báo học vụ ngoài ý muốn.
            cong_bo = canh_bao or self.rng.random() < 0.92
            for ma_lop, tong in zip(chon, self._tong_diem_ky(len(chon))):
                con_cho[ma_lop] -= 1
                self._ghi_diem(ke_hoach, da_dat, lop, ma_sv, ma_lop, tong, cong_bo)

            # HK2 2024-2025
            if canh_bao:
                # 2 học phần chưa đạt (MMT, LTW). Mức đỏ: HDH 5.5 kéo điểm trung bình dưới 5.0;
                # mức vàng: HDH 9.6 nên điểm trung bình vẫn từ 5.0 trở lên. Toàn bộ đã công bố.
                for ma_lop, tong in (
                    ('MMT_2024', self.rng.uniform(3.3, 3.7)), ('LTW_2024', self.rng.uniform(3.3, 3.7)),
                    ('HDH_2024', 5.5 if do else 9.6),
                ):
                    con_cho[ma_lop] -= 1
                    self._ghi_diem(ke_hoach, da_dat, lop, ma_sv, ma_lop, tong, True)
                continue
            ung_vien = [
                ma for ma in LOP_HK2_2024
                if con_cho[ma] > 0 and (ma not in dieu_kien_hk2 or dieu_kien_hk2[ma] in da_dat[ma_sv])
            ]
            self.rng.shuffle(ung_vien)
            chon = ung_vien[:self.rng.choice((1, 2, 2))]
            cong_bo = self.rng.random() < 0.92
            for ma_lop, tong in zip(chon, self._tong_diem_ky(len(chon))):
                con_cho[ma_lop] -= 1
                self._ghi_diem(ke_hoach, da_dat, lop, ma_sv, ma_lop, tong, cong_bo)

        moc_thoi_gian = {
            **{ma: _aware(2024, 8, 26) for ma in LOP_HK1_2024}, **{ma: _aware(2025, 1, 27) for ma in LOP_HK2_2024},
        }
        DangKyHocPhan.objects.bulk_create([
            DangKyHocPhan(
                ma_sinh_vien_id=ma_sv, ma_lop_hoc_phan_id=ma_lop,
                thoi_gian_dang_ky=moc_thoi_gian[ma_lop] + timedelta(minutes=i),
            )
            for i, (ma_sv, ma_lop, _, _, _) in enumerate(ke_hoach)
        ], batch_size=500)
        ma_dang_ky = {
            (sv, ma_lop): pk for pk, sv, ma_lop in DangKyHocPhan.objects.filter(
                ma_lop_hoc_phan_id__in=list(moc_thoi_gian),
            ).values_list('ma_dang_ky', 'ma_sinh_vien_id', 'ma_lop_hoc_phan_id')
        }
        Diem.objects.bulk_create([
            Diem(ma_dang_ky_id=ma_dang_ky[(ma_sv, ma_lop)], diem_qua_trinh=qt, diem_thi=thi, da_cong_bo=cong_bo)
            for ma_sv, ma_lop, qt, thi, cong_bo in ke_hoach
        ], batch_size=500)
        return da_dat

    # ------------------------------------------------------------------ đăng ký kỳ đang mở

    @staticmethod
    def _loai_loi(thong_diep):
        for tu_khoa, ten in (('tiên quyết', 'tiên quyết'), ('trùng', 'trùng lịch'), ('sĩ số', 'đủ sĩ số')):
            if tu_khoa in thong_diep:
                return ten
        return 'khác'

    def _dang_ky_ky_dang_mo(self, sinh_vien_moi, lop, da_dat):
        """Mỗi sinh viên mới đăng ký 3-5 lớp kỳ đang mở qua dang_ky_hoc_phan (đủ kiểm tra tiên quyết,
        trùng lịch, sĩ số). Lỗi nghiệp vụ thì bỏ qua và thử lớp khác, không bao giờ dừng lệnh."""
        thu_tu = list(sinh_vien_moi)
        self.rng.shuffle(thu_tu)  # tránh việc sinh viên mã nhỏ luôn chiếm hết chỗ ở lớp sĩ số nhỏ
        tu_choi = {'tiên quyết': 0, 'trùng lịch': 0, 'đủ sĩ số': 0, 'khác': 0}
        so_dang_ky = {}
        for sv in thu_tu:
            muc_tieu = self.rng.randint(3, 5)
            ung_vien = list(LOP_DANG_KY_NGAU_NHIEN)
            self.rng.shuffle(ung_vien)
            dem = 0
            for ma_lop in ung_vien:
                if dem >= muc_tieu:
                    break
                if lop[ma_lop].ma_hoc_phan_id in da_dat[sv.pk]:
                    continue  # đã đạt học phần này rồi, không học lại
                try:
                    dang_ky_hoc_phan(sv, lop[ma_lop])
                    dem += 1
                except LoiDangKyHocPhan as loi:
                    tu_choi[self._loai_loi(str(loi))] += 1
            so_dang_ky[sv.pk] = dem
        return {'so_dang_ky': so_dang_ky, 'tu_choi': tu_choi}

    # ------------------------------------------------------------------ điểm danh, lịch thi, thông báo

    def _dang_ky_ky_hien_tai(self):
        return DangKyHocPhan.objects.filter(
            ma_lop_hoc_phan__hoc_ky=HOC_KY_HIEN_TAI[0], ma_lop_hoc_phan__nam_hoc=HOC_KY_HIEN_TAI[1],
            trang_thai=TrangThaiDangKy.CON_HIEU_LUC,
        )

    def _tao_diem_danh(self):
        thu_cua_lop = dict(LichHoc.objects.filter(
            ma_lop_hoc_phan__hoc_ky=HOC_KY_HIEN_TAI[0], ma_lop_hoc_phan__nam_hoc=HOC_KY_HIEN_TAI[1],
        ).values_list('ma_lop_hoc_phan_id', 'thu'))
        sinh_vien_theo_lop = {}
        for ma_sv, ma_lop in self._dang_ky_ky_hien_tai().order_by('ma_lop_hoc_phan_id', 'ma_sinh_vien_id').values_list(
            'ma_sinh_vien_id', 'ma_lop_hoc_phan_id',
        ):
            sinh_vien_theo_lop.setdefault(ma_lop, []).append(ma_sv)

        ban_ghi = []
        for ma_lop, danh_sach_sv in sinh_vien_theo_lop.items():
            buoi_gan_nhat = self.hom_nay - timedelta(days=1)
            while buoi_gan_nhat.weekday() != thu_cua_lop[ma_lop] - 2:
                buoi_gan_nhat -= timedelta(days=1)
            for tuan in range(4):
                ngay = buoi_gan_nhat - timedelta(days=7 * tuan)
                for ma_sv in danh_sach_sv:
                    ban_ghi.append(DiemDanh(
                        lop_hoc_phan_id=ma_lop, sinh_vien_id=ma_sv, ngay_diem_danh=ngay,
                        co_mat=self.rng.random() < 0.88,
                    ))
        DiemDanh.objects.bulk_create(ban_ghi, batch_size=500)
        return len(ban_ghi)

    def _tao_lich_thi(self, lop):
        lop_hien_tai = [
            ma for ma, l in lop.items()
            if (l.hoc_ky, l.nam_hoc) == HOC_KY_HIEN_TAI and ma not in LOP_KHONG_CO_LICH_THI
        ]
        lop_hien_tai.sort()
        lich = []
        for i, ma in enumerate(lop_hien_tai):
            ngay = self.hom_nay + timedelta(days=70 + 2 * i)
            if ngay.weekday() == 6:
                ngay += timedelta(days=1)
            gio, phut = [(7, 30), (9, 30), (13, 30), (15, 30)][i % 4]
            lich.append(LichThi(
                lop_hoc_phan_id=ma, ngay_thi=ngay, gio_bat_dau=time(gio, phut),
                thoi_luong_phut=(60, 90, 120)[i % 3], phong_thi=f'P.{301 + i}',
            ))
        LichThi.objects.bulk_create(lich)
        return len(lich)

    def _tao_thong_bao(self, lop_hanh_chinh, lop):
        tk = {t.ten_dang_nhap: t for t in TaiKhoan.objects.filter(
            ten_dang_nhap__in=['pdt_demo', 'gv003', 'gv004', 'gv005'],
        )}
        pdt = tk['pdt_demo']
        # (tiêu đề, nội dung, người gửi, đối tượng, lớp học phần, lớp hành chính, ngày trước, tỷ lệ đã đọc)
        cac_thong_bao = [
            ('Bảo trì hệ thống cuối tuần', 'Hệ thống sẽ tạm ngừng từ 22h thứ Bảy đến 6h sáng Chủ nhật để bảo trì.',
             pdt, DoiTuongThongBao.TAT_CA, None, None, 9, 0.6),
            ('Hướng dẫn sử dụng hệ thống', 'Tài liệu hướng dẫn đăng nhập, đổi mật khẩu và tra cứu thông tin đã được đăng trên trang chủ.',
             pdt, DoiTuongThongBao.TAT_CA, None, None, 7, 0.3),
            ('Đợt đăng ký học phần HK1 2025-2026 đang mở', 'Sinh viên đăng ký học phần trong thời gian đợt đăng ký; lớp đủ sĩ số sẽ không nhận thêm.',
             pdt, DoiTuongThongBao.SINH_VIEN, None, None, 6, 0.7),
            ('Nhắc nộp điểm quá trình', 'Giảng viên hoàn tất nhập điểm quá trình các lớp học phần kỳ này trước hạn quy định.',
             pdt, DoiTuongThongBao.GIANG_VIEN, None, None, 5, 0.5),
            ('Chuẩn bị bài thực hành tuần này', 'Sinh viên cài đặt sẵn hệ quản trị cơ sở dữ liệu trước buổi thực hành.',
             tk['gv004'], DoiTuongThongBao.LOP_HOC_PHAN, 'HQTCSDL_2025', None, 4, 0.5),
            ('Đổi phòng học buổi tới', 'Buổi học Kiến trúc máy tính tuần sau chuyển sang phòng C110.',
             tk['gv005'], DoiTuongThongBao.LOP_HOC_PHAN, 'KTMT_2025', None, 3, 0.2),
            ('Nộp bài tập chương 1', 'Hạn nộp bài tập chương 1 môn Toán cao cấp là hết tuần này.',
             tk['gv003'], DoiTuongThongBao.LOP_HOC_PHAN, 'TOAN_2025', None, 2, 0.6),
            ('Họp lớp đầu kỳ - CNTT_K1', 'Cố vấn học tập họp lớp đầu kỳ, sinh viên tham dự đầy đủ.',
             pdt, DoiTuongThongBao.LOP_HANH_CHINH, None, 'CNTT_K1', 8, 0.4),
            ('Họp lớp đầu kỳ - CNTT_K2', 'Cố vấn học tập họp lớp đầu kỳ, sinh viên tham dự đầy đủ.',
             pdt, DoiTuongThongBao.LOP_HANH_CHINH, None, 'CNTT_K2', 8, 0.3),
            ('Họp lớp đầu kỳ - ATTT_K1', 'Cố vấn học tập họp lớp đầu kỳ, sinh viên tham dự đầy đủ.',
             pdt, DoiTuongThongBao.LOP_HANH_CHINH, None, 'ATTT_K1', 1, 0.1),
        ]
        tai_khoan_sinh_vien = {}
        for ma_lop_hc, ma_sv_tk in SinhVien.objects.values_list('ma_lop_id', 'ma_tai_khoan_id'):
            tai_khoan_sinh_vien.setdefault(ma_lop_hc, []).append(ma_sv_tk)
        tai_khoan_lop_hoc_phan = {}
        for ma_lop, ma_tk in self._dang_ky_ky_hien_tai().values_list('ma_lop_hoc_phan_id', 'ma_sinh_vien__ma_tai_khoan_id'):
            tai_khoan_lop_hoc_phan.setdefault(ma_lop, []).append(ma_tk)
        tai_khoan_theo_vai_tro = {}
        for ma_tk, vai_tro in TaiKhoan.objects.values_list('ma_tai_khoan', 'vai_tro'):
            tai_khoan_theo_vai_tro.setdefault(vai_tro, []).append(ma_tk)

        bay_gio = timezone.now()
        da_doc = []
        for tieu_de, noi_dung, nguoi_gui, doi_tuong, ma_lop_hp, ma_lop_hc, ngay_truoc, ty_le_doc in cac_thong_bao:
            thong_bao = ThongBao.objects.create(
                tieu_de=tieu_de, noi_dung=noi_dung, nguoi_gui=nguoi_gui, doi_tuong=doi_tuong,
                lop_hoc_phan=lop[ma_lop_hp] if ma_lop_hp else None,
                lop_hanh_chinh=lop_hanh_chinh[ma_lop_hc] if ma_lop_hc else None,
            )
            ThongBao.objects.filter(pk=thong_bao.pk).update(thoi_gian_gui=bay_gio - timedelta(days=ngay_truoc, hours=2))
            if doi_tuong == DoiTuongThongBao.LOP_HOC_PHAN:
                nguoi_nhan = tai_khoan_lop_hoc_phan.get(ma_lop_hp, [])
            elif doi_tuong == DoiTuongThongBao.LOP_HANH_CHINH:
                nguoi_nhan = tai_khoan_sinh_vien.get(ma_lop_hc, [])
            elif doi_tuong == DoiTuongThongBao.TAT_CA:
                nguoi_nhan = [ma_tk for ds in tai_khoan_theo_vai_tro.values() for ma_tk in ds]
            else:
                nguoi_nhan = tai_khoan_theo_vai_tro.get(doi_tuong, [])
            da_doc.extend(
                DaDocThongBao(thong_bao=thong_bao, tai_khoan_id=ma_tk)
                for ma_tk in nguoi_nhan if ma_tk != nguoi_gui.pk and self.rng.random() < ty_le_doc
            )
        DaDocThongBao.objects.bulk_create(da_doc, batch_size=500)
        return len(cac_thong_bao)

    # ------------------------------------------------------------------ kết quả

    def _in_ket_qua(self, thong_ke):
        so_dang_ky = thong_ke['dang_ky_ky_moi']['so_dang_ky']
        phan_bo = {}
        for so in so_dang_ky.values():
            phan_bo[so] = phan_bo.get(so, 0) + 1
        tu_choi = thong_ke['dang_ky_ky_moi']['tu_choi']
        w = self.stdout.write
        w('')
        w(self.style.SUCCESS(f'Đã nạp xong dữ liệu đầy đủ. Mật khẩu demo chung: "{MAT_KHAU_MAU}".'))
        w(f'  - {SinhVien.objects.count()} sinh viên, {GiangVien.objects.count()} giảng viên, '
          f'{CoVanHocTap.objects.count()} cố vấn, {LopHanhChinh.objects.count()} lớp hành chính, '
          f'{HocPhan.objects.count()} học phần, {LopHocPhan.objects.count()} lớp học phần.')
        w(f'  - Đăng ký kỳ đang mở của 85 sinh viên mới: {sum(so_dang_ky.values())} lượt thành công; '
          f'số lượt bị từ chối: ' + ', '.join(f'{ten} {so}' for ten, so in tu_choi.items()) + '.')
        w('  - Số sinh viên theo số lớp đã đăng ký: ' + ', '.join(f'{k} lớp: {v}' for k, v in sorted(phan_bo.items())) + '.')
        w(f'  - {thong_ke["so_diem_danh"]} dòng điểm danh, {thong_ke["so_lich_thi"]} lịch thi, '
          f'{thong_ke["so_thong_bao"]} thông báo.')
        w('')
        w('Tài khoản demo (cùng mật khẩu ở trên):')
        w('  - pdt_demo: Phòng Đào tạo. gv001-gv005: giảng viên. sv001-sv090: sinh viên.')
        w('  - cv001 (CNTT_K1), cv002 (CNTT_K2), cv003 (ATTT_K1): cố vấn học tập, mỗi người một lớp 30 sinh viên.')
        w('Gợi ý demo (4 ca đăng ký gốc vẫn còn đúng):')
        w('  - sv001: đăng ký CNPM_2025 và AIUD_2025 -> thành công. sv002: CNPM_2025/AIUD_2025 -> thiếu tiên quyết.')
        w('  - sv003: AIUD_2025 -> trùng lịch với CTDLGT_2025. sv005: CTDLGT_2025 -> lớp đã đủ sĩ số.')
        w('  - Cảnh báo học vụ (HK2 2024-2025), mức đỏ: ' + ', '.join(m.lower() for m in SV_CANH_BAO_DO)
          + '; mức vàng: ' + ', '.join(m.lower() for m in SV_CANH_BAO_VANG) + '.')
