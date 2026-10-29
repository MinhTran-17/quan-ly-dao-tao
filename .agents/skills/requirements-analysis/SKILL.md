---
name: requirements-analysis
description: Quy trình phân tích đề bài gốc "Hệ thống quản lý đào tạo tích hợp AI" và các yêu cầu bổ sung về sau thành actor, use case và chức năng; dùng khi cần đối chiếu một yêu cầu mới với đề, quyết định có được thêm chức năng hay không, hoặc đặt tên/vẽ use case.
---

# Phân tích yêu cầu

## Objective

Biến đề bài (`docs/de-bai.md`) và các yêu cầu phát sinh thành danh sách actor, use case và chức năng rõ ràng, không thừa, không thiếu so với đề, đồng thời chốt các quyết định nghiệp vụ mà đề chưa nêu để lập trình không phải đoán.

## Inputs

- `docs/de-bai.md` (mục 3 "Yêu cầu chức năng" là chuẩn đối chiếu) và `docs/rubric.md` (tiêu chí KT1: actor, use case, ERD, kiến trúc, vị trí AI).
- `AGENTS.md` (bối cảnh, 4 vai trò, quy tắc dữ liệu gửi AI).
- Sơ đồ use case tổng quát và sơ đồ phân rã do sinh viên tự vẽ (draw.io), gửi cho AI để đánh giá.
- Với yêu cầu mở rộng: nội dung lượt làm việc do người dùng giao (có ghi rõ "đã được thầy cho phép").

## Process

1. Đọc đề và liệt kê từng chức năng ở mục 3.1 (quản lý) và 3.2 (AI); xác định 4 actor: Phòng Đào tạo, Giảng viên, Sinh viên, Cố vấn học tập.
2. Đối chiếu từng use case với mục 3 của đề, đánh dấu use case nào có trong đề, use case nào không. Nhờ AI chỉ ra use case còn thiếu và use case ngoài đề, rồi tự quyết định giữ hay xóa (ghi lại ở `docs/ai-log.md`, mục "Kiểm tra, chỉnh sửa" do người làm tự viết).
3. Giai đoạn đầu (KT1, KT2): xóa mọi use case ngoài đề. Sau khi giảng viên cho phép, mở rộng có kiểm soát theo từng lượt 1/6 đến 6/6; mỗi lượt chia thành Phần A, B, C... và nêu rõ ranh giới (ví dụ chỉ số liệu học vụ cho sinh viên, không mở sang tư vấn AI).
4. Với chỗ đề chưa nêu, hỏi lại rồi chốt bằng hằng số cấu hình thay vì ghi cứng: điểm tổng kết 30% quá trình + 70% thi (`TY_LE_DIEM_QUA_TRINH`, `TY_LE_DIEM_THI`), học phần "đã đạt" khi từ 4.0 (`DIEM_DAT_TOI_THIEU`), trùng lịch là cùng thứ và khoảng tiết giao nhau trong cùng học kỳ/năm học.
5. Với mỗi use case ghi actor, đầu vào, xử lý, đầu ra, quyền theo vai trò (ví dụ: giảng viên chỉ nhập điểm lớp mình phụ trách, cố vấn chỉ xem lớp hành chính mình phụ trách).
6. Xác định vị trí AI: đúng 3 chức năng của đề (tư vấn đăng ký học phần, hỏi đáp quy chế, tóm tắt kết quả học tập), kèm nguyên tắc dữ liệu tối thiểu gửi AI.
7. Đặt kế hoạch làm từng bước nhỏ; trình kế hoạch cho người dùng chỉnh và duyệt trước khi viết code.

## Rules

- Giai đoạn đầu không thêm chức năng ngoài đề; chỉ mở rộng khi người dùng xác nhận đã được thầy cho phép, và mở rộng theo từng lượt có phạm vi rõ.
- Tên use case không dùng dấu "&" hay chữ "và" (ví dụ đổi "AI Tóm tắt kết quả học tập và gợi ý cải thiện" thành "AI Tóm tắt kết quả học tập").
- Sơ đồ use case tổng quát không dùng include/extend; ở các sơ đồ phân rã, mọi use case cha có mũi tên include tới "Đăng nhập hệ thống" vì phải đăng nhập mới dùng được.
- Không tự suy ra yêu cầu người dùng không nêu; điều chưa rõ phải hỏi hoặc nêu thành "điểm tự chọn" để người dùng xác nhận.
- Điểm và hồ sơ học tập chỉ gửi AI khi sinh viên hoặc vai trò được phân quyền yêu cầu.

## Outputs

- Danh sách actor, use case, chức năng theo vai trò; bảng quyết định nghiệp vụ đã chốt.
- Kế hoạch từng bước đã được người dùng duyệt (ví dụ kế hoạch 13 bước ở KT2-00).
- Mục ghi nhận trong `docs/ai-log.md`.

## Verification

- Mỗi use case đối chiếu được với một dòng ở mục 3 của đề, hoặc với một lượt mở rộng có ghi "đã được thầy cho phép".
- Không còn use case ngoài đề ở giai đoạn KT1/KT2; tên use case không chứa "&" hoặc "và".
- Ví dụ thực tế đã áp dụng: ở KT1-01 và KT1-08 đã xóa "phản hồi giảng dạy", "giáo trình", "Xem lịch thi", "Điểm danh", "Hủy đăng ký học phần", "Đặt lại mật khẩu", "Mở đợt đăng ký học phần"; ở KT2 người dùng chỉnh kế hoạch để bỏ hủy đăng ký; sau đó các chức năng này quay lại ở lượt 1/6 đến 5/6 khi đã được cho phép.
