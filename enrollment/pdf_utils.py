import os
from io import BytesIO

from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Font DejaVu Sans (hỗ trợ đủ dấu tiếng Việt) — bundle riêng trong thư mục này (xem
# docs/erd.md, lượt 5/6). Dùng chung cho mọi PDF trong dự án, không nhân bản font ở app khác.
_THU_MUC_FONT = os.path.join(settings.BASE_DIR, 'enrollment', 'fonts')
_DA_DANG_KY_FONT = False


def dam_bao_font_dejavu():
    global _DA_DANG_KY_FONT
    if not _DA_DANG_KY_FONT:
        pdfmetrics.registerFont(TTFont('DejaVuSans', os.path.join(_THU_MUC_FONT, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', os.path.join(_THU_MUC_FONT, 'DejaVuSans-Bold.ttf')))
        _DA_DANG_KY_FONT = True


_CO_CHU_NHO_NHAT = 7
_KHOANG_CACH_COT = 0.2 * cm


def vua_cot(chu, ten_font, co_chu, do_rong_toi_da):
    """Trả về (chuỗi, cỡ chữ) sao cho chuỗi không rộng quá do_rong_toi_da (point).

    Thu nhỏ cỡ chữ dần tới _CO_CHU_NHO_NHAT; vẫn không vừa thì cắt bớt và thêm "…",
    để chữ không bao giờ tràn sang cột bên cạnh.
    """
    chu = str(chu)
    co = co_chu
    while co > _CO_CHU_NHO_NHAT and pdfmetrics.stringWidth(chu, ten_font, co) > do_rong_toi_da:
        co -= 0.5
    if pdfmetrics.stringWidth(chu, ten_font, co) <= do_rong_toi_da:
        return chu, co
    while chu and pdfmetrics.stringWidth(chu + '…', ten_font, co) > do_rong_toi_da:
        chu = chu[:-1]
    return chu + '…', co


def tao_pdf_bang(tieu_de, cac_cot, cac_dong, dong_trong='Không có dữ liệu.', ghi_chu_dau_trang=None):
    """Vẽ một PDF đơn giản gồm tiêu đề + một bảng, giữ dấu tiếng Việt qua font DejaVu Sans.

    cac_cot: list[(ten_cot, do_rong_cm)]. cac_dong: list các dòng, mỗi dòng là list giá trị
    theo đúng thứ tự cac_cot. Trả về BytesIO đã seek(0), sẵn sàng đưa vào FileResponse.
    """
    dam_bao_font_dejavu()
    buffer = BytesIO()
    trang = canvas.Canvas(buffer, pagesize=A4)
    chieu_rong, chieu_cao = A4
    le_trai, le_tren = 2 * cm, 2 * cm

    def ve_o(x, y, chu, ten_font, do_rong):
        chu, co = vua_cot(chu, ten_font, 10, do_rong * cm - _KHOANG_CACH_COT)
        trang.setFont(ten_font, co)
        trang.drawString(x, y, chu)

    def ve_tieu_de_trang(y):
        trang.setFont('DejaVuSans-Bold', 14)
        trang.drawString(le_trai, y, tieu_de)
        y -= 0.8 * cm
        if ghi_chu_dau_trang:
            trang.setFont('DejaVuSans', 9)
            trang.drawString(le_trai, y, ghi_chu_dau_trang)
            y -= 0.6 * cm
        x = le_trai
        for ten_cot, do_rong in cac_cot:
            ve_o(x, y, ten_cot, 'DejaVuSans-Bold', do_rong)
            x += do_rong * cm
        y -= 0.4 * cm
        trang.line(le_trai, y, chieu_rong - le_trai, y)
        return y - 0.5 * cm

    y = ve_tieu_de_trang(chieu_cao - le_tren)
    for dong in cac_dong:
        if y < 2 * cm:
            trang.showPage()
            y = ve_tieu_de_trang(chieu_cao - le_tren)
        x = le_trai
        for gia_tri, (_, do_rong) in zip(dong, cac_cot):
            ve_o(x, y, gia_tri, 'DejaVuSans', do_rong)
            x += do_rong * cm
        y -= 0.6 * cm

    if not cac_dong:
        trang.setFont('DejaVuSans', 10)
        trang.drawString(le_trai, y, dong_trong)

    trang.showPage()
    trang.save()
    buffer.seek(0)
    return buffer
