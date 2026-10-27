from collections import defaultdict

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts.forms import validate_so_dien_thoai
from people.lien_he import chuan_hoa_so_dien_thoai
from people.models import CoVanHocTap, GiangVien, SinhVien


def _hop_le(validator, gia_tri):
    try:
        validator(gia_tri)
    except ValidationError:
        return False
    return True


class Command(BaseCommand):
    help = (
        'Liệt kê hồ sơ sinh viên/giảng viên/cố vấn học tập (dữ liệu cũ) có email sai định dạng, email trùng, '
        'số điện thoại sai định dạng hoặc trùng, để Phòng Đào tạo sửa tay. Chỉ đọc, không sửa dữ liệu. '
        'Thoát mã 1 nếu có vấn đề.'
    )

    def handle(self, *args, **options):
        sai_email, sai_sdt = [], []
        theo_email, theo_sdt = defaultdict(list), defaultdict(list)
        for model, nhan in ((SinhVien, 'Sinh viên'), (GiangVien, 'Giảng viên'), (CoVanHocTap, 'Cố vấn học tập')):
            for ho_so in model.objects.order_by('pk').only('pk', 'ho_ten', 'email', 'so_dien_thoai'):
                mo_ta = f'{nhan} {ho_so.pk} ({ho_so.ho_ten})'
                email = (ho_so.email or '').strip()
                sdt = chuan_hoa_so_dien_thoai(ho_so.so_dien_thoai)
                if not _hop_le(validate_email, email):
                    sai_email.append(f'{mo_ta}: email {ho_so.email!r}')
                elif email:
                    theo_email[email.lower()].append(mo_ta)
                if not _hop_le(validate_so_dien_thoai, sdt):
                    sai_sdt.append(f'{mo_ta}: số điện thoại {ho_so.so_dien_thoai!r}')
                elif sdt:
                    theo_sdt[sdt].append(mo_ta)

        nhom = [
            ('Email sai định dạng', sai_email),
            ('Email trùng', [f'{k}: {", ".join(v)}' for k, v in sorted(theo_email.items()) if len(v) > 1]),
            ('Số điện thoại sai định dạng', sai_sdt),
            ('Số điện thoại trùng', [f'{k}: {", ".join(v)}' for k, v in sorted(theo_sdt.items()) if len(v) > 1]),
        ]
        tong = sum(len(ds) for _, ds in nhom)
        if not tong:
            self.stdout.write(self.style.SUCCESS('Mọi email và số điện thoại đều hợp lệ, không trùng.'))
            return
        for tieu_de, ds in nhom:
            if ds:
                self.stdout.write(f'{tieu_de} ({len(ds)}):')
                for dong in ds:
                    self.stdout.write(f'- {dong}')
        self.stdout.write(
            'Cách sửa: Phòng Đào tạo mở trang sửa hồ sơ tương ứng và nhập lại email/số điện thoại đúng '
            '(email dạng ten@gmail.com, số điện thoại 10 chữ số bắt đầu bằng 0, không trùng hồ sơ khác).'
        )
        raise CommandError(f'Có {tong} vấn đề về email/số điện thoại.')
