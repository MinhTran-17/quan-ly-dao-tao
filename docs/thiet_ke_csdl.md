# Thiết kế cơ sở dữ liệu

CSDL MySQL 8.0, tên `qldt`, bảng mã `utf8mb4`. Gồm **21 bảng nghiệp vụ**: 13 bảng theo đề bài và 8 bảng bổ sung (được giảng viên cho phép). Tên bảng và tên cột viết `snake_case`. Kiểu dữ liệu lấy đúng theo CSDL MySQL đang chạy.

Quy ước: PK là khóa chính, FK là khóa ngoại, NOT NULL là bắt buộc có giá trị. Khóa ngoại trong MySQL để mặc định `NO ACTION`: không xóa được bản ghi cha khi còn bản ghi con. Django xử lý thêm ở tầng ứng dụng: mọi khóa ngoại là `PROTECT` (báo lỗi, không cho xóa), riêng `da_doc_thong_bao.ma_thong_bao` là `CASCADE` (xóa thông báo thì xóa luôn các lượt đã đọc). Không có cột điểm tổng kết: điểm tổng kết = 0,3 × điểm quá trình + 0,7 × điểm thi, tính khi cần.

## 1. Danh mục các bảng dữ liệu

| STT | Tên bảng | Thực thể | Mô tả | Nguồn |
|---|---|---|---|---|
| 1 | `tai_khoan` | Tài khoản | Tài khoản đăng nhập của mọi người dùng, xác định vai trò để phân quyền. | Đề bài |
| 2 | `sinh_vien` | Sinh viên | Hồ sơ sinh viên, gắn với một tài khoản và một lớp hành chính. | Đề bài |
| 3 | `giang_vien` | Giảng viên | Hồ sơ giảng viên, gắn với một tài khoản. | Đề bài |
| 4 | `co_van_hoc_tap` | Cố vấn học tập | Hồ sơ cố vấn học tập, gắn với một tài khoản. | Đề bài |
| 5 | `nganh_hoc` | Ngành học | Danh mục ngành đào tạo. | Đề bài |
| 6 | `lop_hanh_chinh` | Lớp hành chính | Lớp sinh hoạt của sinh viên, thuộc một ngành, do một cố vấn phụ trách. | Đề bài |
| 7 | `hoc_phan` | Học phần | Danh mục học phần (môn học) và số tín chỉ. | Đề bài |
| 8 | `dieu_kien_tien_quyet` | Điều kiện tiên quyết | Cặp học phần – học phần tiên quyết phải đạt trước khi đăng ký. | Đề bài |
| 9 | `lop_hoc_phan` | Lớp học phần | Lớp mở cho một học phần trong một học kỳ, do một giảng viên dạy. | Đề bài |
| 10 | `lich_hoc` | Lịch học | Các buổi học trong tuần của lớp học phần (thứ, tiết, phòng). | Đề bài |
| 11 | `dang_ky_hoc_phan` | Đăng ký học phần | Lượt đăng ký của sinh viên vào lớp học phần; hủy chỉ đổi trạng thái, không xóa. | Đề bài |
| 12 | `diem` | Điểm | Điểm quá trình và điểm thi của một lượt đăng ký; không lưu điểm tổng kết. | Đề bài |
| 13 | `tai_lieu_quy_che` | Tài liệu quy chế | Tệp quy chế (PDF/DOCX) dùng cho chatbot hỏi đáp quy chế. | Đề bài |
| 14 | `hoc_ky` | Học kỳ | Danh mục học kỳ theo năm học, có ngày bắt đầu và kết thúc. | Bổ sung |
| 15 | `dot_dang_ky` | Đợt đăng ký | Khoảng thời gian mở đăng ký học phần của một học kỳ. | Bổ sung |
| 16 | `chuong_trinh_dao_tao` | Chương trình đào tạo | Chương trình khung của một ngành theo khóa học. | Bổ sung |
| 17 | `chi_tiet_chuong_trinh` | Chi tiết chương trình | Các học phần thuộc chương trình đào tạo và học kỳ dự kiến. | Bổ sung |
| 18 | `lich_thi` | Lịch thi | Lịch thi của lớp học phần (mỗi lớp tối đa một lịch thi). | Bổ sung |
| 19 | `diem_danh` | Điểm danh | Kết quả điểm danh từng sinh viên theo ngày của lớp học phần. | Bổ sung |
| 20 | `thong_bao` | Thông báo | Thông báo do một tài khoản gửi tới một nhóm đối tượng. | Bổ sung |
| 21 | `da_doc_thong_bao` | Đã đọc thông báo | Đánh dấu tài khoản nào đã đọc thông báo nào. | Bổ sung |

## 2. Chi tiết các bảng

### 2.1. Bảng `tai_khoan` (Tài khoản)

Tài khoản đăng nhập của mọi người dùng, xác định vai trò để phân quyền.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_tai_khoan` | INT AUTO_INCREMENT | PK | Mã tài khoản |
| 2 | `ten_dang_nhap` | VARCHAR(50) | UNIQUE; NOT NULL | Tên đăng nhập |
| 3 | `mat_khau_ma_hoa` | VARCHAR(255) | NOT NULL | Mật khẩu đã mã hóa (băm) |
| 4 | `vai_tro` | VARCHAR(20) | NOT NULL; IN (PHONG_DAO_TAO, GIANG_VIEN, SINH_VIEN, CO_VAN_HOC_TAP) | Vai trò người dùng |
| 5 | `trang_thai` | TINYINT(1) | NOT NULL; mặc định TRUE | Trạng thái hoạt động (FALSE = bị khóa) |
| 6 | `phai_doi_mat_khau` | TINYINT(1) | NOT NULL; mặc định FALSE | Bắt buộc đổi mật khẩu ở lần đăng nhập tới |

Ràng buộc mức bảng:

- CHECK `ck_tai_khoan_vai_tro`: vai_tro thuộc 4 vai trò

### 2.2. Bảng `sinh_vien` (Sinh viên)

Hồ sơ sinh viên, gắn với một tài khoản và một lớp hành chính.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_sinh_vien` | VARCHAR(20) | PK | Mã sinh viên |
| 2 | `ho_ten` | VARCHAR(100) | NOT NULL | Họ và tên |
| 3 | `ngay_sinh` | DATE | NOT NULL | Ngày sinh |
| 4 | `email` | VARCHAR(100) | NOT NULL | Email liên hệ |
| 5 | `so_dien_thoai` | VARCHAR(15) | NOT NULL | Số điện thoại |
| 6 | `ma_lop` | VARCHAR(20) | FK → lop_hanh_chinh; NOT NULL | Mã lớp hành chính |
| 7 | `ma_tai_khoan` | INT | FK → tai_khoan; UNIQUE; NOT NULL | Mã tài khoản |

### 2.3. Bảng `giang_vien` (Giảng viên)

Hồ sơ giảng viên, gắn với một tài khoản.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_giang_vien` | VARCHAR(20) | PK | Mã giảng viên |
| 2 | `ho_ten` | VARCHAR(100) | NOT NULL | Họ và tên |
| 3 | `email` | VARCHAR(100) | NOT NULL | Email liên hệ |
| 4 | `so_dien_thoai` | VARCHAR(15) | NOT NULL | Số điện thoại |
| 5 | `ma_tai_khoan` | INT | FK → tai_khoan; UNIQUE; NOT NULL | Mã tài khoản |

### 2.4. Bảng `co_van_hoc_tap` (Cố vấn học tập)

Hồ sơ cố vấn học tập, gắn với một tài khoản.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_co_van` | VARCHAR(20) | PK | Mã cố vấn học tập |
| 2 | `ho_ten` | VARCHAR(100) | NOT NULL | Họ và tên |
| 3 | `email` | VARCHAR(100) | NOT NULL | Email liên hệ |
| 4 | `so_dien_thoai` | VARCHAR(15) | NOT NULL | Số điện thoại |
| 5 | `ma_tai_khoan` | INT | FK → tai_khoan; UNIQUE; NOT NULL | Mã tài khoản |

### 2.5. Bảng `nganh_hoc` (Ngành học)

Danh mục ngành đào tạo.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_nganh` | VARCHAR(20) | PK | Mã ngành |
| 2 | `ten_nganh` | VARCHAR(100) | NOT NULL | Tên ngành |

### 2.6. Bảng `lop_hanh_chinh` (Lớp hành chính)

Lớp sinh hoạt của sinh viên, thuộc một ngành, do một cố vấn phụ trách.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_lop` | VARCHAR(20) | PK | Mã lớp hành chính |
| 2 | `ten_lop` | VARCHAR(100) | NOT NULL | Tên lớp |
| 3 | `ma_nganh` | VARCHAR(20) | FK → nganh_hoc; NOT NULL | Mã ngành |
| 4 | `ma_co_van` | VARCHAR(20) | FK → co_van_hoc_tap; NOT NULL | Mã cố vấn học tập |
| 5 | `chuong_trinh_dao_tao_id` | INT | FK → chuong_trinh_dao_tao; NULL | Chương trình đào tạo áp dụng |

### 2.7. Bảng `hoc_phan` (Học phần)

Danh mục học phần (môn học) và số tín chỉ.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_hoc_phan` | VARCHAR(20) | PK | Mã học phần |
| 2 | `ten_hoc_phan` | VARCHAR(100) | NOT NULL | Tên học phần |
| 3 | `so_tin_chi` | INT | NOT NULL | Số tín chỉ |

Ràng buộc mức bảng:

- CHECK `ck_hoc_phan_so_tin_chi_duong`: so_tin_chi > 0

### 2.8. Bảng `dieu_kien_tien_quyet` (Điều kiện tiên quyết)

Cặp học phần – học phần tiên quyết phải đạt trước khi đăng ký.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_dieu_kien` | INT AUTO_INCREMENT | PK | Mã điều kiện |
| 2 | `ma_hoc_phan` | VARCHAR(20) | FK → hoc_phan; NOT NULL | Mã học phần |
| 3 | `ma_hoc_phan_tien_quyet` | VARCHAR(20) | FK → hoc_phan; NOT NULL | Mã học phần tiên quyết |

Ràng buộc mức bảng:

- UNIQUE `uk_dieu_kien_tien_quyet_cap`: (ma_hoc_phan, ma_hoc_phan_tien_quyet)
- CHECK `ck_dieu_kien_tien_quyet_khac_hoc_phan`: ma_hoc_phan ≠ ma_hoc_phan_tien_quyet

### 2.9. Bảng `lop_hoc_phan` (Lớp học phần)

Lớp mở cho một học phần trong một học kỳ, do một giảng viên dạy.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_lop_hoc_phan` | VARCHAR(20) | PK | Mã lớp học phần |
| 2 | `hoc_ky` | VARCHAR(10) | NOT NULL | Học kỳ mở lớp |
| 3 | `nam_hoc` | VARCHAR(9) | NOT NULL | Năm học mở lớp |
| 4 | `si_so_toi_da` | INT | NOT NULL | Sĩ số tối đa |
| 5 | `ma_hoc_phan` | VARCHAR(20) | FK → hoc_phan; NOT NULL | Mã học phần |
| 6 | `ma_giang_vien` | VARCHAR(20) | FK → giang_vien; NOT NULL | Mã giảng viên |

Ràng buộc mức bảng:

- CHECK `ck_lop_hoc_phan_si_so_duong`: si_so_toi_da > 0

### 2.10. Bảng `lich_hoc` (Lịch học)

Các buổi học trong tuần của lớp học phần (thứ, tiết, phòng).

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_lich_hoc` | INT AUTO_INCREMENT | PK | Mã lịch học |
| 2 | `thu` | INT | NOT NULL | Thứ trong tuần (2–8, 8 = Chủ nhật) |
| 3 | `tiet_bat_dau` | INT | NOT NULL | Tiết bắt đầu |
| 4 | `so_tiet` | INT | NOT NULL | Số tiết |
| 5 | `phong_hoc` | VARCHAR(20) | NOT NULL | Phòng học |
| 6 | `ma_lop_hoc_phan` | VARCHAR(20) | FK → lop_hoc_phan; NOT NULL | Mã lớp học phần |

Ràng buộc mức bảng:

- CHECK `ck_lich_hoc_thu_hop_le`: 2 ≤ thu ≤ 8

### 2.11. Bảng `dang_ky_hoc_phan` (Đăng ký học phần)

Lượt đăng ký của sinh viên vào lớp học phần; hủy chỉ đổi trạng thái, không xóa.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_dang_ky` | INT AUTO_INCREMENT | PK | Mã đăng ký |
| 2 | `thoi_gian_dang_ky` | DATETIME(6) | NOT NULL | Thời điểm đăng ký |
| 3 | `trang_thai` | VARCHAR(20) | NOT NULL; mặc định CON_HIEU_LUC; IN (CON_HIEU_LUC, DA_HUY) | Trạng thái đăng ký |
| 4 | `ma_sinh_vien` | VARCHAR(20) | FK → sinh_vien; NOT NULL | Mã sinh viên |
| 5 | `ma_lop_hoc_phan` | VARCHAR(20) | FK → lop_hoc_phan; NOT NULL | Mã lớp học phần |
| 6 | `ma_sinh_vien_hieu_luc` | VARCHAR(20) GENERATED | NULL | Cột sinh: mã sinh viên khi còn hiệu lực, ngược lại NULL |
| 7 | `ma_lop_hoc_phan_hieu_luc` | VARCHAR(20) GENERATED | NULL | Cột sinh: mã lớp khi còn hiệu lực, ngược lại NULL |

Ràng buộc mức bảng:

- UNIQUE `uk_dang_ky_hoc_phan_dang_hieu_luc`: (ma_sinh_vien_hieu_luc, ma_lop_hoc_phan_hieu_luc): mỗi cặp sinh viên – lớp tối đa 1 đăng ký còn hiệu lực
- CHECK `ck_dang_ky_hoc_phan_trang_thai`: trang_thai IN (CON_HIEU_LUC, DA_HUY)

### 2.12. Bảng `diem` (Điểm)

Điểm quá trình và điểm thi của một lượt đăng ký; không lưu điểm tổng kết.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_diem` | INT AUTO_INCREMENT | PK | Mã điểm |
| 2 | `diem_qua_trinh` | DECIMAL(4,2) | NULL | Điểm quá trình (0–10) |
| 3 | `diem_thi` | DECIMAL(4,2) | NULL | Điểm thi (0–10) |
| 4 | `ma_dang_ky` | INT | FK → dang_ky_hoc_phan; UNIQUE; NOT NULL | Mã đăng ký |
| 5 | `da_cong_bo` | TINYINT(1) | NOT NULL; mặc định FALSE | Điểm đã công bố cho sinh viên chưa |

Ràng buộc mức bảng:

- CHECK `ck_diem_trong_khoang`: diem_qua_trinh, diem_thi NULL hoặc trong [0, 10]

### 2.13. Bảng `tai_lieu_quy_che` (Tài liệu quy chế)

Tệp quy chế (PDF/DOCX) dùng cho chatbot hỏi đáp quy chế.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_tai_lieu` | INT AUTO_INCREMENT | PK | Mã tài liệu |
| 2 | `ten_tai_lieu` | VARCHAR(200) | NOT NULL | Tên tài liệu |
| 3 | `duong_dan_file` | VARCHAR(255) | NOT NULL | Đường dẫn tệp tài liệu |
| 4 | `ngay_tai_len` | DATE | NOT NULL | Ngày tải lên |
| 5 | `ngay_cap_nhat` | DATE | NOT NULL | Ngày cập nhật tệp |

### 2.14. Bảng `hoc_ky` (Học kỳ)

Danh mục học kỳ theo năm học, có ngày bắt đầu và kết thúc.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã học kỳ (tự tăng) |
| 2 | `hoc_ky` | SMALLINT UNSIGNED | NOT NULL | Số thứ tự học kỳ |
| 3 | `nam_hoc` | VARCHAR(9) | NOT NULL | Năm học (dạng YYYY-YYYY) |
| 4 | `ngay_bat_dau` | DATE | NOT NULL | Ngày bắt đầu học kỳ |
| 5 | `ngay_ket_thuc` | DATE | NOT NULL | Ngày kết thúc học kỳ |

Ràng buộc mức bảng:

- UNIQUE `uk_hoc_ky_nam_hoc`: (hoc_ky, nam_hoc)
- CHECK `ck_hoc_ky_ngay_ket_thuc_sau_ngay_bat_dau`: ngay_ket_thuc > ngay_bat_dau

### 2.15. Bảng `dot_dang_ky` (Đợt đăng ký)

Khoảng thời gian mở đăng ký học phần của một học kỳ.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã đợt đăng ký (tự tăng) |
| 2 | `hoc_ky_id` | INT | FK → hoc_ky; NOT NULL | Học kỳ của đợt |
| 3 | `ngay_mo` | DATETIME(6) | NOT NULL | Thời điểm mở đăng ký |
| 4 | `ngay_dong` | DATETIME(6) | NOT NULL | Thời điểm đóng đăng ký |

Ràng buộc mức bảng:

- CHECK `ck_dot_dang_ky_ngay_dong_sau_ngay_mo`: ngay_dong > ngay_mo

### 2.16. Bảng `chuong_trinh_dao_tao` (Chương trình đào tạo)

Chương trình khung của một ngành theo khóa học.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã chương trình đào tạo (tự tăng) |
| 2 | `nganh_id` | VARCHAR(20) | FK → nganh_hoc; NOT NULL | Ngành của chương trình |
| 3 | `ten_chuong_trinh` | VARCHAR(150) | NOT NULL | Tên chương trình |
| 4 | `khoa_hoc` | VARCHAR(20) | NOT NULL | Khóa học (ví dụ "Khóa 1") |

Ràng buộc mức bảng:

- UNIQUE `uk_chuong_trinh_dao_tao_nganh_khoa_hoc`: (nganh_id, khoa_hoc)

### 2.17. Bảng `chi_tiet_chuong_trinh` (Chi tiết chương trình)

Các học phần thuộc chương trình đào tạo và học kỳ dự kiến.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã chi tiết chương trình (tự tăng) |
| 2 | `chuong_trinh_id` | INT | FK → chuong_trinh_dao_tao; NOT NULL | Chương trình đào tạo |
| 3 | `hoc_phan_id` | VARCHAR(20) | FK → hoc_phan; NOT NULL | Học phần |
| 4 | `hoc_ky_du_kien` | SMALLINT UNSIGNED | NOT NULL | Học kỳ dự kiến trong lộ trình (1–8) |
| 5 | `bat_buoc` | TINYINT(1) | NOT NULL; mặc định TRUE | Học phần bắt buộc hay tự chọn |

Ràng buộc mức bảng:

- UNIQUE `uk_chi_tiet_chuong_trinh_hoc_phan`: (chuong_trinh_id, hoc_phan_id)
- CHECK `ck_chi_tiet_chuong_trinh_hoc_ky_du_kien_hop_le`: 1 ≤ hoc_ky_du_kien ≤ 8

### 2.18. Bảng `lich_thi` (Lịch thi)

Lịch thi của lớp học phần (mỗi lớp tối đa một lịch thi).

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `ma_lich_thi` | INT AUTO_INCREMENT | PK | Mã lịch thi |
| 2 | `ma_lop_hoc_phan` | VARCHAR(20) | FK → lop_hoc_phan; UNIQUE; NOT NULL | Mã lớp học phần |
| 3 | `ngay_thi` | DATE | NOT NULL | Ngày thi |
| 4 | `gio_bat_dau` | TIME(6) | NOT NULL | Giờ bắt đầu thi |
| 5 | `thoi_luong_phut` | INT UNSIGNED | NOT NULL | Thời lượng thi (phút) |
| 6 | `phong_thi` | VARCHAR(20) | NOT NULL | Phòng thi |

Ràng buộc mức bảng:

- CHECK `ck_lich_thi_thoi_luong_duong`: thoi_luong_phut > 0

### 2.19. Bảng `diem_danh` (Điểm danh)

Kết quả điểm danh từng sinh viên theo ngày của lớp học phần.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã điểm danh (tự tăng) |
| 2 | `lop_hoc_phan_id` | VARCHAR(20) | FK → lop_hoc_phan; NOT NULL | Lớp học phần |
| 3 | `sinh_vien_id` | VARCHAR(20) | FK → sinh_vien; NOT NULL | Sinh viên |
| 4 | `ngay_diem_danh` | DATE | NOT NULL | Ngày điểm danh |
| 5 | `co_mat` | TINYINT(1) | NOT NULL; mặc định TRUE | Có mặt hay vắng |

Ràng buộc mức bảng:

- UNIQUE `uk_diem_danh_lop_sinh_vien_ngay`: (lop_hoc_phan_id, sinh_vien_id, ngay_diem_danh)

### 2.20. Bảng `thong_bao` (Thông báo)

Thông báo do một tài khoản gửi tới một nhóm đối tượng.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã thông báo (tự tăng) |
| 2 | `tieu_de` | VARCHAR(200) | NOT NULL | Tiêu đề |
| 3 | `noi_dung` | LONGTEXT | NOT NULL | Nội dung thông báo |
| 4 | `nguoi_gui` | INT | FK → tai_khoan; NOT NULL | Tài khoản gửi |
| 5 | `doi_tuong` | VARCHAR(20) | NOT NULL; IN (TAT_CA, PHONG_DAO_TAO, GIANG_VIEN, SINH_VIEN, CO_VAN_HOC_TAP, LOP_HOC_PHAN, LOP_HANH_CHINH) | Đối tượng nhận thông báo |
| 6 | `ma_lop_hoc_phan` | VARCHAR(20) | FK → lop_hoc_phan; NULL | Lớp học phần nhận (khi đối tượng = LOP_HOC_PHAN) |
| 7 | `ma_lop_hanh_chinh` | VARCHAR(20) | FK → lop_hanh_chinh; NULL | Lớp hành chính nhận (khi đối tượng = LOP_HANH_CHINH) |
| 8 | `thoi_gian_gui` | DATETIME(6) | NOT NULL | Thời điểm gửi |

Ràng buộc mức bảng:

- CHECK `ck_thong_bao_doi_tuong`: doi_tuong thuộc 7 loại đối tượng

### 2.21. Bảng `da_doc_thong_bao` (Đã đọc thông báo)

Đánh dấu tài khoản nào đã đọc thông báo nào.

| STT | Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|---|
| 1 | `id` | INT AUTO_INCREMENT | PK | Mã đã đọc thông báo (tự tăng) |
| 2 | `ma_thong_bao` | INT | FK → thong_bao; NOT NULL | Thông báo |
| 3 | `ma_tai_khoan` | INT | FK → tai_khoan; NOT NULL | Mã tài khoản |
| 4 | `thoi_gian_doc` | DATETIME(6) | NOT NULL | Thời điểm đọc |

Ràng buộc mức bảng:

- UNIQUE `uk_da_doc_thong_bao`: (ma_thong_bao, ma_tai_khoan)

## 3. Biểu đồ

Biểu đồ ERD và Database diagram nằm trong file `docs/so_do/thiet_ke_csdl.drawio` (2 trang).

- **Biểu đồ ERD** (mức logic): thực thể, thuộc tính (khóa chính gạch chân), mối liên kết có tên và bản số theo ký hiệu chân chim. Không ghi kiểu dữ liệu, không ghi cột khóa ngoại.
- **Database diagram** (mức vật lý): đúng tên bảng, tên cột, kiểu dữ liệu MySQL, đánh dấu PK/FK, đường nối là khóa ngoại.
