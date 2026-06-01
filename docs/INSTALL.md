# 🛠️ Cài đặt & Cấu hình Hệ thống — TruthKeep Memory

Đặc tả yêu cầu môi trường, ma trận kiểm thử hệ điều hành, và hướng dẫn cài đặt nâng cao cho **TruthKeep Memory**.

---

## 📋 Yêu cầu Hệ thống

### 1. Phiên bản Python hỗ trợ
*   **Hỗ trợ chính thức (Production Ready)**: `Python 3.11` và `Python 3.12`.
*   **Hỗ trợ thử nghiệm (Experimental)**: `Python 3.10` (hoạt động tốt với các tính năng cục bộ, tuy nhiên CI/CD pipeline ưu tiên các phiên bản `>=3.11` để tối ưu hiệu năng).

### 2. Ma trận Hệ điều hành đã Kiểm thử (Tested OS Matrix)

| Hệ điều hành | Trạng thái | Ghi chú |
|---|---|---|
| **Windows 11 / 10** | Đã kiểm thử đầy đủ | Hoạt động hoàn hảo trong PowerShell/CMD |
| **Ubuntu Linux 20.04+** | Đã kiểm thử đầy đủ | Khởi chạy qua stdio an toàn, tích hợp CI cực kỳ tốt |
| **macOS 13+ (Ventura/Sonoma)** | Đã kiểm thử | Tương thích hoàn toàn kiến trúc Intel và Apple Silicon (M1/M2/M3) |

---

## ⚙️ Hướng dẫn Cài đặt Nâng cao

### Cách 1: Cài đặt Gói Cục bộ (Editable Mode)
Khuyên dùng cho các nhà phát triển muốn tích hợp hoặc chỉnh sửa mã nguồn:
```bash
git clone https://github.com/your-repo/truthkeep-memory.git
cd truthkeep-memory

# Tạo môi trường ảo (Virtual Environment)
python -m venv .venv
source .venv/bin/activate  # Trên Linux/macOS
.venv\Scripts\activate     # Trên Windows

# Cài đặt gói dạng editable kèm dependencies
pip install -e .
```

### Hướng dẫn sử dụng `uv` (Tối ưu hóa tốc độ cài đặt)
Nếu bạn có công cụ `uv` của Astral, việc cài đặt sẽ nhanh hơn gấp 10 lần:
```bash
uv pip install -e .
```

---

## 🔒 Kiểm tra Tính Toàn vẹn Bảo mật (Security & Dependencies verification)

Sau khi cài đặt, bạn nên chạy toàn bộ test suite cục bộ để đảm bảo các thư viện mã hóa toán học hoạt động chính xác trên phần cứng của bạn:

```bash
# Chạy toàn bộ 196+ test cases
python -m pytest tests -v
```

Nếu toàn bộ test suite trả về kết quả `PASSED`, môi trường của bạn đã sẵn sàng hoàn toàn cho việc lưu trữ nhận thức an toàn.
