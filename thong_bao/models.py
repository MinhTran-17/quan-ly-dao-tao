from django.conf import settings
from django.db import models

from accounts.models import VaiTro


class DoiTuongThongBao(models.TextChoices):
    TAT_CA = 'TAT_CA', 'Tất cả'
    # Bốn giá trị theo vai trò dùng đúng chuỗi của accounts.VaiTro (không thêm cột vai_tro
    # riêng) — gửi cho "tất cả Giảng viên" chẳng hạn thì doi_tuong = VaiTro.GIANG_VIEN.
    PHONG_DAO_TAO = VaiTro.PHONG_DAO_TAO
    GIANG_VIEN = VaiTro.GIANG_VIEN
    SINH_VIEN = VaiTro.SINH_VIEN
    CO_VAN_HOC_TAP = VaiTro.CO_VAN_HOC_TAP
    LOP_HOC_PHAN = 'LOP_HOC_PHAN', 'Lớp học phần cụ thể'
    LOP_HANH_CHINH = 'LOP_HANH_CHINH', 'Lớp hành chính cụ thể'


class ThongBao(models.Model):
    id = models.AutoField(primary_key=True)
    tieu_de = models.CharField(max_length=200)
    noi_dung = models.TextField()
    nguoi_gui = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='nguoi_gui',
        related_name='thong_bao_da_gui',
    )
    doi_tuong = models.CharField(max_length=20, choices=DoiTuongThongBao.choices)
    # Chỉ có giá trị khi doi_tuong=LOP_HOC_PHAN/LOP_HANH_CHINH tương ứng, còn lại NULL.
    lop_hoc_phan = models.ForeignKey(
        'classes.LopHocPhan', on_delete=models.PROTECT, null=True, blank=True,
        db_column='ma_lop_hoc_phan', related_name='thong_bao',
    )
    lop_hanh_chinh = models.ForeignKey(
        'academics.LopHanhChinh', on_delete=models.PROTECT, null=True, blank=True,
        db_column='ma_lop_hanh_chinh', related_name='thong_bao',
    )
    thoi_gian_gui = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'thong_bao'
        ordering = ['-thoi_gian_gui']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(doi_tuong__in=DoiTuongThongBao.values),
                name='ck_thong_bao_doi_tuong',
            ),
        ]

    def __str__(self):
        return self.tieu_de


class DaDocThongBao(models.Model):
    id = models.AutoField(primary_key=True)
    thong_bao = models.ForeignKey(
        ThongBao, on_delete=models.CASCADE, db_column='ma_thong_bao', related_name='da_doc',
    )
    tai_khoan = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column='ma_tai_khoan',
        related_name='thong_bao_da_doc',
    )
    thoi_gian_doc = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'da_doc_thong_bao'
        constraints = [
            models.UniqueConstraint(
                fields=['thong_bao', 'tai_khoan'], name='uk_da_doc_thong_bao',
            ),
        ]

    def __str__(self):
        return f'{self.tai_khoan_id} đã đọc {self.thong_bao_id}'
