"""Gửi thư (quên mật khẩu, lệnh thu_gui_email) và ghi log logger qldt.email.

Log chỉ ghi email đã che (s***@gmail.com), loại lỗi; không ghi nội dung thư, link đặt lại hay mật khẩu SMTP.
"""
import logging
import smtplib
import socket
import threading

from django.conf import settings

logger = logging.getLogger('qldt.email')

# Thứ tự quan trọng: lớp con đứng trước lớp cha (SMTPAuthenticationError là SMTPResponseException...).
_GOI_Y_LOI = (
    (smtplib.SMTPAuthenticationError,
     'Máy chủ từ chối đăng nhập: kiểm tra EMAIL_HOST_USER và EMAIL_HOST_PASSWORD (phải là mật khẩu ứng dụng Gmail '
     '16 ký tự, tài khoản đã bật xác minh 2 bước).'),
    (smtplib.SMTPSenderRefused, 'Máy chủ từ chối địa chỉ người gửi: kiểm tra DEFAULT_FROM_EMAIL.'),
    (smtplib.SMTPRecipientsRefused, 'Máy chủ từ chối địa chỉ người nhận.'),
    (smtplib.SMTPNotSupportedError, 'Máy chủ không hỗ trợ lệnh yêu cầu (kiểm tra EMAIL_USE_TLS/cổng).'),
    (smtplib.SMTPConnectError, 'Không mở được kết nối tới máy chủ SMTP.'),
    (smtplib.SMTPServerDisconnected, 'Máy chủ SMTP ngắt kết nối giữa chừng.'),
    (smtplib.SMTPException, 'Lỗi SMTP khác.'),
    (socket.gaierror, 'Không phân giải được tên máy chủ SMTP (mất mạng hoặc sai EMAIL_HOST).'),
    (TimeoutError, 'Hết thời gian chờ máy chủ SMTP (EMAIL_TIMEOUT): mạng chặn cổng 587 hoặc máy chủ không phản hồi.'),
    (ConnectionRefusedError, 'Máy chủ SMTP từ chối kết nối (sai cổng hoặc bị tường lửa chặn).'),
    (OSError, 'Lỗi mạng khi kết nối máy chủ SMTP.'),
)


def che_email(email):
    """'sinhvien@gmail.com' -> 's***@gmail.com'; chuỗi không có '@' -> '***'."""
    ten, _, mien = (email or '').strip().partition('@')
    if not ten or not mien:
        return '***'
    return f'{ten[0]}***@{mien}'


def mo_ta_loi_gui_thu(loi):
    """'<Tên lớp lỗi> (mã SMTP nếu có): gợi ý' — không chứa mật khẩu (thông điệp lỗi smtplib không có mật khẩu,
    và hàm này không dùng str(loi) của các lỗi mạng)."""
    goi_y = next((g for lop, g in _GOI_Y_LOI if isinstance(loi, lop)), 'Lỗi không xác định khi gửi thư.')
    ma = getattr(loi, 'smtp_code', None)
    return f'{type(loi).__name__}{f" (mã {ma})" if ma else ""}: {goi_y}'


def gui_thu(thu, mo_ta):
    """Gửi EmailMessage `thu`, ghi log kết quả. Khi settings.EMAIL_GUI_NEN thì gửi trong luồng nền và trả luồng đó
    (trang web chuyển ngay, không chờ máy chủ SMTP); ngược lại gửi luôn và trả None. Không ném lỗi."""
    nguoi_nhan = ', '.join(che_email(dia_chi) for dia_chi in thu.to)

    def _gui():
        try:
            thu.send()
        except Exception as loi:
            logger.warning('%s: lỗi gửi thư tới %s: %s', mo_ta, nguoi_nhan, mo_ta_loi_gui_thu(loi))
        else:
            logger.info('%s: đã gửi thư tới %s.', mo_ta, nguoi_nhan)

    if getattr(settings, 'EMAIL_GUI_NEN', False):
        luong = threading.Thread(target=_gui, name='gui-email', daemon=True)
        luong.start()
        return luong
    _gui()
    return None
