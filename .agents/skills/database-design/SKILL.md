---
name: database-design
description: Quy trình thay đổi cơ sở dữ liệu đã lặp lại ở mọi lượt thêm chức năng - tạo model, cập nhật docs/erd.md, xem sqlmigrate đối chiếu, chỉ migrate khi được xác nhận; dùng bất cứ khi nào thêm/sửa bảng hoặc cột.
---

# Thiết kế và migrate cơ sở dữ liệu

## Objective

Mọi thay đổi cấu trúc bảng đều được ghi vào `docs/erd.md`, được người dùng đối chiếu SQL thật trước khi chạy, và không phá bảng đã có.

## Inputs

- `docs/erd.md` (13 bảng gốc, tên bảng và cột snake_case) và các mục "Bổ sung ngoài đề (lượt n/6)".
- Yêu cầu của lượt (bảng/cột mới, ràng buộc, ghi chú như "cho phép NULL", "UNIQUE cặp").
- MySQL 8.0.46, database `qldt`.

## Process

1. Đọc `docs/erd.md`, đối chiếu tên bảng/cột đang có trước khi tạo model.
2. Viết model với đủ ràng buộc khai báo trong `Meta.constraints` (UNIQUE, CHECK) và `db_table`, `db_column` đúng tên trong ERD.
3. `python manage.py makemigrations` (chưa migrate). Chạy `python manage.py sqlmigrate <app> <số>` và đưa toàn bộ SQL cho người dùng đối chiếu với `docs/erd.md`.
4. Nối thêm mục mới vào cuối `docs/erd.md` (không xóa hay sửa nội dung cũ), nêu hạn chế nếu có.
5. Người dùng xác nhận ("Đã đối chiếu sqlmigrate, ổn. Chạy migrate") thì mới chạy `python manage.py migrate`, rồi `check` và chạy test.
6. Với ràng buộc MySQL không diễn đạt được, chọn phương án thay thế và nêu lý do (xem ví dụ).
7. Nếu người dùng đặt câu hỏi về dữ liệu cũ (backfill), nêu đề xuất rõ ràng, chờ xác nhận.

## Rules

- Không tự `migrate`; chỉ chạy sau khi người dùng đối chiếu `sqlmigrate` và cho phép.
- Không tự ý xóa hay đổi cấu trúc bảng, cột đã có; không đổi tên bảng/cột trong ERD.
- Không lưu dữ liệu tính được: điểm tổng kết không có cột, tính từ điểm quá trình và điểm thi.
- Khóa ngoại dùng `on_delete=PROTECT` khi dữ liệu tham chiếu quan trọng; không backfill dữ liệu cũ bằng giá trị bịa (để NULL hoặc giữ nguyên).
- Ràng buộc giữa nhiều dòng (ví dụ hai đợt đăng ký cùng học kỳ không chồng thời gian) không viết được bằng CHECK ở MySQL, phải kiểm tra ở form và ghi rõ trong docstring và `docs/erd.md`.

## Outputs

- Model + migration đã được người dùng xem SQL; `docs/erd.md` có mục mới; CSDL đã migrate sau khi được xác nhận.

## Verification

- `makemigrations --check` không còn thay đổi chờ; `check` sạch.
- SQL từ `sqlmigrate` khớp `docs/erd.md`; test kiểm tra được ràng buộc (`IntegrityError` khi vi phạm UNIQUE/CHECK).
- Ví dụ thực tế:
  - Lượt 2/6: thêm `dot_dang_ky` và `dang_ky_hoc_phan.trang_thai`; khi ràng buộc UNIQUE cũ chặn đăng ký lại sau khi hủy, người dùng chọn cho đăng ký lại, và vì MySQL không có UNIQUE có điều kiện nên dùng hai `GeneratedField` chỉ có giá trị khi `CON_HIEU_LUC` cộng UNIQUE trên cặp đó (`enrollment/models.py`), rồi xem lại `sqlmigrate`.
  - Lượt 3/6: `academics.0005` thêm `chuong_trinh_dao_tao`, `chi_tiet_chuong_trinh` và cột nullable `lop_hanh_chinh.chuong_trinh_dao_tao`; xác nhận giữ `PROTECT`, không backfill.
  - Lượt 4/6: `grades.0002_diem_da_cong_bo`; lượt 5/6: `classes.0002_lichthi` và `diem_danh.0001_initial`; lượt 6/6: `thong_bao.0001_initial` (bảng `da_doc_thong_bao` riêng thay vì thêm cột).
