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

## Quên mật khẩu

Trang đăng nhập có link **"Quên mật khẩu?"**. Sinh viên, giảng viên và cố vấn học tập nhập email trong hồ sơ của
mình (không phân biệt hoa thường), hệ thống gửi thư có link đặt lại mật khẩu:

- Link chỉ dùng được một lần và hết hạn sau 30 phút (`PASSWORD_RESET_TIMEOUT` trong `qldt/settings.py`).
- Mật khẩu mới phải qua các ràng buộc mật khẩu hiện có và không được trùng mật khẩu cũ. Đặt lại xong thì tài
  khoản không còn bị buộc đổi mật khẩu, số lần đăng nhập sai và trạng thái tạm chặn đăng nhập được xóa.
- Không gửi thư khi email khớp nhiều hơn một hồ sơ, tài khoản bị khóa, hoặc là tài khoản Phòng Đào tạo (không có
  hồ sơ email). Mọi trường hợp đều hiện cùng một thông báo, nên không đoán được email nào có trong hệ thống.
- Mỗi email và mỗi IP gửi tối đa 3 yêu cầu trong 15 phút (dùng cache, không tạo bảng mới).

Chức năng **Phòng Đào tạo đặt lại mật khẩu** (cấp mật khẩu tạm ở trang Tài khoản) vẫn giữ nguyên.

### Cấu hình gửi thư qua Gmail

1. Bật xác minh 2 bước cho tài khoản Gmail dùng để gửi thư.
2. Vào https://myaccount.google.com/apppasswords, tạo **mật khẩu ứng dụng** (16 ký tự). Không dùng mật khẩu
   đăng nhập Gmail.
3. Điền vào `.env` (không commit tệp này):

   ```
   EMAIL_HOST_USER=ten.tai.khoan@gmail.com
   EMAIL_HOST_PASSWORD=<mật khẩu ứng dụng 16 ký tự>
   DEFAULT_FROM_EMAIL=Phòng Đào tạo <ten.tai.khoan@gmail.com>
   ```

4. Khởi động lại máy chủ (Docker: `docker compose up -d`).
5. Gửi thư thử để kiểm tra cấu hình:

   ```
   python manage.py thu_gui_email dia.chi.cua.ban@gmail.com
   docker compose exec web python manage.py thu_gui_email dia.chi.cua.ban@gmail.com
   ```

   (dòng 1 khi chạy bằng venv, dòng 2 khi chạy bằng Docker). Lệnh in cấu hình đang dùng (không in mật khẩu) và
   kết quả: thành công, hoặc loại lỗi SMTP kèm gợi ý. Ví dụ `SMTPAuthenticationError (mã 535)` là sai
   mật khẩu ứng dụng, `TimeoutError` là mạng chặn cổng 587.

Thư được gửi trong luồng nền (trang chuyển ngay sau khi bấm Gửi), chờ máy chủ SMTP tối đa `EMAIL_TIMEOUT` = 10
giây. Mỗi yêu cầu quên mật khẩu ghi một dòng log `qldt.email` vào `logs/app.log` và ra màn hình máy chủ: đã gửi,
lỗi gửi (loại lỗi SMTP), hoặc lý do không gửi (không khớp hồ sơ, email trùng nhiều hồ sơ, tài khoản bị khóa, tài
khoản Phòng Đào tạo, vượt giới hạn). Email trong log đã được che (`s***@gmail.com`), log không ghi link đặt lại.
Xem nhanh bằng `docker compose logs web | grep qldt.email`.

Chưa điền `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` thì hệ thống **không gửi thư thật** mà in thư ra màn hình
của máy chủ (console backend). Lúc demo lấy link trong thư bằng cách xem cửa sổ đang chạy `runserver`, hoặc
`docker compose logs web` nếu chạy bằng Docker. Thư có chứa link đặt lại mật khẩu, nên không gửi log này cho
người khác.

### Phòng Đào tạo quên mật khẩu

Tài khoản Phòng Đào tạo không có hồ sơ email nên không dùng được "Quên mật khẩu?". Người quản trị máy chủ đặt lại
bằng lệnh `changepassword` của Django (lệnh hỏi mật khẩu mới, không hiện ký tự khi gõ):

```
python manage.py changepassword pdt_admin
```

Chạy bằng Docker thì dùng `docker compose exec web python manage.py changepassword pdt_admin`. Một tài khoản
Phòng Đào tạo khác cũng đặt lại được mật khẩu cho tài khoản này ở trang Tài khoản.

## Chạy test

```
python manage.py test                     # toàn bộ test
python manage.py test --tag don_vi        # test đơn vị: gọi trực tiếp hàm services / tính điểm
python manage.py test --tag tich_hop      # test tích hợp: đi qua URL, view, phân quyền bằng test Client
```

Django tự tạo và xóa database test riêng (`test_qldt`), không ảnh hưởng database `qldt` đang dùng.
Test chức năng AI dùng client giả, không gọi Gemini thật. Test xuyên luồng nhiều vai trò (Phòng Đào tạo
tạo lớp → sinh viên đăng ký → giảng viên nhập điểm → sinh viên xem bảng điểm) ở
`enrollment/tests_luong_tich_hop.py`.

CI (`.github/workflows/ci.yml`) tự chạy mỗi lần push hoặc mở pull request trên GitHub: dựng MySQL 8.0,
cài thư viện, chạy `check`, kiểm tra không thiếu migration, rồi test đơn vị và test tích hợp.
Xem kết quả ở tab **Actions** của repo.

## Rào chắn khi commit (pre-commit)

`.pre-commit-config.yaml` chạy 3 kiểm tra trước **mỗi lần commit**, không phụ thuộc công cụ AI nào:

| Hook | Việc làm |
|---|---|
| `chan-commit-env` | Chặn commit `.env`, `.env.local`, ... (chỉ cho `.env.example`) |
| `quet-khoa-api` | Quét tệp được commit tìm chuỗi giống khóa API (`AIza...`, `sk-...`, `GEMINI_API_KEY=<giá trị>`, private key); in tên tệp và số dòng, không in khóa (`nha_may_agent/quet_khoa.py`, dùng chung mẫu với rào chắn nhà máy agent) |
| `django-check` | Chạy `python manage.py check` khi có tệp `.py`/`.html`/`.txt` thay đổi |

Cài một lần, trong terminal **đã kích hoạt venv** (hook dùng `python` trong PATH để có Django):

```
venv\Scripts\activate
pip install pre-commit
pre-commit install            # gắn hook vào .git/hooks/pre-commit
pre-commit run --all-files    # chạy thử trên toàn repo
```

Từ đó `git commit` tự chạy các hook; hook báo lỗi thì commit bị hủy, sửa xong commit lại. `pre-commit` là công
cụ cho người phát triển nên không nằm trong `requirements.txt` (ảnh Docker và CI không cần).

## Chạy bằng Docker

Cần Docker Desktop (Windows/macOS) hoặc Docker Engine + Compose (Linux). Không cần cài Python, MySQL.

1. Tạo `.env` từ `.env.example` (như mục "Cài đặt lần đầu"), **bắt buộc** đặt `DB_PASSWORD`
   (mật khẩu root của MySQL trong container). `DB_HOST`, `DB_USER`, `DB_PORT` được compose tự ghi đè.
2. Khởi động:

   ```
   docker compose up -d --build
   ```

   Container `db` (MySQL 8.0) chạy trước; khi `db` sẵn sàng, container `web` tự chạy `migrate` rồi mở
   máy chủ ở `http://localhost:8000/`.
3. Tạo tài khoản và dữ liệu mẫu (tùy chọn), chạy lệnh trong container `web`:

   ```
   docker compose exec web python manage.py tao_tai_khoan_phong_dao_tao pdt_admin
   docker compose exec web python manage.py nap_du_lieu_mau
   ```

4. Dừng: `docker compose down` (giữ dữ liệu trong volume); `docker compose down -v` xóa cả dữ liệu.

Dữ liệu MySQL, tệp tải lên và log nằm trong các volume `du_lieu_mysql`, `tep_tai_len`, `nhat_ky`, không mất
khi build lại ảnh. `.env` không nằm trong ảnh (`.dockerignore`), chỉ được đọc lúc chạy.

Khi chạy thật đặt `DJANGO_DEBUG=False`; lúc đó **bắt buộc** có `DJANGO_SECRET_KEY`, thiếu thì ứng dụng
báo lỗi và dừng (không dùng khóa mặc định). Nhớ thêm tên miền/IP vào `DJANGO_ALLOWED_HOSTS`.

### Khuyến nghị khi demo: `DJANGO_DEBUG=False`

Khi demo nên đặt trong `.env`:

```
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<chuỗi ngẫu nhiên dài>
```

Tạo khóa bằng `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`.

Lý do: với `DJANGO_DEBUG=True`, khi gặp lỗi Django hiện trang vàng kèm traceback, đường dẫn mã nguồn, cấu hình
và danh sách URL. Với `DJANGO_DEBUG=False`, người dùng chỉ thấy trang lỗi của hệ thống:

- 403 (`templates/403.html`): "Không có quyền truy cập", ví dụ sinh viên mở trang của Phòng Đào tạo.
- 404 (`templates/404.html`): "Không tìm thấy trang".
- 500 (`templates/500.html`): "Lỗi hệ thống", không lộ chi tiết lỗi; chi tiết chỉ ghi vào `logs/app.log`.

Test `qldt.tests.TrangLoiKhiTatDebugTest` kiểm tra ba trang này. Docker chạy `runserver --insecure` nên CSS
vẫn hiển thị khi `DJANGO_DEBUG=False`. Lệnh `nap_du_lieu_mau` chặn khi `DJANGO_DEBUG=False`: nạp dữ liệu mẫu
trước (lúc còn `True`) hoặc thêm `--force` nếu chắc chắn đây là máy demo.

## Truy cập từ điện thoại qua Cloudflare Tunnel

Cloudflare Tunnel (bản nhanh, không cần tài khoản) tạo một địa chỉ `https://<tên-ngẫu-nhiên>.trycloudflare.com`
trỏ về máy chủ đang chạy trên máy bạn, để mở được từ điện thoại hoặc máy khác.

1. Cài `cloudflared`. Trên Windows: `winget install --id Cloudflare.cloudflared`.
2. Thêm vào `.env`:

   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
   CSRF_TRUSTED_ORIGINS=https://*.trycloudflare.com
   ```

   - `DJANGO_ALLOWED_HOSTS` có `.trycloudflare.com` (dấu chấm đầu nghĩa là mọi tên miền con). Thiếu thì Django
     báo 400 Bad Request.
   - `CSRF_TRUSTED_ORIGINS` có `https://*.trycloudflare.com`: khai báo rõ origin được tin cho kiểm tra CSRF.
     Lỗi 403 "CSRF verification failed. Origin checking failed" khi gửi form (đăng nhập, quên mật khẩu...) xảy ra
     vì trình duyệt gửi Origin `https://...` trong khi máy chủ nhận request `http`. `SECURE_PROXY_SSL_HEADER`
     (bên dưới) đã sửa phần lớn trường hợp; biến này giữ cho form vẫn gửi được nếu proxy không gửi header
     `X-Forwarded-Proto`.
   - Mỗi biến là danh sách cách nhau bởi dấu phẩy; khoảng trắng và giá trị rỗng được bỏ qua.

3. Khởi động lại máy chủ để đọc `.env`. Docker: `docker compose up -d --force-recreate web`; venv: dừng và chạy
   lại `python manage.py runserver`.
4. Mở tunnel (giữ cửa sổ này chạy trong lúc dùng):

   ```
   cloudflared tunnel --url http://localhost:8000
   ```

   Lệnh in ra địa chỉ dạng `https://abc-xyz.trycloudflare.com`. Mở địa chỉ đó trên điện thoại. Mỗi lần chạy lại
   lệnh thì địa chỉ đổi, nhưng không cần sửa `.env` vì đã dùng `*.trycloudflare.com`.

Tunnel nhận HTTPS rồi chuyển tiếp vào máy chủ kèm header `X-Forwarded-Proto: https`. Nhờ
`SECURE_PROXY_SSL_HEADER` trong `qldt/settings.py`, Django biết request gốc là HTTPS, nên link đặt lại mật khẩu
trong email cũng dùng `https://...trycloudflare.com`. Lưu ý: ai có địa chỉ tunnel đều mở được trang đăng nhập,
nên tắt tunnel (Ctrl+C) khi dùng xong và không dùng tài khoản demo mật khẩu chung khi tunnel đang mở cho người lạ.

## Vận hành và theo dõi

### Kiểm tra sức khỏe: `/health/`

```
curl http://127.0.0.1:8000/health/
```

Trả `{"trang_thai": "ok", "ung_dung": "ok", "csdl": "ok"}` (HTTP 200) khi ứng dụng chạy và kết nối được
MySQL; mất kết nối CSDL thì trả `"csdl": "loi"` với HTTP 503. Không cần đăng nhập, không trả thông tin cấu
hình. Docker dùng endpoint này làm `HEALTHCHECK`: `docker compose ps` hiện `(healthy)` khi mọi thứ ổn.

### Xem log

Log ghi ra `logs/app.log`, tự xoay vòng khi đạt 5 MB (giữ 5 tệp cũ `app.log.1` … `app.log.5`).

```
Get-Content logs\app.log -Tail 50 -Wait                 # Windows PowerShell
tail -f logs/app.log                                      # Linux/macOS
docker compose exec web tail -f logs/app.log              # khi chạy bằng Docker
```

Nội dung log:
- Mỗi lượt gọi AI một dòng, ví dụ
  `INFO qldt.ai goi_ai chuc_nang=tu_van_dang_ky ket_qua=thanh_cong loai_loi=- thoi_gian_ms=1840` hoặc
  `WARNING qldt.ai goi_ai chuc_nang=tom_tat_ket_qua ket_qua=loi loai_loi=QuaGioiHanTanSuatAI thoi_gian_ms=320`.
  **Không bao giờ** ghi nội dung prompt, câu trả lời của AI hay điểm (xem `ai_core/theo_doi.py`).
- Lỗi máy chủ (500) của Django và cảnh báo bảo mật (`django.security`, ví dụ lỗi CSRF).

Đếm nhanh tỉ lệ lỗi AI: `Select-String -Path logs\app.log -Pattern "ket_qua=loi"` (PowerShell) hoặc
`grep -c "ket_qua=loi" logs/app.log`.

### Sao lưu và khôi phục CSDL (mysqldump)

Tệp sao lưu chứa dữ liệu cá nhân sinh viên: cất ở nơi an toàn, **không commit** lên Git.

Cài MySQL trên máy:

```
mysqldump -u root -p --single-transaction --routines --default-character-set=utf8mb4 qldt > sao_luu_qldt.sql
mysql -u root -p --default-character-set=utf8mb4 qldt < sao_luu_qldt.sql
```

Chạy bằng Docker (mật khẩu lấy từ biến môi trường trong container, không gõ ra dòng lệnh):

```
docker compose exec db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines qldt' > sao_luu_qldt.sql
docker compose exec -T db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" qldt' < sao_luu_qldt.sql
```

Khôi phục ghi đè dữ liệu hiện có của database `qldt`. Sao lưu cả thư mục `media/` (tài liệu quy chế đã tải
lên) nếu cần khôi phục đầy đủ.

## Nhà máy Agent AI

Dự án tổ chức việc phát triển phần mềm bằng AI như một "nhà máy": mỗi agent đóng một vai trò trong SDLC,
dây chuyền nối các agent theo thứ tự với hai cổng người duyệt, và rào chắn ở nhiều lớp chặn thao tác nguy
hiểm. Mọi thành phần **trung lập với công cụ**: đặc tả bằng Markdown theo chuẩn mở, nhà máy tự động chạy
bằng Gemini qua chính hạ tầng `ai_core` của dự án.

| Thành phần | Vị trí | Vai trò |
|---|---|---|
| Ngữ cảnh (context engineering) | `AGENTS.md`, `docs/agent/ngu_canh_du_an.md` | Mọi agent đọc trước: vai trò, app, quy ước, "code tính, AI diễn giải", quy tắc dữ liệu gửi AI, lệnh test, điều cấm. `AGENTS.md` theo chuẩn mở, công cụ lập trình AI nào cũng đọc được |
| Đặc tả 5 vai trò | `agents/*.md` | `phan_tich_yeu_cau` (chỉ đọc) → `lap_trinh_vien` → `kiem_thu_vien` → `review_code`, `kiem_tra_bao_mat` (chỉ đọc) |
| Dây chuyền | `agents/quy_trinh.md` | Phân tích → **người duyệt đặc tả** → lập trình → viết test → **người duyệt diff** → chạy test (sửa tối đa 2 vòng, vẫn lỗi thì hoàn tác) → review + bảo mật → nhật ký |
| Nhà máy tự động (Gemini) | `nha_may_agent/`, `prompts/nha_may_*/` | `python manage.py chay_nha_may "<yêu cầu>"` chạy đủ dây chuyền; `--chay-thu` chỉ in đặc tả và diff, không ghi gì |
| Rào chắn trong nhà máy | `nha_may_agent/rao_chan.py` | Chỉ ghi trong thư mục app, `templates/`, `prompts/`; cấm `.env`, migration đã có, `settings.py`, `nha_may_agent/`, đường dẫn tuyệt đối/`..`; chặn nội dung giống khóa API và thay đổi làm giảm số test; không đưa `.env`/`venv`/`.git` vào prompt; giới hạn số lượt gọi AI (`NHA_MAY_SO_LUOT_AI_TOI_DA`) |
| Rào chắn mức git | `.pre-commit-config.yaml` | Chặn commit `.env`, quét khóa API, chạy `manage.py check` trước mỗi commit (xem mục "Rào chắn khi commit") |
| Kiểm thử + CI | `@tag('don_vi')`, `@tag('tich_hop')`, `.github/workflows/ci.yml` | Mỗi push/pull request chạy check, kiểm tra migration, test đơn vị và tích hợp trên MySQL 8.0 |
| Theo dõi | `logs/app.log`, `/health/` | Log từng lượt gọi AI kể cả của nhà máy (`chuc_nang=nha_may_<vai_tro>`, không ghi nội dung), kiểm tra sức khỏe ứng dụng và CSDL |
| Nhật ký | `docs/ai-log.md` | Mục "Nhật ký nhà máy agent": mỗi lần chạy nhà máy (trừ chạy thử) thêm yêu cầu, agent đã chạy, số lượt gọi AI, tệp đã đổi, kết quả test, nhận xét review/bảo mật, phần người cần kiểm tra |

### Chạy thử nhà máy

Cần `GEMINI_API_KEY` trong `.env`. Mỗi lần chạy tốn tối đa 3 lượt gọi AI khi chạy thử, tối đa 7 lượt khi chạy đủ.

```
venv\Scripts\python manage.py chay_nha_may "Giảng viên xem số sinh viên đã có đủ điểm trong lớp phụ trách" --chay-thu
```

Nhà máy in đặc tả rồi hỏi `Duyệt đặc tả ...? (y/n)`; gõ `y` để agent lập trình và kiểm thử viên đề xuất thay đổi,
nhà máy in diff rồi dừng (chạy thử không ghi tệp, không chạy test, không ghi nhật ký). Bỏ `--chay-thu` để chạy đủ:
nhà máy hỏi thêm `Áp dụng ...? (y/n)` trước khi ghi tệp và chạy test, cuối cùng ghi nhật ký. Nhà máy **không
commit, không push**: người đọc `git diff` và tự commit.

Nhà máy báo lỗi AI (ví dụ "Dịch vụ AI gặp lỗi") thì chạy lại với `--chi-tiet`: in cấu hình, độ dài prompt và
thời gian từng lượt gọi, agent bị lỗi, loại lỗi gốc, mã HTTP, thông điệp từ API và gợi ý khắc phục (không in khóa API).
Nhà máy dùng cấu hình riêng, không đụng giới hạn của 3 chức năng AI trong sản phẩm: `NHA_MAY_GIOI_HAN_KY_TU`
(ký tự mỗi prompt, phần nội dung tệp/diff tự cắt cho vừa), `NHA_MAY_TIMEOUT_GIAY` (mặc định 180 giây — prompt chứa
mã nguồn và đầu ra dài cần lâu hơn `AI_TIMEOUT_GIAY`; không kịp thì máy chủ trả 504 DEADLINE_EXCEEDED),
`NHA_MAY_SO_LAN_THU_LAI` (mặc định 1).

Dùng công cụ lập trình AI khác thay cho nhà máy: đưa `AGENTS.md` và tệp vai trò của bước đang làm, giữ đúng
hai cổng người duyệt như `agents/quy_trinh.md`.

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

Cả 3 chức năng là **khung chat**: gõ câu hỏi, ví dụ "Tóm tắt học kỳ 1 năm học
2024-2025", "Tóm tắt năm học 2024-2025", "Tư vấn học kỳ 1 năm học 2025-2026, em muốn học các môn về AI",
"Sinh viên bị cảnh báo học tập khi nào?". Code tự đọc học kỳ/năm học trong câu (không nhờ AI hiểu câu), mỗi tin
nhắn gọi AI tối đa một lần; câu thiếu dữ liệu hoặc không liên quan được trả lời ngay mà không gọi AI. Lịch sử
hội thoại lưu trong session (tối đa 10 lượt, không tạo bảng CSDL mới, không gửi lại cho AI).

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
├── Dockerfile, docker-compose.yml, .dockerignore   # đóng gói: web Django + MySQL 8.0
├── .github/workflows/ci.yml   # CI: check + test đơn vị + test tích hợp trên MySQL 8.0
├── .pre-commit-config.yaml   # rào chắn khi commit: chặn .env, quét khóa API, manage.py check
├── AGENTS.md                 # ngữ cảnh cho agent lập trình AI (chuẩn mở)
├── agents/                   # đặc tả 5 vai trò agent + quy_trinh.md (dây chuyền)
├── nha_may_agent/            # nhà máy agent chạy bằng Gemini: lệnh chay_nha_may, rào chắn, test
├── qldt/                      # cấu hình dự án Django (settings, urls, /health/)
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
├── prompts/                        # prompt tách khỏi code: <chức_năng>/<phiên_bản>/{system,user}.txt (cả prompt nhà máy nha_may_*)
├── templates/                       # template dùng chung (base.html, trang lỗi 403/404/500)
├── media/                            # tệp tải lên (quy_che/...), không commit, chỉ tải về qua view có đăng nhập
├── logs/                             # app.log (xoay vòng), không commit
└── docs/
    ├── agent/ngu_canh_du_an.md         # ngữ cảnh dự án cho các agent AI
    ├── de-bai.md, rubric.md, erd.md   # đề bài, tiêu chí chấm, sơ đồ dữ liệu
    ├── thiet_ke_ai.md                  # thiết kế chi tiết 3 chức năng AI
    ├── review_code_ai.md                # báo cáo review bảo mật/chất lượng code các app AI
    ├── bien_ban_kiem_thu.md              # bảng kiểm thử tự động + thủ công theo vai trò
    ├── ai-log.md                          # nhật ký sử dụng AI và nhật ký dây chuyền agent
    └── ca_thu_ai/                          # bộ câu hỏi/ca thử cho từng chức năng AI
```

Mỗi app Django có cấu trúc `models.py` (nếu có bảng riêng), `services.py` (nghiệp vụ/gọi AI), `views.py`, `urls.py`, `tests.py`, `templates/<app>/`; các app AI có thêm `management/commands/chay_ca_thu_*.py`.
