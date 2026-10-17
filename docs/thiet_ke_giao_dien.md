# Thiết kế giao diện

Toàn bộ CSS dùng chung đặt trong khối `<style>` ở `templates/base.html` (không dùng CDN/thư viện
ngoài, không lặp lại ở từng trang). CSS của khung trang (sidebar, thanh trên) nằm ở
`templates/sinh_vien/_css.html`, nạp trong khối `<style>` thứ hai cho mọi người đã đăng nhập;
`templates/nhan_vien/_css.html` bổ sung CSS trang chủ của Phòng Đào tạo, Giảng viên, Cố vấn (xem mục
"Khung sidebar dùng chung"). Thứ duy nhất lấy từ static files là font Be Vietnam Pro (xem mục "Bảng
màu"): khi `DEBUG=False` mà máy chủ chưa phục vụ static thì trình duyệt tự dùng font hệ thống, giao
diện vẫn đầy đủ. Đây là bản ghi lại bảng màu, hệ nút, và quy ước đặt tên lớp CSS để giữ nhất quán khi
thêm trang mới.

## Bảng màu (biến CSS trong `:root`)

Từ khung sidebar (nhánh `feat/giao-dien`) bảng màu đổi sang xanh dương chuyên nghiệp theo bản xem trước
dashboard (skill ui-ux-pro-max, phong cách "Minimalism & Swiss Style"); tên biến giữ nguyên nên mọi
trang đổi theo mà không sửa HTML. Bảng màu Facebook cũ (#1877F2, nền #F0F2F5) có trong lịch sử git
trước commit này.

| Biến | Giá trị | Dùng cho |
|---|---|---|
| `--mau-xanh-chinh` | `#1E40AF` | Màu chính: nút chính, liên kết, mục đang chọn (chữ trắng 8,7:1) |
| `--mau-xanh-chinh-hover` | `#1E3A8A` | Hover của nút chính |
| `--mau-xanh-nhat` | `#EFF6FF` | Nền mục đang chọn ở sidebar, nút nhẹ, nhãn AI, chip "đã đăng ký" |
| `--mau-nen-trang` | `#F5F7FB` | Nền toàn trang, nền tiêu đề bảng, hover mục menu |
| `--mau-the` | `#FFFFFF` | Nền thẻ, bảng, sidebar |
| `--mau-chu` | `#0F172A` | Màu chữ chính |
| `--mau-chu-phu` | `#475569` | Chữ phụ, nhãn, mục menu thường (7,6:1 trên trắng) |
| `--mau-vien` | `#CBD5E1` | Viền dưới tiêu đề bảng, viền hover |
| `--mau-nut-xam` | `#EEF2F6` | Nền nút phụ, kẻ dòng bảng |
| `--mau-nut-xam-hover` | `#E2E8F0` | Hover nút phụ; viền thẻ, sidebar, thanh trên |
| `--mau-do` | `#DC2626` | Badge số thông báo, viền thông báo lỗi, viền trường lỗi |
| `--mau-do-nhat` | `#FEE2E2` | Nền nút nguy hiểm, nền thông báo lỗi |
| `--mau-xanh-la` / `--mau-xanh-la-nhat` | `#16A34A` / `#DCFCE7` | Thông báo thành công, chip "đủ điều kiện", thanh tiến độ |
| `--mau-vang` / `--mau-vang-nhat` | `#D97706` / `#FEF3C7` | Thông báo cảnh báo, khối "Cảnh báo cần chú ý", chip "thiếu tiên quyết" |
| `--mau-cam-nhat` / `--mau-cam-chu` | `#FFEDD5` / `#9A3412` | Chip "trùng lịch" |
| `--mau-xam-nhat` | `#F1F5F9` | Nút vô hiệu, chip "đã đầy"/"đã khóa" |

Font: **Be Vietnam Pro** (4 độ đậm 400/500/600/700) đặt ở `accounts/static/qldt/fonts/` kèm giấy phép
`OFL.txt` (SIL Open Font License 1.1), nạp bằng `@font-face` + `{% static %}` trong `base.html`, không dùng
CDN; Django tự tìm thư mục `static/` của app nên không cần sửa `settings.py`. Dự phòng:
`-apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`. Cỡ chữ gốc `15px`, giãn dòng `1.5`,
tiêu đề (`h1`-`h4`) đậm `700` (không có tệp độ đậm 800 nên không dùng 800 để trình duyệt khỏi tự làm
đậm giả). Bảng và giá trị ô tổng hợp dùng `font-variant-numeric: tabular-nums`. Chữ nhỏ nhất `12px`
(trừ badge số thông báo và tiêu đề nhóm ở sidebar `11px` chữ hoa, đậm). Thẻ (`.khung`, `.khung-bang`,
`.o-tong-hop`, `.the-chuc-nang`) bo góc 12px, viền 1px `--mau-nut-xam-hover` và bóng nhẹ.

## Hệ nút (`.nut`)

Lớp gốc `.nut` định nghĩa hình dạng chung (bo góc 8px, đậm chữ, có hover/focus, chuyển màu
mượt `.15s ease`); kết hợp với một lớp màu và (tùy chọn) một lớp cỡ:

| Lớp màu | Dùng khi |
|---|---|
| `.nut-chinh` | Hành động chính của trang (Lưu, Đăng nhập, Đăng ký, Gửi câu hỏi, + Tạo...). Nền `--mau-xanh-chinh`, hover `--mau-xanh-chinh-hover` |
| `.nut-phu` | Hành động phụ/trung tính (Hủy, Đăng xuất, Xóa lọc, phân trang) |
| `.nut-nhe` | Hành động nhẹ liên quan tới AI hoặc "Sửa"/"Xem" trong bảng. Chữ `--mau-xanh-chinh` |
| `.nut-nguy-hiem` | Hành động phá hủy/hạn chế (Khóa, Xóa). Chữ #B91C1C (5,4:1 trên `--mau-do-nhat`) |
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

- Khung: mọi vai trò đã đăng nhập dùng sidebar bên trái và thanh trên (bộ lớp `.sv-*`, xem "Khung sidebar
  dùng chung"). Trạng thái đang chọn xác định bằng `request.resolver_match.url_name`/`app_name` ngay
  trong template, không cần sửa view.
- `main`: khung nội dung tối đa `1240px` khi đã đăng nhập (`1100px` ở trang chưa đăng nhập), căn giữa.
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

## Khung sidebar dùng chung (thay thanh menu ngang)

Áp dụng cho cả 4 vai trò, thay thanh menu ngang của các lượt giao diện trước (thanh xanh #1877F2, dropdown
#145DBF — xem lịch sử git trước commit "Giao diện: khung sidebar..."). Chỉ đổi template khung (`base.html`,
`sinh_vien/_khung_dau.html`, `nhan_vien/_khung_dau.html`, `menu/_js.html`) và CSS; không đổi view, form, URL,
model. **Mục menu, URL và điều kiện "đang chọn" của từng vai trò giữ nguyên từng chữ** (đã đối chiếu tự động
với bản trước khi đổi). Bản xem trước tham chiếu: trang chủ Sinh viên dạng admin dashboard dựng ngoài dự án.

**Bố cục** (`base.html`): khi đã đăng nhập, `<div class="sv-bo-cuc">` là lưới 2 cột `264px | 1fr`: sidebar
(`<aside class="sv-sidebar">`) chiếm cột trái cả chiều cao; cột phải lần lượt là thanh trên
(`<header class="sv-thanh-tren">`) và `<main>`. Không có chân trang (đã bỏ chân trang 3 cột của Sinh viên). Chưa đăng nhập (trang đăng nhập)
không có lưới này.

| Partial | Nội dung |
|---|---|
| `sinh_vien/_khung_dau.html` | Sidebar (logo + menu Sinh viên) và thanh trên (nút ☰, breadcrumb, chuông, menu người dùng) |
| `nhan_vien/_khung_dau.html` | Như trên cho Phòng Đào tạo / Giảng viên / Cố vấn (`.sv-sidebar--nv`); thanh trên không có breadcrumb hay nhãn vai trò (vai trò đã hiện ở chip người dùng bên phải) |
| `menu/_bieu_tuong.html` | Sprite icon SVG nội tuyến (`<symbol id="sv-i-...">`) dùng chung |
| `menu/_js.html` | Mở/thu gọn nhóm trong sidebar, dropdown menu người dùng, ngăn trượt trên màn hình hẹp |
| `sinh_vien/_css.html` | CSS của khung (tiền tố `sv-`), nạp cho mọi người đã đăng nhập |

- **Sidebar** (`.sv-sidebar`): nền trắng, viền phải mảnh, `position: sticky` cao bằng màn hình, cuộn riêng
  (`overflow-y: auto`) — Phòng Đào tạo nhiều mục vẫn vừa mà không cần ẩn icon như thanh ngang cũ. Trên cùng là
  logo (`<header class="sv-banner">`, `_logo.html`: tên trường đậm, tên hệ thống chữ phụ).
  Vị trí cuộn của sidebar được giữ khi chuyển trang (`menu/_js.html` lưu `scrollTop` vào `sessionStorage` lúc
  `pagehide`, khôi phục khi tải trang; không có vị trí đã lưu thì cuộn cho mục đang chọn hiện ra).
- **Mục menu** (`.sv-menu__muc`, `.sv-menu .sv-nhom__muc`): icon + chữ `--mau-chu-phu`, hover nền
  `--mau-nen-trang`; **mục đang chọn** nền `--mau-xanh-nhat`, chữ `--mau-xanh-chinh` đậm, vạch trái 3px.
- **Nhóm** (`.sv-nhom`): nút nhóm (`.sv-nhom__nut`) thành tiêu đề nhóm chữ hoa nhỏ `11px` màu #64748B kèm mũi
  tên; nhóm chứa trang đang mở có tiêu đề màu `--mau-xanh-chinh`. Mặc định mở hết (`aria-expanded="true"`);
  bấm tiêu đề để thu gọn tại chỗ (`.sv-nhom--dong`, mũi tên xoay), không tự đóng khi bấm ra ngoài. Mục đứng
  riêng ngay sau một nhóm (vd. "Quy chế" sau "Lớp học phần") cách ra và có đường kẻ mảnh phía trên để không bị
  hiểu là mục con.
- **Thanh trên** (`.sv-thanh-tren`): sticky, nền `--mau-nen-trang` hơi trong, viền dưới mảnh. Sinh viên có
  breadcrumb (`.sv-breadcrumb`, "Trang chủ / Tên trang", trang hiện tại đậm; nhãn tra theo `app_name`/`url_name`
  như trước); ba vai trò khác hiện tên vai trò. Góc phải: chip chuông (`.sv-chuong`, badge `.chip-thong-bao`
  đỏ lấy từ `SO_THONG_BAO_CHUA_DOC`, ẩn khi bằng 0, `99+` nếu quá 99) và chip người dùng ("tên đăng nhập · Vai
  trò") mở **dropdown** nền trắng: Thông tin cá nhân / Đổi mật khẩu / Đăng xuất (form POST). Dropdown mở bằng
  hover/focus trên máy tính, bấm trên cảm ứng; đóng khi bấm ra ngoài hoặc nhấn Esc.
- **Không có chân trang**: chân trang 3 cột của Sinh viên (tên trường, liên hệ, liên kết nhanh, bản quyền) đã bỏ
  theo yêu cầu; dòng bản quyền nhỏ ở trang đăng nhập (`.chan-trang-dang-nhap`) vẫn giữ.
- **Phân nhóm theo vai trò** (giữ như trước): Sinh viên — Trang chủ, nhóm Đăng ký học phần (Đăng ký học phần /
  Thời khóa biểu / Lịch sử đăng ký), Học tập (Tiến độ chương trình đào tạo / Bảng điểm / Lịch thi / Điểm danh),
  Trợ lý AI (Tư vấn đăng ký / Tóm tắt kết quả / Hỏi đáp quy chế). Ba vai trò khác: xem bảng ở mục "Menu Phòng
  Đào tạo, Giảng viên, Cố vấn học tập".
- **Responsive**: dưới `1025px` lưới còn một cột; sidebar thành ngăn trượt từ trái (rộng 280px, tối đa 85% màn
  hình), mở bằng nút ☰ ở thanh trên (`aria-controls="sv-sidebar"`), nội dung phía sau phủ lớp tối; bấm ra
  ngoài hoặc nhấn Esc để đóng. Dưới `640px` ẩn phần "· Vai trò" trong chip và tên vai trò ở thanh trên.
- **Độ tương phản** (WCAG): chữ menu thường #475569 trên trắng 7,6:1; mục đang chọn #1E40AF trên #EFF6FF 8,1:1;
  tiêu đề nhóm #64748B 4,8:1; breadcrumb #475569 trên #F5F7FB 7,1:1; chữ trắng trên nút chính #1E40AF 8,7:1;
  badge đỏ #DC2626 trên chip trắng 4,8:1 — đều đạt 4,5:1 (test
  `test_do_tuong_phan_toi_thieu_cua_bang_mau_moi` ghi lại các mức này).

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

**Độ tương phản**: xem mục "Khung sidebar dùng chung" (các mức tính trên bảng màu hiện tại đều đạt 4,5:1;
giới hạn 4,23:1 của thanh menu trắng trên #1877F2 trước đây không còn vì không còn thanh menu nền xanh).

## Menu Phòng Đào tạo, Giảng viên, Cố vấn học tập

Ba vai trò này dùng khung `templates/nhan_vien/_khung_dau.html` với **đúng các lớp `.sv-*` của khung Sinh viên**
(sidebar, nhóm mở/thu gọn, mục đang chọn, thanh trên, menu người dùng — xem "Khung sidebar dùng chung"); sidebar
có thêm lớp `.sv-sidebar--nv`. Không có breadcrumb (thanh trên hiện tên vai trò) và không có chân trang.

**Cách phân nhóm** không ép giống Sinh viên: mỗi vai trò giữ đúng số mục/nhóm theo chức năng thật của mình
(thứ tự trong sidebar như bảng):

| Vai trò | Mục trong sidebar |
|---|---|
| Phòng Đào tạo | Trang chủ, Tài khoản, **Người dùng** (Sinh viên, Giảng viên, Cố vấn học tập, Nhập sinh viên từ Excel), **Học vụ** (Ngành học, Lớp hành chính, Học phần, Điều kiện tiên quyết, Chương trình đào tạo, Danh mục học kỳ, Đợt đăng ký học phần), **Lớp học phần** (Lớp học phần, Lịch học, Lịch thi, Tra cứu lịch sử đăng ký), Quy chế, **Báo cáo** (Sĩ số theo lớp, Học phần nhiều đăng ký, Kết quả học tập), Cảnh báo học vụ, Gửi thông báo |
| Giảng viên | Trang chủ, Lớp phụ trách, Lịch giảng dạy, Gửi thông báo (không có nhóm vì chỉ 3 chức năng) |
| Cố vấn học tập | Trang chủ, Sinh viên phụ trách, Tiến độ học tập, Cảnh báo học vụ, Tóm tắt AI, Hỏi đáp AI, Gửi thông báo |

Các trang tạo/sửa/xóa, xuất tệp và trang có tham số (bảng điểm lớp, điểm danh...) không nằm trên menu; vào từ
nút trong trang danh sách tương ứng (mục cha tương ứng trong sidebar vẫn sáng).

## Trang chủ Phòng Đào tạo: số liệu tổng quan, cảnh báo, thông báo gần đây

Trang chủ Phòng Đào tạo chỉ gồm 3 khối dưới đây (không còn khối lời chào "Xin chào, ... / Vai trò" ở trang chủ Phòng Đào tạo, Giảng viên, Cố vấn vì tên đăng nhập và vai trò đã hiện ở chip thanh trên; trang có tiêu đề `<h1 class="an-chu">Trang chủ</h1>` ẩn cho trình đọc màn hình); lưới thẻ chức năng cũ đã bỏ vì menu trên thanh đã
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

**Khung chat dùng chung** (`ai_core/templates/ai_core/_khung_chat.html`, CSS ở `templates/base.html`): cả 3 trang AI
(tóm tắt, hỏi đáp quy chế, tư vấn đăng ký) là một khung `.khung-chat-ai` gồm luồng tin nhắn `.chat-luong`
(`role="log"`, cuộn riêng, tối đa 68% chiều cao màn hình, tự cuộn tới tin mới nhất), tin của người dùng
`.chat-tin--nguoi-dung` (bong bóng nền `--mau-xanh-chinh` chữ trắng, bên phải) và tin của trợ lý `.chat-tin--tro-ly`
(thẻ nền `--mau-nen-trang`, viền mảnh, bên trái, có nhãn `.nhan-ai` và dòng phạm vi `.chat-pham-vi`); bên dưới là
`.chat-nhap`: ô nhập có chữ mờ ví dụ + nút "Gửi" (Enter để gửi,
Shift + Enter xuống dòng), ghi chú giới hạn ký tự và nút "Xóa cuộc trò chuyện" (chỉ hiện khi có lịch sử). Bảng số liệu,
bảng điểm, bảng trạng thái lớp và đoạn trích nguồn trong câu trả lời thu gọn trong `<details>` để luồng chat gọn.
Trang tóm tắt của Cố vấn có thêm form chọn sinh viên (`.chat-chon-sinh-vien`) phía trên khung chat. Nhãn ẩn cho
trình đọc màn hình dùng `.an-chu`. Dưới 640px bong bóng rộng tối đa 92%, luồng tin không giới hạn chiều cao.

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

## Chỉnh tương phản và khả năng đọc (WCAG)

> Ghi chú: mục này ghi lại lượt chỉnh trước khi đổi sang khung sidebar. Các mã màu cụ thể dưới đây (#166FE5,
> #0B5FCC, #B3122E, #8A8D91...) đã được thay bằng biến của bảng màu mới (xem mục "Bảng màu" và "Khung sidebar
> dùng chung"); các nguyên tắc (giãn dòng, tabular-nums, viền ô nhập ≥ 3:1, vòng focus rõ, viền đỏ trường lỗi,
> kích thước nút, responsive của bảng/bộ lọc, giảm chuyển động) vẫn giữ nguyên.

Lượt chỉnh trên nhánh `feat/giao-dien`, chỉ sửa CSS (không đổi HTML, tên lớp, view). Phong cách tham
chiếu: "Data-Dense Dashboard" (dashboard nhiều bảng và thẻ số liệu). Giữ nguyên bảng màu Facebook và
các màu thanh menu, dropdown, chân trang (đã có test khóa); không thêm biến màu vào `:root`. Tỷ lệ
tương phản tính theo công thức WCAG 2.x.

**Màu** (chữ thường cần 4,5:1):

| Thành phần | Trước | Sau |
|---|---|---|
| `.nut-chinh` (chữ trắng) | nền #1877F2, 4,23:1 | nền #166FE5 (`--mau-xanh-chinh-hover`), 4,73:1; hover #0B5FCC |
| `.nut-nhe` | chữ #1877F2 trên #E7F3FF, 3,76:1 | chữ #0B5FCC, 5,30:1 |
| `.nut-nguy-hiem` | chữ #E41E3F trên #FFEBE9, 4,02:1 | chữ #B3122E, 6,02:1 |
| `.o-lich-hoc` (chữ) | #1877F2 trên #E7F3FF, 3,76:1 | #0B5FCC, 5,30:1 (nền, viền trái giữ nguyên) |
| Liên kết trong văn bản (`p a`, `li a`...) | #1877F2 trên trắng, 4,23:1 | #0B5FCC, 5,96:1 |

Các hằng số #0B5FCC, #B3122E viết thẳng trong quy tắc (cùng cách với #145DBF của dropdown), không thêm
vào `:root`. Thanh menu chữ trắng trên #1877F2 (4,23:1) giữ nguyên, xem mục "Độ tương phản" ở trên.

**Font và chữ**: `body` giãn dòng 1.5 (trước để mặc định khoảng 1.15); `tabular-nums` cho bảng và
`.o-tong-hop__gia-tri`; `.logo__ten-he-thong` và `.o-tong-hop__ghi-chu--nho` từ 11px lên 12px.

**Khoảng cách và thẻ**: `--bong-the` đổi giá trị thành bóng 2 lớp nhẹ
(`0 1px 2px rgba(0,0,0,.06), 0 1px 3px rgba(0,0,0,.1)`, trước là `0 1px 2px rgba(0,0,0,.2)`);
`.luoi-tong-hop` cách nhau 16px (trước 12px); `.nut` cao tối thiểu 36px, `.nut-nho` 32px (vượt mức
24px của WCAG 2.2 về kích thước vùng bấm); nút bị vô hiệu (`:disabled`, `aria-disabled="true"`) mờ 60%,
con trỏ `not-allowed`.

**Bảng**: kẻ dòng dùng `--mau-nut-xam` (#E4E6EB, nhạt hơn #CED0D4 cũ), viền dưới tiêu đề bảng giữ
`--mau-vien`; ô dữ liệu `padding: 11px 14px`, giãn dòng 1.4; dòng có phần tử đang focus bằng bàn phím
(`tr:focus-within`) được tô nền như khi rê chuột (lưới tuần vẫn không tô).

**Form**: viền ô nhập #8A8D91 (3,33:1 trên trắng; #CED0D4 cũ chỉ 1,54:1, dưới mức 3:1 cho thành phần
giao diện), hover đậm sang `--mau-chu-phu`; ô nhập cao tối thiểu 40px; khi focus giữ viền
`--mau-xanh-chinh` và vòng `rgba(24,119,242,.35)` (vòng #E7F3FF cũ chỉ 1,13:1, gần như không thấy),
kèm `outline` trong suốt để chế độ tương phản cao của Windows vẫn hiện viền; trường có lỗi
(`aria-invalid="true"`, Django tự gắn) viền `--mau-do` ngay tại ô. Mọi liên kết có viền focus bàn
phím (`a:focus-visible`, xanh); liên kết ở chân trang Sinh viên dùng viền trắng vì nằm trên nền xanh.
Các thành phần có viền focus riêng (thanh menu, dropdown, chip) giữ nguyên.

**Ô chọn tệp** (`input[type="file"]`: nhập sinh viên từ Excel, tải lên/cập nhật tài liệu quy chế): vùng thả tệp
viền nét đứt 2px `--mau-vien`, nền `--mau-nen-trang`, bo góc 12px, cao tối thiểu 64px; rê chuột đổi viền
`--mau-xanh-chinh` nền `--mau-xanh-nhat`; nút chọn tệp của trình duyệt (`::file-selector-button`) thay bằng nút
viền trắng chữ `--mau-xanh-chinh` (để nút gửi form vẫn là nút chính); kéo thả tệp vào vùng này được (trình duyệt hỗ
trợ sẵn); vẫn giữ viền xanh khi focus và viền đỏ khi trường lỗi. Chỉ CSS trong `base.html`, không đổi form/template.

**Responsive**: dưới 768px chữ trong ô nhập 16px (tránh Safari iPhone tự phóng to); dưới 640px
`.khung` padding 16px, tiêu đề trang 20px, mỗi trường của `.bo-loc` một dòng và nút Lọc/Xóa lọc kéo
rộng đều; `.phan-trang` tự xuống dòng; khi người dùng bật giảm chuyển động (`prefers-reduced-motion`)
thì tắt mọi hiệu ứng chuyển tiếp trên toàn trang.

## Responsive

Khung: dưới `1025px` sidebar thành ngăn trượt mở bằng nút ☰ (cả 4 vai trò, xem "Khung sidebar dùng chung").
Nội dung: dưới `768px` lưới thẻ chức năng một cột, chữ trong ô nhập 16px; dưới `640px` thẻ thu padding, bộ lọc
mỗi trường một dòng. Bảng luôn cuộn ngang trong `.khung-bang` khi tràn.

