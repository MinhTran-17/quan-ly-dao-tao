from django.db import models


class TrangThaiDangKy(models.TextChoices):
    CON_HIEU_LUC = 'CON_HIEU_LUC', 'Còn hiệu lực'
    DA_HUY = 'DA_HUY', 'Đã hủy'


class DangKyHocPhan(models.Model):
    ma_dang_ky = models.AutoField(primary_key=True)
    thoi_gian_dang_ky = models.DateTimeField()
    # Hủy đăng ký chỉ đổi cột này, KHÔNG xóa dòng, để giữ lịch sử (theo quy ước dự án và
    # docs/erd.md). Mọi nơi đếm/xét sĩ số, trùng lịch, tiên quyết, thống kê... chỉ tính
    # các dòng CON_HIEU_LUC — xem enrollment/services.py.
    trang_thai = models.CharField(
        max_length=20, choices=TrangThaiDangKy.choices, default=TrangThaiDangKy.CON_HIEU_LUC,
    )
    ma_sinh_vien = models.ForeignKey(
        'people.SinhVien', on_delete=models.PROTECT, db_column='ma_sinh_vien',
        related_name='dang_ky_hoc_phan',
    )
    ma_lop_hoc_phan = models.ForeignKey(
        'classes.LopHocPhan', on_delete=models.PROTECT, db_column='ma_lop_hoc_phan',
        related_name='dang_ky',
    )
    # Cho phép đăng ký lại sau khi đã hủy: mỗi lần hủy/đăng ký lại tạo một DÒNG MỚI (không
    # sửa dòng cũ), nên (ma_sinh_vien, ma_lop_hoc_phan) có thể lặp lại giữa các dòng lịch sử
    # — chỉ cấm trùng ở các dòng CON_HIEU_LUC. MySQL không có UNIQUE INDEX có điều kiện
    # (khác PostgreSQL "UNIQUE ... WHERE"), nên dùng cách chuẩn thay thế: hai cột SINH
    # (generated) này chỉ có giá trị khi trang_thai=CON_HIEU_LUC, còn lại là NULL; MySQL
    # coi nhiều NULL trong một UNIQUE INDEX là không trùng nhau, nên UNIQUE trên cặp cột
    # này chỉ thực sự chặn trùng giữa các dòng CON_HIEU_LUC. Chọn ràng buộc ở CSDL (qua
    # GeneratedField, có từ Django 5.0) thay vì chỉ kiểm tra ở tầng service vì được đảm bảo
    # bất kể đường vào code nào, và dùng được từ MySQL 5.7.6 trở lên (không cần đúng bản
    # MySQL 8.0.46 mới có index trên biểu thức).
    ma_sinh_vien_hieu_luc = models.GeneratedField(
        expression=models.Case(
            models.When(trang_thai=TrangThaiDangKy.CON_HIEU_LUC, then=models.F('ma_sinh_vien')),
            default=models.Value(None),
        ),
        output_field=models.CharField(max_length=20, null=True),
        db_persist=False,
    )
    ma_lop_hoc_phan_hieu_luc = models.GeneratedField(
        expression=models.Case(
            models.When(trang_thai=TrangThaiDangKy.CON_HIEU_LUC, then=models.F('ma_lop_hoc_phan')),
            default=models.Value(None),
        ),
        output_field=models.CharField(max_length=20, null=True),
        db_persist=False,
    )

    class Meta:
        db_table = 'dang_ky_hoc_phan'
        constraints = [
            models.UniqueConstraint(
                fields=['ma_sinh_vien_hieu_luc', 'ma_lop_hoc_phan_hieu_luc'],
                name='uk_dang_ky_hoc_phan_dang_hieu_luc',
                violation_error_message='Sinh viên đang có một đăng ký còn hiệu lực cho lớp học phần này.',
            ),
            models.CheckConstraint(
                condition=models.Q(trang_thai__in=TrangThaiDangKy.values),
                name='ck_dang_ky_hoc_phan_trang_thai',
            ),
        ]

    def __str__(self):
        return f'{self.ma_sinh_vien_id} - {self.ma_lop_hoc_phan_id}'
