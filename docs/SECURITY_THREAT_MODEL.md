# 🛡️ Mô Hình Hiểm Họa Bảo Mật: TruthKeep Security Threat Model

Tài liệu này xác định ranh giới bảo mật, tài sản cần bảo vệ, các mối đe dọa tiềm tàng và các cơ chế phòng vệ của hệ thống bộ nhớ AI cục bộ **TruthKeep Memory**. Đây là tài liệu nền tảng phục vụ cho giai đoạn thiết kế an ninh doanh nghiệp (Enterprise Security) và chuẩn bị kiểm định độc lập (Third-party Security Audit).

---

## 1. Mục Tiêu & Ranh Giới Bảo Mật (Security Boundaries)

TruthKeep Memory được thiết kế theo triết lý **Cục bộ trước tiên (Local-first, Edge-centric)**. Hệ thống giả định rằng dữ liệu nhạy cảm chỉ nên lưu trữ và xử lý trực tiếp trên thiết bị của người dùng hoặc trong mạng nội bộ an toàn, loại bỏ hoàn toàn nguy cơ rò rỉ qua đám mây của bên thứ ba.

### 1.1. Tài sản cần bảo vệ (What TruthKeep Protects)

1.  **Nội dung Ký ức (Memory Content)**: Toàn bộ văn bản gốc của các cuộc hội thoại, các sự kiện, chỉ thị và sở thích của người dùng được AI học và lưu trữ.
2.  **Liên kết Đồ thị (Graph Links)**: Cấu trúc liên kết ngữ nghĩa giữa các ký ức (`supersedes`, `contradicts`, `evidence_for`, v.v.). Việc lộ đồ thị liên kết có thể giúp kẻ tấn công suy đoán ra mối quan hệ giữa các thực thể nhạy cảm.
3.  **Lịch sử Hiệu chỉnh (Correction History)**: Nhật ký ghi nhận các thay đổi tri thức, các phiên bản cũ bị thay thế (`superseded`).
4.  **Nhật ký Why-Not / Audit Logs**: Các giải thích lý do vì sao một ký ức bị loại bỏ hoặc hạ điểm tin cậy.
5.  **Cơ sở Dữ liệu SQLite (`memory_aegis.db`)**: Tệp lưu trữ vật lý chứa toàn bộ bảng dữ liệu, vector embeddings và khóa mật mã.
6.  **Tệp sao lưu & Xuất bản (Backup / Export Files)**: Các tệp lưu trữ được kết xuất từ hệ thống để dự phòng hoặc đồng bộ hóa.

### 1.2. Ranh giới hệ thống (System Boundaries)

```text
  ┌──────────────────────────────────────────────────────────────┐
  │                   Môi trường người dùng (PC)                 │
  │                                                              │
  │  ┌──────────────────┐  IPC (stdio)  ┌─────────────────────┐  │
  │  │  Client App      │◄─────────────►│ TruthKeep Core      │  │
  │  │  (Cursor/Claude) │               │ - Memory Engine     │  │
  │  └──────────────────┘               │ - Privacy Guard     │  │
  │                                     │ - Cryptography      │  │
  │                                     └──────────┬──────────┘  │
  │                                                │ SQL/Local   │
  │                                                ▼             │
  │                                     ┌─────────────────────┐  │
  │                                     │  SQLite DB File     │  │
  │                                     │ (memory_aegis.db)   │  │
  │                                     └─────────────────────┘  │
  └──────────────────────────────────────────────────────────────┘
```

---

## 2. Mô Hình Kẻ Tấn Công (Attacker Profiles)

Chúng ta phân loại kẻ tấn công dựa trên động cơ, tài nguyên và khả năng tiếp cận hệ thống:

| Kẻ tấn công (Attacker) | Kênh tấn công (Vector) | Khả năng | Mục tiêu |
| :--- | :--- | :--- | :--- |
| **Ứng dụng độc hại cục bộ** *(Local Malicious App)* | Chạy song song trên OS của user mà không có quyền Admin/Root | Đọc các tệp tin trong thư mục AppData, quét bộ nhớ RAM plaintext, hoặc nghe trộm IPC stdio | Lấy cắp tệp tin SQLite `memory_aegis.db` hoặc nghe trộm dữ liệu trao đổi qua MCP |
| **Người đọc trộm tệp tin** *(Physical/Unauthorized File Reader)* | Tiếp cận vật lý hoặc qua mạng LAN chia sẻ tệp để copy tệp DB | Sao chép tệp `memory_aegis.db` hoặc các tệp export/backup không được mã hóa | Đọc trực tiếp nội dung ký ức trong SQLite hoặc FTS5 index |
| **Extension/Agent không tin cậy** *(Untrusted Agent/Plugin)* | Chạy trực tiếp trong IDE (Cursor, VS Code) hoặc chatbot client | Thực hiện hàng loạt truy vấn lặp đi lặp lại để thăm dò bộ nhớ qua kênh tìm kiếm | **Membership Inference Attack**: Xác định xem một từ khóa/thông tin nhạy cảm cụ thể có nằm trong DB của user không |
| **Kẻ tiêm nhiễm dữ liệu** *(Data Poisoning / Prompt Injector)* | Tiêm mã độc thông qua các đoạn chat đầu vào hoặc tài liệu nạp vào AI | Gửi các thông tin lặp đi lặp lại hoặc các câu lệnh ghi đè hệ thống (jailbreak prompts) | **Data Poisoning & Prompt Injection**: Gây nhiễu cấu trúc phân phối xác suất thống kê để tràn bộ đệm hoặc đầu độc bộ nhớ dài hạn |
| **Dependency độc hại** *(Compromised Dependency)* | Chuỗi cung ứng phần mềm (Supply Chain Attack) | Tiêm mã độc vào các gói Python cài đặt qua pip | Đánh cắp khóa mật mã hoặc dữ liệu thô gửi về máy chủ bên ngoài |

---

## 3. Ngoài Phạm Vi Bảo Vệ (Out of Scope / Non-Goals)

TruthKeep **không** được thiết kế để tự vệ trước các trường hợp sau (đây là trách nhiệm của hệ điều hành và người dùng):

1.  **Thiết bị đã bị kiểm soát hoàn toàn (Rooted/Admin Compromised)**: Nếu kẻ tấn công có quyền Root/Administrator hoặc đã cài đặt Keylogger/Trojan ở mức kernel, chúng có thể đọc trực tiếp khóa mật mã trong RAM hoặc can thiệp vào tiến trình thực thi.
2.  **Sự sơ suất của người dùng (User Negligence)**: Người dùng tự public tệp cơ sở dữ liệu `memory_aegis.db` lên các kho lưu trữ công khai (GitHub, Google Drive công cộng) hoặc chia sẻ passphrase/master key cho người khác.
3.  **Tấn công kênh bên vật lý (Hardware Side-channel)**: Đo đạc bức xạ điện từ, mức tiêu thụ năng lượng hoặc thời gian xử lý phần cứng để suy đoán khóa.

---

## 4. Các Biện Pháp Phòng Vệ Kỹ Thuật (Mitigation Matrix)

Để giải quyết triệt để mô hình hiểm họa trên, TruthKeep áp dụng ma trận phòng vệ đa lớp:

### 4.1. Chống rò rỉ dữ liệu khi tệp DB bị đánh cắp (At-Rest Protection)
*   **Cơ chế**: Mã hóa đối xứng ứng dụng sử dụng **AES-256-GCM** thông qua `AESGCMEngine` khi cấu hình `TK_PRIVACY_MODE=strict` hoặc `TK_SECURITY_MODE=hardened`.
*   **Phòng vệ**: Kẻ tấn công copy tệp `memory_aegis.db` chỉ thấy các khối dữ liệu đã được mã hóa ngẫu nhiên và mã xác thực tag. Mọi hành vi sửa đổi trực tiếp vào tệp DB sẽ bị phát hiện ngay lập tức (Tamper Detection) thông qua tag kiểm định và giải mã sẽ thất bại hoàn toàn.

### 4.2. Chống Membership Inference Attacks (In-Search Protection)
*   **Cơ chế**: Sử dụng bộ lọc bảo mật vi sai Bayesian `DifferentialPrivacyShield` kết hợp **Metric Differential Privacy (CMAG 2025)** trên Vector Embeddings.
*   **Phòng vệ**: Khi phát hiện tần suất hoặc cường độ truy vấn đáng ngờ (Probe Intensity vượt ngưỡng), hệ thống tự động chèn nhiễu Laplace/Gaussian vào điểm tương đồng hoặc chặn hoàn toàn các kết quả nhạy cảm để ngăn kẻ tấn công tái dựng lại thông tin gốc thông qua các truy vấn quanh co.

### 4.3. Chống tiêm nhiễm dữ liệu (In-Process Poisoning Protection)
*   **Cơ chế**: Đo đạc độ hỗn loạn thông tin thời gian thực qua **Shannon Entropy Anomaly Detector** (`ShannonEntropyPoisonDetector`).
*   **Phòng vệ**: Phát hiện ngay lập tức các cuộc tấn công tiêm nhiễm dữ liệu dạng lặp chuỗi hoặc prompt injection tràn bộ đệm (khiến Entropy sụt giảm nghiêm trọng). Các vector độc hại sẽ bị cách ly hoặc gắn nhãn `reconcile_required` trước khi được ghi nhận vào bộ nhớ dài hạn.

### 4.4. Bảo vệ dữ liệu tính toán phía máy chủ (Zero-Knowledge Similarity Search)
*   **Cơ chế**: Hệ mật mã đồng cấu **Paillier Cryptosystem** (`PaillierPartiallyHomomorphicEngine`).
*   **Phòng vệ**: Cho phép thực hiện các phép toán nhân ma trận và tính toán khoảng cách (Vector Similarity Search) trên các vector đã mã hóa mà máy chủ trung gian hoàn toàn không biết giá trị thực tế của vector.

---

## 5. Kế Hoạch Đánh Giá & Cập Nhật (Assessment & Maintenance)

1.  **Cập nhật Mô hình Hiệu chỉnh**: Tài liệu Threat Model này sẽ được rà soát định kỳ sau mỗi bản phát hành lớn (Major Release) hoặc khi có thay đổi quan trọng trong kiến trúc lưu trữ dữ liệu.
2.  **Kiểm tra Thâm nhập (Penetration Testing)**: Thực thi định kỳ các security tests độc lập trong thư mục `tests/security/` để đảm bảo không xảy ra hồi quy bảo mật (Security Regressions).
