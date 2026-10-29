---
name: testing
description: Quy trình kiểm thử đã dùng - viết test cho từng lượt, chạy toàn bộ suite, sửa đúng nguyên nhân thay vì sửa test cho qua, báo cáo số lượng và kết quả, dùng ClientAIGia cho chức năng AI; dùng khi thêm chức năng, sửa lỗi hoặc trước khi báo hoàn thành.
---

# Kiểm thử

## Objective

Bảo đảm chức năng đúng đề (đăng ký học phần, điều kiện tiên quyết, trùng lịch, nhập điểm, chức năng AI), không hồi quy, không tốn hạn mức AI thật, và kết quả báo cáo trung thực.

## Inputs

- Yêu cầu test của lượt, `docs/de-bai.md` mục 4, `docs/rubric.md` (KT3 tiêu chí 8: đúng, sai, biên).
- `python manage.py test` (toàn bộ) hoặc `python manage.py test <app>`.
- `docs/bien_ban_kiem_thu.md`, `docs/ca_thu_ai/*.md`.

## Process

1. Với mỗi lượt viết test song song với code: quyền theo 4 vai trò và người chưa đăng nhập, đường đúng, đường sai, trường hợp biên. Ví dụ điểm ngoài 0 đến 10; tính tổng kết 8.0 và 7.5 ra 7.7, 9.0 và 8.5 ra 8.7; đăng ký hợp lệ, thiếu tiên quyết, trùng lịch, lớp đầy, đăng ký trùng.
2. Chạy `check`, rồi chạy toàn bộ test (không chỉ test mới). Ở lượt chỉ chỉnh giao diện nhỏ, người dùng có thể chỉ định chạy riêng app `accounts`; làm đúng theo chỉ định.
3. Khi có lỗi: đọc nguyên văn lỗi, tìm nguyên nhân gốc, sửa mã hoặc sửa đúng kỳ vọng của test khi hành vi thay đổi có chủ đích; không nới lỏng test chỉ để qua.
4. Bug nào cũng thêm test hồi quy: ví dụ thay tệp quy chế hai lần trong cùng một ngày phải làm mới chỉ mục; nguồn AI trích ở các dạng khoản null, chuỗi rỗng, "3", "khoản 3", số nguyên 3 đều phải khớp còn nguồn bịa vẫn bị loại.
5. Test chức năng AI chỉ dùng client giả (`AI_BACKEND='gia'`, `ClientAIGia`), kiểm tra nội dung prompt đã gửi (không có họ tên, email, mã sinh viên, mã tài khoản) và `assert_not_called()` khi không được gọi AI.
6. Test không được phụ thuộc `.env` của máy: cố định cấu hình ngầm bằng `override_settings` (`AI_NGUONG_DIEM_TRUY_HOI`, `AI_TRUY_HOI_PHIEN_BAN`, `AI_GIOI_HAN_KY_TU`, `AI_BACKEND`, `AI_PHIEN_BAN_*`); kiểm chứng bằng chạy hai lần với ngưỡng 10 và 0.5.
7. Chạy song song với người dùng có thể làm `test_qldt` bị xóa; dùng tên database test riêng (cấu hình tạm ngoài repo) khi cần.
8. Khi chạy `manage.py test`, `qldt/settings.py` tự dùng `MD5PasswordHasher` để test nhanh (PBKDF2 mặc định cố ý chậm); chạy thật vẫn dùng PBKDF2.
9. Báo cáo: số test, pass/fail, thời gian; test thủ công ghi ở `docs/bien_ban_kiem_thu.md`, cột "Kết quả" và "Ngày" để người kiểm thử tự điền.

## Rules

- Không gọi API Gemini thật trong test hoặc lúc dev; chỉ chạy `--ai` của các lệnh `chay_ca_thu_*` khi người dùng yêu cầu.
- Không sửa test chỉ để pass; không điền kết quả thủ công khi chưa chạy.
- Không ghi log nội dung prompt chứa dữ liệu học tập, kể cả trong test.
- Báo lỗi và số liệu đúng như chạy được; nếu chưa chạy phần nào thì nói rõ.

## Outputs

- Test tự động cho từng lượt; báo cáo ngắn: `check` sạch, N/N test pass; cập nhật số liệu ở `docs/bien_ban_kiem_thu.md` khi có chạy lại.

## Verification

- `python manage.py test` toàn bộ pass; số test, kết quả, ngày và thời gian chạy của lần gần nhất ghi ở `docs/bien_ban_kiem_thu.md` (không ghi số liệu vào skill vì sẽ cũ); `accounts` là app có test phân quyền toàn hệ thống (`PhanQuyenToanHeThongTest`, 30 URL x 4 vai trò x chưa đăng nhập).
- Ví dụ thực tế: 28 test của `hoi_dap_quy_che` từng fail khi `.env` đặt `AI_NGUONG_DIEM_TRUY_HOI=10` vì dữ liệu test nhỏ; sửa bằng cố định cấu hình trong test, không đổi logic.
