# Báo cáo Hiệu năng Hiệu chỉnh Tri thức: TruthKeep Correction Report

> **Thời gian đo**: 2026-05-27 13:44:00  
> **Môi trường máy chạy**: Windows 11 (AMD64)  
> **Raw JSON Data**: [correction_report.json](raw/correction_report.json)

---

## 1. Kết quả Đo lường Đính chính Tri thức

Chúng tôi đo đạc hành vi của TruthKeep Memory khi tiếp nhận thông tin hiệu chỉnh tri thức (Truth Correction) và kích hoạt lan truyền ngược điều chỉnh niềm tin trên đồ thị liên kết.

| Chỉ số Hiệu năng | Kết quả đo (Full Run) | Mô tả & Ý nghĩa |
|---|---|---|
| **Top-1 Correction Accuracy** | **100%** | Tỷ lệ tìm kiếm trả về chính xác tri thức mới sau khi hiệu chỉnh |
| **Superseded Suppression** | **100%** | Tri thức cũ bị thay thế được chặn hoàn toàn, không rò rỉ ra bên ngoài |
| **Backprop Demotion (Full)** | **0.90%** | Điểm số niềm tin của các nút liên quan bị hạ cấp an toàn khi nút gốc bị đính chính |
| **Backprop Demotion (Without)** | **0%** | Khi tắt Backprop, các ký ức liên đới giữ nguyên niềm tin cũ, gây mâu thuẫn tri thức |
| **Avg Correction Write Latency** | **168.22 ms** | Độ trễ trung bình ghi nhận và lan truyền sửa đổi |
| **Avg Correction Read Latency** | **7.69 ms** | Độ trễ trung bình đọc tri thức hiệu chỉnh |

---

## 2. Đánh giá Động học Sửa sai

1.  **Tính an toàn nhất quán**: Nhờ cơ chế `BackpropagationEngine`, khi một tri thức nền tảng bị thay đổi, các tri thức phụ thuộc trên đồ thị liên kết cũng được tự động cảnh báo giảm điểm tin cậy (demotion) một cách tuyến tính theo độ sâu liên kết ($d \le 2$). Điều này đảm bảo AI không đưa ra các lập luận dựa trên tri thức lỗi thời.
2.  **Chặn đứng rò rỉ**: `Superseded Suppression` đạt 100% chứng minh các Hard Constraints Gate hoạt động hoàn hảo, bảo vệ bộ nhớ khỏi việc truy xuất các thông tin đã bị phán quyết là sai lệch hoặc lỗi thời.
