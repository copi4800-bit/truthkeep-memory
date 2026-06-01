# 💾 Hướng Dẫn Sao Lưu Và Phục Hồi An Toàn: TruthKeep Backup & Restore

Tài liệu này hướng dẫn cách thức thực hiện sao lưu (Backup) và phục hồi (Restore) dữ liệu ký ức an toàn, bảo vệ chống giả mạo và rò rỉ thông tin trong **TruthKeep Memory**.

---

## 1. Kiến Trúc Sao Lưu (Backup Architecture)

Hệ thống cung cấp cơ chế sao lưu cục bộ thông qua `BackupSurface` và CLI. Các tệp tin sao lưu được thiết kế để dễ dàng di chuyển giữa các máy cá nhân của người dùng mà vẫn đảm bảo tính an toàn tối đa.

### 1.1. Định dạng Tệp tin Sao lưu
Tệp sao lưu của TruthKeep là một gói đóng gói nén chứa các thành phần sau:
*   `database.db`: Bản sao lưu vật lý của tệp SQLite `memory_aegis.db` (được khóa và tối ưu bằng câu lệnh `VACUUM`).
*   `metadata.json`: Chứa các thông tin về phiên bản TruthKeep, thời gian tạo, số lượng bản ghi, và checksum SHA-256 của tệp DB.
*   `keys_manifest.json`: (Chỉ có trong Standard Mode) Lưu trữ các khóa RSA công khai/riêng tư tương ứng với từng scope.

---

## 2. Các Chế Độ Sao Lưu Bảo Mật (Secure Backup Modes)

Cơ chế sao lưu tự động điều chỉnh theo cấp độ bảo mật đang được kích hoạt trong hệ thống:

### 2.1. Standard Backup (Sao lưu tiêu chuẩn)
*   **Mô tả**: Tệp cơ sở dữ liệu được nén trực tiếp vào tệp lưu trữ.
*   **Đặc điểm**:
    *   Tệp nén thô, không mã hóa mật khẩu ở mức tệp lưu trữ.
    *   Thích hợp khi đĩa cứng của người dùng đã được bảo vệ bằng các lớp mã hóa đĩa vật lý (BitLocker, FileVault).

### 2.2. Encrypted Backup (Sao lưu mã hóa - Bắt buộc trong Strict Mode)
*   **Mô tả**: Toàn bộ gói sao lưu được mã hóa đối xứng trước khi ghi xuống đĩa bằng mật khẩu/passphrase của người dùng.
*   **Thuật toán mã hóa**:
    1.  **Key Derivation**: Sử dụng **PBKDF2-HMAC-SHA256** với **100,000 iterations** và một chuỗi salt ngẫu nhiên 16 bytes để biến đổi passphrase của người dùng thành khóa đối xứng 32 bytes (256-bit AES key).
    2.  **Encryption**: Mã hóa toàn bộ tệp nén bằng **AES-256-GCM**.
    3.  **Output Format**: Tệp đầu ra có định dạng `.tkbak` chứa: `salt (16B) + nonce (12B) + GCM tag (16B) + encrypted_zip_data`.
*   **Phòng vệ**: Tệp sao lưu `.tkbak` có thể được lưu giữ an toàn trên các đám mây lưu trữ cá nhân (Google Drive, Dropbox) mà không sợ bên thứ ba hoặc nhà cung cấp dịch vụ đám mây đọc được nội dung ký ức bên trong.

---

## 3. Quy Trình Phục Hồi An Toàn (Secure Restore Process)

Khi người dùng thực hiện khôi phục dữ liệu từ một tệp sao lưu:

### 3.1. Xác thực tính toàn vẹn (Integrity Verification)
1.  **Kiểm tra GCM Tag**: Nếu tệp là bản sao lưu mã hóa (`.tkbak`), hệ thống sẽ thực hiện giải mã và kiểm tra tag xác thực **AES-256-GCM** trước khi giải nén. Nếu phát hiện tệp bị chỉnh sửa hoặc sai mật khẩu, tiến trình khôi phục bị chặn đứng lập tức để tránh tấn công chèn mã độc hoặc giải mã sai cấu trúc.
2.  **Kiểm tra Checksum SHA-256**: Hệ thống tính toán lại hash SHA-256 của tệp SQLite được giải nén và so sánh với giá trị băm được lưu trong `metadata.json` để đảm bảo không xảy ra đứt gãy hoặc lỗi dữ liệu trong quá trình ghi đĩa.

### 3.2. Kiểm định Invariants sau khôi phục
Sau khi tệp cơ sở dữ liệu được khôi phục vật lý vào thư mục vận hành, hệ thống tự động khởi chạy bộ kiểm định invariants nền (`truthkeep graph-invariants`) để quét toàn bộ đồ thị tri thức:
*   Đảm bảo không có liên kết chéo scope (No cross-scope link).
*   Đảm bảo không tồn tại vòng lặp thay thế vô hạn (No supersedes cycle).
*   Nếu phát hiện bất kỳ lỗi invariants nào, hệ thống sẽ từ chối áp dụng tệp cơ sở dữ liệu mới và tự động rollback về phiên bản CSDL hoạt động an toàn trước đó.

---

## 4. Các Lệnh CLI Vận Hành Nhanh

*   **Tạo sao lưu tiêu chuẩn**:
    ```bash
    truthkeep backup create --output ./backup_today.zip
    ```
*   **Tạo sao lưu mã hóa**:
    ```bash
    truthkeep backup create --encrypt --passphrase "my-secure-passphrase" --output ./backup_secure.tkbak
    ```
*   **Khôi phục dữ liệu**:
    ```bash
    truthkeep backup restore --file ./backup_secure.tkbak --passphrase "my-secure-passphrase"
    ```
