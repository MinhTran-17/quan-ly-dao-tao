from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font


def _an_toan(gia_tri):
    if isinstance(gia_tri, str):
        return ILLEGAL_CHARACTERS_RE.sub('', gia_tri)
    return gia_tri


def tao_workbook_excel(ten_sheet, tieu_de_cot, cac_dong):
    """Tạo một workbook một sheet, dòng đầu là tiêu đề cột in đậm — dùng chung cho mọi
    chức năng xuất Excel trong dự án (không phụ thuộc app nghiệp vụ nào)."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = ten_sheet
    sheet.append(list(tieu_de_cot))
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for dong in cac_dong:
        sheet.append([_an_toan(gia_tri) for gia_tri in dong])
    return workbook


def phan_hoi_excel(workbook, ten_file):
    """Đưa workbook vào HttpResponse tải về dạng .xlsx."""
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{ten_file}"'
    return response
