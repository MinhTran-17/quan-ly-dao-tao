from django.conf import settings
from django.db import models

from .ma_ho_so import ma_dung_duoc_trong_url as _ma_dung_duoc_trong_url


class SinhVien(models.Model):
    ma_sinh_vien = models.CharField(max_length=20, primary_key=True)
    ho_ten = models.CharField(max_length=100)
    ngay_sinh = models.DateField()
    email = models.CharField(max_length=100)
    so_dien_thoai = models.CharField(max_length=15)
    ma_lop = models.ForeignKey(
        'academics.LopHanhChinh', on_delete=models.PROTECT, db_column='ma_lop',
        related_name='sinh_vien_trong_lop',
    )
    ma_tai_khoan = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='ma_tai_khoan',
        related_name='ho_so_sinh_vien',
    )

    class Meta:
        db_table = 'sinh_vien'

    @property
    def ma_dung_duoc_trong_url(self):
        """False với dữ liệu cũ có mã chứa "/"...: template không tạo liên kết theo mã (tránh NoReverseMatch)."""
        return _ma_dung_duoc_trong_url(self.ma_sinh_vien)

    def __str__(self):
        return f'{self.ma_sinh_vien} - {self.ho_ten}'


class GiangVien(models.Model):
    ma_giang_vien = models.CharField(max_length=20, primary_key=True)
    ho_ten = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    so_dien_thoai = models.CharField(max_length=15)
    ma_tai_khoan = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='ma_tai_khoan',
        related_name='ho_so_giang_vien',
    )

    class Meta:
        db_table = 'giang_vien'

    @property
    def ma_dung_duoc_trong_url(self):
        return _ma_dung_duoc_trong_url(self.ma_giang_vien)

    def __str__(self):
        return f'{self.ma_giang_vien} - {self.ho_ten}'


class CoVanHocTap(models.Model):
    ma_co_van = models.CharField(max_length=20, primary_key=True)
    ho_ten = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    so_dien_thoai = models.CharField(max_length=15)
    ma_tai_khoan = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='ma_tai_khoan',
        related_name='ho_so_co_van',
    )

    class Meta:
        db_table = 'co_van_hoc_tap'

    @property
    def ma_dung_duoc_trong_url(self):
        return _ma_dung_duoc_trong_url(self.ma_co_van)

    def __str__(self):
        return f'{self.ma_co_van} - {self.ho_ten}'
