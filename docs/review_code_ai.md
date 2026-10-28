# Review bảo mật và chất lượng code — các app AI

Phạm vi: `ai_core`, `tu_van_dang_ky`, `tom_tat_ket_qua`, `hoi_dap_quy_che`, `regulations`
(tải lên/tải về tệp). Ngày review: 2026-09-21.

Tiêu chí kiểm tra: phân quyền theo view/đối tượng; dữ liệu cá nhân trong prompt và log;
rò rỉ khóa API (log, thông báo lỗi, template, Git); prompt injection (ghi chú, câu hỏi,
nội dung tài liệu); xử lý lỗi AI; giới hạn tần suất; tải tệp (đuôi, dung lượng, tên tệp,
đường dẫn); truy vấn N+1; ngoại lệ chưa bắt.

Mỗi phát hiện có mức độ (**Nghiêm trọng** / **Trung bình** / **Thấp**), vị trí, mô tả,
cách sửa. Phần 1 là các phát hiện **đã sửa kèm test hồi quy**; phần 2 là các phát hiện
**chưa sửa** (để người quyết định); phần 3 liệt kê các mục đã kiểm tra và không thấy vấn đề.

---

## 1. Đã sửa

### 1.1 [Trung bình] Kiểm tra tệp tải lên chỉ dựa vào đuôi tên tệp, không kiểm tra nội dung

**Vị trí:** `regulations/models.py:11-16` (trước khi sửa)

**Mô tả:** `validate_tai_lieu_file` chỉ so khớp phần đuôi (`os.path.splitext(...)[1]`) với
`{'.pdf', '.docx'}`. Một người dùng có quyền Phòng Đào tạo (hoặc một tài khoản PĐT bị lộ)
có thể đổi tên bất kỳ tệp nào (kể cả tệp thực thi, script) thành `.pdf`/`.docx` để vượt qua
kiểm tra. Tệp sau đó được lưu vào `media/quy_che/` và có thể được tải xuống nguyên vẹn qua
`tai_ve_view`, hoặc được `hoi_dap_quy_che.trich_xuat.trich_van_ban` mở ra để trích chữ.

**Cách sửa:** thêm kiểm tra "magic bytes" (chữ ký byte đầu tệp) khớp với đuôi khai báo:
PDF phải bắt đầu bằng `%PDF`, DOCX (là tệp ZIP/OOXML) phải bắt đầu bằng `PK\x03\x04`.
Đã sửa tại `regulations/models.py:11-30` (hàm `validate_tai_lieu_file`, thêm hằng
`_CHU_KY_THEO_DUOI`), không thêm thư viện ngoài. Test hồi quy:
`regulations/tests.py::TaiLenTaiLieuTest::test_tu_choi_tep_doi_duoi_gia_mao_khong_dung_pdf_that`
và `::test_tu_choi_tep_docx_gia_mao`.

**Còn hạn chế:** vẫn không phải kiểm tra "sâu" (không parse toàn bộ cấu trúc PDF/DOCX để
phát hiện nội dung nhúng độc hại, macro trong DOCX, v.v.) — đủ để chặn kiểu tấn công phổ
biến nhất (đổi đuôi tệp), không phải kiểm tra chống mọi loại tệp độc hại.

### 1.2 [Trung bình] `tu_van_dang_ky` và `tom_tat_ket_qua` không có giới hạn tần suất

**Vị trí:** `tu_van_dang_ky/views.py` (`TuVanDangKyView.form_valid`, trước khi sửa dòng
26-37), `tom_tat_ket_qua/views.py` (`TomTatCuaToiView.post` dòng 27-33 và
`TomTatChoCoVanView.post` dòng 52-64, trước khi sửa)

**Mô tả:** Chỉ `hoi_dap_quy_che` có giới hạn 10 câu hỏi/phút/người dùng
(`hoi_dap_quy_che/gioi_han_tan_suat.py`). Hai chức năng AI còn lại không có giới hạn nào —
một sinh viên gửi form tư vấn đăng ký hoặc bấm tóm tắt kết quả liên tục (kể cả vô ý bằng
cách bấm nhiều lần, hoặc cố ý) sẽ gọi AI thật mỗi lần, không có gì chặn lại. Rủi ro này
**đã được xác nhận là có thật, không chỉ lý thuyết**: hạn mức API miễn phí thực tế quan sát
được trong quá trình phát triển chỉ khoảng **20 request/ngày/model** (`generate_content_
free_tier_requests`) — một người dùng có thể làm cạn hạn mức dùng chung cho **cả ba chức
năng AI** trong vài phút, khiến mọi sinh viên/cố vấn khác không dùng được AI trong ngày đó.

**Cách sửa:** thêm `ai_core/gioi_han_tan_suat.py` (hàm `kiem_tra_va_dem` dùng chung, cùng
cơ chế cache của Django như bản của `hoi_dap_quy_che`, không tạo bảng CSDL mới — đúng
CLAUDE.md), giới hạn mặc định 10 lần/phút/người dùng. Gắn vào:
- `tu_van_dang_ky/views.py:32` (khóa `tu_van_dang_ky:<mã tài khoản>`)
- `tom_tat_ket_qua/views.py:33` (khóa `tom_tat_ket_qua:<mã tài khoản>`, sinh viên tự xem)
- `tom_tat_ket_qua/views.py:68` (cùng khóa theo mã tài khoản CỦA CỐ VẤN, không theo sinh
  viên được chọn — để một cố vấn xem nhiều sinh viên khác nhau vẫn bị đếm chung một hạn mức
  của chính họ, tránh né giới hạn bằng cách đổi sinh viên liên tục)

Khi vượt giới hạn: hiển thị thông báo lỗi thân thiện, **không gọi AI** (kiểm tra bằng
`gia_lap.assert_not_called()` trong test). Test hồi quy: `ai_core/tests.py::
GioiHanTanSuatDungChungTest`, `tu_van_dang_ky/tests.py::GioiHanTanSuatTest`,
`tom_tat_ket_qua/tests.py::GioiHanTanSuatTest`.

**Không đổi:** `hoi_dap_quy_che/gioi_han_tan_suat.py` giữ nguyên (đã có, đã có test, không
sửa để tránh rủi ro hồi quy không cần thiết trên code đang chạy tốt).

---

## 2. Chưa sửa (để quyết định)

### 2.1 [Thấp] `nap_prompt` không bắt lỗi khi prompt tham chiếu biến chưa được truyền

**Vị trí:** `ai_core/prompts.py:35-36` (`Template(...).substitute(**bien)`)

**Mô tả:** `string.Template.substitute()` raise `KeyError` chưa bắt nếu tệp `system.txt`
hoặc `user.txt` của một phiên bản prompt tham chiếu một biến (`$ten_bien`) mà lời gọi
`nap_prompt(...)` không truyền — ví dụ gõ nhầm tên biến khi soạn một phiên bản prompt mới
(`v2`, `v3`...). Khi đó toàn bộ chức năng AI liên quan sẽ trả lỗi 500 (crash trang) thay vì
thông báo thân thiện, cho TỚI KHI được phát hiện và sửa tệp prompt.

**Vì sao chưa sửa:** đây là lỗi CHỈ có thể do người viết prompt (lập trình viên) gõ nhầm khi
tạo phiên bản mới — không phải lỗ hổng có thể khai thác từ dữ liệu người dùng/bên ngoài. Sửa
đúng cách cần: (a) bắt `KeyError` trong `nap_prompt`, raise một ngoại lệ rõ ràng (ví dụ
`BienPromptThieu`), và (b) sửa CẢ BA nơi gọi (`hoi_dap_quy_che`, `tu_van_dang_ky`,
`tom_tat_ket_qua` `services.py`) để bắt ngoại lệ đó và trả thông báo thân thiện — phạm vi
sửa rộng hơn một fix cục bộ, nên để bạn quyết định có muốn làm ngay không.

**Đề xuất khi sửa:** trong `nap_prompt`, bọc hai dòng `Template(...).substitute(...)` bằng
`try/except KeyError as loi: raise KhongTimThayPrompt(f'Prompt "{ten_chuc_nang}/{phien_ban}"
thiếu biến {loi}.') from loi` (tái dùng exception có sẵn thay vì thêm loại mới, vì bản chất
đều là "prompt không dùng được"), rồi thêm `except KhongTimThayPrompt` cạnh `except LoiAI`
ở mỗi hàm `hoi_dap_quy_che()`/`tu_van_dang_ky()`/`tom_tat_ket_qua_hoc_tap()`.

### 2.2 [Trung bình, rủi ro cao khi sửa] N+1 truy vấn khi tính trạng thái lớp học phần

**Vị trí:** `tu_van_dang_ky/services.py:92-96` (`_tinh_danh_sach_trang_thai`, vòng lặp
`for lop in danh_sach_lop`) gọi `enrollment/services.py:116` (`xac_dinh_trang_thai`)

**Mô tả:** Với mỗi lớp học phần đang mở trong học kỳ (M lớp), `_tinh_danh_sach_trang_thai`
gọi `xac_dinh_trang_thai()` một lần — hàm này tự thực hiện tới 4-5 truy vấn riêng (đã đăng
ký?, tiên quyết còn thiếu — có thêm một truy vấn lồng cho MỖI học phần tiên quyết, trùng
lịch — 2 truy vấn, sĩ số hiện tại), cộng thêm một truy vấn `LichHoc` riêng ngay trong
`_tinh_danh_sach_trang_thai`. Tổng số truy vấn tăng tuyến tính theo M — với học kỳ có nhiều
lớp mở, trang tư vấn AI có thể chậm rõ rệt.

**Vì sao chưa sửa:** `xac_dinh_trang_thai` là hàm nghiệp vụ **dùng chung** với luồng đăng ký
học phần thật (`enrollment.services.dang_ky_hoc_phan` gọi các hàm con giống hệt) — đây là
thiết kế CỐ Ý để không viết lại quy tắc nghiệp vụ ở hai nơi (xem docstring trong file). Tối
ưu N+1 ở đây (ví dụ prefetch hàng loạt tiên quyết/đăng ký/lịch cho tất cả lớp một lượt) đòi
hỏi viết lại logic tính trạng thái theo hướng "theo lô" (batch), có nguy cơ ảnh hưởng tới
đúng luồng đăng ký học phần thật (rủi ro cao nếu có sai sót — sai điều kiện tiên quyết/trùng
lịch là lỗi nghiệp vụ nghiêm trọng). Không đủ "rủi ro thấp khi sửa" để tự sửa ngay theo yêu
cầu; nên làm thành một việc tối ưu hiệu năng riêng, có test kỹ trước/sau.

### 2.3 [Thấp/thông tin] Giới hạn tần suất dùng cache mặc định theo tiến trình (LocMemCache)

**Vị trí:** `qldt/settings.py` (không có mục `CACHES` -> Django dùng mặc định
`LocMemCache`); áp dụng cho cả `hoi_dap_quy_che/gioi_han_tan_suat.py` và
`ai_core/gioi_han_tan_suat.py` (mục 1.2)

**Mô tả:** `LocMemCache` lưu trong bộ nhớ của TỪNG TIẾN TRÌNH riêng biệt. Nếu triển khai
thật chạy nhiều tiến trình worker (ví dụ Gunicorn với `--workers 4`) hoặc nhiều máy chủ, mỗi
tiến trình đếm số lần gọi AI ĐỘC LẬP — giới hạn "10 lần/phút" thực tế trở thành "10 lần/phút
× số tiến trình". Không phải lỗi code, mà là giới hạn của lựa chọn hạ tầng cache.

**Vì sao chưa sửa:** CLAUDE.md yêu cầu rõ dùng cache của Django, không tạo bảng CSDL mới cho
việc này — đổi sang cache dùng chung (Redis/Memcached) là một quyết định hạ tầng/triển khai
(cần cài đặt, cấu hình dịch vụ ngoài), không phải một thay đổi code đơn thuần, và đồ án hiện
chạy một tiến trình (`manage.py runserver`) nên chưa phải vấn đề thực tế. Ghi lại để lưu ý
nếu sau này triển khai với nhiều tiến trình/máy chủ.

### 2.4 [Thấp/thông tin] `DEBUG` mặc định `True`, `SECRET_KEY` có giá trị dự phòng

**Vị trí:** `qldt/settings.py:29` (`SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY',
'django-insecure-changeme')`), `qldt/settings.py:32` (`DEBUG = os.environ.get(...,
'True')...`)

**Mô tả:** Đây là mã khung tiêu chuẩn do `django-admin startproject` sinh ra, có cảnh báo
sẵn trong comment. Nếu triển khai thật mà quên đặt `DJANGO_SECRET_KEY`/`DJANGO_DEBUG=False`
trong `.env`, hệ thống sẽ chạy với khóa bí mật đã biết trước và trang lỗi chi tiết công
khai. Rủi ro với `GEMINI_API_KEY` cụ thể được giảm nhẹ vì Django tự động che các biến có
tên chứa "KEY"/"SECRET"/... trên trang debug (`SafeExceptionReporterFilter`), nhưng các
thông tin khác (đường dẫn, câu SQL, session...) vẫn lộ nếu `DEBUG=True` chạy thật.

**Vì sao chưa sửa:** không có "giá trị mặc định an toàn" hợp lý cho `SECRET_KEY`/`DEBUG` —
đây là việc phải cấu hình đúng `.env` khi triển khai, không phải lỗi trong logic code. Đã
có trong `.env.example` (kiểm tra khi triển khai thật cần đặt `DJANGO_DEBUG=False` và một
`DJANGO_SECRET_KEY` ngẫu nhiên đủ dài).

---

## 3. Đã kiểm tra, không phát hiện vấn đề

- **Phân quyền theo view**: mọi view trong 5 app đều qua `YeuCauVaiTroMixin`/
  `yeu_cau_vai_tro` (`accounts/permissions.py`), kiểm tra `request.user.is_authenticated`
  trước, dựa hoàn toàn vào cột `vai_tro` (không dùng `has_perm`/`is_superuser` — đúng
  CLAUDE.md). Đã có test 403/302 cho mọi vai trò không hợp lệ ở cả 5 app.
- **Phân quyền theo đối tượng**: `tom_tat_ket_qua/views.py` (`TomTatChoCoVanView.post`)
  kiểm tra `sinh_vien.ma_lop.ma_co_van_id != co_van.pk` trước khi gọi AI — đã test ca cố
  vấn xem sinh viên ngoài phạm vi (403, không gọi AI). `tu_van_dang_ky`/`hoi_dap_quy_che`
  không nhận tham số định danh đối tượng khác (chủ thể luôn là `request.user`), không có
  bề mặt IDOR. `regulations` chỉ Phòng Đào tạo truy cập, không có khái niệm sở hữu theo
  đối tượng.
- **Dữ liệu cá nhân trong prompt**: cả 3 hàm `hoi_dap_quy_che()`, `tu_van_dang_ky()`,
  `tom_tat_ket_qua_hoc_tap()` chỉ định dạng mã/tên học phần, điểm, lịch, số liệu tổng hợp,
  câu hỏi/ghi chú — không có `ho_ten`/`email`/`ma_sinh_vien`/`ma_tai_khoan` nào được đưa
  vào `_dinh_dang_*`. Xác nhận qua test hiện có (`KhongRoRiDuLieuTest`,
  `KhongRoRiDuLieuGiuaSinhVienTest`, `test_khong_co_thong_tin_ca_nhan_trong_prompt`...).
- **Dữ liệu cá nhân trong log**: không có lệnh gọi `logging`/`print` nào ghi lại nội dung
  prompt hay `chi_tiet_loi_ai` ở bất kỳ đâu trong 5 app.
- **Khóa API không lộ**: `ai_core/clients.py::_trich_chi_tiet_an_toan` chỉ trích `loai`,
  `ma_http`, `thong_diep` từ exception — không bao giờ đọc `settings.GEMINI_API_KEY`. Đã
  rà template (không có `{{ ... }}` nào render khóa/`chi_tiet_loi_ai`), rà Git (`.env` nằm
  trong `.gitignore`, `git ls-files`/`git log --all -- .env` xác nhận chưa từng commit).
- **Prompt injection**: cả 3 prompt (`hoi_dap_quy_che`, `tu_van_dang_ky`,
  `tom_tat_ket_qua`) đều bọc dữ liệu không tin cậy (câu hỏi, ghi chú, đoạn quy chế, tên học
  phần) trong khối `<<<DU_LIEU>>> ... <<<HET_DU_LIEU>>>` với chỉ dẫn rõ "không phải chỉ
  thị" ở cả `system.txt` và `user.txt`. Có test xác nhận vị trí trong khối ở cả 3 app
  (`test_cau_hoi_gai_lenh_nam_dung_trong_khoi_du_lieu`,
  `test_ghi_chu_gai_lenh_van_nam_trong_khoi_du_lieu`,
  `test_noi_dung_gai_lenh_nam_dung_trong_khoi_du_lieu`, và ca 6/10 mới trong
  `chay_ca_thu_tu_van`, ca 10 trong `chay_ca_thu_tom_tat`).
- **Xử lý lỗi AI**: `ai_core/exceptions.py` có đủ các loại lỗi thực tế (thiếu khóa, đầu vào
  quá dài, hết thời gian chờ, giới hạn tần suất — phân biệt theo ngày/phút, phản hồi rỗng,
  sai định dạng, lỗi mô hình khác); cả 3 hàm service đều bắt `except LoiAI` tổng quát nên
  KHÔNG loại lỗi nào có thể lọt ra ngoài làm crash trang — có `LoiAiTest` riêng cho từng
  loại lỗi ở cả 3 app.
- **XSS qua nội dung AI**: không có `|safe` hay `{% autoescape off %}` trong bất kỳ template
  nào của 4 app hiển thị kết quả AI — mọi nội dung AI tạo ra đều qua auto-escape mặc định
  của Django.
- **`regulations`**: đuôi tệp + dung lượng (10MB) được kiểm tra ở `validate_tai_lieu_file`;
  đường dẫn lưu dùng `uuid4().hex` (không dùng tên người dùng đặt, không có path traversal);
  tải xuống chỉ Phòng Đào tạo (`tai_ve_view`), luôn `as_attachment=True`; `trich_van_ban`
  (dùng bởi cả `regulations` và `hoi_dap_quy_che`) bọc try/except bắt MỌI ngoại lệ khi trích
  chữ (tệp hỏng, PDF ảnh quét...), không bao giờ raise ra ngoài.
- **Ngoại lệ chưa bắt khác**: rà toàn bộ `ai_core/clients.py` (mọi nhánh trong
  `_goi_voi_thu_lai`, `_lay_thoi_gian_cho_tu_loi_429`, `_phan_loai_gioi_han_tan_suat` đều
  dùng `getattr`/kiểm tra kiểu phòng thủ, không có truy cập thuộc tính có thể crash);
  `hoi_dap_quy_che/trich_xuat.py` xác nhận không raise ra ngoài (xem trên).
