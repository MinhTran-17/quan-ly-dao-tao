---
name: documentation
description: Quy trình cập nhật tài liệu sau mỗi lượt - nối thêm docs/erd.md, cập nhật thiết kế giao diện, README, biên bản kiểm thử, thiết kế AI; chỉ mô tả cái đã triển khai thật; dùng khi hoàn tất một lượt hoặc thay đổi cách chạy dự án.
---

# Tài liệu

## Objective

Giữ tài liệu khớp với mã đang chạy, đủ để người khác cài đặt, chạy, demo và chấm điểm theo rubric mà không phải đoán.

## Inputs

- Thay đổi vừa làm (model, chức năng, lệnh quản lý, giao diện, cấu hình).
- Các tài liệu hiện có: `docs/erd.md`, `docs/thiet_ke_giao_dien.md`, `docs/thiet_ke_ai.md`, `docs/review_code_ai.md`, `docs/bien_ban_kiem_thu.md`, `docs/ai-log.md`, `docs/ca_thu_ai/`, `prompts/README.md`, `README.md`, `AGENTS.md`.
- `docs/rubric.md` (minh chứng bắt buộc: nhật ký AI, tài liệu thiết kế, test, dữ liệu mẫu, báo cáo chất lượng AI).

## Process

1. Sau khi tạo model: nối thêm mục "Bổ sung ngoài đề (lượt n/6)" vào cuối `docs/erd.md`, nêu bảng/cột mới và hạn chế; không xóa hay sửa nội dung cũ. Bảng phụ của Django nằm ở mục riêng.
2. Sau lượt giao diện: cập nhật `docs/thiet_ke_giao_dien.md` theo từng lượt (bảng màu, hệ nút, lớp CSS, layout riêng của Sinh viên, quy tắc trang AI, responsive).
3. Khi thay đổi cách cài, chạy hoặc demo: cập nhật `README.md` (yêu cầu môi trường, tạo database, `.env`, migrate, tài khoản đầu tiên, nạp dữ liệu mẫu, chạy server, chạy test, demo theo vai trò, chức năng AI, giới hạn hạn mức, cấu trúc thư mục).
4. Khi thay đổi chức năng AI: cập nhật `docs/thiet_ke_ai.md` (luồng, dữ liệu gửi và không gửi, phiên bản prompt, các lớp kiểm tra, xử lý lỗi) và `prompts/README.md`.
5. Sau khi chạy test: cập nhật số liệu ở `docs/bien_ban_kiem_thu.md` (bảng test tự động theo app). Bảng test thủ công để trống cột kết quả và ngày cho người kiểm thử.
6. Ghi `docs/ai-log.md` theo mẫu (KT1-01...): ngày, công cụ, prompt, phản hồi tóm tắt, phần đã dùng; phần "Kiểm tra, chỉnh sửa" do người làm tự viết, chỗ chưa xong đánh dấu NHÁP hoặc TODO.
7. Cập nhật `AGENTS.md` khi có quy tắc mới do người dùng chốt (ví dụ phân quyền chỉ dựa cột `vai_tro`, dữ liệu gửi AI).

## Rules

- Chỉ mô tả chức năng đã triển khai thật; không viết trước.
- Nối thêm, không xóa lịch sử; không sao chép nguyên văn tài liệu thiết kế vào nhiều nơi.
- Không ghi kết quả kiểm thử chưa chạy; không ghi thông tin nhạy cảm (khóa, mật khẩu thật) vào tài liệu.
- Mật khẩu demo `MatKhauDemo123` chỉ ghi kèm cảnh báo không dùng ở môi trường thật.
- Ghi rõ hạn chế đã biết (ví dụ hạn chế của cột học kỳ dạng chuỗi tự do trong `lop_hoc_phan`).

## Outputs

- Bộ tài liệu khớp với mã ở thời điểm cuối lượt; danh sách tài liệu đã cập nhật trong bản tóm tắt.

## Verification

- Tên lệnh, biến môi trường, đường dẫn trong tài liệu chạy được thật (ví dụ `python manage.py nap_du_lieu_day_du`).
- Số liệu test trong biên bản khớp lần chạy gần nhất; nếu số liệu cũ thì ghi rõ ngày chạy hoặc chạy lại.
- Ví dụ thực tế: `docs/erd.md` có các mục "lượt 1/6" đến "lượt 6/6"; README có mục "Bộ dữ liệu đầy đủ cho buổi demo" nêu cả việc lệnh dời ngày bắt đầu học kỳ hiện tại.
