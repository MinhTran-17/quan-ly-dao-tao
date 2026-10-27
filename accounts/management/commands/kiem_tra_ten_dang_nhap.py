from django.core.management.base import BaseCommand, CommandError

from accounts.forms import ten_dang_nhap_hop_le
from accounts.models import TaiKhoan


class Command(BaseCommand):
    help = (
        'Báo các tài khoản cũ có tên đăng nhập sai quy tắc (chỉ được chữ cái không dấu, chữ số, dấu gạch dưới). '
        'Chỉ đọc, không sửa dữ liệu. Thoát mã 1 nếu có tên không hợp lệ.'
    )

    def handle(self, *args, **options):
        khong_hop_le = [
            (ten, vai_tro) for ten, vai_tro in TaiKhoan.objects.order_by('ten_dang_nhap').values_list('ten_dang_nhap', 'vai_tro')
            if not ten_dang_nhap_hop_le(ten)
        ]
        if not khong_hop_le:
            self.stdout.write(self.style.SUCCESS('Mọi tên đăng nhập đều hợp lệ.'))
            return
        for ten, vai_tro in khong_hop_le:
            self.stdout.write(f'- {ten!r} (vai trò {vai_tro})')
        self.stdout.write(
            'Các tài khoản này vẫn đăng nhập được. Cách sửa: Phòng Đào tạo vào Tài khoản > Sửa, đổi sang tên hợp lệ '
            'rồi báo người dùng tên đăng nhập mới.'
        )
        raise CommandError(f'Có {len(khong_hop_le)} tên đăng nhập không hợp lệ.')
