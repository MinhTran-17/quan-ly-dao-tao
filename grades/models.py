from django.db import models

from .tinh_diem import tinh_diem_tong_ket


class Diem(models.Model):
    ma_diem = models.AutoField(primary_key=True)
    diem_qua_trinh = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    diem_thi = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    ma_dang_ky = models.OneToOneField(
        'enrollment.DangKyHocPhan', on_delete=models.PROTECT, db_column='ma_dang_ky',
        related_name='diem',
    )
    # Sinh viên chỉ xem được điểm thật (bảng điểm, tiến độ học tập, điểm trung bình, cảnh
    # báo học vụ) khi cột này là True; giảng viên/cố vấn/Phòng Đào tạo luôn xem điểm thật
    # bất kể giá trị này. Tự đặt lại về False khi giảng viên/Phòng Đào tạo sửa điểm sau khi
    # đã công bố — xem grades/forms.py DiemForm.save().
    da_cong_bo = models.BooleanField(default=False)

    class Meta:
        db_table = 'diem'
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(diem_qua_trinh__isnull=True) | models.Q(diem_qua_trinh__gte=0, diem_qua_trinh__lte=10))
                    & (models.Q(diem_thi__isnull=True) | models.Q(diem_thi__gte=0, diem_thi__lte=10))
                ),
                name='ck_diem_trong_khoang',
                violation_error_message='Điểm phải từ 0 đến 10.',
            ),
        ]

    def tinh_diem_tong_ket(self):
        return tinh_diem_tong_ket(self.diem_qua_trinh, self.diem_thi)

    def __str__(self):
        return f'Điểm của đăng ký {self.ma_dang_ky_id}'
