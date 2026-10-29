Nhật ký sử dụng AI

Quy ước:

Mỗi lần làm việc với AI là một mục, mã theo giai đoạn: KT1-01, KT2-01, KT3-01...
Mục "Kiểm tra, chỉnh sửa" do tôi tự viết
Công cụ: Claude (claude.ai) cho phân tích, thiết kế. Claude Code (Antigravity) cho lập trình
Không dán code dài vào đây, ghi đường dẫn file và mã commit
KT1: Phân tích yêu cầu, thiết kế hệ thống
KT1-01: Đánh giá và chỉnh sơ đồ use case
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Gửi sơ đồ use case tổng quát và đề bài, nhờ đánh giá
Phản hồi (tóm tắt): AI chỉ ra use case còn thiếu so với đề, nhóm use case ngoài đề (phản hồi giảng dạy, giáo trình...), gợi ý đặt tên
Phần đã dùng: Bổ sung use case thiếu (phân quyền, tài liệu quy chế...), xóa use case ngoài đề
Kiểm tra, chỉnh sửa: Tôi đối chiếu từng use case với mục 3 của đề. AI chỉ ra các use case ngoài đề (phản hồi giảng dạy, giáo trình, yêu cầu học vụ, điều chỉnh lịch, chương trình đào tạo, tư vấn học tập) nên tôi xóa hết, vì thầy yêu cầu không thêm chức năng ngoài đề. Ban đầu tôi bỏ AI Tư vấn đăng ký học phần vì trường chưa có, sau đó thêm lại vì đề có yêu cầu chức năng này. Theo yêu cầu của thầy, ở sơ đồ tổng quát tôi không dùng include/extend, và tên use case không dùng "&" hay "và" (ví dụ đổi "AI Tóm tắt kết quả học tập và gợi ý cải thiện" thành "AI Tóm tắt kết quả học tập"). Ở các sơ đồ phân rã tôi giữ mũi tên include tới Đăng nhập hệ thống vì phải đăng nhập mới dùng được chức năng.
KT1-02: Thiết kế ERD
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ ERD từ đề và sơ đồ lớp
Phản hồi (tóm tắt): 13 bảng, khóa chính, khóa ngoại, ràng buộc, giải thích quan hệ
Phần đã dùng: 13 bảng cùng khóa chính, khóa ngoại, ràng buộc (UNIQUE, CHECK) và kiểu dữ liệu, trừ các phần tôi đã chỉnh bên dưới
Kiểm tra, chỉnh sửa: Tôi hỏi thêm AI về chuẩn hóa 3NF và thấy điểm tổng kết tính được từ điểm quá trình và điểm thi, nên bỏ cột này và tính khi cần. Tôi bỏ quan hệ giữa ngành học và học phần vì đề không nêu. Tôi để bảng tài liệu quy chế đứng riêng vì đề không nêu quan hệ với bảng nào. Tôi cũng hỏi lại ý nghĩa các ký hiệu 1, 0..1, * và các đường nối để hiểu quan hệ giữa các bảng trước khi dùng.
KT1-03: Sơ đồ lớp
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ sơ đồ lớp từ đề và các use case đã chốt
Phản hồi (tóm tắt): 13 lớp và kiểu liệt kê VaiTro, quan hệ, bội số, phương thức lấy từ use case
Phần đã dùng: 13 lớp, các quan hệ, bội số và phương thức, trừ các phần tôi đã chỉnh bên dưới
Kiểm tra, chỉnh sửa: Tôi hỏi AI sơ đồ lớp đã chuẩn hóa 3NF chưa, AI chỉ ra thuộc tính diemTongKet là giá trị tính được nên tôi đổi thành thuộc tính dẫn xuất /diemTongKet. Tôi yêu cầu bỏ quan hệ giữa NganhHoc và HocPhan và thuộc tính donViCongTac của GiangVien vì đề không nêu. Tôi cũng hỏi lại ý nghĩa các con số bội số, các loại đường nối và lý do lớp TaiLieuQuyChe không nối với lớp nào, để hiểu trước khi dùng.
KT1-04: Sơ đồ kiến trúc hệ thống
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ kiến trúc frontend, backend, CSDL, AI service và luồng dữ liệu
Phản hồi (tóm tắt): Kiến trúc Django, HTML template, module quản lý, module AI có RAG, LLM API, khối xác thực và phân quyền
Phần đã dùng: Các khối frontend, backend (xác thực phân quyền, module quản lý, module AI), lớp dữ liệu và LLM API
Kiểm tra, chỉnh sửa: Tôi để AI chọn phương án phổ biến là Django, HTML template, PostgreSQL và LLM API vì đề cho phép chọn công nghệ. Sau đó tôi quyết định dùng MySQL vì máy đã có MySQL Workbench. Sau đó tôi đổi khối "PostgreSQL" thành "MySQL" trong sơ đồ.
KT1-05: Sequence diagram luồng gọi AI
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ luồng gọi AI cho chức năng tư vấn đăng ký học phần
Phản hồi (tóm tắt): 1 sequence diagram 21 bước, có kiểm tra quyền trước khi đọc dữ liệu, nhánh không có quyền, nhánh lỗi (timeout, rate limit, phản hồi rỗng)
Phần đã dùng: Toàn bộ luồng của chức năng tư vấn đăng ký học phần
Kiểm tra, chỉnh sửa: Tôi đối chiếu với quy tắc của đề: điểm và hồ sơ chỉ gửi cho AI khi có quyền, nên bước kiểm tra quyền nằm trước bước đọc dữ liệu. Tôi giữ nhánh lỗi vì rubric KT3 yêu cầu xử lý timeout và rate limit. Hai luồng AI còn lại (hỏi đáp quy chế, tóm tắt kết quả) chưa vẽ vì rubric chỉ yêu cầu tối thiểu một luồng. Sau đó tôi đổi lifeline "PostgreSQL" thành "MySQL".
KT1-06: Activity diagram đăng ký học phần
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ quy trình đăng ký học phần theo đề
Phản hồi (tóm tắt): Quy trình 2 làn (Sinh viên, Hệ thống) có 3 điều kiện kiểm tra theo thứ tự: tiên quyết, trùng lịch, sĩ số
Phần đã dùng: Toàn bộ sơ đồ
Kiểm tra, chỉnh sửa: Tôi hỏi lại activity diagram là loại sơ đồ gì để hiểu trước khi dùng. Tôi đối chiếu 3 nhánh lỗi (thiếu tiên quyết, trùng lịch, lớp đầy) với yêu cầu test của đề. Sơ đồ không có hủy đăng ký vì ngoài đề, và nhánh lỗi kết thúc luôn vì đề không yêu cầu vòng lặp.
KT1-07: Wireframe giao diện
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Nhờ vẽ giao diện trang đăng ký học phần và bảng điểm
Phản hồi (tóm tắt): 2 màn hình có khung AI tư vấn và tóm tắt, có khung thông báo lỗi, dữ liệu mẫu theo đề
Phần đã dùng: Cả 2 màn hình
Kiểm tra, chỉnh sửa: Tôi hỏi lại wireframe là gì trước khi nhờ vẽ. Tên giảng viên và điểm số trong hình là dữ liệu bịa để minh họa, chỉ ví dụ SV001 và các học phần lấy từ đề. Tôi chỉ vẽ giao diện sinh viên vì đề chỉ yêu cầu hai trang này.
KT1-08: Sơ đồ use case phân rã
Ngày: 20/09/2026
Công cụ: Claude (claude.ai)
Prompt: Hỏi chức năng con của từng use case theo từng tác nhân, gửi sơ đồ phân rã tôi vẽ để nhờ đánh giá
Phản hồi (tóm tắt): AI đề xuất danh sách chức năng con cho 4 tác nhân, chỉ ra use case ngoài đề (Xem lịch thi, Hủy đăng ký học phần, Điểm danh, Đặt lại mật khẩu, Mở đợt đăng ký học phần) và lỗi hình thức trên sơ đồ
Phần đã dùng: Danh sách chức năng con cho 4 tác nhân. Sơ đồ Phòng Đào tạo dùng bản AI vẽ lại dạng cây rồi tôi sửa tiếp
Kiểm tra, chỉnh sửa: Tôi tự vẽ các sơ đồ phân rã trên draw.io rồi gửi lại nhờ AI đánh giá. Ban đầu tôi chưa muốn xóa Xem lịch thi và Điểm danh, sau đó xóa cùng Hủy đăng ký học phần, Đặt lại mật khẩu, Mở đợt đăng ký học phần vì thầy yêu cầu không thêm chức năng ngoài đề. Tôi hỏi thêm vì sao Giảng viên và Cố vấn ít chức năng, AI trả lời do đề chỉ nêu rõ chức năng của Phòng Đào tạo và Sinh viên.
KT2: Xây dựng chức năng quản lý
KT2-00: Lập kế hoạch xây dựng chức năng quản lý
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Đọc CLAUDE.md và docs/, đề xuất cấu trúc dự án Django và kế hoạch làm từng bước cho phần chức năng quản lý, chưa viết code
Phản hồi (tóm tắt): AI đề xuất 7 app chia theo 13 bảng, dùng bảng tai_khoan làm model người dùng, kế hoạch 13 bước
Phần đã dùng: Cấu trúc app, thứ tự các bước, cách xử lý các bảng phụ của Django, công thức điểm đặt ở hằng số cấu hình
Kiểm tra, chỉnh sửa: Tôi đối chiếu kế hoạch với đề và rubric, thấy có hủy đăng ký là ngoài đề, thiếu quản lý tài khoản của Phòng Đào tạo, thiếu tìm kiếm và lọc theo rubric KT2, thiếu quyền của Phòng Đào tạo và Cố vấn ở phần điểm và tra cứu, chưa nói tới thông báo lỗi. Tôi yêu cầu AI sửa các điểm này. AI hỏi tỷ lệ điểm tổng kết vì đề chưa nêu, tôi chọn 30% quá trình và 70% thi, đặt làm hằng số để đổi được sau này. Tôi chấp nhận đề xuất của AI về các bảng phụ của Django (django_migrations, django_session...) vì đề buộc 13 bảng nghiệp vụ, và yêu cầu ghi rõ vào tài liệu.
Commit: không có (chưa viết code)
KT2-01: Khởi tạo dự án Django với MySQL
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Khởi tạo dự án Django dùng MySQL (database qldt) bằng PyMySQL, cấu hình đọc từ .env, chưa tạo models, chưa migrate. Sau đó yêu cầu hạ Django xuống dòng 6.0
Phản hồi (tóm tắt): AI tạo venv, cài Django, PyMySQL, python-dotenv, dự án qldt, .env, .env.example, .gitignore, requirements.txt. Lần đầu AI cài Django 6.1.1
File được AI hỗ trợ: manage.py, qldt/settings.py, qldt/init.py, qldt/urls.py, requirements.txt, .gitignore, .env.example
Phần đã dùng: Toàn bộ, sau khi hạ Django xuống 6.0.8
Kiểm tra, chỉnh sửa: Trước khi làm, Claude Code báo lỗi 401 vì máy còn biến môi trường ANTHROPIC_BASE_URL trỏ sang DeepSeek từ trước, tôi xóa biến này rồi đăng nhập lại. Tôi tự điền cấu hình kết nối MySQL vào .env, không đưa vào khung chat. PowerShell chặn chạy file kích hoạt venv, tôi sửa bằng lệnh Set-ExecutionPolicy cho tài khoản của mình. Chạy python manage.py check thì lỗi Django 6.1.1 yêu cầu MySQL 8.4 trở lên trong khi máy dùng MySQL 8.0.46. Tôi tra tài liệu Django xác nhận rồi yêu cầu AI hạ xuống Django 6.0 thay vì nâng cấp MySQL, vì không muốn ảnh hưởng các database khác trên máy. Chạy lại check không còn lỗi. Tôi chạy runserver thấy server trả về mã 200, chạy git status thấy .env và venv không nằm trong danh sách commit rồi mới commit.
Commit: 3df1452
KT2-02: App accounts và model TaiKhoan
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Làm bước 2: app accounts với model TaiKhoan theo kế hoạch đã duyệt và docs/erd.md, khai báo AUTH_USER_MODEL trước khi migrate. Tạo migration nhưng CHƯA chạy migrate: cho tôi xem file migration và chạy sqlmigrate để tôi đối chiếu với erd.md. Ghi mục "Bảng phụ của Django" vào cuối docs/erd.md. Models khai báo đầy đủ ràng buộc UNIQUE, CHECK theo erd.md, cột mat_khau_ma_hoa dài 255. Không tự commit
Phản hồi (tóm tắt): AI tạo model TaiKhoan (không kế thừa PermissionsMixin, không có is_superuser), migration 0001, ghi mục bảng phụ của Django vào erd.md
File được AI hỗ trợ: accounts/models.py, accounts/migrations/0001_initial.py, qldt/settings.py, docs/erd.md
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi xem sqlmigrate và đối chiếu với erd.md, thấy khớp rồi mới cho migrate. Tôi yêu cầu AI ghi thêm vào CLAUDE.md quy tắc phân quyền chỉ dựa cột vai_tro, không dùng permission_required hay has_perm vì TaiKhoan không có is_superuser.
Commit: 5eb2d47
KT2-03: Đăng nhập, phân quyền, quản lý tài khoản
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Chạy migrate và check. Bước 3: đăng nhập, đăng xuất theo ten_dang_nhap; base.html có khung thông báo, trang 403, 404, 500 thân thiện; decorator hoặc mixin kiểm tra quyền theo vai_tro; Phòng Đào tạo tạo, cập nhật, khóa, xem danh sách tài khoản (tìm, lọc), gán vai trò; lệnh tạo tài khoản Phòng Đào tạo đầu tiên hỏi mật khẩu bằng getpass; test đăng nhập đúng sai, chặn vai trò, tạo và khóa tài khoản
Phản hồi (tóm tắt): AI tạo accounts/permissions.py (yeu_cau_vai_tro, YeuCauVaiTroMixin), form, view, template quản lý tài khoản, lệnh tao_tai_khoan_phong_dao_tao, trang lỗi 403/404/500
File được AI hỗ trợ: accounts/permissions.py, accounts/forms.py, accounts/views.py, accounts/urls.py, accounts/tests.py, accounts/management/commands/tao_tai_khoan_phong_dao_tao.py, templates/base.html, templates/403.html, 404.html, 500.html, CLAUDE.md
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi chạy check và test, tự đăng nhập thử bằng tài khoản Phòng Đào tạo tạo từ lệnh, thử khóa tài khoản rồi đăng nhập lại để xem bị chặn.
Commit: cbd9ec5
KT2-04: App people, academics, classes (bước 4 đến 6)
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Làm liên tiếp bước 4, 5, 6: people (sinh_vien, giang_vien, co_van_hoc_tap, khóa ngoại tới tai_khoan, UNIQUE), academics (nganh_hoc, lop_hanh_chinh, hoc_phan CHECK so_tin_chi > 0, dieu_kien_tien_quyet UNIQUE cặp và CHECK hai học phần khác nhau), classes (lop_hoc_phan CHECK si_so_toi_da > 0, lich_hoc CHECK thu từ 2 đến 8). CRUD cho Phòng Đào tạo có tìm và lọc; giảng viên chỉ xem lớp và lịch của mình. Lưu ý vòng phụ thuộc giữa people và academics
Phản hồi (tóm tắt): AI tạo 3 app, tách migration academics thành 0001 và 0002 để xử lý vòng phụ thuộc sinh_vien → lop_hanh_chinh → co_van_hoc_tap
File được AI hỗ trợ: people/, academics/, classes/* (models, forms, views, urls, templates, tests, migrations)
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi xem sqlmigrate của từng app để chắc tên bảng, cột, UNIQUE, CHECK đúng erd.md; chạy check và test trước khi commit.
Commit: 50bb68e
KT2-05: App enrollment và grades (đăng ký học phần, điểm)
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Bước 7, 8 với các quyết định đã chốt: học phần đạt khi điểm tổng kết từ 4.0 (DIEM_DAT_TOI_THIEU); điểm tổng kết = 30% quá trình + 70% thi, làm tròn 1 chữ số, tròn lên từ 5, dùng Decimal, không lưu cột; trùng lịch là cùng thứ và khoảng tiết giao nhau trong cùng học kỳ, năm học. Service đăng ký kiểm tra đúng thứ tự tiên quyết, trùng lịch, sĩ số, dừng ở lỗi đầu tiên và nêu rõ lý do; dùng transaction và khóa dòng lớp học phần khi kiểm tra sĩ số. Giảng viên chỉ nhập điểm lớp mình phụ trách
Phản hồi (tóm tắt): AI tạo enrollment/services.py (dang_ky_hoc_phan trong transaction.atomic, select_for_update), grades/tinh_diem.py (ROUND_HALF_UP), view nhập và xem điểm theo vai trò
File được AI hỗ trợ: enrollment/models.py, enrollment/services.py, enrollment/views.py, enrollment/tests.py, grades/models.py, grades/tinh_diem.py, grades/forms.py, grades/views.py, grades/tests.py, qldt/settings.py
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi kiểm tra test có đủ ca đăng ký hợp lệ, thiếu tiên quyết, trùng lịch, lớp đầy, đăng ký trùng; tự tính tay vài điểm tổng kết (ví dụ 8.0 và 7.5 ra 7.7) để đối chiếu với kết quả test.
Commit: a8c36f4
KT2-06: App regulations và reports
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Bước 9: tai_lieu_quy_che, Phòng Đào tạo tải lên PDF hoặc DOCX (kiểm tra đuôi, tối đa 10 MB, tên không trùng), tải về qua view bắt buộc đăng nhập, không mở công khai MEDIA_URL. Bước 10: thống kê sĩ số theo lớp, học phần nhiều đăng ký, kết quả học tập tổng hợp, dùng truy vấn tổng hợp của ORM, không lặp truy vấn trong vòng lặp
Phản hồi (tóm tắt): AI tạo 2 app, thống kê dùng aggregate, test quyền và test tệp sai đuôi, quá lớn
File được AI hỗ trợ: regulations/, reports/, qldt/settings.py, qldt/urls.py
Phần đã dùng: Toàn bộ, sau một lần chỉnh
Kiểm tra, chỉnh sửa: Tôi yêu cầu sửa: tai_ve_view chỉ cho Phòng Đào tạo, các vai trò khác nhận 403, vì sinh viên và cố vấn chỉ tiếp cận quy chế qua chatbot; kiểm tra reports dùng hằng số DIEM_DAT_TOI_THIEU chứ không ghi cứng 4.0.
Commit: 38e09d6
KT2-07: Rà soát phân quyền toàn hệ thống, dữ liệu mẫu, README
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Bước 11: liệt kê mọi URL kèm vai trò được phép, test chéo vai trò bằng cả 4 vai trò và người chưa đăng nhập (sinh viên không xem dữ liệu sinh viên khác, giảng viên không sửa điểm lớp người khác, cố vấn không xem sinh viên ngoài lớp phụ trách). Bước 12: lệnh nạp dữ liệu mẫu có ca của đề (SV001 đã đạt CSDL, CTDL&GT) và ca lỗi thiếu tiên quyết, trùng lịch, lớp đầy; README hướng dẫn cài, chạy, demo
Phản hồi (tóm tắt): AI tạo PhanQuyenToanHeThongTest (ma trận URL × vai trò), lệnh nap_du_lieu_mau, README
File được AI hỗ trợ: accounts/tests.py, accounts/forms.py, accounts/management/commands/nap_du_lieu_mau.py, README.md, .env.example
Phần đã dùng: Toàn bộ, sau một lần chỉnh
Kiểm tra, chỉnh sửa: Tôi phát hiện đổi vai_tro của tài khoản đang gắn hồ sơ sẽ để lại hồ sơ mồ côi, yêu cầu chặn ở form kèm test. Tôi chạy nap_du_lieu_mau và thử tay 4 ca lỗi bằng sv001, sv002, sv003, sv005.
Commit: 9ead1a9
KT3: Tích hợp AI, tối ưu prompt, kiểm thử
Tối ưu prompt (mỗi chức năng AI làm ít nhất 3 vòng)
Chức năng AI	Vòng	Phiên bản prompt	Dữ liệu thử	Kết quả	Vấn đề	Cải tiến
Hỏi đáp quy chế	1	v1, truy hồi v1 (4 đoạn)	10 câu trong docs/ca_thu_ai/hoi_dap_quy_che.md	Câu 1 sai, câu 6 (thời tiết) và câu 7 (gài lệnh) đúng; nhiều câu lỗi giới hạn tần suất	Truy hồi bỏ sót Điều 14, 15 cho câu "buộc thôi học"	Truy hồi v2: thêm bigram, đưa tiêu đề Điều vào chỉ mục, lấy 6 đoạn; thêm --cau, --khoang_cach
Hỏi đáp quy chế	2	v1, truy hồi v2	Câu 1 đến 5, 8, 9, 10	5 câu đúng, 0 câu sai, 3 câu chưa có kết quả do hạn mức và lỗi dịch vụ (ket_qua_quy_che_vong_2.txt)	Nguồn chính "Điều 3" của câu 4 bị loại nhầm	Chuẩn hóa so khớp nguồn (_loc_nguon); prompt v2: trả lời trực tiếp 1-2 câu, khoảng 120 từ, chép nguyên văn nguồn
Hỏi đáp quy chế	3	v2, truy hồi v2, ngưỡng 10	Câu 1, 2	Câu 1 đúng, trích Điều 14 và 15; câu 2 hết hạn mức (ket_qua_quy_che_vong_3.txt)	Chưa chạy đủ 10 câu do hạn mức Gemini miễn phí (20 lượt/ngày)	Chạy lại đủ 10 câu khi có hạn mức
Tư vấn đăng ký	1	v1	10 ca trong docs/ca_thu_ai/tu_van_dang_ky.md	7/7 ca gọi AI thật có trả lời, gợi ý đúng lớp, không bịa mã lớp (ket_qua_tu_van_vong_1.txt)	Mục lưu ý dài; ca 4, 5 nói quá dữ liệu ("không có lớp nào đủ điều kiện trong cơ sở dữ liệu")	Prompt v2
Tư vấn đăng ký	2	v2	Như vòng 1	7/7 đúng, lưu ý gọn, không nói quá dữ liệu (ket_qua_tu_van_vong_2.txt)	Không thấy lỗi	Thử prompt v3
Tư vấn đăng ký	3	v3	Như vòng 1	7/7 đúng, kết quả giống hệt v2 (ket_qua_tu_van_vong_3.txt)	v3 không cải thiện thêm so với v2	Chọn v2
Tóm tắt kết quả	1	v1	10 ca trong docs/ca_thu_ai/tom_tat_ket_qua.md	5/5 ca gọi AI thật có trả lời, số liệu khớp code (ket_qua_tom_tat_vong_1.txt)	Ca 5 đưa học phần đã đạt (CA5_HPB, 7.5) vào mục cần cải thiện; điểm mạnh viết chung chung	Prompt v2
Tóm tắt kết quả	2	v2	Như vòng 1	5/5 đúng, nêu đủ mã và điểm từng học phần (ket_qua_tom_tat_vong_2.txt)	Không thấy lỗi	Thử prompt v3
Tóm tắt kết quả	3	v3	Như vòng 1	5/5 số liệu đúng, câu trả lời ngắn nhất (ket_qua_tom_tat_vong_3.txt)	Liệt kê thiếu: ca 1 chỉ 2/5, ca 2 chỉ 2/4 học phần đạt	Chọn v2

Ghi chú: các vòng tư vấn và tóm tắt chạy lại ngày 29/10/2026 bằng model gemini-3.5-flash-lite, vì gemini-3.8-flash bị quá tải (lỗi 504) và hết hạn mức miễn phí. Tôi đổi model bằng dòng GEMINI_MODEL trong .env, không sửa code. Riêng ca 1 tóm tắt v3 có kết quả từ gemini-3.8-flash ở lần chạy trước.

KT3-01: Hạ tầng gọi AI (ai_core)
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Bắt đầu KT3, lượt 1: hạ tầng gọi AI, CHƯA làm chức năng nào cụ thể. Nhà cung cấp Gemini, khóa lấy từ GEMINI_API_KEY trong .env, dùng SDK chính thức hiện hành (google-genai), tên model đặt ở GEMINI_MODEL. App ai_core gồm client có timeout (AI_TIMEOUT_GIAY), thử lại có giới hạn (AI_SO_LAN_THU_LAI) khi hết thời gian, 429 hoặc 5xx; mọi lỗi chuyển thành ngoại lệ riêng của dự án. Sau đó: kiem_tra_ai báo "Dịch vụ AI gặp lỗi", thêm --chi_tiet in loại lỗi, mã HTTP, thông điệp API (tuyệt đối không in khóa) và cho biết nguyên nhân
Phản hồi (tóm tắt): AI tạo ai_core (GeminiClient, ClientAIGia, exceptions, nap_prompt dùng string.Template, dinh_dang_ket_qua kèm cảnh báo cố định), prompts/README.md, lệnh kiem_tra_ai
File được AI hỗ trợ: ai_core/clients.py, ai_core/exceptions.py, ai_core/prompts.py, ai_core/dinh_dang.py, ai_core/management/commands/kiem_tra_ai.py, ai_core/tests.py, prompts/README.md, prompts/kiem_tra_ket_noi/v1/
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi chạy kiem_tra_ai với khóa thật, gặp lỗi chung chung nên yêu cầu thêm --chi_tiet để biết nguyên nhân; kiểm tra phần in lỗi không lộ khóa API.
Commit: f7a0d71
KT3-02: AI tư vấn đăng ký học phần
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Lượt 2 KT3: app tu_van_dang_ky, không tạo bảng mới, nguyên tắc code tính, AI giải thích. Dùng lại đúng các hàm kiểm tra của enrollment.services, không viết lại logic. Mỗi lớp đang mở có trạng thái do code tính (đủ điều kiện, thiếu tiên quyết, trùng lịch, đã đầy, đã đăng ký). Chỉ Sinh viên, đối tượng lấy từ request.user. Ghi chú tối đa 300 ký tự. Dữ liệu gửi AI chỉ gồm học phần đã đạt, lớp đang mở kèm trạng thái, ghi chú; không gửi họ tên, email, mã sinh viên, mã tài khoản
Phản hồi (tóm tắt): AI tách hàm xac_dinh_trang_thai trong enrollment.services để dùng chung cho đăng ký thật và tư vấn, tạo prompt v1 với lược đồ JSON goi_y, chua_nen_dang_ky, luu_y, lọc mã lớp bịa, bộ 10 ca thử
File được AI hỗ trợ: tu_van_dang_ky/*, enrollment/services.py, prompts/tu_van_dang_ky/v1/, docs/ca_thu_ai/tu_van_dang_ky.md
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi kiểm tra test bằng client giả: prompt không có họ tên, email, mã sinh viên; lớp thiếu tiên quyết hay đã đầy không được nằm trong goi_y; mã lớp bịa bị loại.
Commit: 0c6e5f5
KT3-03: AI tóm tắt kết quả học tập
Ngày: 20/09/2026
Công cụ: Claude Code
Prompt: Lượt 3 KT3: app tom_tat_ket_qua, không tạo bảng mới, code tính số liệu (tổng tín chỉ đạt, số học phần đạt và chưa đạt, điểm cao nhất, thấp nhất), AI chỉ diễn giải. Sinh viên tóm tắt của chính mình; cố vấn chọn sinh viên thuộc lớp mình phụ trách, ngoài phạm vi thì 403. Không gửi thông tin định danh
Phản hồi (tóm tắt): AI tạo service tính số liệu, prompt v1 (tom_tat, diem_manh, can_cai_thien, ke_hoach_goi_y, luu_y), lọc mã học phần bịa, bộ 10 ca thử
File được AI hỗ trợ: tom_tat_ket_qua/*, grades/services.py, prompts/tom_tat_ket_qua/v1/, docs/ca_thu_ai/tom_tat_ket_qua.md
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi kiểm tra test cố vấn chọn sinh viên ngoài lớp nhận 403 và client giả không bị gọi; prompt không nhận xét về con người, chỉ về kết quả.
Commit: 210e501
KT3-04: Chatbot hỏi đáp quy chế (RAG) và vòng 1, vòng 2
Ngày: 20/09/2026 đến 21/09/2026
Công cụ: Claude Code
Prompt: Lượt 4 KT3: app hoi_dap_quy_che, không tạo bảng mới, trích chữ từ PDF và DOCX đã tải lên, chia đoạn theo Điều, khoản (tối đa khoảng 1500 ký tự, giữ tên tài liệu, Điều, khoản), xếp hạng BM25 tự cài, chỉ mục giữ trong bộ nhớ, không dùng embedding ngoài, lấy tối đa 4 đoạn, bỏ đoạn dưới ngưỡng. Sau vòng 1: thêm --cau, --khoang_cach, dừng hẳn khi gặp lỗi tần suất; truy hồi thêm bigram, tiêu đề Điều, lấy 6 đoạn; chưa đổi prompt v1
Phản hồi (tóm tắt): AI tạo trich_xuat.py, chia_doan.py, bm25.py, chi_muc.py, services.py, lệnh chay_ca_thu_quy_che, truy hồi v1 và v2 chọn bằng AI_TRUY_HOI_PHIEN_BAN
File được AI hỗ trợ: hoi_dap_quy_che/*, prompts/hoi_dap_quy_che/v1/, docs/ca_thu_ai/hoi_dap_quy_che.md, ai_core/clients.py
Phần đã dùng: Toàn bộ, sau nhiều lần chỉnh
Kiểm tra, chỉnh sửa: Tôi phát hiện chữ ký làm mới chỉ mục chỉ dựa ngày cập nhật nên thay tệp hai lần trong một ngày không làm mới, yêu cầu thêm duong_dan_file và test. Tôi chạy vòng 1 với Gemini thật, thấy truy hồi hụt và lỗi tần suất, nên yêu cầu cải tiến truy hồi. Tôi yêu cầu AI không tự gọi Gemini thật khi phát triển vì hạn mức ít, và phân biệt hết hạn mức ngày với vượt tần suất phút. Test hoi_dap_quy_che từng fail khi .env đặt ngưỡng 10, sửa bằng cố định cấu hình trong test.
Commit: f6c6c1e
KT3-05: Sửa lọc nguồn chatbot
Ngày: 21/09/2026
Công cụ: Claude Code
Prompt: Kết quả thật câu 4: AI trả lời đúng nhưng nguồn chính "Điều 3" bị loại dù đoạn đó có trong danh sách truy hồi. Điều tra và sửa, không gọi AI thật: viết test client giả trả nguồn ở các dạng khoản null, "", "3", "khoản 3", số 3; chuẩn hóa so khớp; nguồn không thuộc đoạn đã gửi vẫn bị loại
Phản hồi (tóm tắt): AI tìm ra so khớp phân biệt dạng chữ và số, sửa _loc_nguon chuẩn hóa tiền tố, kiểu, khoảng trắng, hoa thường
File được AI hỗ trợ: hoi_dap_quy_che/services.py, hoi_dap_quy_che/tests.py
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Lỗi do tôi tự phát hiện khi đọc kết quả chạy thật. Tôi kiểm tra test hồi quy: nguồn hợp lệ ở nhiều dạng được giữ, nguồn bịa vẫn bị loại.
Commit: 682795e
KT3-06: Prompt v2 chatbot quy chế và tùy chọn chạy ca thử (chuẩn bị vòng 3)
Ngày: 21/09/2026
Công cụ: Claude Code
Prompt: Tạo prompts/hoi_dap_quy_che/v2 từ v1, chỉ đổi: trả lời trực tiếp 1-2 câu trước, tổng khoảng 120 từ; nguồn chép nguyên văn từ tiêu đề đoạn, nguồn đầu tiên là đoạn chứa câu trả lời; đoạn chỉ dẫn chiếu "do quy chế của cơ sở đào tạo quy định" thì nói đúng như vậy. Không sửa v1. Thêm --phien_ban_prompt, --ghi_vao, in số lượt gọi dự kiến và hỏi xác nhận
Phản hồi (tóm tắt): AI tạo v2, thêm các tùy chọn, test bằng client giả
File được AI hỗ trợ: prompts/hoi_dap_quy_che/v2/, hoi_dap_quy_che/management/commands/chay_ca_thu_quy_che.py, hoi_dap_quy_che/services.py, tests
Phần đã dùng: Toàn bộ
Kiểm tra, chỉnh sửa: Tôi so sánh v1 và v2 để chắc chỉ đổi đúng 3 điểm; chạy vòng 3 với Gemini thật, câu 1 đúng nhưng câu 2 hết hạn mức.
Commit: 7bb65c5
KT3-07: Công cụ ca thử tư vấn và tóm tắt, review code AI
Ngày: 21/09/2026
Công cụ: Claude Code
Prompt: Làm 4 việc, không gọi AI thật: (1) lệnh chay_ca_thu_tu_van và chay_ca_thu_tom_tat giống chay_ca_thu_quy_che, mỗi ca dựng dữ liệu trong giao dịch rồi hoàn tác, tự kiểm tra Đạt/Không đạt; (2) review bảo mật và chất lượng code của ai_core, tu_van_dang_ky, tom_tat_ket_qua, hoi_dap_quy_che, regulations, ghi docs/review_code_ai.md; (3), (4) tài liệu thiết kế AI và biên bản kiểm thử
Phản hồi (tóm tắt): AI tạo 2 lệnh ca thử, báo cáo review (đã sửa: kiểm tra magic bytes khi tải tệp, giới hạn tần suất cho tư vấn và tóm tắt; chưa sửa: N+1 trong tính trạng thái, KeyError khi prompt thiếu biến, LocMemCache, DEBUG/SECRET_KEY mặc định), docs/thiet_ke_ai.md, docs/bien_ban_kiem_thu.md
File được AI hỗ trợ: tu_van_dang_ky/management/commands/chay_ca_thu_tu_van.py, tom_tat_ket_qua/management/commands/chay_ca_thu_tom_tat.py, ai_core/gioi_han_tan_suat.py, regulations/models.py, docs/review_code_ai.md, docs/thiet_ke_ai.md, docs/bien_ban_kiem_thu.md
Phần đã dùng: Toàn bộ; các phát hiện chưa sửa giữ lại để tôi quyết định
Kiểm tra, chỉnh sửa: Tôi đọc báo cáo review, đồng ý sửa ngay các lỗi rủi ro thấp, giữ nguyên hàm xac_dinh_trang_thai dùng chung để không ảnh hưởng đăng ký thật. Biên bản ghi 317/317 test đạt ngày 21/09/2026.
Commit: e26c096
Mở rộng chức năng (đã được thầy cho phép) và giao diện

Mỗi lượt theo cùng quy trình: AI đối chiếu docs/erd.md, tạo model, cho tôi xem sqlmigrate, tôi đối chiếu xong mới cho migrate; AI viết code và test; tôi thử tay rồi tự commit.

Mã	Ngày	Prompt (tóm tắt)	Tôi kiểm tra, quyết định	Commit
MR-01	22/09/2026	Lượt 1/6: đổi mật khẩu và đặt lại mật khẩu (cột phai_doi_mat_khau, middleware ép đổi, mật khẩu tạm hiện một lần), danh mục học kỳ, thông tin cá nhân	Đồng ý không backfill hoc_ky (không bịa ngày); phát hiện thiếu nút "Đặt lại mật khẩu" trên danh sách tài khoản, yêu cầu làm nốt	86c4f3f
MR-02	22/09/2026	Lượt 2/6: đợt đăng ký học phần (CHECK ngay_dong > ngay_mo, không chồng thời gian), hủy đăng ký khi chưa có điểm	Khi ràng buộc UNIQUE cũ chặn đăng ký lại sau khi hủy, tôi chọn hướng B (cho đăng ký lại, chỉ tối đa 1 dòng còn hiệu lực); xem sqlmigrate hai lần trước khi migrate	9f10ed2
MR-03	22/09/2026	Lượt 3/6: chương trình đào tạo, chi tiết chương trình, xem tiến độ học tập	Xác nhận giữ on_delete=PROTECT, không backfill (để NULL)	84805ce
MR-04	22/09/2026	Lượt 4/6: điểm trung bình học kỳ và tích lũy, xếp loại học lực, cảnh báo học vụ, công bố điểm	Đồng ý giữ ranh giới, không mở rộng phần công bố điểm sang tư vấn và tóm tắt AI	8a1fa1b
MR-05	22/09/2026 đến 23/09/2026	Lượt 5/6: điểm danh, lịch giảng dạy và thời khóa biểu lưới tuần, lịch thi, xuất PDF giữ dấu tiếng Việt	Xem lại sqlmigrate của classes.0002_lichthi và diem_danh.0001 trước khi migrate	2c5b94e
MR-06	23/09/2026	Lượt 6/6: xuất bảng điểm và thời khóa biểu PDF, nhập sinh viên từ Excel, xuất thống kê Excel, thông báo	Xem sqlmigrate của thong_bao.0001, chạy lại toàn bộ test trước khi commit	33e534b
GD-01	24/09/2026	Giao diện Sinh viên lượt 1/3: layout dùng chung, giữ bảng màu, chỉ mượn bố cục, liệt kê file sẽ sửa và chờ xác nhận	Đồng ý 3 điểm tự chọn của AI; yêu cầu sửa lỗi tab Bảng điểm không sáng	2575445
GD-02	24/09/2026	Giao diện Sinh viên lượt 2/3: trang chủ và bảng điểm	Bỏ cột Điểm chữ ở lượt này; yêu cầu sửa định dạng phần trăm hoàn thành (unlocalize)	c425d7f
GD-03	24/09/2026 đến 26/09/2026	Giao diện lượt 3/3 và trang chủ, menu các vai trò khác; lệnh nap_du_lieu_day_du; rà soát menu 4 vai trò; chức năng xóa có trang xác nhận	Xác nhận 3 điểm tự chọn; tự thử tay và phát hiện: tìm điều kiện tiên quyết theo mã bị lỗi, thiếu nút xóa ngành, học phần, chương trình, tạo tài khoản cố vấn bị lỗi, lớp hành chính không thấy chương trình vừa tạo; yêu cầu sửa từng lỗi	0aab96d
SK-01	24/09/2026	Viết 11 file SKILL.md trong .agents/skills, mỗi skill phản ánh đúng quy trình thật đã dùng, có ví dụ thật	Đối chiếu nội dung skill với mã nguồn; cập nhật lại số test, phiên bản Django, số bảng ngày 13/10/2026	abda886, fb8e64c
Cuối kỳ
Mã	Ngày	Prompt (tóm tắt)	Phản hồi, phần đã dùng	Tôi kiểm tra, chỉnh sửa	Commit
CK-01	02/10/2026	Liệt kê toàn bộ model (bảng, field, FK, UNIQUE, CHECK) và URL/view theo từng vai trò, xuất ra tong_hop_hien_trang.md	AI đọc model và URL bằng Django, liệt kê 118 URL theo vai trò	Dùng làm căn cứ để tự kiểm tra sơ đồ lớp và use case	df9f015
CK-02	02/10/2026	Gửi XML sơ đồ lớp, sơ đồ lớp chi tiết, use case tổng quát tự vẽ, hỏi đã đúng chưa	AI chỉ ra chỗ sai so với code; vẽ use case phân rã 4 tác nhân theo phong cách thầy	Tôi sửa: Sinh viên chỉ giữ 9 use case gốc; extend không nối tầng; bỏ "Kiểm tra điều kiện tiên quyết" vì chạy ngầm, sau khi thầy hỏi về include	Sơ đồ tự vẽ, chưa đưa vào repo
CK-03	02/10/2026	Thầy yêu cầu vẽ biểu đồ trạng thái, trình tự, thành phần, triển khai	AI vẽ 6 biểu đồ trình tự (đăng nhập, đăng ký, điểm, 3 chức năng AI), thành phần, triển khai	Tôi hỏi lại về trạng thái kết thúc và lớp Điểm	df9f015
CK-04	02/10/2026 đến 03/10/2026	Thiết kế CSDL gồm danh mục bảng, database diagram, ERD; sau đó yêu cầu ERD "đúng và không màu mè"	AI đọc kiểu cột thật từ information_schema của MySQL, viết thiet_ke_csdl.md (21 bảng) và 3 sơ đồ	Tôi bật MySQL để AI đọc đúng kiểu cột (tinyint, NO ACTION) thay vì đoán	df9f015
CK-05	03/10/2026	Làm file Word báo cáo theo khung báo cáo mẫu	AI dựng báo cáo chương 1 đến 4, mục lục, danh mục hình và bảng tự động, khung chèn hình	Tôi tự viết chương 5 Kiểm thử, nhờ AI rà soát: sửa thông báo khóa tài khoản, lỗi 403, hai điều kiện cảnh báo học vụ, bảng các vòng tối ưu	df9f015
CK-06	13/10/2026	Kiểm tra nội dung skill và sơ đồ use case có khớp code; test chạy lâu	AI đối chiếu khoảng 40 tên hàm, test trong skill với code; đổi bộ băm mật khẩu khi chạy test sang MD5	Chạy toàn bộ test: 943/943 đạt trong 49 giây (Docker, 28/10/2026)	fb8e64c
Nhật ký dây chuyền agent

Mỗi lần chạy lệnh /tinh-nang-moi (xem .claude/README.md), điều phối viên thêm một dòng vào bảng dưới đây. Không ghi dữ liệu cá nhân, điểm thật hay khóa API. Cột cuối do người tự kiểm tra và đánh dấu.

Thời gian	Yêu cầu	Agent đã chạy	Kết quả test	Vấn đề review	Phần người cần kiểm tra
YYYY-MM-DD HH:MM	(mẫu) Mô tả yêu cầu rút gọn	phan-tich-yeu-cau → (người duyệt) → lap-trinh-vien → kiem-thu-vien (0 vòng sửa) → review-code, kiem-tra-bao-mat	Ran N tests, OK	Nghiêm trọng 0, Trung bình 0, Nhỏ 0; Bảo mật 0	[ ] Thử tay trên trình duyệt; [ ] đọc lại diff