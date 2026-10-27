# Quy trình: dây chuyền nhà máy agent

Dây chuyền biến một yêu cầu thành thay đổi code đã kiểm thử và được review, qua 5 vai trò agent. Các tệp
trong `agents/` là đặc tả vai trò **trung lập**: dùng được với bất kỳ công cụ lập trình AI nào (đưa nội dung
tệp vai trò kèm `AGENTS.md` làm chỉ dẫn hệ thống), hoặc chạy tự động bằng Gemini qua `nha_may_agent`.

## Sơ đồ

```
yêu cầu
  │
  ▼
[1] phan_tich_yeu_cau ──► đặc tả (căn cứ đề, phạm vi, phân quyền, tiêu chí chấp nhận, ca test)
  │                        └─ ngoài đề → DỪNG
  ▼
[CỔNG NGƯỜI 1] duyệt đặc tả? ── không → DỪNG
  │
  ▼
[2] lap_trinh_vien ──► các thay đổi tệp (toàn văn tệp mới) ──► RÀO CHẮN kiểm tra từng tệp
  │                                                             └─ vi phạm → DỪNG, không ghi gì
  ▼
[CỔNG NGƯỜI 2] xem diff, áp dụng? ── không → DỪNG        (chế độ chạy thử: in diff rồi DỪNG)
  │
  ▼
[3] chạy test (kiem_thu_vien) ── fail ──► lap_trinh_vien sửa (tối đa 2 vòng) ── vẫn fail → hoàn tác, DỪNG
  │ đạt
  ▼
[4] review_code ─┐
[5] kiem_tra_bao_mat ─┴─► nhận xét theo mức Nghiêm trọng / Trung bình / Nhỏ
  │
  ▼
báo cáo + docs/ai-log.md ("Nhật ký nhà máy agent")  ──►  NGƯỜI đọc diff và tự commit
```

## Các bước

| Bước | Vai trò | Đầu vào | Đầu ra | Điều kiện dừng |
|---|---|---|---|---|
| 1 | `phan_tich_yeu_cau` | Yêu cầu, `AGENTS.md`, `docs/de-bai.md`, danh sách tệp | Đặc tả Markdown + danh sách tệp liên quan | Ngoài đề |
| Cổng 1 | Người | Đặc tả | Duyệt / không | Không duyệt |
| 2 | `lap_trinh_vien` | Đặc tả đã duyệt, nội dung tệp liên quan | Toàn văn các tệp cần ghi | Rào chắn chặn |
| Cổng 2 | Người | Diff | Áp dụng / không | Không áp dụng, hoặc đang chạy thử |
| 3 | `kiem_thu_vien` (tự động: chạy bộ test) | Code sau khi ghi | Kết quả test | Vẫn fail sau 2 vòng sửa |
| 3' | `lap_trinh_vien` (vòng sửa) | Đặc tả, tệp hiện tại, lỗi test | Tệp đã sửa | Như bước 2 |
| 4 | `review_code` | Diff, đặc tả | Vấn đề theo mức độ | — |
| 5 | `kiem_tra_bao_mat` | Diff, đặc tả | Lỗ hổng theo mức độ | — |
| Cuối | Người | Báo cáo, diff | Commit (agent không bao giờ tự commit/push) | — |

## Rào chắn

Ở ba lớp, không lớp nào phụ thuộc vào việc AI "tự giác":

1. **Trong nhà máy (`nha_may_agent/rao_chan.py`)**: chỉ ghi tệp trong các thư mục app, `templates/`, `prompts/`;
   cấm `.env`, migration đã có, `settings.py`, `nha_may_agent/`, đường dẫn tuyệt đối hoặc `..`; chặn nội dung
   giống API key; chặn ghi đè làm mất test; giới hạn số lượt gọi AI mỗi lần chạy; hoàn tác khi test vẫn fail.
2. **Ở git (`.pre-commit-config.yaml`)**: chặn commit `.env`, quét khóa API trong tệp được commit, chạy `manage.py check`.
3. **Ở CI (`.github/workflows/ci.yml`)**: mọi push/pull request chạy check, kiểm tra migration, test đơn vị và tích hợp trên MySQL 8.0.

## Chạy

Tự động bằng Gemini (cần `GEMINI_API_KEY` trong `.env`):

```
venv\Scripts\python manage.py chay_nha_may "Mô tả yêu cầu" --chay-thu     # chỉ in đặc tả + diff, không ghi gì
venv\Scripts\python manage.py chay_nha_may "Mô tả yêu cầu"                # chạy đủ dây chuyền
```

Thủ công với công cụ AI khác: lần lượt đưa cho công cụ `AGENTS.md` + tệp vai trò của bước đang làm, giữ
đúng hai cổng người duyệt, chạy `manage.py test` sau bước lập trình, và ghi kết quả vào `docs/ai-log.md`.
