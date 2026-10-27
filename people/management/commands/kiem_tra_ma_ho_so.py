from django.core.management.base import BaseCommand, CommandError

from people.ma_ho_so import ma_hop_le
from people.models import CoVanHocTap, GiangVien, SinhVien


class Command(BaseCommand):
    help = (
        'Báo các mã sinh viên/giảng viên/cố vấn học tập cũ không hợp lệ (chỉ được chữ cái không dấu và chữ số). '
        'Chỉ đọc, không sửa dữ liệu. Thoát mã 1 nếu có mã không hợp lệ.'
    )

    def handle(self, *args, **options):
        khong_hop_le = []
        for model, truong, nhan in (
            (SinhVien, 'ma_sinh_vien', 'Sinh viên'),
            (GiangVien, 'ma_giang_vien', 'Giảng viên'),
            (CoVanHocTap, 'ma_co_van', 'Cố vấn học tập'),
        ):
            for ma, ho_ten in model.objects.order_by(truong).values_list(truong, 'ho_ten'):
                if not ma_hop_le(ma):
                    khong_hop_le.append((nhan, ma, ho_ten))

        if not khong_hop_le:
            self.stdout.write(self.style.SUCCESS('Mọi mã hồ sơ đều hợp lệ.'))
            return
        for nhan, ma, ho_ten in khong_hop_le:
            self.stdout.write(f'- {nhan}: mã {ma!r} ({ho_ten})')
        self.stdout.write(
            'Cách sửa: tạo hồ sơ mới với mã hợp lệ (chuyển tài khoản, đăng ký, điểm sang hồ sơ mới) rồi xóa hồ sơ cũ, '
            'hoặc nhờ người quản trị CSDL đổi mã trong MySQL. Các trang danh sách vẫn hiển thị hồ sơ này nhưng '
            'không tạo liên kết theo mã.'
        )
        raise CommandError(f'Có {len(khong_hop_le)} mã hồ sơ không hợp lệ.')
