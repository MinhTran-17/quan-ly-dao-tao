# Hệ thống quản lý đào tạo có tích hợp AI

## 1. Mô tả bài toán
Cơ sở đào tạo cần quản lý sinh viên, giảng viên, học phần, lớp học, đăng ký học, điểm và quy chế đào tạo. Sinh viên thường gặp khó khăn khi tra cứu điều kiện tiên quyết, lịch học và quy định học vụ. Đề tài yêu cầu xây dựng hệ thống quản lý đào tạo có tích hợp AI tư vấn đăng ký học phần, hỏi đáp quy chế và tóm tắt kết quả học tập.

## 2. Mục tiêu
- Xây dựng hệ thống quản lý sinh viên, giảng viên, học phần, lớp học, đăng ký học và điểm.
- Tích hợp AI để tư vấn đăng ký môn học, trả lời quy chế và tóm tắt tiến độ học tập.
- Sử dụng AI trong SDLC để thiết kế nghiệp vụ đào tạo, CSDL, API, kiểm thử và tài liệu.
- Hỗ trợ sinh viên, cố vấn học tập và phòng đào tạo ra quyết định tốt hơn.

## 3. Yêu cầu chức năng
### 3.1. Chức năng quản lý
1. Đăng nhập và phân quyền phòng đào tạo, giảng viên, sinh viên, cố vấn học tập.
2. Quản lý sinh viên, giảng viên, ngành học, lớp hành chính.
3. Quản lý học phần, số tín chỉ, điều kiện tiên quyết.
4. Quản lý lớp học phần, lịch học, sĩ số.
5. Đăng ký học phần và kiểm tra điều kiện đăng ký.
6. Nhập, sửa, xem điểm quá trình, điểm thi, điểm tổng kết.
7. Tra cứu thời khóa biểu, bảng điểm, lịch sử đăng ký.
8. Thống kê kết quả học tập, sĩ số, học phần có nhiều sinh viên đăng ký.

### 3.2. Chức năng AI
1. AI tư vấn đăng ký học phần dựa trên học phần đã học, điều kiện tiên quyết và lịch học.
2. Chatbot hỏi đáp quy chế đào tạo từ tài liệu quy định.
3. AI tóm tắt kết quả học tập và gợi ý kế hoạch cải thiện cho sinh viên.

## 4. Yêu cầu kỹ thuật
- Backend: Django/FastAPI/Flask.
- Frontend: React/Vue/HTML template.
- CSDL: PostgreSQL/MySQL/SQLite.
- AI Engine: OpenAI/Gemini/Claude/Hugging Face/Ollama.
- Khuyến khích RAG cho chatbot quy chế đào tạo.
- Có kiểm soát quyền truy cập điểm và hồ sơ học tập.
- Có test cho đăng ký học phần, điều kiện tiên quyết, nhập điểm và chức năng AI.

## 5. Dữ liệu đầu vào, đầu ra và dữ liệu hệ thống
- Dữ liệu chính: sinh viên, giảng viên, ngành, học phần, lớp học phần, đăng ký, điểm, quy chế.
- Đầu vào quản lý: thông tin sinh viên, học phần, lịch học, điểm, đăng ký.
- Đầu vào AI: bảng điểm, học phần đã học, danh sách lớp mở, tài liệu quy chế.
- Đầu ra quản lý: bảng điểm, thời khóa biểu, danh sách lớp, thống kê.
- Đầu ra AI: gợi ý đăng ký, câu trả lời quy chế, tóm tắt tiến độ học tập.

Ví dụ dữ liệu mẫu: `Sinh viên SV001 đã đạt CSDL, CTDL&GT; muốn đăng ký Công nghệ phần mềm và AI ứng dụng`.

Prompt mẫu:

System: Bạn là trợ lý học vụ. Chỉ tư vấn dựa trên dữ liệu học phần, điểm và quy chế được cung cấp. Không cam kết thay quyết định của phòng đào tạo.
User: Dữ liệu sinh viên: {{student_academic_record}}. Danh sách lớp mở: {{open_courses}}. Hãy gợi ý các học phần nên đăng ký kỳ tới và giải thích điều kiện tiên quyết.

Điểm và hồ sơ học tập chỉ được gửi AI khi sinh viên hoặc vai trò được phân quyền yêu cầu.

## 6. Hướng dẫn sử dụng AI trong từng giai đoạn SDLC
### Giai đoạn 1: Phân tích yêu cầu và thiết kế hệ thống (Bài KT1)
- Dùng AI phân tích nghiệp vụ đăng ký học, nhập điểm, tra cứu quy chế.
- Dùng AI sinh use case cho sinh viên, giảng viên, phòng đào tạo, cố vấn.
- Dùng AI thiết kế ERD cho học phần, lớp học phần, đăng ký, điểm.
- Dùng AI xác định vị trí AI: tư vấn đăng ký, hỏi đáp quy chế, tóm tắt học tập.
- Dùng AI sinh prototype trang đăng ký học phần và bảng điểm.

### Giai đoạn 2: Xây dựng chức năng quản lý (Bài KT2)
- Dùng AI sinh API CRUD cho sinh viên, học phần, lớp học phần, điểm.
- Dùng AI sinh logic kiểm tra điều kiện tiên quyết và trùng lịch.
- Dùng AI debug lỗi tính điểm tổng kết và lọc lớp mở.
- Lưu prompt, phản hồi AI và phần code đã chỉnh sửa.

### Giai đoạn 3: Tích hợp AI, tối ưu prompt và kiểm thử (Bài KT3)
- Dùng AI thiết kế prompt tư vấn không vượt quá quy chế.
- Dùng AI sinh code truy xuất dữ liệu học tập theo quyền.
- Dùng AI sinh test case cho thiếu điều kiện tiên quyết, trùng lịch, câu hỏi ngoài quy chế.
- Tối ưu prompt qua ít nhất 3 vòng để tăng tính chính xác của gợi ý.

### Giai đoạn 4: Hoàn thiện, triển khai và báo cáo (Bài thi cuối kỳ)
- Dùng AI sinh README và hướng dẫn demo theo vai trò.
- Dùng AI review bảo mật dữ liệu điểm.
- Dùng AI sinh báo cáo kỹ thuật và slide thuyết trình.
- Dùng AI hỗ trợ đóng gói dữ liệu mẫu và triển khai.

## 7. Mức độ khó
Nâng cao: Hệ thống có quy trình đăng ký phức tạp, điều kiện tiên quyết, trùng lịch và dữ liệu học tập nhạy cảm. Chức năng AI tư vấn cần dựa trên dữ liệu đúng và có giới hạn rõ.