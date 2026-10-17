"""Khung chat hỏi đáp quy chế: chuyển kết quả (services.KetQuaHoiDap) sang dạng lưu được trong session
(ai_core.lich_su_chat). Mỗi câu hỏi vẫn là một yêu cầu độc lập: truy hồi BM25 theo đúng câu đó, không gửi các câu hỏi
trước cho AI."""


def _doan(doan, khoa_noi_dung):
    return {
        'ten_tai_lieu': doan['ten_tai_lieu'], 'dieu': doan['dieu'], 'khoan': doan['khoan'] or '',
        'noi_dung': doan[khoa_noi_dung],
    }


def ket_qua_thanh_dict(ket_qua):
    return {
        'loai': 'hoi_dap',
        'tra_loi': ket_qua.tra_loi,
        'khong_tim_thay': ket_qua.khong_tim_thay,
        'loi_ai': ket_qua.loi_ai or '',
        'nguon': [_doan(nguon, 'trich_doan') for nguon in ket_qua.nguon],
        'ghi_chu_loc': list(ket_qua.ghi_chu_loc),
        # Khi AI lỗi vẫn cho người dùng tự đọc các đoạn quy chế đã truy hồi.
        'doan_lien_quan': [_doan(doan, 'noi_dung') for doan, _ in ket_qua.doan_truy_hoi] if ket_qua.loi_ai else [],
    }
