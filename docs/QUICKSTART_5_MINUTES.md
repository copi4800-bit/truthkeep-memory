# ⚡ Quickstart 5 Minutes — TruthKeep Memory

Chào mừng bạn đến với **TruthKeep Memory**! Hướng dẫn siêu ngắn này giúp bạn cài đặt, khởi chạy, và kiểm chứng động cơ bộ nhớ AI cục bộ hoạt động hoàn hảo trong vòng đúng 5 phút.

---

## 📋 Yêu cầu Hệ thống
- **Hỗ trợ Chính thức**: Python 3.11 - 3.12 (Được đảm bảo và kiểm thử tự động đầy đủ trong CI matrix).
- **Thử nghiệm (Experimental)**: Python 3.10 (Chỉ chạy khi ma trận CI vượt qua hoặc tự kiểm thử thủ công qua pytest).

---

## 🚀 4 Bước Vận Hành Ngay

### Bước 1: Cài đặt Gói phát triển
Mở Terminal tại thư mục dự án và chạy:
```bash
# Cài đặt dạng editable package
pip install -e .
```

### Bước 2: Khởi tạo Cơ sở Dữ liệu
Thiết lập SQLite DB và chạy tự động các tệp tin di trú (migrations) an toàn:
```bash
truthkeep setup
```

### Bước 3: Khởi động MCP Stdio Server (Tự động)
TruthKeep hoạt động ở chế độ **Secure MCP Stdio-Only** (Không mở cổng mạng, an toàn tuyệt đối). Nó sẽ được khởi chạy tự động bởi các host (như Cursor, Claude Desktop) khi cần và tự đóng khi kết thúc.

*Để kiểm tra nhanh tính tương thích của luồng stdio JSON-RPC trên máy của bạn:*
```bash
truthkeep mcp-probe
```
*Để in bảng điều khiển trực quan ASCII Dashboard của hệ thống:*
```bash
truthkeep dashboard
```

### Bước 4: Kiểm chứng Động học Toán học (Self-Test)
Chạy script kiểm chứng toán học cục bộ để đo lường độ chính xác của Bayesian posterior và Bellman dynamics:
```bash
python scripts/prove_it.py
```

---

## 🛠️ Trải nghiệm Nạp & Truy xuất Ký ức bằng CLI

Động cơ cung cấp giao diện dòng lệnh mạnh mẽ để bạn tương tác trực tiếp với tri thức nhận thức:

```bash
# 1. Ghi nhớ một sự thật mới
truthkeep remember "Mimi is a blue robotic companion created in Tokyo."

# 2. Truy vấn ký ức (Tìm kiếm ngữ nghĩa + Tôpô TDA-inspired)
truthkeep recall "Who is Mimi?"

# 3. Đính chính sự thật (Kích hoạt sóng Lan truyền ngược đồ thị tri thức)
truthkeep correct "Mimi was actually created in Osaka in 2025."

# 4. Xem logs hệ thống trực tiếp
truthkeep logs --tail 50
```

---

## 🎓 Tiếp tục nghiên cứu
*   Xem đặc tả toán học chi tiết tại: [MATHEMATICAL_MEMORY_SUBSTRATE.md](docs/MATHEMATICAL_MEMORY_SUBSTRATE.md)
*   Xem báo cáo đo đạc hiệu năng tại: [reports/ablation_math_report.md](reports/ablation_math_report.md)
