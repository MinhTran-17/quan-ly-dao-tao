# Thiết kế giao diện

Toàn bộ CSS dùng chung đặt trong một khối `<style>` duy nhất ở `templates/base.html` (không
dùng CDN/thư viện ngoài, không lặp lại ở từng trang, chạy được cả khi `DEBUG=False` vì không
phụ thuộc static files). Ngoại lệ duy nhất: CSS của layout riêng vai trò Sinh viên nằm ở
`templates/sinh_vien/_css.html`, được `base.html` nạp trong một khối `<style>` thứ hai chỉ khi
`user.vai_tro == 'SINH_VIEN'` (xem mục "Layout riêng của Sinh viên"). Đây là bản ghi lại bảng
màu, hệ nút, và quy ước đặt tên lớp CSS để giữ nhất quán khi thêm trang mới.

## Bảng màu (biến CSS trong `:root`)

| Biến | Giá trị | Dùng cho |
|---|---|---|
| `--mau-xanh-chinh` | `#1877F2` | Màu thương hiệu chính: nút chính, liên kết, tab đang chọn |
| `--mau-xanh-chinh-hover` | `#166FE5` | Hover của nút chính |
| `--mau-xanh-nhat` | `#E7F3FF` | Nền nút nhẹ, nhãn AI, chip "đã đăng ký", hover liên kết trong đoạn văn |
| `--mau-nen-trang` | `#F0F2F5` | Nền toàn trang, nền tiêu đề bảng |
| `--mau-the` | `#FFFFFF` | Nền thẻ, bảng |
| `--mau-chu` | `#050505` | Màu chữ chính |
| `--mau-chu-phu` | `#65676B` | Chữ phụ, nhãn, chữ tiêu đề bảng |
| `--mau-vien` | `#CED0D4` | Viền input, viền dưới ô bảng |
| `--mau-nut-xam` | `#E4E6EB` | Nền nút phụ |
| `--mau-nut-xam-hover` | `#D8DADF` | Hover nút phụ |
| `--mau-do` | `#E41E3F` | Chữ nút nguy hiểm, viền/khung thông báo lỗi |
| `--mau-do-nhat` | `#FFEBE9` | Nền nút nguy hiểm, nền thông báo lỗi |
| `--mau-xanh-la` | `#42B72A` | Viền thông báo thành công, chip "đủ điều kiện" |
| `--mau-vang` | `#F7B928` | Viền thông báo cảnh báo, chip "thiếu tiên quyết" |
| `--mau-cam-nhat` / `--mau-cam-chu` | `#FFE8D6` / `#9A4B00` | Chip "trùng lịch" |
| `--mau-xam-nhat` | `#EDEDED` | Nút vô hiệu, chip "đã đầy"/"đã khóa" |

Font: `-apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`, cỡ chữ gốc `15px`,
tiêu đề (`h1`-`h4`) đậm (`font-weight: 800`).

## Hệ nút (`.nut`)

Lớp gốc `.nut` định nghĩa hình dạng chung (bo góc 6px, đậm chữ, có hover/focus, chuyển màu
mượt `.15s ease`); kết hợp với một lớp màu và (tùy chọn) một lớp cỡ:

| Lớp màu | Dùng khi |
|---|---|
| `.nut-chinh` | Hành động chính của trang (Lưu, Đăng nhập, Đăng ký, Gửi câu hỏi, + Tạo...) |
| `.nut-phu` | Hành động phụ/trung tính (Hủy, Đăng xuất, Xóa lọc, phân trang) |
| `.nut-nhe` | Hành động nhẹ liên quan tới AI hoặc "Sửa"/"Xem" trong bảng |
| `.nut-nguy-hiem` | Hành động phá hủy/hạn chế (Khóa, Xóa) |
| `.nut-vo-hieu` | Trạng thái không thể thao tác (vd. "Đã đầy") — không phải liên kết thật |

Lớp cỡ `.nut-nho` giảm padding/cỡ chữ, dùng cho nút trong cột "Thao tác" của bảng để
không phá vỡ chiều cao hàng. `.nut-day-du` kéo nút rộng hết chiều ngang (nút đăng nhập).
Nhiều nút cạnh nhau trong một ô bọc trong `<div class="nhom-nut">` (flex, có khoảng cách,
tự xuống dòng khi chật chỗ) để không rối khi màn hình hẹp.

Mọi liên kết hành động (Sửa, Khóa, Xóa, Tải về, Đăng ký, "+ Tạo...", Đăng xuất, "Mở"...)
đều là `.nut`, không phải chữ gạch chân. Liên kết thường trong đoạn văn/danh sách (ví dụ
"Nhờ AI tư vấn...") giữ nguyên dạng liên kết văn bản, màu `--mau-xanh-chinh`, không gạch
chân, đổi nền nhạt khi hover.

## Logo dùng chung

`templates/_logo.html` render một biểu tượng SVG vẽ trực tiếp (khối vuông bo góc nền xanh,
mũ tốt nghiệp trắng ở giữa — không dùng ảnh/CDN ngoài) kèm tên trường + tên hệ thống, lấy
từ `settings.TEN_TRUONG`/`settings.TEN_HE_THONG` (đọc từ `.env`, đưa vào mọi template qua
context processor `qldt.context_processors.thong_tin_he_thong`). Cùng một đoạn HTML này
được `{% include %}` ở hai nơi, chỉ khác nhau bởi CSS của lớp cha bọc ngoài:
- `.sv-banner .logo`: icon 48px, hiện đủ hai dòng chữ đậm màu xanh (banner của mọi vai trò
  đã đăng nhập: Sinh viên và các vai trò dùng khung `nhan_vien/_khung_dau.html`).
- `.the-dang-nhap__logo .logo`: xếp dọc, icon lớn hơn, hiện đủ cả tên trường và tên hệ
  thống, dùng ở trang đăng nhập.

Thêm hạng mục mới cần logo chỉ cần `{% include '_logo.html' %}` rồi viết CSS riêng cho lớp
cha bọc ngoài theo đúng khuôn mẫu trên, không cần sửa `_logo.html`.

## Bố cục trang

- Thanh menu: mọi vai trò đã đăng nhập dùng cùng bộ lớp `.sv-*` (banner trắng có logo + thanh menu
  xanh `#1877F2` cố định, xem "Layout riêng của Sinh viên" và "Menu Phòng Đào tạo, Giảng viên, Cố vấn
  học tập" bên dưới). Trạng thái đang chọn xác định bằng `request.resolver_match.url_name`/`app_name`
  ngay trong template, không cần sửa view.
- `main`: khung nội dung tối đa `1100px`, căn giữa.
- `.khung`: thẻ trắng bo góc 8px, bóng nhẹ — đơn vị hiển thị cơ bản (form, khối kết quả...).
- `.luoi-the` / `.the-chuc-nang`: lưới thẻ chức năng ở trang chủ, mỗi thẻ có tiêu đề, mô tả
  một dòng, nút "Mở"; `.nhom-chuc-nang` gom các thẻ theo nhóm với tiêu đề nhóm viết hoa nhỏ.
- `.khung-bang`: bọc ngoài `<table>` để có bo góc, bóng, và cuộn ngang khi bảng rộng hơn màn
  hình (thay vì để bảng tràn ra ngoài trang trên di động).
- `.bo-loc`: form lọc/tìm kiếm xếp hàng ngang, mỗi trường trong `.truong` co giãn đều, nút
  "Lọc"/"Tìm" (`.nut-chinh`) đi kèm "Xóa lọc" (`.nut-phu`) trỏ về URL không tham số.
- `.phan-trang`: dòng điều hướng trang (« Trước / Trang x/y / Sau »), style bằng `.nut-phu
  .nut-nho`. Có sẵn partial dùng chung `templates/_phan_trang.html` cho các trang không cần
  giữ lại tham số lọc khi chuyển trang; trang nào cần giữ lại (vd. danh sách tài khoản) tự
  viết khối tương đương với cùng lớp CSS.
- `templates/_truong_form.html`: partial dùng chung để render một `form` Django thành các
  khối `.truong` (nhãn, ô nhập, ghi chú, lỗi) — dùng ở mọi trang tạo/sửa để không lặp mã.

## Layout riêng của Sinh viên (lượt giao diện 1/3)

Chỉ áp dụng khi `user.vai_tro == 'SINH_VIEN'`; các vai trò khác dùng khung riêng nhưng cùng kiểu dáng
menu (mục "Menu Phòng Đào tạo, Giảng viên, Cố vấn học tập"). Chỉ đổi giao diện — không đổi view, URL, model, settings. Bảng màu Facebook giữ nguyên,
phần CSS mới chỉ dùng lại biến `:root` có sẵn (có test kiểm tra không khai báo biến màu mới).

Cấu trúc (`templates/base.html` rẽ nhánh và `{% include %}` 3 partial trong `templates/sinh_vien/`):

| Partial | Nội dung |
|---|---|
| `_khung_dau.html` | Sprite icon SVG nội tuyến (`<symbol id="sv-i-...">`, gọi bằng `<use>`), banner, thanh menu, chuông thông báo, chip người dùng, breadcrumb, JS mở/đóng dropdown |
| `_chan_trang.html` | Footer 3 cột + dòng bản quyền |
| `_css.html` | Toàn bộ CSS của layout này (tiền tố lớp `sv-`) |

- **Banner** (`.sv-banner`): nền trắng, viền dưới 1px, `_logo.html` (icon vuông bo góc) cùng hai
  dòng tên trường (`TEN_TRUONG`) và tên hệ thống (`TEN_HE_THONG`), đậm, màu `--mau-xanh-chinh`.
- **Thanh menu** (`.sv-thanh-menu`): full width, nền `--mau-xanh-chinh` (#1877F2), chữ và icon
  trắng, bóng nhẹ, `position: sticky`. Mỗi mục có icon + chữ; hover nền trắng mờ; mục đang chọn có
  `border-bottom: 3px` **trắng** cộng nền trắng mờ (xanh đậm hơn sẽ không phân biệt được trên nền
  xanh). Viền focus bàn phím của thanh là trắng. Bốn mục chính: Trang chủ,
  Đăng ký học phần (Đăng ký học phần / Thời khóa biểu / Lịch sử đăng ký), Học tập (Tiến độ
  chương trình đào tạo / Bảng điểm / Lịch thi / Điểm danh), Trợ lý AI (Tư vấn đăng ký / Tóm tắt
  kết quả / Hỏi đáp quy chế). Chỉ liệt kê trang đã có thật; thêm trang Sinh viên mới thì phải
  thêm vào đây (test `LayoutSinhVienTest.test_menu_chi_chua_cac_trang_sinh_vien_da_co_that`
  liệt kê chính xác tập trang).
- **Dropdown** (`.sv-nhom__xo`, gồm cả dropdown của chip người dùng): nền xanh đậm **#145DBF** (đậm hơn
  thanh menu #1877F2 để thấy ranh giới giữa menu chính và menu con), chữ/icon trắng, bo góc 8px, bóng đổ
  đậm hơn; mục hover nền **#0D47A1**; các mục ngăn cách bằng đường kẻ trắng 15%
  (`.sv-nhom__xo > * + *`); mục đang chọn phân biệt bằng chữ đậm + vạch trắng 3px bên trái + nền trắng mờ
  (không dùng xanh). Viền focus bàn phím trong dropdown là trắng. Hai màu xanh đậm là hằng số riêng
  (không thêm biến vào `:root`). Bảng menu sổ xuống của hamburger (dưới 768px) vẫn nền trắng nên danh
  sách con bên trong dùng nền trong suốt + chữ tối, không có đường kẻ. Desktop mở bằng hover/focus, cảm
  ứng mở bằng bấm (`aria-expanded`), đóng khi bấm ra ngoài hoặc nhấn Esc.
- **Trạng thái "đang chọn"**: xác định trong template bằng `request.resolver_match.app_name` +
  `url_name`. Riêng "Bảng điểm" nhận cả `app_name == 'grades'` vì `bang_diem_cua_toi` chuyển
  hướng sang `bang_diem_sinh_vien` (trước đây tab này không bao giờ sáng).
- **Góc phải**: chip chuông (`.sv-chuong`) trỏ `thong_bao:danh_sach`, badge `.chip-thong-bao` màu
  `--mau-do` lấy từ `SO_THONG_BAO_CHUA_DOC` (số thật, ẩn khi bằng 0, hiện `99+` nếu quá 99);
  chip người dùng giữ định dạng "tên đăng nhập · Sinh viên", mở dropdown Thông tin cá nhân /
  Đổi mật khẩu / Đăng xuất (form POST). Hai chip nền **trắng** chữ đen trên thanh xanh — badge đỏ
  #E41E3F và nền xanh gần bằng nhau về độ sáng nên badge phải nằm trên nền chip trắng mới đọc rõ.
- **Breadcrumb** (`.sv-breadcrumb`): "Trang chủ / Tên trang", chữ nhỏ `--mau-chu-phu`, không viền,
  căn lề theo khung nội dung. Nhãn tra theo `app_name`/`url_name` ngay trong `_khung_dau.html`,
  gồm cả trang không nằm trong menu (hủy đăng ký, chi tiết thông báo, thông tin cá nhân, đổi mật
  khẩu). Trang không có nhãn (vd. 403/404) chỉ hiện "Trang chủ".
- **Khung nội dung**: `main` giữ `max-width: 1100px`; banner/menu/breadcrumb/footer dùng
  `.sv-container` cùng độ rộng để thẳng lề. `body.co-bo-cuc-sv` là flex dọc để footer luôn nằm dưới.
- **Footer** (`.sv-chan-trang`): nền `--mau-xanh-chinh`, 3 cột — tiêu đề cột chữ trắng, phần phụ trắng
  độ đục 85% — trường + địa chỉ, Liên hệ, Liên kết nhanh (Trang chủ / Thông báo / Thông tin cá
  nhân; hover nền trắng mờ, ghi đè quy tắc chung `li a:hover` vì chữ trắng) — và dòng "© năm
  `TEN_TRUONG`" căn giữa, ngăn cách bằng đường trắng mờ. Địa chỉ/điện thoại/email ghi cứng "(chưa cập nhật)" trong template (chưa có biến `.env`).
- **Responsive**: dưới `960px` thu gọn padding và ẩn phần "· Sinh viên" trong chip; dưới `768px`
  menu chính thành nút hamburger mở danh sách sổ xuống (nhóm bung theo kiểu accordion), chuông và
  chip người dùng vẫn hiện.

## Trang chủ và bảng điểm của Sinh viên (lượt giao diện 2/3)

Giữ nguyên layout lượt 1/3 và bảng màu; chỉ đổi nội dung hai trang. Nguyên tắc chung: mọi hành
động là nút `.nut` (không liên kết chữ, không gạch chân), khối nào không có dữ liệu thật thì
không hiện (không bịa), số điểm chỉ dùng điểm **đã công bố** khi chính sinh viên xem.

**Thành phần dùng chung** (CSS ở `templates/base.html`, vì trang bảng điểm cũng do Phòng Đào tạo/
Cố vấn học tập xem):
- `.tieu-de-trang`: hàng tiêu đề trang, tiêu đề bên trái, nhóm nút (`.nhom-nut`) bên phải.
- `.luoi-tong-hop` (`--3` hoặc `--4` cột; 2 cột dưới 768px, 1 cột dưới 400px) chứa các `.o-tong-hop`:
  nhãn xám nhỏ (`__nhan`) phía trên, giá trị đậm (`__gia-tri`, màu `--mau-xanh-chinh`, hoặc
  `--den` = `--mau-chu` cho giá trị chữ như xếp loại) phía dưới, `__ghi-chu` cho câu ngắn khi
  chưa có số. Không dùng màu đỏ cho giá trị.
- `.canh-bao-khoi`: khối cảnh báo học vụ dùng lại `.thong-bao--warning` (vàng nhạt) hoặc
  `.thong-bao--error` (đỏ nhạt). Logic cảnh báo chỉ có hai điều kiện nên mức độ chia theo số lý
  do: một lý do là vàng, hai lý do là đỏ.
- `.bang-diem`: header nền `--mau-xanh-nhat`, dòng xen kẽ nhẹ, `tr.hang-nhom` (nền `--mau-nen-trang`,
  chữ đậm) là dòng tiêu đề nhóm "Học kỳ X - YYYY-YYYY" tạo bằng `{% ifchanged %}` trong template
  (view đã sắp `-nam_hoc, hoc_ky` nên các dòng cùng học kỳ liền nhau).

**Trang chủ** (`accounts/templates/accounts/_trang_chu_sinh_vien.html`; CSS riêng `.sv-*` ở
`templates/sinh_vien/_css.html`): chào mừng (họ tên, mã, lớp, ngày) → cảnh báo học vụ (nếu có, kèm
nút "Xem chi tiết" tới bảng điểm đúng học kỳ) → lưới 6 ô "Tóm tắt học tập" (điểm TB tích lũy,
xếp loại, tín chỉ tích lũy/tổng chương trình, % hoàn thành kèm thanh tiến độ, điểm TB học kỳ gần
nhất, học phần bắt buộc đã đạt) → "Sắp diễn ra" (chỉ khi có dữ liệu) và "Thông báo mới nhất".
Các vai trò khác vẫn dùng lưới thẻ chức năng cũ. Dữ liệu do `accounts/tong_hop_sinh_vien.py` gom,
chỉ gọi lại service sẵn có (`grades`, `tien_do_hoc_tap`, `thong_bao`); `accounts/views.py:trang_chu`
chỉ thêm context này cho Sinh viên.
- Tín chỉ tích lũy = tổng tín chỉ các học phần đã đạt trong chương trình; tổng = mọi học phần của
  chương trình (bắt buộc + tự chọn). Phần trăm hoàn thành giữ nguyên định nghĩa của
  `tinh_tien_do` (chỉ học phần bắt buộc).
- "Sắp diễn ra": lịch thi từ hôm nay trở đi (tối đa 3 dòng, chỉ lớp còn hiệu lực); buổi học hôm
  nay/tuần này chỉ tính các lớp thuộc học kỳ đang diễn ra theo danh mục `hoc_ky` vì `lich_hoc` chỉ
  có thứ + tiết, không có ngày cụ thể. Không có học kỳ hiện tại thì ẩn phần buổi học.
- Chưa gắn hồ sơ sinh viên: chỉ hiện thông báo nhắc liên hệ Phòng Đào tạo và khối thông báo.
- Số phần trăm trong `style="width: ..."` phải qua `|unlocalize` (locale `vi` in dấu phẩy thập phân).

**Bảng điểm** (`grades/templates/grades/bang_diem_sinh_vien.html`, view giữ nguyên): tiêu đề kèm nút
"Xuất PDF" (nút chính, chỉ Sinh viên) và nút AI (`nut-nhe`); bộ chọn học kỳ; cảnh báo; lưới 4 ô
(điểm TB và xếp loại của học kỳ đang chọn, và tích lũy); bảng 7 cột: Mã học phần, Tên học phần, Số
tín chỉ, Điểm quá trình, Điểm thi, Điểm tổng kết, Trạng thái. Chip trạng thái dùng lớp chip có sẵn:
"Đã công bố", "Đang chờ công bố" (chỉ Sinh viên, điểm bị ẩn thành "—"), "Chưa công bố" (Cố vấn/
Phòng Đào tạo thấy điểm thật), "Chưa nhập điểm". Điểm 0 hiển thị đúng là 0 (không bị hiểu nhầm là
chưa nhập). **Chưa có cột "Điểm chữ"**: dự án chưa có thang điểm chữ theo Thông tư, sẽ làm ở một
lượt riêng khi có logic quy đổi.

## Các trang còn lại của Sinh viên (lượt giao diện 3/3)

Giữ nguyên layout (lượt 1/3), trang chủ và bảng điểm (lượt 2/3); chỉ đổi giao diện các trang còn
lại theo cùng nguyên tắc: mọi hành động là nút, không chữ gạch chân, không thêm cột không có dữ
liệu thật.

**Bảng dùng chung `.bang-sv`** (CSS ở `templates/base.html`, cùng kiểu `.bang-diem`): header nền
`--mau-xanh-nhat`, dòng xen kẽ nhẹ (`tr.hang-diem`), dòng tiêu đề nhóm (`tr.hang-nhom`, nền
`--mau-nen-trang`, chữ đậm; `.hang-nhom__phu` cho chú thích nhỏ cạnh tiêu đề nhóm), dòng làm nhạt
(`tr.hang-mo`, dùng cho lịch sử đã hủy và lịch thi đã qua). `.tieu-de-nhom` là hàng "tiêu đề + chip
đếm" phía trên một bảng; `.bang-tien-do` cố định độ rộng cột để hai bảng liền nhau thẳng hàng.
Đã áp dụng cho: Lớp đang mở, Thời khóa biểu, Lịch sử đăng ký, Lịch thi, Tiến độ học tập, Điểm danh,
Thông báo (danh sách — trang này dùng chung cho mọi vai trò), bảng trạng thái lớp của Tư vấn AI và
"Bảng điểm chi tiết" của Tóm tắt AI. `.o-lich-hoc` (ô có lớp trong lưới tuần) nay có viền trái
3px màu `--mau-xanh-chinh`; ô trống nền trắng — lịch giảng dạy của Giảng viên dùng chung lớp này nên
cũng đổi theo.

- **Lớp đang mở**: dòng nhóm "Học kỳ X - YYYY-YYYY" kèm chip trạng thái đợt (Đang mở đăng ký /
  Ngoài đợt đăng ký); **lý do đợt đăng ký chỉ nêu một lần ở dòng nhóm**, không lặp ở từng hàng và
  không trùng câu với thông báo lỗi (trước đây câu "Chưa có đợt đăng ký nào cho học kỳ này." hiện hai
  lần sau khi bấm đăng ký vào học kỳ ngoài đợt). Sĩ số dạng chip "đã đăng ký/tối đa": dưới 80% xanh
  lá nhạt (`chip--du_dieu_kien`), từ 80% vàng nhạt (`chip--thieu_tien_quyet`), đã đầy xám
  (`chip--da_day`). Cột Trạng thái dùng đúng chip có sẵn cho 6 trạng thái của
  `enrollment.services.xac_dinh_trang_thai` (view gắn `lop.trang_thai_dk` cho từng lớp — hàm này có
  từ trước, cùng thứ tự kiểm tra với `dang_ky_hoc_phan()`; mỗi lớp tốn thêm vài truy vấn, tối đa 20
  lớp mỗi trang). Nút "Đăng ký" (`nut-chinh`) chỉ có khi đủ điều kiện, còn lại là nút vô hiệu xám.
- **Thời khóa biểu**: nút "Xuất PDF" (`nut-chinh`) và nút đổi chế độ xem cạnh tiêu đề; "Hủy đăng ký"
  giữ `nut-nguy-hiem`.
- **Lịch thi**: gom theo ngày thi ("Thứ 4, 14/10/2026"), lịch đã qua làm nhạt; giữ các cột có dữ liệu
  thật (không có SBD vì hệ thống không lưu số báo danh).
- **Tiến độ học tập**: 3 ô tổng hợp (% hoàn thành kèm thanh tiến độ, bắt buộc đã đạt, bắt buộc còn
  thiếu), rồi hai nhóm "Đã đạt" (chip xanh lá nhạt) và "Còn thiếu" (chip vàng nhạt) gom theo học kỳ dự
  kiến (gộp bắt buộc + tự chọn bằng `|add` và `|dictsort` trong template), nhãn Bắt buộc/Tự chọn cạnh
  tên học phần. Chưa gán chương trình đào tạo thì hiện khối cảnh báo rõ ràng. Trang tiến độ của Cố
  vấn dùng chung `_ket_qua.html` nên đổi theo.
- **Trang AI**: đã kiểm tra bằng client AI giả (không gọi AI thật); chỉ đồng bộ header hai bảng, các
  phần còn lại giữ nguyên.

**Độ tương phản** (WCAG, tính trên #1877F2): chữ/icon trắng 4,23:1; chữ phụ trắng 85% ở chân trang
3,50:1; mục đang chọn (trắng trên nền trắng mờ 12%) 3,55:1; chip chữ đen trên trắng 20,4:1; badge đỏ
#E41E3F trên chip trắng 4,61:1 (nhưng chỉ 1,09:1 nếu đặt thẳng lên nền xanh — vì vậy chip phải nền
trắng). Các mức 3,5–4,2 đạt cho chữ đậm/thành phần giao diện (≥ 3:1) nhưng chưa đạt 4,5:1 của chữ
thường: đây là giới hạn của việc dùng chính màu thương hiệu #1877F2 làm nền, nên thanh menu dùng
trắng 100%, cỡ 14px đậm. Muốn đạt AA đầy đủ phải dùng xanh đậm hơn cho nền (ngoài bảng màu hiện tại).
Riêng dropdown (#145DBF) chữ trắng đạt 6,3:1 và mục hover (#0D47A1) đạt 8,6:1 — đạt AA đầy đủ.

## Menu Phòng Đào tạo, Giảng viên, Cố vấn học tập

Thay cho thanh trên trắng cũ (`.thanh-tren`, tab phẳng, không dropdown, không icon), ba vai trò này dùng
khung `templates/nhan_vien/_khung_dau.html` (CSS bổ sung ở `templates/nhan_vien/_css.html`). Khung này
**dùng lại đúng các lớp `.sv-*`** của menu Sinh viên nên đồng bộ về màu và kiểu dáng:
- Màu: thanh chính nền `--mau-xanh-chinh` (`#1877F2`) chữ trắng; dropdown nền `#145DBF` chữ trắng; mục hover
  `#0D47A1`.
- Kiểu dáng: icon SVG nét ở mỗi mục; mục đang chọn ở thanh chính có gạch chân trắng 3px (`border-bottom`) và mục
  đang chọn trong dropdown có vạch trắng bên trái; dropdown mở bằng hover trên máy tính, bấm trên cảm ứng.
- Dùng chung với Sinh viên: `templates/menu/_bieu_tuong.html` (bộ icon SVG, thêm các icon mới cho menu
  quản lý: nhóm người, giảng viên, tải lên, cảnh báo, gửi, tiên quyết, ngành) và `templates/menu/_js.html`
  (mở/đóng dropdown, hamburger, Esc, bấm ra ngoài). Các quy tắc `.sv-*` nằm ở `sinh_vien/_css.html`, nạp cho mọi
  người đã đăng nhập (`templates/base.html`).
- Không có breadcrumb và chân trang (chỉ Sinh viên có). Chuông thông báo (kèm số chưa đọc) và dropdown
  người dùng (Thông tin cá nhân, Đổi mật khẩu, Đăng xuất) ở góc phải, giống Sinh viên.

**Cách phân nhóm** không ép giống Sinh viên: mỗi vai trò giữ đúng số tab/nhóm theo chức năng thật của mình.

| Vai trò | Thanh chính |
|---|---|
| Phòng Đào tạo | Trang chủ, Tài khoản, **Người dùng** (Sinh viên, Giảng viên, Cố vấn học tập, Nhập sinh viên từ Excel), **Học vụ** (Ngành học, Lớp hành chính, Học phần, Điều kiện tiên quyết, Chương trình đào tạo, Danh mục học kỳ, Đợt đăng ký học phần), **Lớp học phần** (Lớp học phần, Lịch học, Lịch thi, Tra cứu lịch sử đăng ký), Quy chế, **Báo cáo** (Sĩ số theo lớp, Học phần nhiều đăng ký, Kết quả học tập), Cảnh báo học vụ, Gửi thông báo |
| Giảng viên | Trang chủ, Lớp phụ trách, Lịch giảng dạy, Gửi thông báo (không có dropdown vì chỉ 3 chức năng) |
| Cố vấn học tập | Trang chủ, Sinh viên phụ trách, Tiến độ học tập, Cảnh báo học vụ, Tóm tắt AI, Hỏi đáp AI, Gửi thông báo |

Các trang tạo/sửa/xóa, xuất tệp và trang có tham số (bảng điểm lớp, điểm danh...) không nằm trên menu; vào từ
nút trong trang danh sách tương ứng. Nhóm "Học vụ" có 7 mục — vẫn đủ ngắn để tìm nên chưa tách nhỏ hơn.

Responsive: `.sv-container--rong` (tối đa 1440px) vì các vai trò này có nhiều tab; từ 1101px đến 1439px thanh của
Phòng Đào tạo (9 mục) ẩn icon ở thanh chính để vừa một hàng (icon trong dropdown vẫn còn); dưới 1100px chuyển
sang nút hamburger, dropdown xếp dọc trong menu xổ xuống (`.sv-thanh-menu--nv`).

## Trang chủ Phòng Đào tạo: số liệu tổng quan, cảnh báo, thông báo gần đây

Trang chủ Phòng Đào tạo chỉ gồm lời chào và 3 khối dưới đây; lưới thẻ chức năng cũ đã bỏ vì menu trên thanh đã
có đủ liên kết tới mọi trang quản lý (Giảng viên và Cố vấn vẫn dùng lưới thẻ chức năng). Dữ liệu do `accounts/tong_hop_phong_dao_tao.py`
gom cho view `trang_chu` (chỉ gọi lại service/truy vấn có sẵn, không tính lại luật); partial
`accounts/templates/accounts/_trang_chu_phong_dao_tao.html`; CSS ở `templates/nhan_vien/_css.html`.

1. **Số liệu tổng quan** (`.luoi-tong-hop--5`, dùng lại `.o-tong-hop` của trang chủ Sinh viên: nhãn xám nhỏ phía trên, giá trị đậm
   phía dưới, nút "Xem chi tiết"): sinh viên đang hoạt động (tài khoản đang kích hoạt); lớp học phần của học kỳ đang xét; đợt đăng
   ký đang hiệu lực; sinh viên bị cảnh báo học vụ (`hoc_ky_gan_nhat_co_du_diem` + `canh_bao_hoc_vu`, điểm thật, chỉ tài khoản
   đang hoạt động; ghi chú xám "tính theo học kỳ gần nhất của từng sinh viên, có thể khác trang chi tiết theo học kỳ"); lớp học
   phần đã đầy chỗ (số đăng ký còn hiệu lực đạt sĩ số tối đa, trong học kỳ đang xét).
   **Học kỳ đang xét**: học kỳ của đợt đăng ký đang hiệu lực (nhiều đợt thì lấy học kỳ mới nhất); nếu không có đợt nào thì học kỳ
   mới nhất trong danh mục (năm học lớn nhất rồi số học kỳ lớn nhất). Dòng chú thích dưới tiêu đề khối ghi rõ học kỳ và nguồn chọn.
2. **Cảnh báo cần chú ý** (`.khoi-chu-y`, nền `--mau-vang-nhat`, vạch trái `--mau-vang`): mỗi loại một dòng theo thứ tự ưu tiên
   (sinh viên cảnh báo mức đỏ, lớp học phần đã đầy chỗ, mỗi đợt đăng ký sắp đóng trong 3 ngày), tối đa 5 dòng, mỗi dòng có nút
   dẫn tới trang liên quan. Mức đỏ = có cả 2 lý do cảnh báo (cùng quy ước trang chủ Sinh viên). **Ẩn hẳn** nếu không có dòng nào.
3. **Thông báo đã gửi gần đây** (`.khoi-gan-day`): 5 thông báo mới nhất do tài khoản Phòng Đào tạo gửi (tiêu đề, đối tượng nhận,
   thời gian) và nút "Xem tất cả" tới trang mới `thong_bao:da_gui` ("Thông báo đã gửi", chỉ Phòng Đào tạo, phân trang 20 dòng).
   Đối tượng nhận hiển thị qua partial `thong_bao/_doi_tuong.html` (có dấu tiếng Việt cho các đối tượng theo vai trò).
   Ban đầu dự kiến khối "Hoạt động gần đây" từ nhật ký hoạt động, nhưng dự án chưa có bảng/app ghi nhật ký nên thay bằng khối này.

Mọi hành động trong 3 khối là nút `.nut` (không chữ gạch chân). Responsive: lưới 5 ô chuyển 3 cột dưới 1000px, 2 cột dưới 640px,
1 cột dưới 400px; dòng cảnh báo xếp dọc dưới 640px.

## Trang chủ Giảng viên

Cùng phong cách trang chủ Phòng Đào tạo (dùng lại `.khoi-tong-quan`, `.luoi-tong-hop--5`/`.o-tong-hop`, `.khoi-chu-y`,
`.khoi-gan-day` trong `templates/nhan_vien/_css.html`); lưới thẻ chức năng cũ đã bỏ vì menu trên thanh đã có đủ liên kết
(Cố vấn học tập cũng vậy, xem mục sau). Dữ liệu: `accounts/tong_hop_giang_vien.py`; partial `accounts/templates/accounts/_trang_chu_giang_vien.html`.
Mọi số liệu chỉ của các lớp học phần do chính giảng viên phụ trách; tài khoản chưa gắn hồ sơ giảng viên chỉ thấy lời nhắn liên hệ
Phòng Đào tạo.

1. **Số liệu tổng quan** (5 ô, nút "Xem chi tiết"): lớp học phần đang phụ trách và số sinh viên khác nhau đang đăng ký (đều trong
   học kỳ đang xét — cách chọn như trang chủ Phòng Đào tạo); buổi dạy hôm nay (đúng thứ trong tuần); buổi dạy trong tuần (số dòng
   lịch học của các lớp học kỳ đang xét); lớp còn điểm chưa công bố (mọi học kỳ: lớp có ít nhất một điểm đã nhập nhưng
   `da_cong_bo=False`).
2. **Cảnh báo cần chú ý** (nền vàng nhạt, mỗi loại một dòng, ẩn khi không có gì): lớp còn điểm chưa công bố; lớp có buổi dạy hôm qua
   (đúng thứ, hôm qua nằm trong học kỳ, có sinh viên đăng ký) nhưng chưa có điểm danh ngày đó; lịch thi trong 7 ngày tới. Một lớp thì
   nút dẫn thẳng tới bảng điểm/điểm danh (kèm `?ngay=`) của lớp đó, nhiều lớp thì dẫn tới Lớp phụ trách.
3. **Buổi dạy hôm nay** (mã lớp, tên học phần, tiết, phòng; nút "Xem lịch giảng dạy") và **Thông báo gần đây** (5 thông báo liên quan
   tới giảng viên qua `thong_bao_lien_quan`, chip "Mới" cho thông báo chưa đọc, nút "Xem tất cả" tới trang Thông báo). Chỉ hiển thị,
   không tự đánh dấu đã đọc.

## Trang chủ Cố vấn học tập

Cùng phong cách với trang chủ Phòng Đào tạo và Giảng viên (dùng lại `.khoi-tong-quan`, `.luoi-tong-hop--5`/`.o-tong-hop`, `.khoi-chu-y`,
`.khoi-gan-day`; thêm hai chip `.chip--muc-do`/`.chip--muc-vang` trong `templates/nhan_vien/_css.html`); lưới thẻ chức năng cũ đã bỏ vì menu trên
thanh đã có đủ liên kết. Như vậy không vai trò nào còn lưới thẻ chức năng ở trang chủ. Dữ liệu: `accounts/tong_hop_co_van.py` (phần thông báo gần đây
và cách ghép danh sách dùng chung ở `accounts/tong_hop_chung.py`); partial `accounts/templates/accounts/_trang_chu_co_van.html`. Mọi số liệu chỉ
của sinh viên thuộc các lớp hành chính do cố vấn phụ trách; tài khoản chưa gắn hồ sơ cố vấn chỉ thấy lời nhắn liên hệ Phòng Đào tạo.

1. **Số liệu tổng quan** (5 ô, nút "Xem chi tiết"): lớp hành chính phụ trách (kèm mã lớp); sinh viên phụ trách; sinh viên bị cảnh báo học vụ (kèm số
   mức đỏ; dùng đúng `hoc_ky_gan_nhat_co_du_diem` + `canh_bao_hoc_vu` như trang "Cảnh báo học vụ" của Cố vấn nên hai nơi luôn khớp số dòng); sinh viên
   chưa đăng ký học phần nào trong học kỳ đang xét (cách chọn như trang chủ Phòng Đào tạo); thông báo chưa đọc.
2. **Cảnh báo cần chú ý** (nền vàng nhạt, mỗi loại một dòng, ẩn khi không có gì): sinh viên cảnh báo mức đỏ (2 lý do); sinh viên chưa đăng ký học phần
   khi học kỳ đang xét đang trong đợt đăng ký. Mỗi dòng liệt kê tối đa 3 mã sinh viên rồi "và N sinh viên khác".
3. **Sinh viên cần quan tâm** (tối đa 5 sinh viên bị cảnh báo, mức đỏ xếp trước; mã, họ tên, lớp, học kỳ, điểm trung bình, lý do, nút "Xem bảng điểm",
   nút "Xem tất cả" tới trang Cảnh báo học vụ) và **Thông báo gần đây** (5 thông báo liên quan, chip "Mới" cho thông báo chưa đọc; chỉ hiển thị, không
   tự đánh dấu đã đọc).

## Chip trạng thái (`.chip`)

Dùng hậu tố đúng bằng giá trị hằng số trạng thái trong code (không cần bảng tra cứu riêng
trong CSS): `chip--du_dieu_kien`, `chip--thieu_tien_quyet`, `chip--trung_lich`,
`chip--da_day`, `chip--da_dang_ky` (khớp `enrollment.services.DU_DIEU_KIEN`... — xem
`tu_van_dang_ky/templates/tu_van_dang_ky/trang_tu_van.html`: `class="chip chip--{{
muc.trang_thai }}"`), cộng `chip--dang-hoat-dong` / `chip--da-khoa` cho trạng thái tài
khoản và `chip--ai` dự phòng cho nhãn liên quan AI.

## Trang AI (quy tắc riêng)

- `.nhan-ai`: chip nhỏ "Trợ lý AI" ở đầu khối kết quả AI.
- `.khung-ket-qua-ai`: viền trái xanh 3px, dùng cho khối nhận xét/trả lời của AI.
- `.nhom-goi-y` / `.nhom-chua-nen`: nền xanh lá nhạt / đỏ nhạt cho hai nhóm gợi ý của tư vấn
  đăng ký học phần.
- Lỗi AI hiển thị bằng `.thong-bao--error` (dùng trực tiếp trên `<p>`, không chỉ trong danh
  sách `messages`) để nổi bật nhất quán với các thông báo khác — nội dung câu chữ giữ
  nguyên như trước.
- **Hạn chế đã biết**: câu cảnh báo cố định "Nội dung do AI tạo, chỉ mang tính tham khảo..."
  (`ai_core.dinh_dang.CANH_BAO_AI`) được nối thẳng vào cuối chuỗi trả lời ở tầng Python
  (`dinh_dang_ket_qua()`), không phải một phần tử HTML riêng — nên không tô được riêng màu
  vàng cho đúng một mình câu này mà không sửa code tầng service (ngoài phạm vi "chỉ đổi
  giao diện" của lần này). Toàn bộ khối trả lời (gồm cả câu cảnh báo) vẫn nằm trong
  `.khung-ket-qua-ai` dễ nhận biết.

## Ngày tháng

`LANGUAGE_CODE` đổi thành `vi` (`qldt/settings.py`) để số liệu (điểm số) hiển thị đúng kiểu
Việt Nam (dấu phẩy thập phân). Ngày/giờ hiển thị luôn ép định dạng rõ ràng bằng filter
template (`|date:"d/m/Y"` cho ngày, `|date:"d/m/Y H:i"` cho ngày giờ) thay vì dựa vào định
dạng mặc định của locale, để chắc chắn ra đúng `dd/mm/yyyy` ở mọi nơi hiển thị ngày.

## Responsive

Dưới `768px`: lưới thẻ chức năng chuyển thành một cột. Thanh menu chuyển sang nút hamburger dưới
`768px` với Sinh viên (xem "Layout riêng của Sinh viên") và dưới `1100px` với Phòng Đào tạo,
Giảng viên, Cố vấn học tập (nhiều tab hơn, xem mục "Menu Phòng Đào tạo, Giảng viên, Cố vấn học
tập"). Bảng luôn cuộn ngang trong `.khung-bang` khi tràn.
