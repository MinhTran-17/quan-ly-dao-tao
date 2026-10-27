from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts.gui_email import che_email, logger, mo_ta_loi_gui_thu

_CONSOLE = 'django.core.mail.backends.console.EmailBackend'


class Command(BaseCommand):
    help = (
        'Gửi một thư thử tới <địa_chỉ> bằng cấu hình email đang chạy (đọc từ .env), in rõ thành công hay loại lỗi '
        'SMTP. Không in mật khẩu. Thoát mã 1 nếu gửi lỗi.'
    )

    def add_arguments(self, parser):
        parser.add_argument('dia_chi', help='Địa chỉ email nhận thư thử')

    def handle(self, *args, **options):
        dia_chi = options['dia_chi'].strip()
        try:
            validate_email(dia_chi)
        except ValidationError:
            raise CommandError(f'Địa chỉ "{dia_chi}" không đúng định dạng email.')

        self.stdout.write('Cấu hình email đang dùng:')
        self.stdout.write(f'  EMAIL_BACKEND       = {settings.EMAIL_BACKEND}')
        if settings.EMAIL_BACKEND != _CONSOLE:
            self.stdout.write(f'  EMAIL_HOST          = {settings.EMAIL_HOST}:{settings.EMAIL_PORT} '
                              f'(EMAIL_USE_TLS={settings.EMAIL_USE_TLS}, EMAIL_TIMEOUT={settings.EMAIL_TIMEOUT} giây)')
        self.stdout.write(f'  EMAIL_HOST_USER     = {settings.EMAIL_HOST_USER or "(trống)"}')
        self.stdout.write(f'  EMAIL_HOST_PASSWORD = {"(đã đặt, không hiển thị)" if settings.EMAIL_HOST_PASSWORD else "(trống)"}')
        self.stdout.write(f'  DEFAULT_FROM_EMAIL  = {settings.DEFAULT_FROM_EMAIL}')

        if settings.EMAIL_BACKEND == _CONSOLE:
            self.stdout.write(self.style.WARNING(
                'Chưa cấu hình Gmail (EMAIL_HOST_USER/EMAIL_HOST_PASSWORD trống): thư KHÔNG được gửi thật, chỉ in ra '
                'màn hình bên dưới. Điền hai biến này vào .env rồi chạy lại docker compose up -d.'
            ))

        thu = EmailMessage(
            subject=f'[{settings.TEN_HE_THONG}] Thư thử cấu hình email',
            body='Đây là thư thử từ lệnh thu_gui_email. Nhận được thư này nghĩa là cấu hình gửi thư đã đúng.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[dia_chi],
        )
        try:
            thu.send()
        except Exception as loi:
            logger.warning('Thư thử: lỗi gửi thư tới %s: %s', che_email(dia_chi), mo_ta_loi_gui_thu(loi))
            raise CommandError(f'Gửi thư thất bại: {mo_ta_loi_gui_thu(loi)}')
        logger.info('Thư thử: đã gửi thư tới %s.', che_email(dia_chi))
        if settings.EMAIL_BACKEND == _CONSOLE:
            self.stdout.write(self.style.WARNING('Đã in thư ra màn hình (không gửi thật).'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Máy chủ SMTP đã nhận thư gửi tới {dia_chi}. Kiểm tra hộp thư đến và thư mục Spam.'
            ))
