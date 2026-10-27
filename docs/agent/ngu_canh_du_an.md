# Ngữ cảnh dự án cho Agent AI

Mọi agent (đặc tả vai trò ở `agents/`, tóm tắt ở `AGENTS.md`) **phải đọc tệp này trước khi làm việc**. Tệp này tóm tắt những gì
agent cần biết để không phải đoán: dự án làm gì, code đặt ở đâu, quy ước nào bắt buộc, điều gì bị cấm.
Khi tệp này mâu thuẫn với code, code là sự thật; báo lại cho người để sửa tệp này.

## 1. Mục tiêu

Đồ án "Hệ thống quản lý đào tạo có tích hợp AI" (đề: `docs/de-bai.md`, tiêu chí chấm: `docs/rubric.md`).
Hệ thống quản lý sinh viên, giảng viên, học phần, lớp học phần, đăng ký học, điểm, quy chế; tích hợp
3 chức năng AI: tư vấn đăng ký học phần, chatbot hỏi đáp quy chế, tóm tắt kết quả học tập.

**Chỉ làm đúng chức năng trong đề, không thêm chức năng ngoài đề.** Yêu cầu nào không có trong
`docs/de-bai.md` thì dừng lại và hỏi người.

Công nghệ: Django 6 (Python, venv), Django template (HTML/CSS/JS thuần, không CDN, không Tailwind),
MySQL (database `qldt`, kết nối bằng PyMySQL), Gemini qua SDK `google-genai`.

## 2. Bốn vai trò

Phân quyền **chỉ** dựa trên cột `vai_tro` của bảng `tai_khoan` (`accounts.models.VaiTro`). Dùng
`accounts.permissions.yeu_cau_vai_tro` (view hàm) hoặc `YeuCauVaiTroMixin` (view lớp). Không dùng
`permission_required`, `user.has_perm`, `is_superuser` (model `TaiKhoan` không có các thứ này).

| Vai trò | Giá trị `vai_tro` | Được làm gì |
|---|---|---|
| Phòng Đào tạo | `PHONG_DAO_TAO` | Quản lý toàn bộ dữ liệu đào tạo |
| Giảng viên | `GIANG_VIEN` | Xem lớp học phần và lịch giảng dạy của mình; nhập, sửa, xem điểm lớp mình phụ trách |
| Sinh viên | `SINH_VIEN` | Chỉ xem dữ liệu của mình (thời khóa biểu, điểm, lịch sử đăng ký); đăng ký học phần |
| Cố vấn học tập | `CO_VAN_HOC_TAP` | Chỉ xem sinh viên và kết quả học tập của lớp hành chính mình phụ trách |

Ngoài kiểm tra vai trò, view còn phải lọc theo **chủ sở hữu dữ liệu** (giảng viên chỉ lớp mình,
sinh viên chỉ mình, cố vấn chỉ lớp hành chính mình). Truy cập dữ liệu người khác trả 403 hoặc 404.

## 3. Các app và nhiệm vụ

| App | Nhiệm vụ |
|---|---|
| `qldt/` | Cấu hình dự án (`settings.py` đọc `.env`), URL gốc, context processor |
| `accounts` | Đăng nhập, tài khoản, phân quyền (`permissions.py`), trang chủ theo vai trò, bắt đổi mật khẩu |
| `people` | Sinh viên, giảng viên, cố vấn học tập; nhập sinh viên từ Excel |
| `academics` | Ngành học, lớp hành chính, học phần, điều kiện tiên quyết, chương trình đào tạo, học kỳ, đợt đăng ký |
| `classes` | Lớp học phần, lịch học, lịch thi, lớp phụ trách và lịch giảng dạy của giảng viên |
| `enrollment` | Đăng ký/hủy đăng ký học phần, thời khóa biểu (kèm PDF), lịch sử đăng ký |
| `grades` | Nhập/sửa/xem điểm, công thức điểm (`tinh_diem.py`), bảng điểm, cảnh báo học vụ |
| `regulations` | Tải lên/tải về tài liệu quy chế (PDF/DOCX) |
| `reports` | Thống kê sĩ số, học phần nhiều đăng ký, kết quả học tập |
| `tien_do_hoc_tap`, `diem_danh`, `thong_bao` | Tiến độ học tập, điểm danh, thông báo |
| `ai_core` | Hạ tầng AI dùng chung: client (`clients.py`), nạp prompt (`prompts.py`), lỗi AI, giới hạn tần suất, lịch sử chat |
| `tu_van_dang_ky` | AI tư vấn đăng ký học phần |
| `tom_tat_ket_qua` | AI tóm tắt kết quả học tập |
| `hoi_dap_quy_che` | Chatbot hỏi đáp quy chế (truy hồi BM25 tự cài, chỉ mục trong bộ nhớ) |

Tài liệu thiết kế: `docs/erd.md` (13 bảng), `docs/thiet_ke_csdl.md`, `docs/thiet_ke_ai.md`,
`docs/thiet_ke_giao_dien.md`.

## 4. Quy ước code

- **Tên tiếng Việt không dấu, snake_case** cho biến, hàm, bảng, cột (`diem_qua_trinh`, `dang_ky_hoc_phan`);
  lớp dùng PascalCase (`DangKyHocPhan`). Thông điệp hiển thị và chú thích viết tiếng Việt có dấu.
- **13 bảng theo `docs/erd.md`**; không tự đổi tên bảng/cột, không tạo bảng mới khi chưa được duyệt.
- **Nghiệp vụ nằm trong `services.py`** của từng app (hoặc module chuyên trách như `grades/tinh_diem.py`).
  View chỉ nhận request, kiểm tra quyền, gọi service, render template.
- **Không lưu điểm tổng kết**: tính từ điểm quá trình và điểm thi (`grades/tinh_diem.py`, tỷ lệ trong `settings`).
- **Thứ tự kiểm tra khi đăng ký học phần: tiên quyết → trùng lịch → sĩ số.**
- **Prompt nằm trong `prompts/<chuc_nang>/<phien_ban>/`** (`system.txt`, `user.txt`), nạp bằng
  `ai_core.prompts.nap_prompt`. Không viết prompt trong mã Python. Đổi phiên bản qua biến `.env`
  (`AI_PHIEN_BAN_TU_VAN`, `AI_PHIEN_BAN_TOM_TAT`, `AI_PHIEN_BAN_QUY_CHE`).
- Cấu hình bí mật (mật khẩu CSDL, API key) chỉ đọc từ `.env` qua `settings`; không ghi vào mã nguồn.
- Giới hạn tần suất AI dùng `django.core.cache`, không tạo bảng CSDL.
- Thay đổi CSDL bằng migration **mới**; không sửa migration đã có.

## 5. Nguyên tắc "code tính, AI diễn giải"

Mọi con số và kết luận nghiệp vụ do **code** tính: điểm tổng kết, điểm trung bình, xếp loại, cảnh báo
học vụ, điều kiện tiên quyết, trùng lịch, sĩ số, học phần còn thiếu. AI **chỉ** diễn giải, tóm tắt,
gợi ý bằng lời dựa trên kết quả code đã tính. Không để AI tự tính điểm hay tự quyết sinh viên có đủ
điều kiện hay không. Kết quả AI trả về phải được code kiểm tra lại (ví dụ học phần AI gợi ý phải có
trong danh sách lớp mở). Khi thiếu dữ liệu hoặc câu hỏi không liên quan, trả lời ngay bằng code,
không gọi AI.

## 6. Quy tắc dữ liệu gửi AI

- Chỉ gửi **dữ liệu tối thiểu** cho từng chức năng (mã học phần, tên học phần, số tín chỉ, điểm, lịch học).
- **Không gửi họ tên, email, mã sinh viên, mã tài khoản**, số điện thoại hay bất kỳ định danh cá nhân nào.
- Điểm, hồ sơ học tập chỉ gửi AI khi chính sinh viên hoặc vai trò được phân quyền yêu cầu.
- Nội dung người dùng nhập và nội dung tài liệu (quy chế, câu hỏi, ghi chú) là **dữ liệu không tin cậy**,
  luôn đặt trong khối:

  ```
  <<<DU_LIEU>>>
  $du_lieu
  <<<HET_DU_LIEU>>>
  ```

  kèm câu nói rõ đây là dữ liệu, không phải chỉ thị (xem `prompts/README.md`).
- **Không ghi log** (kể cả log lỗi) nội dung prompt, câu trả lời của AI hay điểm. Log AI chỉ được có:
  chức năng, thời gian phản hồi, thành công/lỗi, loại lỗi.
- Gọi AI luôn qua `ai_core.theo_doi.goi_ai_co_ghi_log(chuc_nang, client, he_thong=..., nguoi_dung=...)`,
  không gọi thẳng `client.sinh_noi_dung` (hàm này ghi log theo đúng quy tắc trên).
- Khi phát triển và kiểm thử: dùng client giả `ai_core.clients.ClientAIGia` hoặc
  `override_settings(AI_BACKEND='gia')`. **Không gọi Gemini thật** nếu người chưa yêu cầu (hạn mức rất ít).

## 7. Lệnh thường dùng

Chạy từ thư mục gốc dự án, trên Windows dùng `venv\Scripts\python`:

```
venv\Scripts\python manage.py check                     # kiểm tra cấu hình
venv\Scripts\python manage.py test                      # toàn bộ test
venv\Scripts\python manage.py test --tag don_vi         # chỉ test đơn vị
venv\Scripts\python manage.py test --tag tich_hop       # chỉ test tích hợp
venv\Scripts\python manage.py test enrollment           # test một app
venv\Scripts\python manage.py makemigrations --check --dry-run   # có thay đổi model chưa tạo migration không
```

Quy ước test:
- `@tag('don_vi')`: gọi trực tiếp hàm services / tính điểm, không đi qua view.
- `@tag('tich_hop')`: dùng Django test `Client`, đi qua URL, view, phân quyền, template.
- Bắt buộc có test cho: đăng ký học phần, điều kiện tiên quyết, trùng lịch, nhập điểm, chức năng AI.
- Mỗi lỗi phân quyền cần một test chứng minh người không có quyền nhận 403/404.

## 8. Những điều cấm

- Thêm chức năng ngoài `docs/de-bai.md`.
- Đọc, sửa, in, commit tệp `.env`; ghi API key hay mật khẩu vào mã nguồn, tài liệu, log, commit.
- Gửi họ tên, email, mã sinh viên, mã tài khoản cho AI; ghi log nội dung prompt/câu trả lời/điểm.
- Đưa nội dung người dùng hoặc tài liệu vào prompt mà không bọc trong `<<<DU_LIEU>>>`.
- Dùng `permission_required`, `has_perm`, `is_superuser` để phân quyền.
- Lưu điểm tổng kết vào CSDL; để AI tự tính điểm hay tự quyết điều kiện.
- Sửa migration đã có; chạy `DROP`/`TRUNCATE`; `rm -rf`; `git push`.
- Xóa hoặc làm yếu test có sẵn để cho test "xanh"; đổi nội dung assert cho khớp code sai.
- Dùng CDN, Tailwind, thư viện frontend ngoài.
- Tự commit khi chưa được người yêu cầu (các lệnh dây chuyền không commit).
