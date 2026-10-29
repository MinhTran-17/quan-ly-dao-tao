---
name: code-review
description: Quy trình review code đã dùng cho các app AI và regulations (lượt 6 của KT3) - rà theo tiêu chí, phân mức độ nghiêm trọng, ghi docs/review_code_ai.md, sửa ngay lỗi rủi ro thấp kèm test hồi quy, để lỗi rủi ro cao cho người dùng quyết định.
---

# Review code

## Objective

Tìm lỗi bảo mật và chất lượng ở phạm vi được giao, sửa những gì an toàn để sửa, và ghi rõ phần còn lại để người dùng quyết định.

## Inputs

- Phạm vi review (ở lượt 6: `ai_core`, `tu_van_dang_ky`, `tom_tat_ket_qua`, `hoi_dap_quy_che`, `regulations`).
- Danh sách tiêu chí do người dùng đưa ra: phân quyền theo view và theo đối tượng, dữ liệu cá nhân trong prompt và log, rò rỉ khóa API, prompt injection, xử lý lỗi AI, giới hạn tần suất, tải tệp, truy vấn N+1, ngoại lệ chưa bắt.
- Mã nguồn, test hiện có, `AGENTS.md`.

## Process

1. Đọc mã trong phạm vi theo từng tiêu chí; dùng `grep` để tìm `logging`, `print`, `|safe`, `permission_required`, chỗ truy cập biến môi trường.
2. Với mỗi phát hiện ghi: mức độ (Nghiêm trọng, Trung bình, Thấp), vị trí file và dòng, mô tả, kịch bản gây hại, cách sửa.
3. Sửa ngay phát hiện nghiêm trọng hoặc trung bình mà rủi ro khi sửa thấp, kèm test hồi quy chạy được.
4. Phát hiện rủi ro cao khi sửa hoặc thuộc quyết định hạ tầng thì không tự sửa: ghi lý do và đề xuất cách sửa.
5. Liệt kê các mục đã kiểm tra và không thấy vấn đề (để người đọc biết đã rà những gì).
6. Ghi báo cáo vào `docs/review_code_ai.md` gồm ba phần: 1. Đã sửa, 2. Chưa sửa (để quyết định), 3. Đã kiểm tra không phát hiện vấn đề.
7. Chạy `check` và toàn bộ test; tóm tắt cho người dùng kèm danh sách phát hiện chưa sửa.

## Rules

- Chỉ sửa khi rủi ro thấp; không tái cấu trúc hàm dùng chung nghiệp vụ chỉ để tối ưu.
- Không sửa code đang chạy tốt và đã có test (ví dụ giữ nguyên `hoi_dap_quy_che/gioi_han_tan_suat.py`).
- Mỗi lỗi đã sửa phải có test hồi quy; báo cáo không nêu điều chưa kiểm chứng.
- Cũng xét transaction và ngoại lệ dữ liệu: ví dụ `dang_ky_hoc_phan` chạy trong `transaction.atomic`, khóa dòng lớp khi đếm sĩ số và bắt `IntegrityError` thành `LoiDangKyHocPhan`.

## Outputs

- `docs/review_code_ai.md`, bản sửa nhỏ kèm test hồi quy.
- Danh sách phát hiện chưa sửa gửi người dùng.

## Verification

- Test hồi quy nêu trong báo cáo tồn tại và pass; `check` sạch.
- Ví dụ thực tế trong `docs/review_code_ai.md`:
  - Đã sửa: kiểm tra tệp chỉ dựa vào đuôi (Trung bình) bằng magic bytes trong `validate_tai_lieu_file`; `tu_van_dang_ky` và `tom_tat_ket_qua` thiếu giới hạn tần suất (Trung bình) bằng `ai_core/gioi_han_tan_suat.py`.
  - Chưa sửa: N+1 trong `_tinh_danh_sach_trang_thai` gọi `xac_dinh_trang_thai` (Trung bình, rủi ro cao khi sửa vì hàm dùng chung với đăng ký thật); `KeyError` ở `nap_prompt` khi prompt thiếu biến (Thấp); `LocMemCache` theo tiến trình; `DEBUG` và `SECRET_KEY` mặc định.
- Ở bước rà soát phân quyền toàn hệ thống (bước 11) phát hiện đổi `vai_tro` của tài khoản đang gắn hồ sơ có thể để lại hồ sơ mồ côi, đã chặn ở form kèm test.
