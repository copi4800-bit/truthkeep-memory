# 🔄 Migration Notes — Upgrading to v10.7-secure-mcp-stdio-dev-beta

Hướng dẫn chi tiết di chuyển dữ liệu và cập nhật cấu trúc hệ thống từ các phiên bản cũ lên **TruthKeep Memory v10.7-secure-mcp-stdio-dev-beta**.

---

## 🚨 Thay đổi Lớn nhất: Loại bỏ Hoàn toàn HTTP Daemon & Cổng mạng (Zero Open Ports)

Kể từ phiên bản **v10.7**, TruthKeep Memory chuyển dịch hoàn toàn sang mô hình **Secure MCP Stdio-Only**.
*   **Không còn tiến trình chạy nền liên tục (No Background Daemon)**: Toàn bộ thư mục `aegis_py/daemon` và các lệnh `truthkeep start / stop / restart` đã bị xóa bỏ hoàn toàn.
*   **Không mở cổng mạng (Zero Open Ports)**: Hệ thống không còn lắng nghe trên bất kỳ cổng TCP/UDP nào (như `8765`), loại bỏ hoàn toàn bề mặt tấn công mạng (Zero Attack Surface).
*   **Tự động quản lý vòng đời (Auto-Launch)**: Máy chủ MCP chạy hoàn toàn qua luồng giao tiếp tiêu chuẩn (`stdin` / `stdout`), tự động bật/tắt an toàn theo vòng đời của ứng dụng Host như Cursor, Claude Desktop hoặc Codex App.

---

## 🚀 Các bước Cập nhật nhanh

### Bước 1: Dừng và Xóa bỏ các Tiến trình Daemon cũ
Nếu máy của bạn đang chạy các daemon phiên bản cũ chạy ngầm, hãy tắt chúng đi:
```bash
# Trên Windows (Task Manager hoặc PowerShell):
Stop-Process -Name python -Force # Hoặc tắt thủ công tiến trình python chạy nền của truthkeep

# Trên Linux/macOS:
pkill -f "truthkeep.mcp"
```

### Bước 2: Pull và Cập nhật Gói
Cập nhật gói mã nguồn mới nhất:
```bash
git pull origin main
pip install -e .
```

### Bước 3: Di trú Cơ sở dữ liệu (Migrations) và Setup
Thiết lập cơ sở dữ liệu SQLite cục bộ an toàn:
```bash
truthkeep setup
```

### Bước 4: Kiểm thử kết nối MCP Stdio cục bộ
Để kiểm chứng tính tương thích của luồng stdio JSON-RPC trên máy của bạn mà không cần mở bất kỳ cổng mạng nào, hãy chạy lệnh probe:
```bash
truthkeep mcp-probe
```

---

## ⚠️ Những Lưu ý Quan trọng khi nâng cấp

1.  **Cập nhật cấu hình của Host**:
    *   Hãy đảm bảo các tệp cấu hình MCP của các Host (Cursor, Claude Desktop, Codex App) được cập nhật theo mẫu mới trong thư mục `examples/`. Các cấu hình này khởi chạy trực tiếp thông qua lệnh `python -m truthkeep.mcp` thay vì gọi REST API như trước.
2.  **Định tuyến Direct SQLite**:
    *   Các lệnh CLI như `truthkeep status`, `truthkeep dashboard`, và `truthkeep doctor` giờ đây sẽ truy vấn trực tiếp vào tệp SQLite local rồi thoát ngay lập tức, không tạo bất kỳ tiến trình nền nào bị treo.
