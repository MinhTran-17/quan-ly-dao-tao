import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import TaiKhoan, VaiTro


class Command(BaseCommand):
    help = (
        'Tạo tài khoản Phòng Đào tạo đầu tiên. '
        'Mật khẩu được hỏi qua getpass, không nhận qua tham số dòng lệnh.'
    )

    def add_arguments(self, parser):
        parser.add_argument('ten_dang_nhap', type=str, help='Tên đăng nhập của tài khoản Phòng Đào tạo')

    def handle(self, *args, **options):
        ten_dang_nhap = options['ten_dang_nhap'].strip()
        if not ten_dang_nhap:
            raise CommandError('Tên đăng nhập không được để trống.')
        if TaiKhoan.objects.filter(ten_dang_nhap=ten_dang_nhap).exists():
            raise CommandError(f'Tên đăng nhập "{ten_dang_nhap}" đã tồn tại.')

        mat_khau = getpass.getpass('Mật khẩu: ')
        xac_nhan = getpass.getpass('Nhập lại mật khẩu: ')
        if mat_khau != xac_nhan:
            raise CommandError('Hai lần nhập mật khẩu không khớp.')

        try:
            validate_password(mat_khau)
        except ValidationError as loi:
            raise CommandError('\n'.join(loi.messages))

        TaiKhoan.objects.create_user(
            ten_dang_nhap=ten_dang_nhap,
            vai_tro=VaiTro.PHONG_DAO_TAO,
            password=mat_khau,
        )
        self.stdout.write(self.style.SUCCESS(f'Đã tạo tài khoản Phòng Đào tạo "{ten_dang_nhap}".'))
