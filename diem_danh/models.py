from django.db import models


class DiemDanh(models.Model):
    """Điểm danh theo buổi học của một lớp học phần — chỉ để theo dõi chuyên cần, KHÔNG
    tính vào điểm quá trình (không đụng tới app grades)."""

    id = models.AutoField(primary_key=True)
    lop_hoc_phan = models.ForeignKey(
        'classes.LopHocPhan', on_delete=models.PROTECT, related_name='diem_danh',
    )
    sinh_vien = models.ForeignKey(
        'people.SinhVien', on_delete=models.PROTECT, related_name='diem_danh',
    )
    ngay_diem_danh = models.DateField()
    co_mat = models.BooleanField(default=True)

    class Meta:
        db_table = 'diem_danh'
        ordering = ['-ngay_diem_danh']
        constraints = [
            models.UniqueConstraint(
                fields=['lop_hoc_phan', 'sinh_vien', 'ngay_diem_danh'],
                name='uk_diem_danh_lop_sinh_vien_ngay',
                violation_error_message='Sinh viên này đã được điểm danh cho ngày này.',
            ),
        ]

    def __str__(self):
        trang_thai = 'có mặt' if self.co_mat else 'vắng'
        return f'{self.sinh_vien_id} - {self.lop_hoc_phan_id} - {self.ngay_diem_danh} ({trang_thai})'
