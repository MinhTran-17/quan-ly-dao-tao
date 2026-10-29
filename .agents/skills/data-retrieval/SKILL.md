---
name: data-retrieval
description: Cách các chức năng AI của dự án truy xuất dữ liệu tối thiểu trước khi đưa vào prompt - dùng lại service nghiệp vụ có sẵn, không gửi thông tin định danh, truy hồi đoạn quy chế bằng BM25 với ngưỡng điểm; dùng khi thêm hoặc sửa dữ liệu đầu vào của một chức năng AI.
---

# Truy xuất dữ liệu cho AI

## Objective

Lấy đúng và chỉ đúng dữ liệu cần cho từng chức năng AI, bằng logic nghiệp vụ đã có, để kết quả chính xác và không lộ thông tin cá nhân.

## Inputs

- Quyết định của bước phân tích (skill `question-analysis`): đối tượng, học kỳ, câu hỏi.
- Service sẵn có: `enrollment.services` (`danh_sach_hoc_phan_da_dat`, `xac_dinh_trang_thai`, `tim_hoc_phan_tien_quyet_con_thieu`, `tim_lich_trung`), `grades.services` (`bang_diem_chi_tiet`), `grades.tinh_diem`.
- Tài liệu quy chế do Phòng Đào tạo tải lên qua app `regulations` (PDF, DOCX).
- Cấu hình: `AI_GIOI_HAN_KY_TU`, `AI_NGUONG_DIEM_TRUY_HOI`, `AI_TRUY_HOI_PHIEN_BAN`.

## Process

1. **Tư vấn đăng ký**: lấy học phần đã đạt (mã, tên, tín chỉ, điểm tổng kết), danh sách lớp đang mở (mã lớp, tên học phần, lịch) và trạng thái đã tính bằng đúng `xac_dinh_trang_thai`, hàm dùng chung với đăng ký thật. Không viết lại luật tiên quyết, trùng lịch, sĩ số.
2. **Tóm tắt kết quả**: lấy bảng điểm từ `grades.services.bang_diem_chi_tiet` (mỗi học phần một dòng, giữ điểm cao nhất nếu học lại), điểm tổng kết từ `Diem.tinh_diem_tong_ket()`; số liệu tổng hợp do code tính: tổng tín chỉ đã đạt, số học phần đạt và chưa đạt, học phần điểm cao nhất và thấp nhất (một học phần thì cao nhất bằng thấp nhất, không chia 0).
3. **Hỏi đáp quy chế**: trích chữ từ PDF (`pypdf`) và DOCX (`python-docx`); chia đoạn theo Điều, khoản, điểm, cắt cứng khoảng 1500 ký tự, mỗi đoạn giữ tên tài liệu, số Điều, số khoản; xếp hạng bằng BM25 tự cài (`hoi_dap_quy_che/bm25.py`, `chi_muc.py`), chỉ mục giữ trong bộ nhớ, làm mới khi chữ ký thay đổi (`ma_tai_lieu`, `ngay_cap_nhat`, `duong_dan_file`).
4. Truy hồi v2: thêm bigram âm tiết, đưa tiêu đề Điều vào nội dung chỉ mục của mọi đoạn thuộc Điều đó (khi gửi AI và hiển thị vẫn dùng đoạn gốc), lấy tối đa 6 đoạn (v1 là 4); bỏ đoạn dưới ngưỡng điểm; nếu tổng độ dài vượt `AI_GIOI_HAN_KY_TU` thì bỏ bớt đoạn điểm thấp nhất thay vì báo lỗi.
5. Định dạng dữ liệu thành văn bản trong khối dữ liệu của `user.txt`; chỉ đưa các trường cần thiết.

## Rules

- Không gửi họ tên, email, mã sinh viên, mã tài khoản, kể cả khi cố vấn xem sinh viên khác.
- Tư vấn chỉ gửi điểm tổng kết của học phần đã đạt, không gửi điểm quá trình hay điểm thi; tóm tắt gửi điểm quá trình, điểm thi, điểm tổng kết.
- Không tính lại công thức điểm hay luật đăng ký; dùng lại hàm có sẵn và hằng số `DIEM_DAT_TOI_THIEU`.
- Chatbot quy chế không dùng dịch vụ embedding ngoài; không gửi toàn văn tài liệu, chỉ đoạn liên quan; không gửi dữ liệu học tập hay cá nhân.
- Quyền theo đối tượng kiểm tra trước khi đọc dữ liệu (xem skill `security-review`).
- Ghi chú hiện tại: các chức năng AI dùng điểm thật (không lọc `da_cong_bo`); lượt 4/6 đã cố ý không mở rộng phần công bố điểm sang tư vấn hoặc tóm tắt AI.

## Outputs

- Cấu trúc dữ liệu tối thiểu cho từng chức năng (danh sách lớp kèm trạng thái, bảng điểm kèm số liệu, các đoạn quy chế kèm nguồn) dùng để dựng prompt và để hiển thị lại bằng dữ liệu do code cung cấp.

## Verification

- Test không rò rỉ: `test_khong_co_thong_tin_ca_nhan_trong_prompt`, `KhongRoRiDuLieuGiuaSinhVienTest` (sinh viên A không có dữ liệu sinh viên B trong prompt).
- Kiểm tra truy hồi bằng `chay_ca_thu_quy_che` (không `--ai`): câu 1 phải có đoạn Điều 14 khoản 2 và Điều 15 khoản 2, câu 4 phải có Điều 3; test tự động có ca thay tệp trong cùng một ngày thì chỉ mục nhận nội dung mới.
- Ví dụ thực tế: sửa chữ ký làm mới chỉ mục thêm `duong_dan_file` vì `ngay_cap_nhat` chỉ là ngày; chạy `chay_ca_thu_quy_che` không `--ai` để xem các đoạn truy hồi cùng điểm.
