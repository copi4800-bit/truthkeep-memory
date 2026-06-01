# 🔒 Chính Sách Quyền Riêng Tư Cục Bộ: TruthKeep Privacy Policy

TruthKeep Memory được xây dựng trên nguyên tắc **Quyền riêng tư tuyệt đối ngay từ khâu thiết kế (Privacy by Design)**. Dữ liệu ký ức của bạn là tài sản tối mật. Chúng tôi cam kết bảo vệ dữ liệu đó bằng các biện pháp toán học và mật mã học tiên tiến nhất mà không cần gửi bất kỳ dữ liệu nào lên đám mây.

---

## 1. Nguyên Tắc Cốt Lõi Về Quyền Riêng Tư (Core Privacy Principles)

1.  **Chủ quyền Dữ liệu Cục bộ (Local Data Sovereignty)**: Toàn bộ dữ liệu hội thoại, đồ thị nhận thức, khóa bảo mật và dấu vết kiểm toán đều được lưu trữ trực tiếp trên thiết bị cá nhân của bạn. Không có cơ chế gửi dữ liệu tự động về máy chủ trung tâm.
2.  **Giảm thiểu Thu thập (Data Minimization)**: Chỉ những thông tin cần thiết để tạo lập ngữ cảnh thông minh và duy trì tính nhất quán tri thức mới được ghi nhận vào bộ nhớ dài hạn.
3.  **Quyền được Quên (Right to be Forgotten)**: Người dùng có toàn quyền kiểm soát, chỉnh sửa, lưu trữ hoặc xóa bỏ vĩnh viễn bất kỳ nút ký ức nào thông qua các lệnh CLI hoặc giao diện người dùng. Khi một ký ức bị xóa, toàn bộ các liên kết đồ thị liên quan đến nó cũng sẽ bị thu hồi triệt để.

---

## 2. Các Cấp Độ Bảo Vệ Quyền Riêng Tư (Privacy Modes)

Hệ thống hoạt động dưới ba cấu hình quyền riêng tư linh hoạt, có thể điều chỉnh qua biến môi trường `TK_SECURITY_MODE` hoặc `TK_PRIVACY_MODE`:

### 2.1. Standard Mode (Mặc định)
*   **Mô tả**: Tối ưu hóa giữa hiệu năng tìm kiếm ngữ cảnh và bảo vệ cục bộ.
*   **Đặc điểm**:
    *   Nội dung ký ức được lưu trong SQLite và lập chỉ mục qua FTS5 dưới dạng plaintext để hỗ trợ tìm kiếm toàn văn nhanh chóng.
    *   Tệp cơ sở dữ liệu được bảo vệ bằng quyền truy cập mức hệ điều hành (OS File Permissions).

### 2.2. Strict Privacy Mode (`TK_PRIVACY_MODE=strict` hoặc `hardened` mode)
*   **Mô tả**: Cấu hình bảo mật cấp doanh nghiệp, bảo vệ tối đa chống lại các tiến trình độc hại chạy cùng máy hoặc kẻ trộm tệp tin DB.
*   **Đặc điểm**:
    *   **Không ghi Plaintext xuống DB**: Toàn bộ nội dung ký ức (`content`) bắt buộc phải đi qua lớp mã hóa đối xứng **AES-256-GCM** trước khi lưu vào SQLite.
    *   **Vô hiệu hóa Plaintext FTS5**: Chặn hoàn toàn việc đẩy văn bản rõ vào chỉ mục tìm kiếm FTS5 của SQLite.
    *   **Không log nội dung nhạy cảm**: Toàn bộ log vận hành và audit log không bao giờ in nội dung thô của ký ức hoặc các khóa mật mã.
    *   **Mã hóa đầu ra mặc định**: Mọi hoạt động sao lưu (`backup`) hoặc xuất bản dữ liệu (`export`) đều bắt buộc phải mã hóa bằng mật khẩu người dùng thông qua cơ chế PBKDF2-HMAC-SHA256.

---

## 3. Các Động Cơ Bảo Vệ Quyền Riêng Tư Toán Học (Mathematical Privacy Engines)

TruthKeep là hệ thống bộ nhớ AI đầu tiên tích hợp các thuật toán toán học tiên tiến để chứng minh khả năng bảo vệ quyền riêng tư bằng thực nghiệm:

### 3.1. Bảo mật vi sai trên Embeddings (Metric Differential Privacy)
*   **Thuật toán**: CMAG Gaussian Noise (2025) đạt chuẩn $(\varepsilon, \delta)$-Differential Privacy (Dwork 2006).
*   **Cách hoạt động**: Khi một vector nhúng (embedding) của ký ức được tạo ra, hệ thống tự động sinh nhiễu Gaussian chuẩn thông qua thuật toán Box-Muller và bơm vào vector. Vector sau đó được chuẩn hóa L2 về mặt cầu đơn vị để giữ nguyên hình học Poincaré.
*   **Mục đích**: Toán học chứng minh kẻ tấn công không thể đảo ngược (Reverse Engineering) vector nhúng để khôi phục lại văn bản thô ban đầu, đồng thời ngăn chặn các cuộc tấn công suy luận thành viên (Membership Inference Attack).

### 3.2. Lá chắn truy cập Bayesian (Bayesian Differential Privacy Shield)
*   **Thuật toán**: Phân phối Laplace + Định lý Bayes (1763).
*   **Cách hoạt động**: Hệ thống theo dõi tần suất và mức độ tương đồng của các truy vấn tìm kiếm theo từng scope. Khi phát hiện các mẫu truy vấn đáng ngờ (Probe Intensity cao), hệ thống tự động tính toán nguy cơ rò rỉ thông tin bằng xác suất Bayes và bơm nhiễu Laplace để làm mờ điểm số hoặc suppress kết quả hoàn toàn.
*   **Mục đích**: Chặn đứng các Agent hoặc Extension độc hại liên tục truy vấn quanh co để dò la các thông tin bí mật trong bộ nhớ dài hạn.

---

## 4. Xử lý Metadata & Nhật ký Kiểm toán (Metadata & Auditing)

1.  **Metadata Redaction**: Khi xuất báo cáo vận hành hoặc giải thích vì sao (`why-not`), hệ thống tự động ẩn danh hoặc lược bỏ các dữ liệu thô nhạy cảm nếu chưa được người dùng cấp quyền rõ ràng.
2.  **Scope Isolation**: Dữ liệu ký ức giữa các scope khác nhau (ví dụ: `project-A` và `project-B`) được cách ly vật lý và logic hoàn toàn ở mức SQL. Tuyệt đối không bao giờ xảy ra tình trạng rò rỉ dữ liệu chéo scope (Zero Cross-Scope Leak).
