from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ai_core.exceptions import LoiAI
from nha_may_agent.dieu_phoi import NhaMayAgent, ghi_nhat_ky, mo_ta_chi_tiet, mo_ta_ket_qua, tao_client


class Command(BaseCommand):
    help = (
        'Chạy nhà máy agent bằng Gemini cho một yêu cầu: phân tích → người duyệt đặc tả → lập trình → '
        'kiểm thử viên viết test → người duyệt diff → ghi tệp, chạy test (sửa tối đa 2 vòng) → review + '
        'kiểm tra bảo mật → ghi docs/ai-log.md. Không commit, không push.'
    )

    def add_arguments(self, parser):
        parser.add_argument('yeu_cau', help='Mô tả yêu cầu (đặt trong ngoặc kép).')
        parser.add_argument(
            '--chay-thu', action='store_true', dest='chay_thu',
            help='Chạy thử: chỉ in đặc tả và diff đề xuất, không ghi tệp nào, không chạy test, không ghi nhật ký.',
        )
        parser.add_argument(
            '--chi-tiet', '--chi_tiet', action='store_true', dest='chi_tiet',
            help=(
                'In thêm chẩn đoán: cấu hình nhà máy, độ dài prompt và thời gian từng lượt gọi AI; khi lỗi AI thì in '
                'loại lỗi gốc, mã HTTP, thông điệp API (giống kiem_tra_ai --chi_tiet). Không bao giờ in khóa API.'
            ),
        )
        parser.add_argument(
            '--so-luot-toi-da', type=int, default=None, dest='so_luot_toi_da',
            help=f'Số lượt gọi AI tối đa cho lần chạy này (mặc định {settings.NHA_MAY_SO_LUOT_AI_TOI_DA}).',
        )

    def handle(self, *args, **options):
        yeu_cau = options['yeu_cau'].strip()
        if not yeu_cau:
            raise CommandError('Yêu cầu rỗng.')
        if options['so_luot_toi_da'] is not None and options['so_luot_toi_da'] < 1:
            raise CommandError('--so-luot-toi-da phải lớn hơn 0.')
        try:
            client = tao_client()
        except LoiAI as loi:
            raise CommandError(str(loi)) from loi

        nha_may = NhaMayAgent(
            client=client,
            hoi=lambda cau_hoi: input(cau_hoi),
            in_ra=self.stdout.write,
            so_luot_toi_da=options['so_luot_toi_da'],
            chay_thu=options['chay_thu'],
        )
        ket_qua = nha_may.chay(yeu_cau)

        self.stdout.write('===== BÁO CÁO =====')
        self.stdout.write('\n'.join(mo_ta_ket_qua(ket_qua)))
        if options['chi_tiet']:
            self.stdout.write('\n'.join(mo_ta_chi_tiet(ket_qua, client)))
        if ket_qua.trang_thai == 'chay_thu':
            self.stdout.write('Chạy thử: không ghi tệp nào, không ghi nhật ký.')
            return
        duong_dan_nhat_ky = settings.BASE_DIR / 'docs' / 'ai-log.md'
        ghi_nhat_ky(duong_dan_nhat_ky, ket_qua)
        self.stdout.write(self.style.SUCCESS(f'Đã ghi nhật ký vào {duong_dan_nhat_ky.relative_to(settings.BASE_DIR)}.'))
