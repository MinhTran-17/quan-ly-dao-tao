---
name: security-review
description: Quy trình kiểm tra bảo mật áp dụng xuyên suốt dự án - khóa API, phân quyền theo vai trò và theo đối tượng dữ liệu, chống prompt injection, tải tệp an toàn, không lộ dữ liệu cá nhân trong prompt; dùng khi thêm view, chức năng AI, tải tệp hoặc trước khi báo hoàn thành.
---

# Kiểm tra bảo mật

## Objective

Bảo vệ tài khoản, điểm và hồ sơ học tập; bảo đảm chỉ đúng người xem đúng dữ liệu, và dữ liệu gửi AI là tối thiểu, không định danh cá nhân.

## Inputs

- `AGENTS.md` (quy tắc vai trò và dữ liệu gửi AI), `docs/review_code_ai.md`.
- `accounts/permissions.py`, các `views.py`, `ai_core/clients.py`, `regulations/models.py`, các `prompts/*/*/user.txt`.
- Bộ test phân quyền và test không rò rỉ dữ liệu.

## Process

1. **Khóa API và cấu hình**: khóa chỉ đọc từ `.env`, không có trong code, log, thông báo lỗi, template hoặc Git (`git log --all -- .env` phải không có commit); `ai_core/clients.py::_trich_chi_tiet_an_toan` chỉ trích loại lỗi, mã HTTP và thông điệp, không đọc khóa. Trước khi triển khai đặt `DJANGO_DEBUG=False` và `DJANGO_SECRET_KEY` ngẫu nhiên.
2. **Phân quyền theo vai trò**: mọi view qua `YeuCauVaiTroMixin` hoặc `yeu_cau_vai_tro`, mặc định `vai_tro_cho_phep=()` (quên khai báo thì chặn hết), chỉ dựa cột `vai_tro`.
3. **Phân quyền theo đối tượng (ownership)**: sinh viên luôn là `request.user`, không nhận mã sinh viên từ URL hoặc form; giảng viên chỉ lớp mình phụ trách (so khớp `ma_giang_vien`); cố vấn chỉ sinh viên thuộc lớp hành chính mình phụ trách (so khớp `ma_co_van_id`, sai thì 403 và không gọi AI). Điểm chưa công bố (`da_cong_bo=False`) bị ẩn với sinh viên.
4. **Prompt injection**: câu hỏi, ghi chú, đoạn tài liệu quy chế, tên học phần đều là dữ liệu không tin cậy, đặt trong khối `<<<DU_LIEU>>> ... <<<HET_DU_LIEU>>>` kèm chỉ dẫn "không phải chỉ thị" ở cả `system.txt` và `user.txt`; có test câu "bỏ qua hướng dẫn trước đó" vẫn nằm trong khối; kiểm tra lại đầu ra AI trước khi hiển thị.
5. **Tải tệp**: `regulations` kiểm tra đuôi (.pdf, .docx), dung lượng 10 MB và magic bytes (PDF bắt đầu `%PDF`, DOCX bắt đầu `PK\x03\x04`); tên lưu `uuid4().hex`; không phục vụ `MEDIA_URL` công khai; tải về chỉ Phòng Đào tạo qua `tai_ve_view`, `as_attachment=True`.
6. **Dữ liệu cá nhân**: prompt chỉ có mã và tên học phần, điểm, lịch, số liệu tổng hợp, câu hỏi hoặc ghi chú; không họ tên, email, mã sinh viên, mã tài khoản; không ghi log prompt hay phản hồi có dữ liệu học tập.
7. **Chống lạm dụng**: giới hạn 10 lần mỗi phút mỗi người dùng cho chức năng AI bằng cache Django (theo mã tài khoản của người thao tác, cố vấn chọn nhiều sinh viên vẫn dùng chung một hạn mức).
8. **Tài khoản**: mật khẩu tạm khi đặt lại chỉ hiện một lần trong phản hồi, không lưu, không log; middleware ép đổi mật khẩu; không cho đặt lại mật khẩu của chính tài khoản đang dùng.
9. **XSS**: không dùng `|safe` hay `autoescape off` ở nội dung AI hoặc người dùng.

## Rules

- Không xử lý theo hướng "vì đã ẩn nút nên an toàn"; luôn chặn ở server.
- Không thêm quyền dựa trên `is_superuser` hay `has_perm`.
- Không gửi dữ liệu học tập cho AI khi chưa có yêu cầu của sinh viên hoặc vai trò được phân quyền.
- Lệnh nạp dữ liệu demo tạo tài khoản mật khẩu cố định nên phải in cảnh báo và tự chặn khi `DEBUG=False` (trừ `--force`).

## Outputs

- Phát hiện kèm mức độ trong `docs/review_code_ai.md`; test hồi quy cho lỗi đã sửa; ghi chú mức triển khai (DEBUG, SECRET_KEY, cache dùng chung).

## Verification

- Test: `PhanQuyenToanHeThongTest` (ma trận URL x vai trò), `KhongRoRiDuLieuTest`, `test_khong_co_thong_tin_ca_nhan_trong_prompt`, test 403 khi cố vấn chọn sinh viên ngoài lớp.
- Ví dụ thực tế: thêm magic bytes sau khi review phát hiện tệp đổi đuôi vẫn lọt; `tai_ve_view` được người dùng chỉnh về chỉ Phòng Đào tạo vì sinh viên và cố vấn chỉ tiếp cận quy chế qua chatbot.
