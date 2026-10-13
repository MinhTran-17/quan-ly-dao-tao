import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models

DUOI_HOP_LE = {'.pdf', '.docx'}
DUNG_LUONG_TOI_DA = 10 * 1024 * 1024  # 10 MB

# Chữ ký byte đầu tệp (magic bytes) tương ứng từng đuôi hợp lệ — PDF luôn bắt đầu bằng
# "%PDF", DOCX là tệp ZIP (Office Open XML) nên bắt đầu bằng chữ ký ZIP "PK\x03\x04".
# Chỉ kiểm tra đuôi tên tệp là chưa đủ: ai đó có thể đổi tên một tệp bất kỳ thành .pdf/.docx
# để vượt qua kiểm tra rồi được Phòng Đào tạo tải lên/hệ thống trích xuất xử lý.
_CHU_KY_THEO_DUOI = {
    '.pdf': (b'%PDF',),
    '.docx': (b'PK\x03\x04',),
}


def validate_tai_lieu_file(tep):
    duoi = os.path.splitext(tep.name)[1].lower()
    if duoi not in DUOI_HOP_LE:
        raise ValidationError('Chỉ chấp nhận tệp PDF hoặc DOCX.')
    if tep.size > DUNG_LUONG_TOI_DA:
        raise ValidationError('Dung lượng tệp không được vượt quá 10 MB.')
    vi_tri_ban_dau = tep.tell()
    dau_tep = tep.read(4)
    tep.seek(vi_tri_ban_dau)
    if not any(dau_tep.startswith(chu_ky) for chu_ky in _CHU_KY_THEO_DUOI[duoi]):
        raise ValidationError('Nội dung tệp không đúng định dạng PDF/DOCX (có thể đã đổi đuôi tệp).')


def duong_dan_tai_len(instance, ten_file_goc):
    duoi = os.path.splitext(ten_file_goc)[1].lower()
    return os.path.join('quy_che', f'{uuid.uuid4().hex}{duoi}')


class TaiLieuQuyChe(models.Model):
    ma_tai_lieu = models.AutoField(primary_key=True)
    ten_tai_lieu = models.CharField(max_length=200)
    duong_dan_file = models.FileField(
        upload_to=duong_dan_tai_len, max_length=255, validators=[validate_tai_lieu_file],
    )
    ngay_tai_len = models.DateField()
    ngay_cap_nhat = models.DateField()

    class Meta:
        db_table = 'tai_lieu_quy_che'

    def __str__(self):
        return self.ten_tai_lieu
