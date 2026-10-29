---
name: architecture-design
description: Quy trình thiết kế kiến trúc hệ thống đã dùng cho dự án Django + MySQL, tách app theo domain, có tầng ai_core dùng chung cho 3 chức năng AI; dùng khi thêm app mới, quyết định đặt logic ở đâu, hoặc chọn công nghệ/cấu hình.
---

# Thiết kế kiến trúc

## Objective

Giữ kiến trúc nhất quán: mỗi app Django là một domain, nghiệp vụ nằm ở `services.py`, phân quyền dùng chung một chỗ, và mọi chức năng AI dựa trên cùng một hạ tầng `ai_core`.

## Inputs

- `docs/de-bai.md` mục 4 (yêu cầu kỹ thuật), `docs/erd.md`, `AGENTS.md`.
- Sơ đồ kiến trúc KT1-04 (frontend, backend, CSDL, AI service, luồng dữ liệu).
- Môi trường máy: MySQL 8.0.46, PowerShell, venv.

## Process

1. Chọn công nghệ theo `AGENTS.md`: Django + template HTML/CSS/JS, MySQL (database `qldt`) qua PyMySQL, cấu hình đọc từ `.env`, LLM Gemini qua SDK `google-genai`. Ban đầu AI đề xuất PostgreSQL, sau đó người dùng quyết định MySQL vì máy đã có MySQL Workbench.
2. Khởi tạo dự án (`qldt/`), kiểm tra `python manage.py check`. Khi Django 6.1.1 đòi MySQL 8.4 trở lên, hạ xuống Django 6.0 (`requirements.txt` ghim `Django==6.0.8`) thay vì nâng MySQL, vì không muốn ảnh hưởng các database khác trên máy.
3. Chia app theo domain và 13 bảng của `docs/erd.md`: `accounts` (model `TaiKhoan` làm người dùng), `people`, `academics`, `classes`, `enrollment`, `grades`, `regulations`, `reports`; các lượt mở rộng thêm `tien_do_hoc_tap`, `diem_danh`, `thong_bao`.
4. Mỗi app có `models.py` (nếu có bảng), `services.py` (nghiệp vụ), `views.py`, `urls.py`, `tests.py`, `templates/<app>/`. View mỏng, quy tắc nghiệp vụ đặt ở service để dùng lại (ví dụ `enrollment.services.xac_dinh_trang_thai` dùng cho cả đăng ký thật và tư vấn AI).
5. Xử lý phụ thuộc vòng khi có: `people` và `academics` tham chiếu lẫn nhau (sinh_vien trỏ lop_hanh_chinh, lop_hanh_chinh trỏ co_van_hoc_tap) nên tách migration; giữa `enrollment` và `grades` không có vòng thật vì `Diem` tham chiếu bằng chuỗi `'enrollment.DangKyHocPhan'` và `enrollment.services` truy cập điểm qua thuộc tính ngược `dang_ky.diem`.
6. Phân quyền dùng chung ở `accounts/permissions.py` (`yeu_cau_vai_tro`, `YeuCauVaiTroMixin`), chỉ dựa cột `vai_tro`.
7. Tầng AI: `ai_core` (`clients.py` có `GeminiClient` và `ClientAIGia`, `exceptions.py`, `prompts.py`, `dinh_dang.py`, `gioi_han_tan_suat.py`, lệnh `kiem_tra_ai`); ba app chức năng `tu_van_dang_ky`, `tom_tat_ket_qua`, `hoi_dap_quy_che` chỉ gọi qua `ai_core`. Prompt để ở `prompts/`, tách khỏi code.
8. Cập nhật `README.md` (cấu trúc thư mục) và `docs/thiet_ke_ai.md` khi thêm app.

## Rules

- 13 bảng nghiệp vụ theo đề trong `docs/erd.md`, cộng 8 bảng bổ sung qua các lượt mở rộng 1/6 đến 6/6 (tổng 21 bảng, xem `docs/thiet_ke_csdl.md`); bảng phụ của Django (django_migrations, django_session...) được ghi rõ ở mục "Bảng phụ của Django".
- Không dùng `PermissionsMixin`, `permission_required`, `has_perm`, `is_superuser`.
- Hằng số nghiệp vụ đặt ở `qldt/settings.py`, không ghi cứng trong code (`TY_LE_DIEM_*`, `DIEM_DAT_TOI_THIEU`, `AI_*`).
- Nguyên tắc AI: "code tính, AI diễn giải"; giới hạn tần suất dùng cache của Django, không tạo bảng CSDL mới.
- Mật khẩu CSDL và khóa API chỉ ở `.env`, `.env` nằm trong `.gitignore`.

## Outputs

- Cấu trúc app và luồng dữ liệu nhất quán với README và `docs/thiet_ke_ai.md`.
- Cấu hình chạy được: `requirements.txt`, `.env.example` (không có giá trị nhạy cảm).

## Verification

- `python manage.py check` sạch; `python manage.py makemigrations --check` không còn thay đổi chờ.
- Không có import vòng giữa các app; `grep` không thấy `permission_required`/`has_perm`/`is_superuser`.
- Ví dụ thực tế: `hoi_dap_quy_che` mới thêm nhưng chỉ gọi `ai_core.clients.lay_client_ai()` và `nap_prompt`, không tạo client riêng; đổi backend giả cho test chỉ cần `AI_BACKEND='gia'`.
