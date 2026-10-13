from django.db import models


class LopHocPhan(models.Model):
    ma_lop_hoc_phan = models.CharField(max_length=20, primary_key=True)
    hoc_ky = models.CharField(max_length=10)
    nam_hoc = models.CharField(max_length=9)
    si_so_toi_da = models.IntegerField()
    ma_hoc_phan = models.ForeignKey(
        'academics.HocPhan', on_delete=models.PROTECT, db_column='ma_hoc_phan',
        related_name='lop_hoc_phan',
    )
    ma_giang_vien = models.ForeignKey(
        'people.GiangVien', on_delete=models.PROTECT, db_column='ma_giang_vien',
        related_name='lop_phu_trach',
    )

    class Meta:
        db_table = 'lop_hoc_phan'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(si_so_toi_da__gt=0),
                name='ck_lop_hoc_phan_si_so_duong',
                violation_error_message='Sĩ số tối đa phải lớn hơn 0.',
            ),
        ]

    def __str__(self):
        return f'{self.ma_lop_hoc_phan} ({self.hoc_ky} {self.nam_hoc})'


class LichHoc(models.Model):
    ma_lich_hoc = models.AutoField(primary_key=True)
    thu = models.IntegerField()
    tiet_bat_dau = models.IntegerField()
    so_tiet = models.IntegerField()
    phong_hoc = models.CharField(max_length=20)
    ma_lop_hoc_phan = models.ForeignKey(
        LopHocPhan, on_delete=models.PROTECT, db_column='ma_lop_hoc_phan',
        related_name='lich_hoc',
    )

    class Meta:
        db_table = 'lich_hoc'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(thu__gte=2, thu__lte=8),
                name='ck_lich_hoc_thu_hop_le',
                violation_error_message='Thứ học phải từ 2 đến 8.',
            ),
        ]

    def __str__(self):
        return f'{self.ma_lop_hoc_phan_id} - Thứ {self.thu} tiết {self.tiet_bat_dau}'


class LichThi(models.Model):
    ma_lich_thi = models.AutoField(primary_key=True)
    # OneToOneField tự tạo UNIQUE trên lop_hoc_phan — mỗi lớp học phần tối đa một lịch thi.
    lop_hoc_phan = models.OneToOneField(
        LopHocPhan, on_delete=models.PROTECT, db_column='ma_lop_hoc_phan',
        related_name='lich_thi',
    )
    ngay_thi = models.DateField()
    gio_bat_dau = models.TimeField()
    thoi_luong_phut = models.PositiveIntegerField()
    phong_thi = models.CharField(max_length=20)

    class Meta:
        db_table = 'lich_thi'
        ordering = ['ngay_thi', 'gio_bat_dau']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(thoi_luong_phut__gt=0),
                name='ck_lich_thi_thoi_luong_duong',
                violation_error_message='Thời lượng thi phải lớn hơn 0.',
            ),
        ]

    def __str__(self):
        return f'Lịch thi {self.lop_hoc_phan_id} ({self.ngay_thi:%d/%m/%Y})'
