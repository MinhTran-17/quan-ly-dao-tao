import time
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings

from hoi_dap_quy_che.chi_muc import truy_hoi
from hoi_dap_quy_che.services import hoi_dap_quy_che

DUONG_DAN_MAC_DINH = 'docs/ca_thu_ai/hoi_dap_quy_che.md'
KHOANG_CACH_GIAY_MAC_DINH = 15


def _doc_bang_cau_hoi(duong_dan):
    """Đọc cột "Câu hỏi" trong bảng Markdown của tệp ca thử. Không phụ thuộc thư viện
    phân tích Markdown ngoài — chỉ cần tìm đúng cột theo tên tiêu đề, đủ dùng cho một
    bảng đơn giản như docs/ca_thu_ai/hoi_dap_quy_che.md."""
    dong_bang = [dong for dong in duong_dan.read_text(encoding='utf-8').splitlines() if dong.strip().startswith('|')]
    if len(dong_bang) < 3:
        return []
    tieu_de = [o.strip() for o in dong_bang[0].strip().strip('|').split('|')]
    try:
        chi_so_cau_hoi = next(i for i, ten in enumerate(tieu_de) if 'câu hỏi' in ten.lower())
    except StopIteration:
        return []
    cau_hoi = []
    for dong in dong_bang[2:]:  # bỏ dòng tiêu đề và dòng phân cách (|---|---|...)
        cot = [o.strip() for o in dong.strip().strip('|').split('|')]
        if len(cot) > chi_so_cau_hoi and cot[chi_so_cau_hoi]:
            cau_hoi.append(cot[chi_so_cau_hoi])
    return cau_hoi


def _phan_tich_danh_sach_cau(gia_tri, tong_so):
    """Phân tích --cau ("3,4,8") thành list số thứ tự (1-based), theo đúng thứ tự người
    dùng nhập. None/rỗng nghĩa là chạy tất cả, theo thứ tự trong tệp."""
    if not gia_tri:
        return list(range(1, tong_so + 1))
    ket_qua = []
    for phan in gia_tri.split(','):
        phan = phan.strip()
        if not phan.isdigit():
            raise CommandError(f'Giá trị --cau không hợp lệ: "{phan}" (phải là số nguyên dương).')
        so = int(phan)
        if not (1 <= so <= tong_so):
            raise CommandError(f'Giá trị --cau không hợp lệ: {so} (tệp chỉ có {tong_so} câu hỏi).')
        ket_qua.append(so)
    return ket_qua


class Command(BaseCommand):
    help = (
        'Chạy bộ câu hỏi thử trong docs/ca_thu_ai/hoi_dap_quy_che.md qua luồng truy hồi '
        '(mặc định) hoặc qua AI thật (--ai), in kết quả để đối chiếu.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--ai', action='store_true',
            help='Gọi AI thật cho từng câu hỏi (mặc định chỉ chạy truy hồi, không tốn quota).',
        )
        parser.add_argument(
            '--tep', default=DUONG_DAN_MAC_DINH,
            help=f'Đường dẫn tệp chứa bảng câu hỏi (mặc định {DUONG_DAN_MAC_DINH}).',
        )
        parser.add_argument(
            '--cau', default=None,
            help='Chỉ chạy các câu có số thứ tự này (bắt đầu từ 1), cách nhau bằng dấu phẩy, '
                 'ví dụ --cau 3,4,8 (mặc định: chạy tất cả).',
        )
        parser.add_argument(
            '--khoang_cach', type=float, default=KHOANG_CACH_GIAY_MAC_DINH,
            help=f'Số giây chờ giữa hai lần gọi AI liên tiếp khi dùng --ai (mặc định {KHOANG_CACH_GIAY_MAC_DINH}).',
        )
        parser.add_argument(
            '--chi_tiet', action='store_true',
            help=(
                'Khi một câu bị lỗi AI, in thêm loại lỗi gốc, mã HTTP, thông điệp lỗi do API '
                'trả về, số ký tự prompt đã gửi và tên model (không bao giờ in khóa API).'
            ),
        )
        parser.add_argument(
            '--phien_ban_prompt', default=None,
            help='Ghi đè AI_PHIEN_BAN_QUY_CHE chỉ cho lần chạy này (không đổi .env/settings lâu dài).',
        )
        parser.add_argument(
            '--ghi_vao', default=None,
            help='Đường dẫn tệp để NỐI (append) kết quả lần chạy này vào, kèm tiêu đề '
                 '(ngày giờ, phiên bản prompt/truy hồi, ngưỡng điểm, model thực tế, danh sách câu).',
        )
        parser.add_argument(
            '--yes', action='store_true',
            help='Bỏ qua xác nhận (y/n) trước khi gọi AI thật (mặc định luôn hỏi khi dùng --ai).',
        )

    def handle(self, *args, **options):
        duong_dan = Path(options['tep'])
        if not duong_dan.is_absolute():
            duong_dan = Path(settings.BASE_DIR) / duong_dan
        if not duong_dan.exists():
            raise CommandError(f'Không tìm thấy tệp "{duong_dan}".')

        danh_sach_cau_hoi = _doc_bang_cau_hoi(duong_dan)
        if not danh_sach_cau_hoi:
            raise CommandError(f'Không đọc được câu hỏi nào từ bảng trong "{duong_dan}".')

        chi_so_can_chay = _phan_tich_danh_sach_cau(options['cau'], len(danh_sach_cau_hoi))

        phien_ban_prompt = options['phien_ban_prompt']
        if phien_ban_prompt:
            thu_muc_prompt = settings.AI_PROMPTS_DIR / 'hoi_dap_quy_che' / phien_ban_prompt
            if not (thu_muc_prompt / 'system.txt').exists() or not (thu_muc_prompt / 'user.txt').exists():
                raise CommandError(f'Không tìm thấy prompt hoi_dap_quy_che phiên bản "{phien_ban_prompt}".')

        quan_ly_phien_ban_prompt = (
            override_settings(AI_PHIEN_BAN_QUY_CHE=phien_ban_prompt) if phien_ban_prompt else nullcontext()
        )
        with quan_ly_phien_ban_prompt:
            self._chay(options, duong_dan, danh_sach_cau_hoi, chi_so_can_chay)

    def _chay(self, options, duong_dan, danh_sach_cau_hoi, chi_so_can_chay):
        cac_dong_ghi = [] if options['ghi_vao'] else None

        def ghi(dong='', kieu=None):
            self.stdout.write(kieu(dong) if kieu else dong)
            if cac_dong_ghi is not None:
                cac_dong_ghi.append(dong)

        ghi(f'Đọc được {len(danh_sach_cau_hoi)} câu hỏi từ "{duong_dan}".')
        if options['cau']:
            ghi(f'Chỉ chạy câu: {", ".join(str(i) for i in chi_so_can_chay)}.')
        if options['phien_ban_prompt']:
            ghi(f'Ghi đè phiên bản prompt (chỉ lần chạy này): {settings.AI_PHIEN_BAN_QUY_CHE}')

        # Truy hồi trước cho mọi câu đã chọn — dùng lại kết quả này cho cả phần đếm số
        # lượt gọi AI dự kiến lẫn vòng lặp chính, tránh tính lại BM25 hai lần một câu.
        du_lieu_theo_cau = {i: truy_hoi(danh_sach_cau_hoi[i - 1]) for i in chi_so_can_chay}

        if options['ai']:
            so_luot_du_kien = sum(1 for i in chi_so_can_chay if du_lieu_theo_cau[i])
            ghi(
                f'Chế độ --ai: dự kiến gọi AI thật cho {so_luot_du_kien}/{len(chi_so_can_chay)} câu '
                f'(có đoạn đạt ngưỡng điểm), tốn quota API '
                f'(khoảng cách giữa các lần gọi: {options["khoang_cach"]}s).',
                self.style.WARNING,
            )
            if so_luot_du_kien > 0 and not options['yes']:
                tra_loi_xac_nhan = input('Tiếp tục gọi AI thật? (y/n): ').strip().lower()
                if tra_loi_xac_nhan not in ('y', 'yes'):
                    ghi('Đã hủy, không gọi AI.')
                    return
        ghi()

        da_chay = []
        so_co_tra_loi = 0
        so_loi_ai = 0
        so_khong_goi_ai = 0
        bi_gioi_han_tan_suat = False
        pham_vi_gioi_han = None  # 'ngay', 'phut', hoặc None (không xác định) khi bi_gioi_han_tan_suat
        model_thuc_te_ghi_nhan = None

        for vi_tri, i in enumerate(chi_so_can_chay):
            cau_hoi = danh_sach_cau_hoi[i - 1]
            ghi(f'Câu {i}: {cau_hoi}', self.style.MIGRATE_HEADING)
            doan_truy_hoi = du_lieu_theo_cau[i]
            if not doan_truy_hoi:
                ghi('  (Không truy hồi được đoạn nào đạt ngưỡng điểm — sẽ không gọi AI.)')
            else:
                for doan, diem in doan_truy_hoi:
                    khoan_text = f', khoản {doan["khoan"]}' if doan['khoan'] else ''
                    ghi(
                        f"  - [{diem:.3f}] {doan['ten_tai_lieu']} - Điều {doan['dieu']}{khoan_text} "
                        f"({len(doan['noi_dung'])} ký tự)"
                    )

            da_chay.append(i)

            if options['ai']:
                if not doan_truy_hoi:
                    so_khong_goi_ai += 1
                else:
                    ket_qua = hoi_dap_quy_che(cau_hoi)
                    if ket_qua.model_thuc_te and not model_thuc_te_ghi_nhan:
                        model_thuc_te_ghi_nhan = ket_qua.model_thuc_te
                    if ket_qua.loi_ai:
                        so_loi_ai += 1
                        ghi(f'  Lỗi AI: {ket_qua.loi_ai}', self.style.ERROR)
                        if options['chi_tiet']:
                            chi_tiet = ket_qua.chi_tiet_loi_ai
                            if chi_tiet:
                                ghi(f"    Loại lỗi gốc: {chi_tiet.get('loai')}")
                                ghi(f"    Mã HTTP: {chi_tiet.get('ma_http')}")
                                ghi(f"    Thông điệp từ API: {chi_tiet.get('thong_diep')}")
                            else:
                                ghi('    (Không có thêm chi tiết cho loại lỗi này.)')
                            ghi(f'    Số ký tự prompt đã gửi: {ket_qua.do_dai_prompt}')
                            ghi(f'    Model: {settings.GEMINI_MODEL}')
                        if ket_qua.loai_loi_ai == 'QuaGioiHanTanSuatAI':
                            bi_gioi_han_tan_suat = True
                            pham_vi_gioi_han = ket_qua.pham_vi_gioi_han_tan_suat
                    else:
                        so_co_tra_loi += 1
                        ghi(f'  Trả lời: {ket_qua.tra_loi}')
                        for nguon in ket_qua.nguon:
                            khoan_text = f", khoản {nguon['khoan']}" if nguon['khoan'] else ''
                            ghi(f"    Nguồn: {nguon['ten_tai_lieu']} - Điều {nguon['dieu']}{khoan_text}")
                        for gc in ket_qua.ghi_chu_loc:
                            ghi(f'  {gc}', self.style.WARNING)

                    if not bi_gioi_han_tan_suat and vi_tri < len(chi_so_can_chay) - 1:
                        time.sleep(options['khoang_cach'])

                if bi_gioi_han_tan_suat:
                    ghi()
                    if pham_vi_gioi_han == 'ngay':
                        thong_bao_dung = (
                            'Đã hết hạn mức hôm nay, thử lại sau khi hạn mức được đặt lại — '
                            'DỪNG HẲN, không chạy tiếp các câu còn lại.'
                        )
                    elif pham_vi_gioi_han == 'phut':
                        thong_bao_dung = (
                            'Vượt tần suất theo phút (429) — DỪNG HẲN, không chạy tiếp các câu còn lại.'
                        )
                    else:
                        thong_bao_dung = (
                            'Bị giới hạn tần suất (429, không xác định rõ theo ngày hay theo phút) — '
                            'DỪNG HẲN, không chạy tiếp các câu còn lại.'
                        )
                    ghi(thong_bao_dung, self.style.ERROR)
                    break

            ghi()

        if options['ai']:
            chua_chay = [i for i in chi_so_can_chay if i not in da_chay]
            ghi(f'Đã chạy: {", ".join(str(i) for i in da_chay) if da_chay else "(không có)"}')
            ghi(f'Chưa chạy: {", ".join(str(i) for i in chua_chay) if chua_chay else "(không có)"}')
            ghi()
            ghi('Tổng kết:', self.style.MIGRATE_HEADING)
            ghi(f'  Số câu có trả lời: {so_co_tra_loi}')
            ghi(f'  Số câu lỗi AI: {so_loi_ai}')
            ghi(f'  Số câu không gọi AI (không truy hồi được đoạn nào): {so_khong_goi_ai}')
            ghi()

        if bi_gioi_han_tan_suat:
            if pham_vi_gioi_han == 'ngay':
                ghi('Dừng sớm: đã hết hạn mức hôm nay, thử lại sau khi hạn mức được đặt lại.', self.style.WARNING)
            elif pham_vi_gioi_han == 'phut':
                ghi('Dừng sớm do vượt tần suất theo phút.', self.style.WARNING)
            else:
                ghi('Dừng sớm do bị giới hạn tần suất.', self.style.WARNING)
        else:
            ghi('Hoàn tất.', self.style.SUCCESS)

        if cac_dong_ghi is not None:
            self._ghi_vao_tep(options['ghi_vao'], da_chay, model_thuc_te_ghi_nhan, cac_dong_ghi)

    def _ghi_vao_tep(self, duong_dan_str, da_chay, model_thuc_te, cac_dong):
        duong_dan = Path(duong_dan_str)
        if not duong_dan.is_absolute():
            duong_dan = Path(settings.BASE_DIR) / duong_dan
        dau_de = [
            f'=== Chạy lúc {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===',
            f'Phiên bản prompt (AI_PHIEN_BAN_QUY_CHE): {settings.AI_PHIEN_BAN_QUY_CHE}',
            f'Phiên bản truy hồi (AI_TRUY_HOI_PHIEN_BAN): {settings.AI_TRUY_HOI_PHIEN_BAN}',
            f'Ngưỡng điểm truy hồi (AI_NGUONG_DIEM_TRUY_HOI): {settings.AI_NGUONG_DIEM_TRUY_HOI}',
            f'Model thực tế API trả về: {model_thuc_te or "(không có)"}',
            f'Danh sách câu đã chạy: {", ".join(str(i) for i in da_chay) if da_chay else "(không có)"}',
            '',
        ]
        duong_dan.parent.mkdir(parents=True, exist_ok=True)
        with duong_dan.open('a', encoding='utf-8') as tep:
            tep.write('\n'.join(dau_de + cac_dong) + '\n\n')
        self.stdout.write(self.style.SUCCESS(f'Đã ghi kết quả vào "{duong_dan}".'))
