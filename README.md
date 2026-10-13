# Hệ thống quản lý đào tạo có tích hợp AI

Đồ án môn học, xây dựng theo đề "Hệ thống quản lý đào tạo có tích hợp AI" (xem `docs/de-bai.md`, tiêu chí chấm ở `docs/rubric.md`, sơ đồ dữ liệu ở `docs/erd.md`).

Phần chức năng quản lý (Phòng Đào tạo, Giảng viên, Sinh viên, Cố vấn học tập) đã hoàn thành: đăng nhập/phân quyền, quản lý sinh viên/giảng viên/cố vấn/ngành/lớp/học phần/lớp học phần/lịch học, đăng ký học phần (kiểm tra tiên quyết, trùng lịch, sĩ số), nhập điểm, tài liệu quy chế, thống kê báo cáo. Ba chức năng AI cũng đã hoàn thành: tư vấn đăng ký học phần, tóm tắt kết quả học tập, và chatbot hỏi đáp quy chế đào tạo — xem mục "Chức năng AI" bên dưới và `docs/thiet_ke_ai.md` (thiết kế chi tiết từng chức năng).

## Công nghệ sử dụng

- Backend: Django 6.0 (Python), môi trường ảo venv
- Frontend: Django template (HTML, CSS, JavaScript)
- CSDL: MySQL, database `qldt`, kết nối bằng PyMySQL
- Cấu hình nhạy cảm (mật khẩu CSDL, sau này có API key AI) đọc từ file `.env`, không commit `.env`

## Yêu cầu môi trường

- Python 3.11 trở lên
- MySQL Server 8.0 (Django 6.0 tương thích MySQL 8.0; nếu dùng Django 6.1 trở lên cần MySQL 8.4+)
- Git

## Cài đặt lần đầu

Các lệnh dưới đây chạy trong PowerShell tại thư mục gốc dự án. Nếu dùng Linux/macOS, thay `venv\Scripts\activate` bằng `source venv/bin/activate`.

### 1. Tạo môi trường ảo và cài thư viện

```
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Tạo database MySQL

Đăng nhập MySQL rồi chạy:

```sql
CREATE DATABASE qldt CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Tạo file `.env`

Sao chép `.env.example` thành `.env`, rồi điền giá trị thật (đặc biệt là `DB_PASSWORD` và một `DJANGO_SECRET_KEY` ngẫu nhiên):

```
copy .env.example .env
```

Có thể tạo `DJANGO_SECRET_KEY` ngẫu nhiên bằng:

```
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`.env` không commit lên git (đã có trong `.gitignore`).

### 4. Chạy migrate

```
python manage.py migrate
```

Lệnh này tạo 13 bảng nghiệp vụ theo `docs/erd.md` cùng một số bảng phụ do Django yêu cầu (xem mục "Bảng phụ của Django" ở cuối `docs/erd.md`).

### 5. Tạo tài khoản Phòng Đào tạo đầu tiên

```
python manage.py tao_tai_khoan_phong_dao_tao pdt_admin
```

Lệnh sẽ hỏi mật khẩu qua `getpass` (không gõ mật khẩu qua tham số dòng lệnh, không hiện ký tự khi gõ). Mật khẩu phải qua được các ràng buộc mật khẩu mặc định của Django (tối thiểu 8 ký tự, không quá phổ biến...).

### 6. Nạp dữ liệu mẫu để demo (tùy chọn)

```
python manage.py nap_du_lieu_mau
```

**Cảnh báo: lệnh này chỉ dùng để demo/phát triển.** Nó tạo hàng loạt tài khoản dùng chung một mật khẩu cố định:

- Mật khẩu demo: `MatKhauDemo123`
- Tài khoản: `pdt_demo` (Phòng Đào tạo), `gv001`/`gv002` (Giảng viên), `cv001` (Cố vấn học tập), `sv001`...`sv005` (Sinh viên)

Lệnh sẽ tự chặn nếu `DJANGO_DEBUG=False` (coi như môi trường thật) — chỉ vượt qua bằng cờ `--force` nếu chắc chắn đây vẫn là môi trường demo. **Không chạy lệnh này trên máy chủ thật/dữ liệu thật.** Lệnh chỉ chạy được một lần trên dữ liệu trống (chạy lại sẽ báo lỗi vì dữ liệu mẫu đã tồn tại).

#### Bộ dữ liệu đầy đủ cho buổi demo (tùy chọn)

```
python manage.py nap_du_lieu_day_du
```

Lệnh này nạp bộ dữ liệu lớn hơn, dùng cùng mật khẩu `MatKhauDemo123` và cùng cơ chế chặn (`DJANGO_DEBUG=False` cần `--force`). Chạy được trên CSDL trống (tự nạp luôn dữ liệu của `nap_du_lieu_mau`) hoặc sau khi đã chạy `nap_du_lieu_mau` (chỉ bổ sung phần còn thiếu). Toàn bộ chạy trong một transaction (lỗi thì không thay đổi gì), mất khoảng 10-20 giây, dữ liệu ngẫu nhiên dùng seed cố định nên lần nào cũng giống nhau. Chạy lại lần hai sẽ báo lỗi vì đã có lớp `ATTT_K1`.

- 3 lớp hành chính (`CNTT_K1`, `CNTT_K2`, `ATTT_K1`), mỗi lớp 30 sinh viên (`sv001`...`sv090`), cố vấn `cv001`/`cv002`/`cv003` (mỗi người đúng một lớp), 5 giảng viên `gv001`...`gv005`
- 13 học phần (7 cặp tiên quyết), 22 lớp học phần của HK1 và HK2 năm 2024-2025 (đã qua, có điểm) và HK1 2025-2026 (đang mở đăng ký)
- Kỳ đang mở: sinh viên mới đăng ký 3-5 lớp qua đúng dịch vụ đăng ký (kiểm tra tiên quyết, trùng lịch, sĩ số), có điểm danh, lịch thi và 10 thông báo
- 8 sinh viên bị cảnh báo học vụ (mức đỏ `sv010`, `sv036`, `sv052`, `sv066`; mức vàng `sv018`, `sv025`, `sv045`, `sv080`) để thử màn hình cố vấn/cảnh báo
- 4 ca lỗi đăng ký của `sv001`...`sv005` (thiếu tiên quyết, trùng lịch, đủ sĩ số) vẫn đúng như mô tả ở trên
- Lệnh này dời ngày bắt đầu của HK1 2025-2026 lùi 28 ngày (để có các buổi điểm danh trong quá khứ thuộc đúng học kỳ)

## Chạy server

```
python manage.py runserver
```

Mở `http://127.0.0.1:8000/`.

## Chạy test

```
python manage.py test
```

Django tự tạo và xóa database test riêng (`test_qldt`), không ảnh hưởng database `qldt` đang dùng.

## Hướng dẫn demo theo vai trò

Sau khi nạp dữ liệu mẫu (bước 6), đăng nhập tại `/dang-nhap/` với các tài khoản sau (mật khẩu chung: `MatKhauDemo123`):

### Phòng Đào tạo (`pdt_demo`)

- Trang chủ có đủ liên kết: Quản lý tài khoản, Lớp học phần, Tra cứu lịch sử đăng ký, Tài liệu quy chế, các trang thống kê.
- Thử tạo/khóa tài khoản tại "Quản lý tài khoản".
- Xem `Lớp học phần` → mở lớp `CTDLGT_2025` xem "Danh sách đăng ký" (đã có SV003) và "Điểm".
- Xem 3 trang thống kê: sĩ số theo lớp, học phần nhiều đăng ký nhất, kết quả học tập tổng hợp.

### Giảng viên (`gv001` hoặc `gv002`)

- `gv001` dạy `CSDL_2024`, `CTDLGT_2024`, `CTDLGT_2025`. `gv002` dạy `CNPM_2025`, `AIUD_2025`.
- Vào "Lớp phụ trách" → "Bảng điểm" của một lớp để nhập/sửa điểm.

### Sinh viên (`sv001`...`sv005`) — demo quy trình đăng ký học phần

Vào "Đăng ký học phần" (`/dang-ky/lop-dang-mo/`):

| Tài khoản | Đăng ký lớp | Kết quả mong đợi |
|---|---|---|
| `sv001` | `CNPM_2025` rồi `AIUD_2025` | Thành công (đã đạt `CTDLGT`, `CSDL` từ kỳ trước — đúng ví dụ trong đề bài) |
| `sv002` | `CNPM_2025` hoặc `AIUD_2025` | Báo lỗi **thiếu học phần tiên quyết** |
| `sv003` | `AIUD_2025` | Báo lỗi **trùng lịch** với `CTDLGT_2025` (đã đăng ký, cùng Thứ 2) |
| `sv005` | `CTDLGT_2025` | Báo lỗi **lớp đã đủ sĩ số** (sĩ số tối đa = 1, `sv003` đã chiếm chỗ) |

Sau khi đăng ký, `sv001` có thể xem "Thời khóa biểu", "Lịch sử đăng ký", "Bảng điểm của tôi".

### Cố vấn học tập (`cv001`)

- Phụ trách lớp hành chính `CNTT_K1` (toàn bộ `sv001`...`sv005`).
- Vào "Sinh viên phụ trách" → bấm "Xem điểm" một sinh viên để xem bảng điểm.

## Chức năng AI

Hệ thống có 3 chức năng dùng AI (Gemini, qua SDK chính thức `google-genai`), theo nguyên
tắc **"code tính, AI diễn giải"**: mọi con số/điều kiện đều do code Django tính sẵn, AI chỉ
được gửi kết quả đã tính để giải thích/xếp loại/tóm tắt — không bao giờ tự tính lại hay
được tin tưởng tuyệt đối (mọi thứ AI trả về đều được lọc lại bằng code trước khi hiển thị).

1. **Tư vấn đăng ký học phần** (`tu_van_dang_ky`, trang `/tu-van-dang-ky/`, chỉ Sinh viên) —
   gợi ý lớp nên đăng ký trong một học kỳ dựa trên trạng thái từng lớp (đủ điều kiện/thiếu
   tiên quyết/trùng lịch/đã đầy/đã đăng ký) do code tính.
2. **Tóm tắt kết quả học tập** (`tom_tat_ket_qua`, trang `/tom-tat-ket-qua/toi/` cho Sinh
   viên tự xem, `/tom-tat-ket-qua/co-van/` cho Cố vấn học tập xem sinh viên lớp mình phụ
   trách) — tóm tắt điểm mạnh/học phần cần cải thiện dựa trên số liệu do code tính (tổng
   tín chỉ đã đạt, số học phần đạt/chưa đạt, điểm cao nhất/thấp nhất).
3. **Chatbot hỏi đáp quy chế đào tạo** (`hoi_dap_quy_che`, trang `/hoi-dap-quy-che/`, Sinh
   viên và Cố vấn học tập) — trả lời câu hỏi dựa trên các đoạn quy chế truy hồi được (tự cài
   BM25, không dùng dịch vụ embedding ngoài) từ tài liệu đã tải lên ở "Tài liệu quy chế".

Chi tiết luồng xử lý, dữ liệu gửi/không gửi cho AI, các lớp kiểm tra sau khi AI trả lời, và
cách xử lý từng loại lỗi của mỗi chức năng: xem `docs/thiet_ke_ai.md`.

### Biến môi trường (`.env`)

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `GEMINI_API_KEY` | Khóa API Gemini | (bắt buộc phải điền) |
| `GEMINI_MODEL` | Tên model Gemini dùng gọi (đổi được, không cần sửa code) | `gemini-flash-latest` |
| `AI_TIMEOUT_GIAY` | Thời gian chờ tối đa một lượt gọi (giây) | `20` |
| `AI_SO_LAN_THU_LAI` | Số lần thử lại khi hết thời gian chờ/bị giới hạn tần suất (429)/lỗi máy chủ (5xx) | `2` |
| `AI_GIOI_HAN_KY_TU` | Số ký tự tối đa cho nội dung gửi AI, vượt quá bị từ chối trước khi gọi API | `8000` |
| `AI_PHIEN_BAN_TU_VAN` | Phiên bản prompt `prompts/tu_van_dang_ky/<phiên bản>/` | `v1` |
| `AI_PHIEN_BAN_TOM_TAT` | Phiên bản prompt `prompts/tom_tat_ket_qua/<phiên bản>/` | `v1` |
| `AI_PHIEN_BAN_QUY_CHE` | Phiên bản prompt `prompts/hoi_dap_quy_che/<phiên bản>/` | `v1` |
| `AI_NGUONG_DIEM_TRUY_HOI` | Ngưỡng điểm BM25 tối thiểu để một đoạn quy chế được coi là liên quan | `0.5` |
| `AI_TRUY_HOI_PHIEN_BAN` | Phiên bản thuật toán truy hồi cho chatbot quy chế: `v1` (bản cũ) hoặc `v2` (có bigram + tiêu đề Điều) | `v2` |

### Lấy khóa API và cấu hình

1. Lấy khóa miễn phí tại <https://aistudio.google.com/apikey>.
2. Dán vào `.env`: `GEMINI_API_KEY=<khóa của bạn>`. **Không commit khóa lên Git** (`.env` đã
   nằm trong `.gitignore`; các biến còn lại trong bảng trên có giá trị mặc định hợp lý, chỉ
   cần đổi khi muốn thử nghiệm/so sánh).

### Kiểm tra kết nối AI

```
python manage.py kiem_tra_ai
```

Gửi một câu chào không chứa dữ liệu người dùng để xác nhận khóa/kết nối hoạt động, không
bao giờ in khóa API ra màn hình. Thêm `--chi_tiet` để xem loại lỗi gốc/mã HTTP/thông điệp
API khi thất bại (vẫn không in khóa).

### Chạy ca thử (so sánh chất lượng giữa các phiên bản prompt, không tốn quota nếu không dùng `--ai`)

Mỗi chức năng AI có một bộ ca thử mô tả trong `docs/ca_thu_ai/*.md` và một lệnh quản lý
tương ứng chạy đúng luồng `services.py` như trên trang web thật (`tu_van_dang_ky`/
`tom_tat_ket_qua` dựng dữ liệu trong một transaction rồi hoàn tác — không làm bẩn CSDL):

```
python manage.py chay_ca_thu_tu_van       # docs/ca_thu_ai/tu_van_dang_ky.md, 10 ca
python manage.py chay_ca_thu_tom_tat      # docs/ca_thu_ai/tom_tat_ket_qua.md, 10 ca
python manage.py chay_ca_thu_quy_che      # docs/ca_thu_ai/hoi_dap_quy_che.md, 10 câu
```

Mặc định (không `--ai`) chỉ kiểm tra ở tầng code (trạng thái/số liệu do code tính, độ dài
prompt, không có dữ liệu cá nhân trong prompt) và **không gọi AI thật**. Tùy chọn chung của
cả 3 lệnh:

- `--ai`: gọi AI thật cho các ca cần AI thật — in trước số lượt gọi dự kiến và hỏi xác nhận
  `y/n` (bỏ qua bằng `--yes`) vì hạn mức gói miễn phí rất thấp (xem mục hạn mức bên dưới).
- `--cau 1,4,8`: chỉ chạy các câu/ca được liệt kê (số thứ tự, cách nhau bằng dấu phẩy).
- `--phien_ban_prompt v2`: ghi đè phiên bản prompt chỉ cho lần chạy này (không cần sửa
  `.env`), dùng để so sánh nhanh giữa các phiên bản.
- `--ghi_vao ket-qua.txt`: nối (append) kết quả lần chạy vào một tệp, kèm tiêu đề (ngày
  giờ, phiên bản prompt, model thực tế API trả về, danh sách câu/ca đã chạy) để so sánh các
  lần chạy với nhau theo thời gian.
- `chay_ca_thu_quy_che` có thêm `--khoang_cach` (giây chờ giữa các lần gọi AI, mặc định 15)
  và `--chi_tiet` (in thêm loại lỗi gốc/mã HTTP/thông điệp API khi một câu lỗi).

### Đổi phiên bản prompt để so sánh

Thêm một thư mục `prompts/<chức_năng>/v2/` (copy từ `v1/`, chỉnh nội dung `system.txt`/
`user.txt`), rồi:

- Đổi lâu dài: sửa biến `AI_PHIEN_BAN_*` tương ứng trong `.env`.
- Đổi thử một lần: dùng `--phien_ban_prompt v2` khi chạy lệnh ca thử ở trên, hoặc set biến
  môi trường tạm thời khi chạy `runserver`.

### Giới hạn hạn mức gói miễn phí và cách hệ thống xử lý khi hết

Gói miễn phí Gemini có hạn mức theo **ngày** (quan sát thực tế trong quá trình phát triển:
chỉ khoảng 20 request/ngày cho một số model) và theo **phút**. Khi hệ thống bị từ chối do
vượt hạn mức (lỗi HTTP 429):

- `ai_core` tự đọc thời gian chờ nhà cung cấp đề xuất (nếu có, tối đa 60 giây) và thử lại
  theo `AI_SO_LAN_THU_LAI`; nếu vẫn thất bại, phân biệt rõ **hết hạn mức hôm nay** (thông
  báo "đã hết hạn mức sử dụng hôm nay, vui lòng thử lại sau khi hạn mức được đặt lại") với
  **vượt tần suất theo phút** (thử lại sau vài phút) — xem `ai_core/exceptions.py`.
- Mọi chức năng AI đều hiển thị thông báo lỗi thân thiện bằng tiếng Việt, **không bao giờ
  crash trang** — dữ liệu do code tính (trạng thái lớp học phần, bảng điểm, đoạn quy chế
  truy hồi được) vẫn hiển thị đầy đủ dù AI thất bại.
- `tu_van_dang_ky`, `tom_tat_ket_qua`, `hoi_dap_quy_che` đều giới hạn tần suất theo người
  dùng (mặc định 10 lần/phút, dùng cache của Django — xem `ai_core/gioi_han_tan_suat.py` và
  `hoi_dap_quy_che/gioi_han_tan_suat.py`) để một người dùng không thể một mình làm cạn hạn
  mức dùng chung của cả hệ thống.
- Khi phát triển/thử nghiệm (viết code, chạy test), luôn dùng client giả — mặc định của các
  lệnh `chay_ca_thu_*` (không thêm `--ai`) đã tự làm việc này, không cần cấu hình gì thêm —
  trừ khi thật sự cần xác nhận với AI thật, để tiết kiệm hạn mức ít ỏi của gói miễn phí.

## Cấu trúc thư mục

```
UDTTNT/
├── manage.py
├── requirements.txt
├── .env.example              # mẫu biến môi trường, không có giá trị thật
├── qldt/                      # cấu hình dự án Django (settings, urls)
├── accounts/                  # tai_khoan: đăng nhập, phân quyền, quản lý tài khoản
├── people/                    # sinh_vien, giang_vien, co_van_hoc_tap
├── academics/                 # nganh_hoc, lop_hanh_chinh, hoc_phan, dieu_kien_tien_quyet
├── classes/                   # lop_hoc_phan, lich_hoc
├── enrollment/                 # dang_ky_hoc_phan (đăng ký học phần)
├── grades/                     # diem, tính điểm tổng kết
├── regulations/                 # tai_lieu_quy_che (tải lên/tải về tài liệu quy chế)
├── reports/                     # thống kê/báo cáo (không có bảng riêng)
├── ai_core/                     # hạ tầng gọi Gemini dùng chung: client, exception, prompt loader,
│                                 # client giả cho test, giới hạn tần suất dùng chung, lệnh kiem_tra_ai
├── tu_van_dang_ky/               # chức năng AI tư vấn đăng ký học phần, lệnh chay_ca_thu_tu_van
├── tom_tat_ket_qua/               # chức năng AI tóm tắt kết quả học tập, lệnh chay_ca_thu_tom_tat
├── hoi_dap_quy_che/                # chatbot hỏi đáp quy chế (BM25 tự cài), lệnh chay_ca_thu_quy_che
├── prompts/                        # prompt tách khỏi code: <chức_năng>/<phiên_bản>/{system,user}.txt
├── templates/                       # template dùng chung (base.html, trang lỗi 403/404/500)
├── media/                            # tệp tải lên (quy_che/...), không commit, chỉ tải về qua view có đăng nhập
└── docs/
    ├── de-bai.md, rubric.md, erd.md   # đề bài, tiêu chí chấm, sơ đồ dữ liệu
    ├── thiet_ke_ai.md                  # thiết kế chi tiết 3 chức năng AI
    ├── review_code_ai.md                # báo cáo review bảo mật/chất lượng code các app AI
    ├── bien_ban_kiem_thu.md              # bảng kiểm thử tự động + thủ công theo vai trò
    ├── ai-log.md                          # nhật ký các vòng thử nghiệm/tối ưu prompt
    └── ca_thu_ai/                          # bộ câu hỏi/ca thử cho từng chức năng AI
```

Mỗi app Django có cấu trúc `models.py` (nếu có bảng riêng), `services.py` (nghiệp vụ/gọi AI), `views.py`, `urls.py`, `tests.py`, `templates/<app>/`; các app AI có thêm `management/commands/chay_ca_thu_*.py`.
