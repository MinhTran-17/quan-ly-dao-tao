import re

from django.core.exceptions import ValidationError
from django.db import models


def validate_nam_hoc(gia_tri):
    khop = re.fullmatch(r'(\d{4})-(\d{4})', gia_tri)
    if not khop:
        raise ValidationError('Năm học phải theo định dạng "YYYY-YYYY", ví dụ 2025-2026.')
    nam_dau, nam_sau = int(khop.group(1)), int(khop.group(2))
    if nam_sau != nam_dau + 1:
        raise ValidationError('Năm học phải gồm hai năm liên tiếp, ví dụ 2025-2026.')


class NganhHoc(models.Model):
    ma_nganh = models.CharField(max_length=20, primary_key=True)
    ten_nganh = models.CharField(max_length=100)

    class Meta:
        db_table = 'nganh_hoc'

    def __str__(self):
        return f'{self.ma_nganh} - {self.ten_nganh}'


class LopHanhChinh(models.Model):
    ma_lop = models.CharField(max_length=20, primary_key=True)
    ten_lop = models.CharField(max_length=100)
    ma_nganh = models.ForeignKey(
        NganhHoc, on_delete=models.PROTECT, db_column='ma_nganh', related_name='lop_hanh_chinh',
    )
    ma_co_van = models.ForeignKey(
        'people.CoVanHocTap', on_delete=models.PROTECT, db_column='ma_co_van',
        related_name='lop_phu_trach',
    )
    # Cho phép NULL vì lớp hành chính có sẵn trước khi có chức năng này chưa được gán
    # chương trình đào tạo nào (xem docs/erd.md, lượt 3/6).
    chuong_trinh_dao_tao = models.ForeignKey(
        'academics.ChuongTrinhDaoTao', on_delete=models.PROTECT, null=True, blank=True,
        related_name='lop_hanh_chinh',
    )

    class Meta:
        db_table = 'lop_hanh_chinh'

    def __str__(self):
        return f'{self.ma_lop} - {self.ten_lop}'


class HocPhan(models.Model):
    ma_hoc_phan = models.CharField(max_length=20, primary_key=True)
    ten_hoc_phan = models.CharField(max_length=100)
    so_tin_chi = models.IntegerField()

    class Meta:
        db_table = 'hoc_phan'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(so_tin_chi__gt=0),
                name='ck_hoc_phan_so_tin_chi_duong',
                violation_error_message='Số tín chỉ phải lớn hơn 0.',
            ),
        ]

    def __str__(self):
        return f'{self.ma_hoc_phan} - {self.ten_hoc_phan}'


class DieuKienTienQuyet(models.Model):
    ma_dieu_kien = models.AutoField(primary_key=True)
    ma_hoc_phan = models.ForeignKey(
        HocPhan, on_delete=models.PROTECT, db_column='ma_hoc_phan',
        related_name='dieu_kien_tien_quyet',
    )
    ma_hoc_phan_tien_quyet = models.ForeignKey(
        HocPhan, on_delete=models.PROTECT, db_column='ma_hoc_phan_tien_quyet',
        related_name='la_tien_quyet_cua',
    )

    class Meta:
        db_table = 'dieu_kien_tien_quyet'
        constraints = [
            models.UniqueConstraint(
                fields=['ma_hoc_phan', 'ma_hoc_phan_tien_quyet'],
                name='uk_dieu_kien_tien_quyet_cap',
                violation_error_message='Điều kiện tiên quyết này đã tồn tại.',
            ),
            models.CheckConstraint(
                condition=~models.Q(ma_hoc_phan=models.F('ma_hoc_phan_tien_quyet')),
                name='ck_dieu_kien_tien_quyet_khac_hoc_phan',
                violation_error_message='Học phần tiên quyết phải khác học phần đang xét.',
            ),
        ]

    def __str__(self):
        return f'{self.ma_hoc_phan_id} cần tiên quyết {self.ma_hoc_phan_tien_quyet_id}'


class HocKy(models.Model):
    """Danh mục học kỳ. Không phải khóa ngoại thật của lop_hoc_phan — xem giới hạn ở
    docs/thiet_ke_giao_dien.md/docs/erd.md: lop_hoc_phan.hoc_ky/nam_hoc vẫn là chuỗi tự do,
    dropdown chỉ sao chép giá trị từ đây sang khi tạo/sửa lớp học phần."""

    id = models.AutoField(primary_key=True)
    hoc_ky = models.PositiveSmallIntegerField()
    nam_hoc = models.CharField(max_length=9, validators=[validate_nam_hoc])
    ngay_bat_dau = models.DateField()
    ngay_ket_thuc = models.DateField()

    class Meta:
        db_table = 'hoc_ky'
        ordering = ['-nam_hoc', 'hoc_ky']
        constraints = [
            models.UniqueConstraint(
                fields=['hoc_ky', 'nam_hoc'],
                name='uk_hoc_ky_nam_hoc',
                violation_error_message='Học kỳ này của năm học này đã có trong danh mục.',
            ),
            models.CheckConstraint(
                condition=models.Q(ngay_ket_thuc__gt=models.F('ngay_bat_dau')),
                name='ck_hoc_ky_ngay_ket_thuc_sau_ngay_bat_dau',
                violation_error_message='Ngày kết thúc phải sau ngày bắt đầu.',
            ),
        ]

    def __str__(self):
        return f'Học kỳ {self.hoc_ky} - {self.nam_hoc}'


class DotDangKy(models.Model):
    """Đợt đăng ký học phần của một học kỳ. Ràng buộc "hai đợt cùng học kỳ không được chồng
    lấp thời gian" là ràng buộc GIỮA NHIỀU DÒNG nên không đặt được thành CHECK constraint ở
    MySQL (MySQL không có EXCLUDE constraint như PostgreSQL) — kiểm tra ở tầng ứng dụng, xem
    DotDangKyForm.clean() (academics/forms.py)."""

    id = models.AutoField(primary_key=True)
    hoc_ky = models.ForeignKey(HocKy, on_delete=models.PROTECT, related_name='dot_dang_ky')
    ngay_mo = models.DateTimeField()
    ngay_dong = models.DateTimeField()

    class Meta:
        db_table = 'dot_dang_ky'
        ordering = ['hoc_ky', 'ngay_mo']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ngay_dong__gt=models.F('ngay_mo')),
                name='ck_dot_dang_ky_ngay_dong_sau_ngay_mo',
                violation_error_message='Ngày đóng phải sau ngày mở.',
            ),
        ]

    def __str__(self):
        return f'Đợt đăng ký {self.hoc_ky} ({self.ngay_mo:%d/%m/%Y %H:%M} - {self.ngay_dong:%d/%m/%Y %H:%M})'


class ChuongTrinhDaoTao(models.Model):
    """Chương trình đào tạo của một ngành cho một khóa tuyển sinh. Mỗi (ngành, khóa) chỉ
    có một chương trình nên không cần cột phiên bản riêng — sửa chương trình hiện có khi
    cần thay đổi, không tạo phiên bản mới."""

    id = models.AutoField(primary_key=True)
    nganh = models.ForeignKey(NganhHoc, on_delete=models.PROTECT, related_name='chuong_trinh_dao_tao')
    ten_chuong_trinh = models.CharField(max_length=150)
    khoa_hoc = models.CharField(max_length=20)

    class Meta:
        db_table = 'chuong_trinh_dao_tao'
        constraints = [
            models.UniqueConstraint(
                fields=['nganh', 'khoa_hoc'],
                name='uk_chuong_trinh_dao_tao_nganh_khoa_hoc',
                violation_error_message='Ngành này đã có chương trình đào tạo cho khóa này.',
            ),
        ]

    def __str__(self):
        return f'{self.ten_chuong_trinh} ({self.khoa_hoc})'


class ChiTietChuongTrinh(models.Model):
    """Một học phần trong lộ trình của một chương trình đào tạo. hoc_ky_du_kien là học kỳ
    thứ mấy trong lộ trình (1..8), KHÔNG phải khóa ngoại tới academics.HocKy (bảng đó là
    lịch học kỳ thật theo năm học, còn đây là thứ tự trong chương trình khung, không gắn
    với một năm học cụ thể nào)."""

    id = models.AutoField(primary_key=True)
    chuong_trinh = models.ForeignKey(
        ChuongTrinhDaoTao, on_delete=models.PROTECT, related_name='chi_tiet',
    )
    hoc_phan = models.ForeignKey(
        HocPhan, on_delete=models.PROTECT, related_name='chi_tiet_chuong_trinh',
    )
    hoc_ky_du_kien = models.PositiveSmallIntegerField()
    bat_buoc = models.BooleanField(default=True)

    class Meta:
        db_table = 'chi_tiet_chuong_trinh'
        ordering = ['hoc_ky_du_kien', 'hoc_phan']
        constraints = [
            models.UniqueConstraint(
                fields=['chuong_trinh', 'hoc_phan'],
                name='uk_chi_tiet_chuong_trinh_hoc_phan',
                violation_error_message='Học phần này đã có trong chương trình đào tạo.',
            ),
            models.CheckConstraint(
                condition=models.Q(hoc_ky_du_kien__gte=1, hoc_ky_du_kien__lte=8),
                name='ck_chi_tiet_chuong_trinh_hoc_ky_du_kien_hop_le',
                violation_error_message='Học kỳ dự kiến phải từ 1 đến 8.',
            ),
        ]

    def __str__(self):
        return f'{self.chuong_trinh} - {self.hoc_phan_id} (kỳ {self.hoc_ky_du_kien})'
