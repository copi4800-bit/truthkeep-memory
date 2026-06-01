# 🔍 Sổ Tay Chuẩn Bị Kiểm Định Bảo Mật: TruthKeep Audit Prep Guide

Tài liệu này được biên soạn để hỗ trợ các kiểm định viên độc lập bên thứ ba (Third-party Security Auditors) nhanh chóng nắm bắt cấu trúc an ninh, thiết lập môi trường thử nghiệm và thực thi các công cụ kiểm toán mã nguồn trên **TruthKeep Memory**.

---

## 1. Bản Đồ Mã Nguồn Bảo Mật (Security Source Map)

Toàn bộ các mô-đun an ninh, mã hóa và bảo vệ quyền riêng tư được tập trung tại thư mục [aegis_py/security/](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/):

| Tệp tin (File) | Vai trò trong hệ thống | Thuật toán cốt lõi |
| :--- | :--- | :--- |
| [`__init__.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/__init__.py) | Cổng xuất bản các API bảo mật của hệ thống | Quản lý exports |
| [`config.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/config.py) | Định cấu hình các mức bảo mật (`demo`, `local`, `hardened`) | Quản lý chế độ bảo mật |
| [`crypto_math.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/crypto_math.py) | Thư viện toán học mật mã thuần Python | Euler-Fermat, Extended Euclid, CRT Acceleration, Bayes |
| [`key_manager.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/key_manager.py) | Quản lý vòng đời khóa mật mã theo từng scope | Lưu trữ SQLite & Caching |
| [`memory_vault.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/memory_vault.py) | Lớp mã hóa trong suốt cho dữ liệu ký ức SQLite | Encrypt-on-write, Decrypt-on-read |
| [`privacy_guard.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/privacy_guard.py) | Các lá chắn bảo mật vi sai và phát hiện tiêm nhiễm | Laplace & Gaussian noise, Shannon Entropy, Paillier FHE |
| [`aes_gcm.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/aes_gcm.py) | Lõi mã hóa đối xứng AES-256-GCM thuần Python | PBKDF2-HMAC-SHA256, GCM Tamper Verification |
| [`signed_audit.py`](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/signed_audit.py) | Cơ chế ký số audit log bảo vệ chống chỉnh sửa ngược | SHA-256 HMAC Chaining |

---

## 2. Thiết Lập Môi Trường Kiểm Toán (Audit Environment Setup)

TruthKeep được thiết kế với **Zero External Dependencies** (Không phụ thuộc thư viện ngoài) cho toàn bộ lõi thuật toán mật mã học. Bạn chỉ cần cài đặt Python 3.12+ và các công cụ phát triển/kiểm thử tiêu chuẩn.

### 2.1. Cài đặt các gói kiểm thử và quét tĩnh
```bash
# Cài đặt pytest cho các ca kiểm thử
pip install pytest pytest-asyncio anyio

# Cài đặt các công cụ quét bảo mật tĩnh (SAST)
pip install bandit pip-audit ruff
```

---

## 3. Quy Trình Chạy Thực Nghiệm Kiểm Thử Bảo Mật (Security Test Suite)

Chúng tôi đã xây dựng một bộ kiểm thử bảo mật chuyên biệt tại thư mục `tests/security/` (hoặc trực tiếp tại `tests/` của dự án). Các ca kiểm thử này giả lập trực tiếp các kịch bản tấn công thực tế:

### 3.1. Chạy toàn bộ các bài test mật mã và an ninh
```bash
# Chạy bộ test kiểm thử toán học mật mã và lá chắn vi sai
python -m pytest tests/test_math_harmony.py -v

# Chạy bộ test kiểm thử an ninh chuyên sâu (AES-GCM, Entropy, Paillier)
python -m pytest tests/test_secure_memory_security.py -v
```

### 3.2. Các Kịch bản Kiểm tra chính trong Test Suite
1.  **Tamper Detection Test**: Sửa đổi ngẫu nhiên 1 byte trong chuỗi bản mã AES-256-GCM và xác nhận hệ thống chặn đứng quá trình giải mã, báo lỗi giả mạo thành công.
2.  **Shannon Entropy Poison Test**: Bơm một chuỗi lặp ký tự dài (tương đương Prompt Injection lặp chuỗi) và xác nhận hệ thống phát hiện sự sụt giảm Entropy cực mạnh dưới mức sàn bảo mật.
3.  **Bayesian Privacy Test**: Giả lập cuộc tấn công Membership Inference bằng cách truy vấn liên tục các từ khóa nhạy cảm giống nhau và kiểm chứng relevance score bị bơm nhiễu Laplace thích hợp để che giấu thông tin.

---

## 4. Báo Cáo Quét Bảo Mật Tĩnh (SAST & Vulnerability Scans)

Trước khi thực hiện kiểm định thủ công, kiểm định viên có thể tự động chạy các công cụ quét tĩnh sau để kiểm chứng chất lượng mã nguồn:

### 4.1. Quét lỗ hổng bảo mật mã nguồn bằng Bandit
Bandit là công cụ phân tích tĩnh chuyên sâu để phát hiện các vấn đề an ninh phổ biến trong mã nguồn Python:
```bash
bandit -r aegis_py/ -x aegis_py/v10/
```
*(Lưu ý: Một số cảnh báo về việc sử dụng thư viện `random` chuẩn của Python là hoàn toàn bình thường do cơ chế tự động fallback trên các thiết bị nhúng không có entropy nguồn. Kiểm định viên nên tập trung vào chế độ `hardened` mode nơi `secrets` hoặc `/dev/urandom` được bắt buộc kích hoạt).*

### 4.2. Kiểm tra chuỗi cung ứng bằng pip-audit
Đảm bảo các thư viện phát triển (nằm trong `requirements.txt` hoặc `pyproject.toml`) không chứa bất kỳ lỗ hổng bảo mật nào đã được công bố trong cơ sở dữ liệu CVE quốc gia:
```bash
pip-audit -r requirements.txt
```

---

## 5. Các Giới Hạn Cần Lưu Ý Của Kiểm Định Viên
*   **Pure-Python Cryptography**: Các thuật toán mật mã đối xứng và bất đối xứng đều được tự viết thủ công bằng Python thuần túy nhằm phục vụ mục đích học thuật, tự chứng minh và tương thích tối đa với các thiết bị nhúng cấu hình thấp. Trong triển khai sản xuất thực tế quy mô lớn, chúng tôi khuyến khích liên kết với các thư viện native liên kết với phần cứng (như OpenSSL thông qua thư viện `cryptography` của Python) để tối ưu hiệu năng và chống lại các cuộc tấn công side-channel.
*   **FHE & ZKP Simulators**: Các cơ chế Fully Homomorphic Encryption (FHE) và Zero-Knowledge Proofs (ZKP) phức tạp hiện đang được vận hành dưới dạng các lớp mô phỏng toán học chính xác (Simulators) trong chế độ `local` để bảo toàn hiệu năng CPU cục bộ.
