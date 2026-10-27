"""Theo dõi (monitoring) các lượt gọi AI.

Mỗi lượt gọi ghi đúng một dòng log vào logger 'qldt.ai' (ra logs/app.log, xem LOGGING trong
settings) gồm: chức năng, kết quả (thanh_cong/loi), loại lỗi, thời gian phản hồi (ms).

TUYỆT ĐỐI không ghi nội dung prompt, câu trả lời của AI hay điểm của sinh viên — kể cả khi lỗi
(không ghi str(loi), vì thông điệp lỗi từ API có thể lặp lại một phần nội dung gửi đi).
"""
import logging
import time

logger = logging.getLogger('qldt.ai')


def goi_ai_co_ghi_log(chuc_nang, client, *, he_thong, nguoi_dung):
    """Gọi client.sinh_noi_dung(...) như cũ, đo thời gian và ghi log; ngoại lệ được ném lại nguyên vẹn."""
    bat_dau = time.perf_counter()
    try:
        phan_hoi = client.sinh_noi_dung(he_thong=he_thong, nguoi_dung=nguoi_dung)
    except Exception as loi:
        logger.warning(
            'goi_ai chuc_nang=%s ket_qua=loi loai_loi=%s thoi_gian_ms=%d',
            chuc_nang, type(loi).__name__, (time.perf_counter() - bat_dau) * 1000,
        )
        raise
    logger.info(
        'goi_ai chuc_nang=%s ket_qua=thanh_cong loai_loi=- thoi_gian_ms=%d',
        chuc_nang, (time.perf_counter() - bat_dau) * 1000,
    )
    return phan_hoi
