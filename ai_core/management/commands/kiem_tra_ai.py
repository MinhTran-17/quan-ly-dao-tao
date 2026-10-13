from django.core.management.base import BaseCommand

from ai_core.clients import lay_client_ai
from ai_core.exceptions import LoiAI
from ai_core.prompts import KhongTimThayPrompt, nap_prompt


class Command(BaseCommand):
    help = (
        'Kiểm tra khóa API và kết nối tới dịch vụ AI bằng một câu chào không chứa dữ '
        'liệu người dùng. Không bao giờ in hoặc ghi log khóa API.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--chi_tiet', action='store_true',
            help=(
                'Khi thất bại, in thêm loại lỗi gốc, mã HTTP và thông điệp lỗi do API '
                'trả về (không bao giờ in khóa API).'
            ),
        )

    def handle(self, *args, **options):
        try:
            he_thong, nguoi_dung = nap_prompt('kiem_tra_ket_noi', 'v1')
            client = lay_client_ai()
            ket_qua = client.sinh_noi_dung(he_thong=he_thong, nguoi_dung=nguoi_dung)
        except (LoiAI, KhongTimThayPrompt) as loi:
            self.stderr.write(self.style.ERROR(f'Kết nối AI thất bại: {loi}'))
            if options['chi_tiet']:
                chi_tiet = getattr(loi, 'chi_tiet', None)
                if chi_tiet:
                    self.stderr.write(f"  Loại lỗi gốc: {chi_tiet.get('loai')}")
                    self.stderr.write(f"  Mã HTTP: {chi_tiet.get('ma_http')}")
                    self.stderr.write(f"  Thông điệp từ API: {chi_tiet.get('thong_diep')}")
                else:
                    self.stderr.write('  (Không có thêm chi tiết cho loại lỗi này.)')
            return

        self.stdout.write(self.style.SUCCESS('Kết nối AI thành công.'))
        self.stdout.write(f'Phản hồi: {ket_qua}')
        model_thuc_te = getattr(client, 'model_version_thuc_te', None)
        if model_thuc_te:
            self.stdout.write(f'Model thực tế API trả về: {model_thuc_te}')
