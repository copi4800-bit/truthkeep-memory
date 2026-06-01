# Giới Hạn Bảo Mật Thực Tế: TruthKeep Security Limitations

> [!WARNING]
> TruthKeep Memory là một động cơ bộ nhớ AI thực nghiệm ưu tiên cục bộ (local-first). Mặc dù tích hợp nhiều lớp toán học và mật mã học nâng cao, hệ thống có những giới hạn vật lý và mật mã cụ thể cần được document rõ ràng để tránh bị hiểu nhầm hoặc lạm dụng trong các môi trường sản xuất có yêu cầu an ninh tối cao (military/high-finance) mà không có biện pháp phòng ngừa.

---

## 1. Giới hạn trong 3 Chế độ Bảo mật (Security Modes)

### 1.1. `demo` Mode
*   **Mô phỏng Mật mã (Simulators)**: Các thuật toán FHE, ZKP, và PQC trong chế độ này hoàn toàn là **mô phỏng toán học thuần túy (simulators)** để tối ưu hóa hiệu năng trên các máy cục bộ yếu hoặc chạy thử nghiệm nhanh.
*   **Rủi ro**: Không có khả năng chống lại kẻ tấn công chủ động có quyền truy cập vật lý hoặc quyền đọc file SQLite. Tuyệt đối không dùng chế độ này cho dữ liệu nhạy cảm thực tế.

### 1.2. `local` Mode
*   **SQLite Plaintext**: Mặc định, SQLite lưu trữ tệp tin `.db` ở dạng plaintext. Dù nội dung ký ức được đóng dấu (Content Seal) để chống sửa đổi trái phép, cấu trúc cơ sở dữ liệu và các siêu dữ liệu (metadata) vẫn có thể bị đọc bởi các tiến trình khác trên cùng hệ điều hành.
*   **Biện pháp khuyến nghị**: Sử dụng mã hóa đĩa vật lý (BitLocker trên Windows, FileVault trên macOS) hoặc chuyển sang `hardened` mode để mã hóa trực tiếp từng bản ghi ở mức ứng dụng.

### 1.3. `hardened` Mode
*   **Trạng thái Scaffold/Contract**: Trong phiên bản hiện tại, `hardened` mode chủ yếu đóng vai trò là một **khung kiến trúc định hướng (contract/scaffold)**. Các cấu trúc lớp và cấu hình đã sẵn sàng, nhưng cơ chế mật mã thực tế bên dưới vẫn đang sử dụng các thuật toán classical nhúng (như 512-bit RSA, SQLite FTS5 index plaintext).
*   **Các bước cần thiết để hoàn thiện**: Để nâng cấp chế độ này lên production-grade thực thụ, cần:
    1. Tăng kích thước khóa lên 2048/4096-bit hoặc dùng ECDH/Ed25519 thông qua thư viện native `cryptography`.
    2. Chuyển đổi PRNG sang CSPRNG thực sự bằng thư viện `secrets` hoặc `os.urandom`.
    3. Tích hợp mã hóa FTS5 index bằng SQLCipher hoặc các giải pháp tương đương.
    4. Quản lý Master Key qua native OS Keychain thay vì lưu trữ dạng hex trong SQLite.

---

## 2. Rủi ro PRNG (`random` vs `secrets`) trên thiết bị nhúng

*   **Vấn đề**: Để tương thích với các môi trường nhúng và MicroPython (nơi thư viện mã nguồn tiêu chuẩn `secrets` và `/dev/urandom` có thể không khả dụng hoặc thiếu phần cứng entropy nguồn), các bộ sinh số ngẫu nhiên của TruthKeep có thể tự động fallback về thư viện `random` chuẩn của Python.
*   **Rủi ro mật mã**: Thư viện `random` của Python sử dụng thuật toán **Mersenne Twister**. Đây là bộ sinh số ngẫu nhiên giả ngẫu nhiên (PRNG) tuần hoàn, **không an toàn về mặt mật mã học (not cryptographically secure)**. Kẻ tấn công quan sát được khoảng 624 số nguyên liên tiếp xuất ra từ Mersenne Twister có thể dự đoán chính xác toàn bộ các số ngẫu nhiên tiếp theo, từ đó bẻ gãy khóa RSA hoặc ZKP challenge.
*   **Khuyến nghị an toàn**: Khi chạy TruthKeep trên máy chủ hoặc PC cá nhân, luôn đảm bảo biến cấu hình bảo mật trỏ về `secrets` (sử dụng entropy của hệ điều hành) để sinh khóa.

---

## 3. Giới hạn của thuật toán RSA-512 thực nghiệm

*   **Vấn đề**: Ở chế độ nhúng/demo mặc định, TruthKeep có thể sinh khóa RSA với kích thước chỉ **512-bit** để đảm bảo thời gian sinh khóa cực nhanh (<50ms) trên các máy cấu hình thấp.
*   **Rủi ro**: Khóa RSA-512 đã bị bẻ gãy từ năm 1999 bằng phương pháp sàng số trường tổng quát (General Number Field Sieve). Một máy tính cá nhân hiện đại ngày nay có thể phân tích nhân tử một khóa RSA-512 chỉ trong vòng vài giờ đồng hồ.
*   **Khuyến nghị**: Đối với bất kỳ triển khai thực tế nào liên quan đến thông tin bảo mật, hãy định cấu hình tham số `bit_size` của `EuclidKeyForge` tối thiểu là **2048-bit** hoặc **4096-bit** để đạt mức độ bảo mật cao theo tiêu chuẩn hiện tại.

---

## 4. Tổng kết khuyến nghị triển khai (Deployment Architecture)

Mô hình triển khai an toàn nhất cho hệ thống có sự tham gia của các thiết bị nhúng (như robot Mimi sử dụng ESP32):

```text
┌────────────────────────┐            Secure Channel            ┌────────────────────────┐
│  Client (ESP32 Body)   │◄────────────────────────────────────►│  Local Sidecar Engine  │
│                        │       (PQC-style / AES Tunnel)       │  (Running on PC/Pi)   │
│ - Chỉ gửi text/audio   │                                      │ - Chạy hardened mode   │
│ - Nhận lệnh thực thi   │                                      │ - Quản lý OS Keychain  │
└────────────────────────┘                                      └────────────────────────┘
```

*   **Không chạy** toàn bộ engine TruthKeep trên chip nhúng ESP32.
*   **Luôn chạy** TruthKeep cục bộ trên một máy tính cá nhân (PC), Raspberry Pi, hoặc server cục bộ trong mạng LAN được bảo vệ bởi tường lửa.
