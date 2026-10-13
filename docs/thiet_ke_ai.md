# Thiết kế các chức năng AI

Nguyên tắc chung cho cả 3 chức năng (chi tiết hạ tầng dùng chung ở `ai_core/`):

- **"Code tính, AI diễn giải"**: mọi con số/điều kiện nghiệp vụ (trạng thái lớp học phần,
  điểm tổng kết, đoạn quy chế liên quan...) đều do code Django tính trước; AI chỉ nhận kết
  quả đã tính để giải thích/xếp loại/tóm tắt, không bao giờ được tin tưởng tự tính lại.
- **Không gửi dữ liệu định danh cá nhân** (họ tên, email, mã sinh viên, mã tài khoản) cho
  AI — chỉ gửi mã/tên học phần, điểm, lịch, số liệu tổng hợp, nội dung câu hỏi/ghi chú.
- **Dữ liệu không tin cậy luôn nằm trong khối đánh dấu** `<<<DU_LIEU>>> ... <<<HET_DU_LIEU>>>`
  trong `user.txt`, kèm chỉ dẫn rõ ràng ở cả `system.txt` lẫn `user.txt` rằng nội dung trong
  khối không phải chỉ thị — áp dụng cho MỌI trường có thể chứa nội dung không do lập trình
  viên viết cứng (câu hỏi, ghi chú, tên học phần, đoạn tài liệu quy chế).
- **Luôn xác thực lại sau khi AI trả lời** trước khi hiển thị: parse JSON đúng lược đồ, đối
  chiếu mọi mã/nguồn AI trích với đúng dữ liệu đã gửi (loại bỏ mục bịa/không đủ điều kiện),
  và luôn hiển thị dữ liệu do code tính (bảng trạng thái/bảng điểm/đoạn quy chế) ngay cả khi
  AI lỗi — trang không bao giờ chỉ phụ thuộc vào AI để hoạt động.
- **Xử lý lỗi thống nhất** qua `ai_core.exceptions.LoiAI` và các lớp con — mọi hàm
  `services.py` của 3 chức năng đều `except LoiAI` tổng quát, không để lỗi thư viện lộ ra
  view/template.
- **Client giả** (`ai_core.clients.ClientAIGia`, chọn qua `settings.AI_BACKEND='gia'`) dùng
  cho mọi test và cho công cụ ca thử khi không có `--ai` — không gọi mạng, không tốn quota.

---

## 1. Tư vấn đăng ký học phần (`tu_van_dang_ky`)

**Trang:** `/tu-van-dang-ky/` (chỉ Sinh viên, luôn tư vấn cho `request.user`, không nhận
tham số chọn sinh viên khác).

### Luồng xử lý

1. Sinh viên chọn học kỳ/năm học, nhập ghi chú tự do (tối đa 300 ký tự, không bắt buộc).
2. `ai_core.gioi_han_tan_suat.kiem_tra_va_dem` kiểm tra giới hạn tần suất (10 lần/phút);
   vượt giới hạn thì báo lỗi thân thiện, không gọi tiếp bước nào bên dưới.
3. `tu_van_dang_ky.services._tinh_danh_sach_trang_thai` liệt kê mọi lớp học phần đang mở
   trong học kỳ/năm học đã chọn, gọi đúng `enrollment.services.xac_dinh_trang_thai` (hàm
   dùng chung với luồng đăng ký học phần thật) để xác định trạng thái từng lớp: đủ điều
   kiện / thiếu tiên quyết (kèm danh sách học phần còn thiếu) / trùng lịch (kèm lớp trùng)
   / đã đầy / đã đăng ký.
4. Nếu không có lớp nào đang mở: trả về thông báo cố định, **không gọi AI** (tiết kiệm
   quota cho trường hợp vô nghĩa).
5. Dựng prompt từ `prompts/tu_van_dang_ky/<AI_PHIEN_BAN_TU_VAN>/`, gọi AI qua
   `ai_core.clients.lay_client_ai()`.
6. `_loc_va_lam_giau` lọc kết quả AI trả về: bỏ mọi mã lớp không có trong danh sách đã gửi
   (bịa) hoặc không ở trạng thái "đủ điều kiện" trong mục `goi_y` — mỗi mục bị loại đều có
   dòng giải thích trong `ghi_chu_loc` hiển thị cho người dùng.
7. Hiển thị bảng trạng thái do code tính + gợi ý AI đã lọc; nếu AI lỗi, chỉ hiển thị bảng
   trạng thái kèm thông báo lỗi.

Tham số `goi_ai=False` (dùng bởi `chay_ca_thu_tu_van` khi không `--ai`) dừng lại ngay sau
bước 5 (đã dựng prompt, chưa gọi AI) — trang web thật luôn gọi với `goi_ai=True` (mặc định),
hành vi không đổi.

### Dữ liệu gửi / không gửi cho AI

| Gửi | Không gửi |
|---|---|
| Mã/tên học phần đã đạt + điểm tổng kết | Họ tên, email, mã sinh viên, mã tài khoản |
| Mã lớp học phần đang mở, tên học phần, lịch học, trạng thái đã tính | Điểm quá trình/điểm thi chi tiết (chỉ gửi điểm tổng kết của học phần ĐÃ ĐẠT) |
| Ghi chú tự do của sinh viên (trong khối DỮ LIỆU) | Dữ liệu của sinh viên khác |

### Phiên bản prompt hiện có

- `v1` (`prompts/tu_van_dang_ky/v1/`): lược đồ JSON `{"goi_y": [...], "chua_nen_dang_ky":
  [...], "luu_y": "..."}`, mỗi mục `goi_y`/`chua_nen_dang_ky` có `ma_lop_hoc_phan` + `ly_do`.
  Đổi qua `AI_PHIEN_BAN_TU_VAN` hoặc `--phien_ban_prompt` khi chạy `chay_ca_thu_tu_van`.

### Các lớp kiểm tra sau khi AI trả lời

1. `_trich_json`: JSON hợp lệ, đúng kiểu object (bắt cả trường hợp AI bọc trong khối
   ```` ```json ... ``` ````).
2. `_loc_va_lam_giau`: mọi `ma_lop_hoc_phan` trong `goi_y` phải (a) có trong danh sách lớp
   đã gửi và (b) đang ở trạng thái "đủ điều kiện đăng ký"; mục trong `chua_nen_dang_ky` chỉ
   cần (a). Mục vi phạm bị loại, ghi lý do vào `ghi_chu_loc`.
3. Mỗi mục còn lại được "làm giàu" lại bằng dữ liệu CODE tính (tên học phần, lịch) thay vì
   tin nội dung AI tự ghi, để tránh AI mô tả sai một lớp có thật.

### Xử lý lỗi

Bắt `ai_core.exceptions.LoiAI` (mọi loại con: thiếu khóa, đầu vào quá dài, hết thời gian
chờ, giới hạn tần suất, phản hồi rỗng/sai định dạng, lỗi mô hình khác) và JSON sai định
dạng — ghi vào `KetQuaTuVan.loi_ai`, hiển thị thông báo thân thiện, vẫn hiện đầy đủ bảng
trạng thái lớp học phần do code tính.

---

## 2. Tóm tắt kết quả học tập (`tom_tat_ket_qua`)

**Trang:** `/tom-tat-ket-qua/toi/` (Sinh viên tự xem) và `/tom-tat-ket-qua/co-van/` (Cố vấn
học tập chọn một sinh viên trong danh sách lớp mình phụ trách).

### Luồng xử lý

1. (Cố vấn) chọn một sinh viên từ danh sách; server kiểm tra lại
   `sinh_vien.ma_lop.ma_co_van_id == co_van.pk`, sai thì 403 ngay, **không gọi AI**.
2. `ai_core.gioi_han_tan_suat.kiem_tra_va_dem` kiểm tra giới hạn tần suất theo NGƯỜI ĐANG
   XEM (sinh viên tự xem, hoặc cố vấn — không theo sinh viên được chọn, để cố vấn xem nhiều
   sinh viên khác nhau vẫn dùng chung một hạn mức của chính họ).
3. `grades.services.bang_diem_chi_tiet` lấy bảng điểm (mỗi học phần một dòng, giữ điểm cao
   nhất nếu học lại), dùng đúng `Diem.tinh_diem_tong_ket()` (không tính lại công thức).
4. Nếu chưa có điểm nào: trả thông báo cố định, **không gọi AI**.
5. Tính số liệu tổng hợp: tổng tín chỉ đã đạt, số học phần đạt/chưa đạt, học phần điểm cao
   nhất/thấp nhất (nếu chỉ có 1 học phần thì cao nhất = thấp nhất, không lỗi/không chia 0).
6. Dựng prompt từ `prompts/tom_tat_ket_qua/<AI_PHIEN_BAN_TOM_TAT>/`, gọi AI.
7. Lọc `can_cai_thien`: bỏ mọi `ma_hoc_phan` không có trong bảng điểm đã gửi (bịa), ghi lý
   do vào `ghi_chu_loc`.
8. Hiển thị bảng số liệu + bảng điểm chi tiết (luôn có, kể cả khi AI lỗi) cộng với nhận xét
   AI đã lọc.

Tham số `goi_ai=False` (dùng bởi `chay_ca_thu_tom_tat` khi không `--ai`) dừng lại sau bước 6
(đã dựng prompt, chưa gọi AI). View thật (cả hai trang) luôn gọi `goi_ai=True` — không có
tùy chọn tắt AI ở tầng view, vì trang luôn cần trả lời ngay trong một lượt request.

### Dữ liệu gửi / không gửi cho AI

| Gửi | Không gửi |
|---|---|
| Mã/tên học phần, tín chỉ, học kỳ/năm học, điểm quá trình/điểm thi/điểm tổng kết | Họ tên, email, mã sinh viên, mã tài khoản (kể cả khi cố vấn xem sinh viên khác) |
| Số liệu tổng hợp do code tính | — |

### Phiên bản prompt hiện có

- `v1` (`prompts/tom_tat_ket_qua/v1/`): lược đồ JSON `{"tom_tat": "...", "diem_manh": [...],
  "can_cai_thien": [{"ma_hoc_phan", "ly_do"}], "ke_hoach_goi_y": [...], "luu_y": "..."}`.
  Đổi qua `AI_PHIEN_BAN_TOM_TAT` hoặc `--phien_ban_prompt` khi chạy `chay_ca_thu_tom_tat`.

### Các lớp kiểm tra sau khi AI trả lời

1. `_trich_json`: JSON hợp lệ (bắt cả trường hợp bọc markdown, cả trường hợp AI trả văn bản
   thường không phải JSON).
2. `_loc_can_cai_thien`: mọi `ma_hoc_phan` phải có trong bảng điểm đã gửi, mục bịa bị loại
   và ghi lý do.
3. `_loc_danh_sach_chuoi`: `diem_manh`/`ke_hoach_goi_y` chỉ giữ phần tử là chuỗi/số, bỏ qua
   phần tử có kiểu bất thường (phòng AI trả sai kiểu dữ liệu).

### Xử lý lỗi

Giống mục 1 — bắt `LoiAI` tổng quát + JSON sai định dạng, ghi `KetQuaTomTat.loi_ai`, luôn
hiển thị bảng số liệu/bảng điểm do code tính.

---

## 3. Chatbot hỏi đáp quy chế đào tạo (`hoi_dap_quy_che`)

**Trang:** `/hoi-dap-quy-che/` (Sinh viên và Cố vấn học tập).

### Luồng xử lý

1. Người dùng nhập câu hỏi tự do (tối đa 500 ký tự).
2. `hoi_dap_quy_che.gioi_han_tan_suat.kiem_tra_va_dem` kiểm tra giới hạn tần suất (10 câu
   hỏi/phút/người dùng).
3. `hoi_dap_quy_che.chi_muc.truy_hoi`: trích chữ từ mọi tài liệu quy chế đã tải lên
   (`regulations`, PDF qua `pypdf`/DOCX qua `python-docx`), chia đoạn theo Điều → khoản →
   điểm → cắt cứng theo độ dài (~1500 ký tự/đoạn), xếp hạng bằng BM25 tự cài (không dùng
   dịch vụ embedding ngoài) theo `AI_TRUY_HOI_PHIEN_BAN`, lấy tối đa 4 (`v1`) hoặc 6 (`v2`)
   đoạn đạt ngưỡng `AI_NGUONG_DIEM_TRUY_HOI`, cắt bớt đoạn điểm thấp nếu tổng độ dài vượt
   `AI_GIOI_HAN_KY_TU`. Chỉ mục giữ trong bộ nhớ (cấp module), tự làm mới khi có tài liệu
   được tải lên/cập nhật/xóa (so chữ ký `ma_tai_lieu` + `ngay_cap_nhat` + `duong_dan_file`).
4. Nếu không có đoạn nào đạt ngưỡng: trả câu cố định "Không tìm thấy nội dung phù hợp trong
   quy chế, vui lòng liên hệ Phòng Đào tạo.", **không gọi AI**.
5. Dựng prompt từ `prompts/hoi_dap_quy_che/<AI_PHIEN_BAN_QUY_CHE>/` (đoạn trích kèm nguồn
   `[Nguồn: <tên tài liệu>, Điều X, khoản Y]`), gọi AI.
6. `_loc_nguon`: đối chiếu mọi nguồn AI trích với đúng đoạn đã truy hồi (đã chuẩn hóa tiền
   tố "Điều "/"khoản ", kiểu số/chuỗi, khoảng trắng, hoa/thường — xem mục kiểm tra bên
   dưới); nếu `co_trong_quy_che=true` nhưng không còn nguồn hợp lệ nào, coi như không đủ
   tin cậy và thay bằng câu "không tìm thấy" cố định.
7. Hiển thị câu trả lời + nguồn + đoạn trích gốc để người dùng tự đối chiếu, cộng cảnh báo
   cố định "Nội dung do AI tạo...".

Không có tham số `goi_ai=False` riêng cho chức năng này — công cụ `chay_ca_thu_quy_che` khi
không `--ai` gọi thẳng `truy_hoi()` (bước 3, vốn đã là một hàm độc lập với việc gọi AI).

### Dữ liệu gửi / không gửi cho AI

| Gửi | Không gửi |
|---|---|
| Câu hỏi của người dùng | Họ tên, email, mã sinh viên/tài khoản của người hỏi |
| Đoạn quy chế công khai đã truy hồi (kèm tên tài liệu/Điều/khoản) | Toàn văn tài liệu (chỉ gửi các đoạn liên quan nhất, không gửi cả tài liệu) |

### Phiên bản prompt và phiên bản truy hồi hiện có

- Prompt: `v1` (`prompts/hoi_dap_quy_che/v1/`) — lược đồ JSON `{"co_trong_quy_che": bool,
  "tra_loi": "...", "nguon": [{"ten_tai_lieu", "dieu", "khoan"}]}`, không giới hạn độ dài
  câu trả lời. `v2` (`prompts/hoi_dap_quy_che/v2/`) — cùng lược đồ, thêm ràng buộc: 1-2 câu
  đầu trả lời trực tiếp rồi mới nêu thêm thông tin liên quan (tổng ≤ ~120 từ), nguồn phải
  chép nguyên văn từ dòng `[Nguồn: ...]` của đoạn được cung cấp, chỉ liệt kê đoạn thực sự
  dùng, nguồn đầu tiên là đoạn chứa câu trả lời trực tiếp. Đổi qua `AI_PHIEN_BAN_QUY_CHE`
  hoặc `--phien_ban_prompt` khi chạy `chay_ca_thu_quy_che`.
- Truy hồi: `v1` (bản cũ, tách từ đơn âm tiết, tối đa 4 đoạn) và `v2` (mặc định — thêm
  bigram âm tiết liền nhau, chỉ mục hóa gộp tiêu đề Điều cho MỌI đoạn thuộc Điều đó dù đoạn
  có tự nhiên chứa tiêu đề hay không, tối đa 6 đoạn). Đổi qua `AI_TRUY_HOI_PHIEN_BAN` — đây
  là phiên bản THUẬT TOÁN truy hồi, khác với phiên bản PROMPT ở trên.

### Các lớp kiểm tra sau khi AI trả lời

1. `_trich_json`: JSON hợp lệ (bắt cả trường hợp bọc markdown).
2. `_loc_nguon`/`_tim_doan_khop`: chuẩn hóa Điều/khoản/tên tài liệu (bỏ tiền tố "Điều
   "/"khoản ", ép kiểu số/chuỗi, cắt khoảng trắng, không phân biệt hoa/thường) trước khi so
   khớp với đoạn đã truy hồi. Nếu Điều đó chỉ gửi một đoạn KHÔNG tách khoản, chấp nhận nguồn
   dù AI có ghi khoản hay không (hiển thị theo đúng đoạn truy hồi). Nguồn không khớp đoạn
   nào đã gửi (sai Điều/tài liệu, hoặc sai khoản khi Điều có tách khoản) bị loại, ghi lý do
   cụ thể (dạng dữ liệu AI trả về) vào `ghi_chu_loc`.
3. Quy tắc "có nhưng không nguồn hợp lệ" ở bước 6 (luồng xử lý) — chống trường hợp AI khẳng
   định "có trong quy chế" nhưng không trích được nguồn thật nào.

### Xử lý lỗi

Giống 2 chức năng trên, thêm phân biệt `pham_vi_gioi_han_tan_suat` (`'ngay'`/`'phut'`/
`None`) cho lỗi 429 — xem `ai_core/exceptions.py::QuaGioiHanTanSuatAI` và mục "Giới hạn hạn
mức" trong `README.md`.

---

## Hạ tầng dùng chung (`ai_core`)

- `clients.py`: `GeminiClient` (gọi thật, qua SDK chính thức `google-genai`, tắt automatic
  function calling vì không dùng), `ClientAIGia` (giả, dùng cho mọi test), `lay_client_ai()`
  (chọn theo `settings.AI_BACKEND`); thử lại có backoff tăng dần cho hết thời gian chờ/lỗi
  máy chủ, tôn trọng thời gian chờ do API đề xuất khi bị giới hạn tần suất (tối đa 60 giây).
- `exceptions.py`: `LoiAI` (gốc) và các lớp con cho từng nguyên nhân cụ thể.
- `prompts.py`: `nap_prompt(ten_chuc_nang, phien_ban, **bien)` nạp cặp
  `prompts/<chức_năng>/<phiên_bản>/{system,user}.txt`, điền biến bằng cú pháp
  `string.Template` (`$ten_bien`, không dùng `{}` của `str.format` để viết thẳng ví dụ JSON
  trong prompt mà không phải escape).
- `dinh_dang.py`: `dinh_dang_ket_qua()` luôn thêm cảnh báo cố định "Nội dung do AI tạo...".
- `gioi_han_tan_suat.py`: giới hạn tần suất dùng chung cho `tu_van_dang_ky`/`tom_tat_ket_qua`
  (10 lần/phút/người dùng, cache của Django, không tạo bảng CSDL mới).
- `management/commands/kiem_tra_ai.py`: kiểm tra kết nối, không gửi dữ liệu người dùng.
