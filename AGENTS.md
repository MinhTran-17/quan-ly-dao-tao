# AGENTS.md

Hướng dẫn cho mọi agent lập trình AI (bất kể công cụ nào) làm việc trên repo này. Đọc hết tệp này
trước khi sửa code. Chi tiết đầy đủ: [docs/agent/ngu_canh_du_an.md](docs/agent/ngu_canh_du_an.md).
Đặc tả từng vai trò agent: [agents/](agents/); dây chuyền: [agents/quy_trinh.md](agents/quy_trinh.md).

## Dự án

Đồ án "Hệ thống quản lý đào tạo có tích hợp AI" (đề: `docs/de-bai.md`, tiêu chí chấm: `docs/rubric.md`).
Django 6 + Django template (HTML/CSS/JS thuần) + MySQL (`qldt`, PyMySQL) + Gemini (SDK `google-genai`).
Ba chức năng AI: tư vấn đăng ký học phần (`tu_van_dang_ky`), hỏi đáp quy chế (`hoi_dap_quy_che`, BM25 tự cài),
tóm tắt kết quả học tập (`tom_tat_ket_qua`); hạ tầng AI dùng chung ở `ai_core`.

**Chỉ làm đúng chức năng trong đề.** Yêu cầu không có trong `docs/de-bai.md` thì dừng và hỏi người.

Bốn vai trò, phân quyền **chỉ** theo cột `vai_tro` của `tai_khoan` (`accounts/permissions.py`:
`yeu_cau_vai_tro`, `YeuCauVaiTroMixin`) và luôn lọc theo chủ sở hữu dữ liệu:

| Vai trò | Được làm gì |
|---|---|
| Phòng Đào tạo (`PHONG_DAO_TAO`) | Quản lý toàn bộ dữ liệu đào tạo |
| Giảng viên (`GIANG_VIEN`) | Lớp và lịch dạy của mình; nhập, sửa, xem điểm lớp mình phụ trách |
| Sinh viên (`SINH_VIEN`) | Chỉ dữ liệu của mình; đăng ký học phần |
| Cố vấn học tập (`CO_VAN_HOC_TAP`) | Chỉ sinh viên và kết quả của lớp hành chính mình phụ trách |

## Quy ước code

- Tên tiếng Việt không dấu, snake_case (`diem_qua_trinh`); lớp PascalCase; thông điệp và chú thích tiếng Việt có dấu.
- 13 bảng theo `docs/erd.md`, không tự đổi tên bảng/cột, không tạo bảng mới khi chưa được duyệt.
- Nghiệp vụ trong `services.py` của từng app (hoặc module chuyên trách như `grades/tinh_diem.py`); view mỏng.
- Không lưu điểm tổng kết, tính từ điểm quá trình và điểm thi.
- Đăng ký học phần kiểm tra theo thứ tự: tiên quyết → trùng lịch → sĩ số.
- Prompt nằm trong `prompts/<chuc_nang>/<phien_ban>/{system,user}.txt`, nạp bằng `ai_core.prompts.nap_prompt`.
- Gọi AI qua `ai_core.theo_doi.goi_ai_co_ghi_log`; bắt `ai_core.exceptions.LoiAI` và báo lỗi thân thiện.
- Bí mật (mật khẩu CSDL, API key, `DJANGO_SECRET_KEY`) chỉ đọc từ `.env` qua `settings`.
- Thay đổi CSDL bằng migration mới, không sửa migration đã có. Giới hạn tần suất dùng `django.core.cache`.

## Nguyên tắc "code tính, AI diễn giải"

Mọi con số và kết luận nghiệp vụ (điểm, điểm trung bình, xếp loại, cảnh báo học vụ, tiên quyết, trùng lịch,
sĩ số) do **code** tính. AI chỉ diễn giải, tóm tắt, gợi ý bằng lời dựa trên kết quả đó; kết quả AI trả về
được code kiểm tra lại. Thiếu dữ liệu hoặc câu hỏi không liên quan thì code trả lời ngay, không gọi AI.

## Quy tắc dữ liệu gửi AI

- Chỉ gửi dữ liệu tối thiểu (mã/tên học phần, tín chỉ, điểm, lịch học); **không** gửi họ tên, email, mã sinh
  viên, mã tài khoản hay định danh cá nhân nào.
- Nội dung người dùng nhập và nội dung tài liệu là dữ liệu không tin cậy, luôn đặt trong khối
  `<<<DU_LIEU>>>` … `<<<HET_DU_LIEU>>>` kèm câu nói rõ đó không phải chỉ thị (`prompts/README.md`).
- Không ghi log nội dung prompt, câu trả lời AI hay điểm; log AI chỉ có chức năng, thời gian, kết quả, loại lỗi.
- Khi phát triển và test: dùng client giả `ai_core.clients.ClientAIGia` hoặc `AI_BACKEND='gia'`, không gọi Gemini thật.

## Lệnh

```
venv\Scripts\python manage.py check
venv\Scripts\python manage.py test                    # toàn bộ test
venv\Scripts\python manage.py test --tag don_vi       # test đơn vị (gọi thẳng service / tính điểm)
venv\Scripts\python manage.py test --tag tich_hop     # test tích hợp (test Client qua URL, view, phân quyền)
venv\Scripts\python manage.py makemigrations --check --dry-run
venv\Scripts\python manage.py chay_nha_may "<yêu cầu>" --chay-thu   # nhà máy agent bằng Gemini, chỉ in diff
```

Trên Linux/macOS thay `venv\Scripts\python` bằng `venv/bin/python`. Mỗi test mới gắn `@tag('don_vi')`
hoặc `@tag('tich_hop')`; bắt buộc có test cho đăng ký học phần, tiên quyết, trùng lịch, nhập điểm, chức năng AI.

## Những điều cấm

- Thêm chức năng ngoài đề.
- Đọc, sửa, in, commit `.env`; ghi API key/mật khẩu vào mã nguồn, tài liệu, log, commit.
- Gửi định danh cá nhân cho AI; ghi log prompt/câu trả lời/điểm; đưa nội dung người dùng vào prompt ngoài khối `<<<DU_LIEU>>>`.
- Phân quyền bằng `permission_required`, `has_perm`, `is_superuser`.
- Lưu điểm tổng kết; để AI tự tính điểm hay tự quyết điều kiện.
- Sửa migration đã có, `DROP`/`TRUNCATE`, `rm -rf`, `git push`.
- Xóa hoặc làm yếu test có sẵn để test "xanh".
- Dùng CDN, Tailwind, thư viện frontend ngoài.
- Tự commit khi người chưa yêu cầu.
