# ERD: 13 bảng (PK khóa chính, FK khóa ngoại, UK duy nhất)

- tai_khoan: ma_tai_khoan INT PK; ten_dang_nhap VARCHAR(50) UK; mat_khau_ma_hoa VARCHAR(255); vai_tro VARCHAR(20) CHECK IN (PHONG_DAO_TAO, GIANG_VIEN, SINH_VIEN, CO_VAN_HOC_TAP); trang_thai BOOLEAN
- sinh_vien: ma_sinh_vien VARCHAR(20) PK; ho_ten VARCHAR(100); ngay_sinh DATE; email VARCHAR(100); so_dien_thoai VARCHAR(15); ma_lop FK lop_hanh_chinh; ma_tai_khoan FK tai_khoan UK
- giang_vien: ma_giang_vien VARCHAR(20) PK; ho_ten; email; so_dien_thoai; ma_tai_khoan FK tai_khoan UK
- co_van_hoc_tap: ma_co_van VARCHAR(20) PK; ho_ten; email; so_dien_thoai; ma_tai_khoan FK tai_khoan UK
- nganh_hoc: ma_nganh VARCHAR(20) PK; ten_nganh VARCHAR(100)
- lop_hanh_chinh: ma_lop VARCHAR(20) PK; ten_lop VARCHAR(100); ma_nganh FK nganh_hoc; ma_co_van FK co_van_hoc_tap
- hoc_phan: ma_hoc_phan VARCHAR(20) PK; ten_hoc_phan VARCHAR(100); so_tin_chi INT CHECK > 0
- dieu_kien_tien_quyet: ma_dieu_kien INT PK; ma_hoc_phan FK hoc_phan; ma_hoc_phan_tien_quyet FK hoc_phan; UNIQUE (ma_hoc_phan, ma_hoc_phan_tien_quyet); CHECK hai cột khác nhau
- lop_hoc_phan: ma_lop_hoc_phan VARCHAR(20) PK; hoc_ky VARCHAR(10); nam_hoc VARCHAR(9); si_so_toi_da INT CHECK > 0; ma_hoc_phan FK hoc_phan; ma_giang_vien FK giang_vien
- lich_hoc: ma_lich_hoc INT PK; thu INT CHECK 2 đến 8; tiet_bat_dau INT; so_tiet INT; phong_hoc VARCHAR(20); ma_lop_hoc_phan FK lop_hoc_phan
- dang_ky_hoc_phan: ma_dang_ky INT PK; thoi_gian_dang_ky DATETIME; ma_sinh_vien FK sinh_vien; ma_lop_hoc_phan FK lop_hoc_phan; UNIQUE (ma_sinh_vien, ma_lop_hoc_phan)
- diem: ma_diem INT PK; diem_qua_trinh DECIMAL(4,2); diem_thi DECIMAL(4,2); ma_dang_ky FK dang_ky_hoc_phan UK; CHECK điểm từ 0 đến 10; KHÔNG có cột điểm tổng kết
- tai_lieu_quy_che: ma_tai_lieu INT PK; ten_tai_lieu VARCHAR(200); duong_dan_file VARCHAR(255); ngay_tai_len DATE; ngay_cap_nhat DATE

## Bảng phụ của Django

Ngoài 13 bảng nghiệp vụ trên, Django tự tạo thêm một số bảng khi migrate. Các bảng này không lưu dữ liệu đào tạo, không đổi tên/cột của 13 bảng trên.

- `django_migrations`: Django tự quản lý lịch sử migrate.
- `django_session`: lưu phiên đăng nhập (bắt buộc để dùng đăng nhập bằng session của Django).
- `django_content_type`: phụ thuộc bắt buộc của app `django.contrib.auth`.
- `auth_permission`, `auth_group`, `auth_group_permissions`: do app `django.contrib.auth` tự tạo, nhưng dự án không gán quyền/nhóm nào cho tài khoản (không dùng `PermissionsMixin`), nên các bảng này luôn rỗng.

Quyết định tránh cột thừa ở bảng `tai_khoan` (model `TaiKhoan` trong `accounts/models.py`):

- Không dùng `django.contrib.admin` (không thêm vào `INSTALLED_APPS`) để không phát sinh bảng log admin.
- Model `TaiKhoan` kế thừa `AbstractBaseUser`, không kế thừa `PermissionsMixin`, nên không có cột `is_superuser` và không có bảng gán `groups`/`user_permissions` cho tài khoản.
- Bỏ cột `last_login` (đặt `last_login = None` trong model) vì ERD không có cột này, đồng thời ngắt việc Django tự ghi lại thời gian đăng nhập cuối cho cột đã bỏ.
- Thuộc tính Python `password` và `is_active` là quy ước bắt buộc của `AbstractBaseUser`/Django khi đăng nhập, nhưng ánh xạ `db_column` về đúng tên cột ERD: `password` → cột `mat_khau_ma_hoa`, `is_active` → cột `trang_thai`. Tên cột thật trong MySQL không đổi.

## Bổ sung ngoài đề (đã được giảng viên cho phép, lượt 1/6)

Các mục dưới đây bổ sung thêm cho 13 bảng ở trên, không xóa/sửa nội dung đã có phía trên.

- tai_khoan: thêm cột `phai_doi_mat_khau BOOLEAN DEFAULT FALSE` — bật khi Phòng Đào tạo đặt lại mật khẩu (mật khẩu tạm) hoặc tài khoản mới cần đổi mật khẩu ngay; tắt lại sau khi người dùng tự đổi mật khẩu thành công.
- hoc_ky (bảng mới, danh mục học kỳ): `id INT PK`; `hoc_ky SMALLINT` (số học kỳ); `nam_hoc VARCHAR(9)` (dạng "YYYY-YYYY", hai năm liên tiếp); `ngay_bat_dau DATE`; `ngay_ket_thuc DATE` CHECK sau ngày bắt đầu; UNIQUE (hoc_ky, nam_hoc). **Không phải khóa ngoại của `lop_hoc_phan`**: hai cột `lop_hoc_phan.hoc_ky`/`lop_hoc_phan.nam_hoc` giữ nguyên kiểu chuỗi tự do như đã có ở trên, không đổi cột, không thêm FK — màn hình tạo/sửa lớp học phần chỉ dùng danh mục này để chọn rồi sao chép giá trị chuỗi tương ứng vào hai cột đó. Hạn chế: sau khi sao chép, sửa một mục trong `hoc_ky` không tự cập nhật lại các `lop_hoc_phan` đã tạo trước đó; dữ liệu `lop_hoc_phan` có sẵn trước khi bảng này tồn tại (học kỳ/năm học chưa có trong danh mục) phải được Phòng Đào tạo thêm vào danh mục thì mới sửa được lớp học phần đó qua giao diện.

## Bổ sung ngoài đề (lượt 2/6)

- dang_ky_hoc_phan: thêm cột `trang_thai VARCHAR(20) CHECK IN (CON_HIEU_LUC, DA_HUY) DEFAULT CON_HIEU_LUC`. Hủy đăng ký chỉ đổi cột này sang `DA_HUY`, KHÔNG xóa dòng, để giữ lịch sử. Cho phép đăng ký lại sau khi hủy: mỗi lần hủy/đăng ký lại tạo một DÒNG MỚI (không sửa dòng cũ), nên bỏ ràng buộc UNIQUE (ma_sinh_vien, ma_lop_hoc_phan) cũ (chặn hoàn toàn việc đăng ký lại) và thay bằng ràng buộc chỉ cho phép TỐI ĐA MỘT dòng `CON_HIEU_LUC` cho mỗi cặp tại một thời điểm, các dòng `DA_HUY` lịch sử không bị giới hạn số lượng. **Cách hiện thực** (MySQL không có UNIQUE INDEX có điều kiện như PostgreSQL "UNIQUE ... WHERE"): thêm hai cột sinh (generated, `GENERATED ALWAYS AS (...) VIRTUAL`, có từ MySQL 5.7.6 — dùng qua `models.GeneratedField` của Django, có từ Django 5.0) là `ma_sinh_vien_hieu_luc`/`ma_lop_hoc_phan_hieu_luc`, chỉ có giá trị bằng `ma_sinh_vien`/`ma_lop_hoc_phan` khi `trang_thai=CON_HIEU_LUC`, còn lại là NULL; đặt `UNIQUE (ma_sinh_vien_hieu_luc, ma_lop_hoc_phan_hieu_luc)` — MySQL coi nhiều NULL trong một UNIQUE INDEX là không trùng nhau nên ràng buộc chỉ thực sự chặn trùng giữa các dòng `CON_HIEU_LUC`. Chọn ràng buộc ở CSDL (không chỉ kiểm tra ở service) để được đảm bảo bất kể đường vào code nào, và không cần đúng bản MySQL 8.0.46. Mọi nơi đếm sĩ số, xét trùng lịch/tiên quyết, và các thống kê đều chỉ tính các dòng `CON_HIEU_LUC` (xem `enrollment/services.py`).
- dot_dang_ky (bảng mới, đợt đăng ký học phần): `id INT PK`; `hoc_ky_id INT FK hoc_ky`; `ngay_mo DATETIME`; `ngay_dong DATETIME` CHECK sau ngày mở. **Hạn chế**: ràng buộc "hai đợt cùng học kỳ không được chồng lấp thời gian" là ràng buộc giữa NHIỀU DÒNG (không phải trong một dòng), nên không đặt được thành CHECK constraint ở MySQL (MySQL không có EXCLUDE constraint như PostgreSQL) — chỉ kiểm tra được ở tầng ứng dụng (`academics/forms.py`), không có ràng buộc CSDL chống chồng lấp; nếu có ai ghi thẳng vào CSDL bỏ qua ứng dụng thì ràng buộc này không được đảm bảo.

## Bổ sung ngoài đề (lượt 3/6)

- lop_hanh_chinh: thêm cột `chuong_trinh_dao_tao_id INT FK chuong_trinh_dao_tao NULL` — cho phép NULL vì lớp hành chính có sẵn trước khi có chức năng này chưa được gán chương trình đào tạo nào.
- chuong_trinh_dao_tao (bảng mới): `id INT PK`; `nganh_id VARCHAR(20) FK nganh_hoc`; `ten_chuong_trinh VARCHAR(150)`; `khoa_hoc VARCHAR(20)` (ví dụ "Khóa 1"); UNIQUE (nganh_id, khoa_hoc) — mỗi ngành/khóa chỉ có một chương trình, không có cột phiên bản riêng.
- chi_tiet_chuong_trinh (bảng mới): `id INT PK`; `chuong_trinh_id INT FK chuong_trinh_dao_tao`; `hoc_phan_id VARCHAR(20) FK hoc_phan`; `hoc_ky_du_kien SMALLINT` CHECK từ 1 đến 8; `bat_buoc BOOLEAN DEFAULT TRUE`; UNIQUE (chuong_trinh_id, hoc_phan_id). **`hoc_ky_du_kien` không phải khóa ngoại tới `hoc_ky`**: đây là học kỳ thứ mấy trong lộ trình chương trình khung (1..8), không gắn với một năm học lịch cụ thể nào, khác với bảng `hoc_ky` (lịch học kỳ thật theo năm học).

## Bổ sung ngoài đề (lượt 4/6)

- diem: thêm cột `da_cong_bo BOOLEAN DEFAULT FALSE` — Giảng viên bấm "Công bố điểm" mới bật lên; tự đặt lại về `FALSE` nếu điểm bị sửa sau khi đã công bố (phải công bố lại). Sinh viên chỉ xem được điểm/tính điểm trung bình/tích lũy/cảnh báo học vụ/coi là "đã đạt" ở trang tiến độ học tập của chính mình khi cột này `TRUE`; Giảng viên/Cố vấn học tập/Phòng Đào tạo luôn xem và dùng điểm thật bất kể cột này, vì họ cần biết để xử lý nghiệp vụ.

## Bổ sung ngoài đề (lượt 5/6)

- diem_danh (bảng mới, app `diem_danh`): `id INT PK`; `lop_hoc_phan_id VARCHAR(20) FK lop_hoc_phan`; `sinh_vien_id VARCHAR(20) FK sinh_vien`; `ngay_diem_danh DATE`; `co_mat BOOLEAN DEFAULT TRUE`; UNIQUE (lop_hoc_phan_id, sinh_vien_id, ngay_diem_danh). Chỉ để theo dõi chuyên cần, KHÔNG tính vào điểm quá trình hay bất kỳ cột nào ở bảng `diem`.
- lich_thi (bảng mới, app `classes`): `ma_lich_thi INT PK`; `ma_lop_hoc_phan VARCHAR(20) FK lop_hoc_phan UNIQUE` (mỗi lớp học phần tối đa một lịch thi); `ngay_thi DATE`; `gio_bat_dau TIME`; `thoi_luong_phut INT` CHECK > 0; `phong_thi VARCHAR(20)`.

## Bổ sung ngoài đề (lượt 6/6)

Phần A (xuất bảng điểm/thời khóa biểu ra PDF) và Phần B (nhập sinh viên/xuất báo cáo bằng Excel) không thêm/đổi bảng nào — chỉ đọc dữ liệu đã có hoặc ghi vào các bảng `sinh_vien`/`tai_khoan` đã có qua đúng luồng tạo sinh viên/tài khoản sẵn có.

- thong_bao (bảng mới, app `thong_bao`): `id INT PK`; `tieu_de VARCHAR(200)`; `noi_dung TEXT`; `nguoi_gui INT FK tai_khoan`; `doi_tuong VARCHAR(20)` CHECK IN (TAT_CA, PHONG_DAO_TAO, GIANG_VIEN, SINH_VIEN, CO_VAN_HOC_TAP, LOP_HOC_PHAN, LOP_HANH_CHINH); `ma_lop_hoc_phan VARCHAR(20) FK lop_hoc_phan NULL` (chỉ có giá trị khi doi_tuong=LOP_HOC_PHAN); `ma_lop_hanh_chinh VARCHAR(20) FK lop_hanh_chinh NULL` (chỉ có giá trị khi doi_tuong=LOP_HANH_CHINH); `thoi_gian_gui DATETIME` tự động điền lúc tạo. Bốn giá trị `doi_tuong` theo vai trò (PHONG_DAO_TAO/GIANG_VIEN/SINH_VIEN/CO_VAN_HOC_TAP) dùng đúng chuỗi của `accounts.VaiTro`, không thêm cột `vai_tro` riêng.
- da_doc_thong_bao (bảng mới, app `thong_bao`): `id INT PK`; `ma_thong_bao INT FK thong_bao`; `ma_tai_khoan INT FK tai_khoan`; `thoi_gian_doc DATETIME` tự động điền lúc tạo; UNIQUE (ma_thong_bao, ma_tai_khoan). Dùng để đánh dấu đã đọc mà không cần thêm cột vào `thong_bao`.