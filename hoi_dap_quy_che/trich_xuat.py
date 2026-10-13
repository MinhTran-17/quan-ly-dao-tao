import os

import pypdf
from docx import Document as TepDocx


def _trich_tu_pdf(tep):
    doc = pypdf.PdfReader(tep)
    return '\n'.join(trang.extract_text() or '' for trang in doc.pages)


def _trich_tu_docx(tep):
    doc = TepDocx(tep)
    return '\n'.join(doan.text for doan in doc.paragraphs)


def trich_van_ban(duong_dan_file):
    """Trích văn bản thuần từ một FileField (PDF hoặc DOCX).

    Không phụ thuộc model Django nào — chỉ cần một FieldFile (hoặc đối tượng có .open()
    và .name) — để regulations/views.py và hoi_dap_quy_che/chi_muc.py đều gọi được mà
    không tạo phụ thuộc vòng giữa hai app.

    Trả về chuỗi rỗng nếu không trích được (tệp hỏng, PDF ảnh quét không có lớp chữ...),
    không bao giờ raise ra ngoài.
    """
    duoi = os.path.splitext(duong_dan_file.name)[1].lower()
    try:
        with duong_dan_file.open('rb') as tep:
            if duoi == '.pdf':
                return _trich_tu_pdf(tep)
            if duoi == '.docx':
                return _trich_tu_docx(tep)
    except Exception:
        return ''
    return ''
