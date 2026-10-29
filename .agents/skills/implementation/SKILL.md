---
name: implementation
description: Quy trình lập trình đã dùng trong dự án - đọc kế hoạch đã duyệt, nêu file sẽ sửa và chờ xác nhận với lượt lớn, viết code, chạy check và test, báo cáo file đã đổi, không tự commit; dùng cho mọi lượt thêm hoặc sửa chức năng.
---

# Lập trình

## Objective

Làm đúng phạm vi được giao, từng bước nhỏ, dễ kiểm tra: người dùng xem, thử tay rồi tự commit.

## Inputs

- Kế hoạch hoặc yêu cầu của lượt (Phần A, B, C...), `AGENTS.md`, `docs/erd.md`.
- Trạng thái mã hiện tại (`git status`, các file liên quan).
- Quyết định đã chốt từ các lượt trước (công thức điểm, quy tắc kiểm tra đăng ký...).

## Process

1. Đọc yêu cầu, `AGENTS.md` và mã liên quan trước khi làm; với chức năng lớn, đề xuất kế hoạch và chờ người dùng chỉnh, duyệt (ví dụ kế hoạch KT2 được chỉnh 6 điểm).
2. Với lượt lớn hoặc thay đổi rộng (giao diện Sinh viên lượt 1/3 đến 3/3, `nap_du_lieu_day_du`): liệt kê file sẽ tạo hoặc sửa và các điểm tự chọn, chờ xác nhận, rồi mới viết code.
3. Nếu lượt có bảng mới, dừng ở bước model + migration để người dùng xem `sqlmigrate` (xem skill `database-design`).
4. Viết code: dùng lại service có sẵn thay vì viết lại logic (ví dụ tư vấn AI gọi `enrollment.services.xac_dinh_trang_thai`); phân quyền dùng `YeuCauVaiTroMixin`; hằng số ở `settings.py`.
5. Sau mỗi phần chạy `python manage.py check`; cuối lượt chạy test (xem skill `testing`).
6. Báo cáo: liệt kê file đã tạo/sửa theo từng phần, kết quả `check` và test (số lượng pass/fail), điểm nào khác kế hoạch hoặc lỗi tìm thấy khi tự kiểm.
7. Không tự commit. Người dùng kiểm tra, thử tay rồi tự commit; các lượt tiếp theo mở đầu bằng "Lượt trước đã commit".

## Rules

- Không thêm chức năng ngoài phạm vi lượt hiện tại; phần đã làm ở lượt trước thì bỏ qua (ví dụ Phần C của lượt 6/6 đã làm ở lượt 5/6).
- Không tự migrate, không tự commit, không gọi API Gemini thật khi phát triển (dùng `ClientAIGia`, trừ khi người dùng yêu cầu).
- Chưa rõ thì hỏi hoặc nêu rõ điểm tự chọn để người dùng xác nhận; không đoán và làm luôn.
- Nếu `check` hoặc test lỗi thì cho xem nguyên văn lỗi, sửa đúng nguyên nhân.
- Cấu hình nhạy cảm (mật khẩu CSDL, khóa API) chỉ đọc từ `.env`, không ghi vào mã.

## Outputs

- Mã (model, service, view, form, template), test tương ứng, tài liệu cập nhật.
- Bản tóm tắt: file đã đổi, kết quả `check`/test, câu hỏi còn mở.

## Verification

- `check` sạch; test pass; `git status` chỉ có file thuộc phạm vi lượt.
- Ví dụ thực tế: lượt 2/6 (đợt đăng ký và hủy đăng ký) làm theo thứ tự đợt đăng ký, tiên quyết, trùng lịch, sĩ số trong `dang_ky_hoc_phan`; khi phát hiện ràng buộc cũ chặn đăng ký lại, dừng, hỏi, người dùng chọn hướng B rồi mới viết tiếp. Lượt giao diện 3/3 chỉ tiến hành sau khi người dùng xác nhận 3 điểm tự chọn.
