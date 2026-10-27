"""Rào chắn của nhà máy agent: quyết định agent AI được đọc/ghi tệp nào và nội dung nào bị chặn.

Thuần Python (không import Django) để dùng lại được ở hook pre-commit (nha_may_agent/quet_khoa.py).
Mọi thay đổi do agent đề xuất đều đi qua kiem_tra_ghi() TRƯỚC khi ghi; chỉ cần một tệp vi phạm là cả
lượt thay đổi bị từ chối (xem dieu_phoi.NhaMayAgent._kiem_tra_thay_doi).
"""
import re
from pathlib import Path, PurePosixPath

# Thư mục gốc agent được ghi: các app Django, template, prompt. Không có qldt/ (cấu hình), docs/,
# agents/, nha_may_agent/, .github/ ... và không có tệp ở thư mục gốc (manage.py, requirements.txt).
THU_MUC_DUOC_GHI = (
    'accounts', 'people', 'academics', 'classes', 'enrollment', 'grades', 'regulations', 'reports',
    'tien_do_hoc_tap', 'diem_danh', 'thong_bao', 'ai_core', 'tu_van_dang_ky', 'tom_tat_ket_qua',
    'hoi_dap_quy_che', 'templates', 'prompts',
)
DUOI_DUOC_GHI = {'.py', '.html', '.css', '.js', '.txt', '.md', '.json'}
KICH_THUOC_TOI_DA = 200_000  # ký tự mỗi tệp

# Không đưa nội dung các thư mục này vào prompt (bí mật, môi trường, dữ liệu người dùng, log).
THU_MUC_KHONG_DUOC_DOC = {'.git', 'venv', '.venv', 'media', 'logs', 'node_modules', '__pycache__'}
DUOI_KHONG_DUOC_DOC = {'.sqlite3', '.pyc', '.pyo', '.sql', '.pem', '.key'}

MAU_KHOA_API = [
    (re.compile(r'AIza[0-9A-Za-z_\-]{35}'), 'khóa Google API (AIza...)'),
    (re.compile(r'\bsk-ant-[0-9A-Za-z_\-]{20,}'), 'khóa Anthropic (sk-ant-...)'),
    (re.compile(r'\bsk-(?:proj-)?[0-9A-Za-z_\-]{20,}'), 'khóa OpenAI (sk-...)'),
    (re.compile(r'GEMINI_API_KEY\s*[=:]\s*["\']?[0-9A-Za-z_\-]{20,}'), 'giá trị GEMINI_API_KEY'),
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'), 'khóa riêng (private key)'),
]
MAU_HAM_TEST = re.compile(r'^\s*(?:async\s+)?def\s+test\w*\s*\(', re.M)


class ViPhamRaoChan(Exception):
    """Thao tác bị rào chắn từ chối; thông điệp an toàn để in và ghi nhật ký (không chứa nội dung tệp)."""


def tim_khoa_api(van_ban):
    """Trả (mô tả loại khóa, vị trí ký tự) của chuỗi đầu tiên giống khóa API, hoặc None."""
    for mau, mo_ta in MAU_KHOA_API:
        khop = mau.search(van_ban)
        if khop:
            return mo_ta, khop.start()
    return None


def la_tep_env(ten):
    ten = ten.lower()
    return ten == '.env' or (ten.startswith('.env.') and ten != '.env.example')


def chuan_hoa_duong_dan(goc, duong_dan):
    """Đổi đường dẫn agent đưa ra thành đường dẫn tương đối an toàn bên trong thư mục gốc."""
    if not isinstance(duong_dan, str) or not duong_dan.strip():
        raise ViPhamRaoChan('Đường dẫn tệp rỗng hoặc không phải chuỗi.')
    chuoi = duong_dan.strip().replace('\\', '/')
    if chuoi.startswith(('/', '~')) or re.match(r'^[A-Za-z]:', chuoi):
        raise ViPhamRaoChan(f'Không chấp nhận đường dẫn tuyệt đối: {chuoi}')
    tuong_doi = PurePosixPath(chuoi)
    if '..' in tuong_doi.parts:
        raise ViPhamRaoChan(f'Không chấp nhận ".." trong đường dẫn: {chuoi}')
    goc = Path(goc).resolve()
    tuyet_doi = (goc / tuong_doi).resolve()
    if goc != tuyet_doi and goc not in tuyet_doi.parents:
        raise ViPhamRaoChan(f'Đường dẫn trỏ ra ngoài thư mục dự án: {chuoi}')
    return tuong_doi


def _so_ham_test(van_ban):
    return len(MAU_HAM_TEST.findall(van_ban))


def kiem_tra_ghi(goc, duong_dan, noi_dung):
    """Kiểm tra một thay đổi tệp; hợp lệ thì trả đường dẫn tương đối (dạng a/b.py), không thì ném ViPhamRaoChan."""
    tuong_doi = chuan_hoa_duong_dan(goc, duong_dan)
    ten = tuong_doi.name
    if la_tep_env(ten):
        raise ViPhamRaoChan(f'Cấm ghi tệp bí mật {tuong_doi}.')
    if 'nha_may_agent' in tuong_doi.parts:
        raise ViPhamRaoChan(f'Cấm agent sửa chính nhà máy agent: {tuong_doi}.')
    if ten == 'settings.py':
        raise ViPhamRaoChan(f'Cấm agent sửa cấu hình {tuong_doi}.')
    if tuong_doi.parts[0] not in THU_MUC_DUOC_GHI:
        raise ViPhamRaoChan(
            f'{tuong_doi} nằm ngoài các thư mục được ghi ({", ".join(THU_MUC_DUOC_GHI)}).'
        )
    if tuong_doi.suffix.lower() not in DUOI_DUOC_GHI:
        raise ViPhamRaoChan(f'Không cho ghi tệp đuôi "{tuong_doi.suffix}": {tuong_doi}.')
    tep = Path(goc) / tuong_doi
    if 'migrations' in tuong_doi.parts and tep.exists():
        raise ViPhamRaoChan(f'Cấm sửa migration đã có: {tuong_doi}. Thay đổi CSDL phải bằng migration mới.')
    if not isinstance(noi_dung, str):
        raise ViPhamRaoChan(f'Nội dung tệp {tuong_doi} không phải chuỗi.')
    if len(noi_dung) > KICH_THUOC_TOI_DA:
        raise ViPhamRaoChan(f'Tệp {tuong_doi} quá lớn ({len(noi_dung)} ký tự, tối đa {KICH_THUOC_TOI_DA}).')
    khoa = tim_khoa_api(noi_dung)
    if khoa:
        raise ViPhamRaoChan(f'Nội dung {tuong_doi} có chuỗi giống {khoa[0]}; không ghi khóa vào mã nguồn.')
    if (ten == 'tests.py' or ten.startswith('tests_')) and tep.is_file():
        so_cu = _so_ham_test(tep.read_text(encoding='utf-8', errors='replace'))
        so_moi = _so_ham_test(noi_dung)
        if so_moi < so_cu:
            raise ViPhamRaoChan(f'Thay đổi làm giảm số test trong {tuong_doi} ({so_cu} → {so_moi}); không được xóa test.')
    return tuong_doi.as_posix()


def kiem_tra_doc(goc, duong_dan):
    """Tệp agent muốn xem làm ngữ cảnh: trả đường dẫn tuyệt đối nếu được phép đọc, không thì ném ViPhamRaoChan."""
    tuong_doi = chuan_hoa_duong_dan(goc, duong_dan)
    if la_tep_env(tuong_doi.name):
        raise ViPhamRaoChan(f'Cấm đưa tệp bí mật {tuong_doi} vào prompt.')
    if THU_MUC_KHONG_DUOC_DOC & set(tuong_doi.parts):
        raise ViPhamRaoChan(f'Không đọc tệp trong thư mục bị loại trừ: {tuong_doi}.')
    if tuong_doi.suffix.lower() in DUOI_KHONG_DUOC_DOC:
        raise ViPhamRaoChan(f'Không đọc tệp loại "{tuong_doi.suffix}": {tuong_doi}.')
    tep = Path(goc) / tuong_doi
    if not tep.is_file():
        raise ViPhamRaoChan(f'Không có tệp {tuong_doi}.')
    return tep
