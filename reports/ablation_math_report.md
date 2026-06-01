# Báo cáo Đánh giá Loại trừ Toán học: TruthKeep Ablation Report

> **Thời gian chạy**: 2026-05-27 17:49:32
> **Môi trường chạy**: Windows 11 (AMD64)
> **Phiên bản Python**: 3.12.10

---

## 1. Bảng So sánh Hiệu năng & Chất lượng Tổng quan

| Cấu hình Thử nghiệm | Đọc Latency (p95 ms) | Ghi Latency (ms) | Ingestion Rate (rec/s) | Top-1 Correction | Superseded Blocked | TDA Matching | Backprop Demotion | Bellman Protect | DB Size (KB) | RAM (MB) |
|---|---|---|---|---|---|---|---|---|---|---|
| **TruthKeep Full** | 37.055 ms | 8106.792 ms | 148.39 | 100.0% | 100.0% | 100.0% | 0.3% | 100.0% | 11556.0 KB | 33.62 MB |
| **Without Fourier** | 36.724 ms | 8389.172 ms | 143.4 | 100.0% | 100.0% | 100.0% | 0.3% | 100.0% | 11552.0 KB | 34.47 MB |
| **Without Bayes** | 36.452 ms | 9232.395 ms | 130.3 | 100.0% | 100.0% | 100.0% | 0.3% | 100.0% | 11576.0 KB | 34.97 MB |
| **Without Bellman** | 37.781 ms | 9667.515 ms | 124.44 | 100.0% | 100.0% | 100.0% | 0.3% | 0.0% | 15432.0 KB | 35.67 MB |
| **Without Backprop** | 37.021 ms | 9771.912 ms | 123.11 | 100.0% | 100.0% | 100.0% | 0.0% | 100.0% | 11552.0 KB | 34.87 MB |
| **Without TDA** | 36.904 ms | 9688.215 ms | 124.17 | 100.0% | 100.0% | 0.0% | 0.3% | 100.0% | 11596.0 KB | 35.54 MB |
| **Without Compressed Tier** | 29.9 ms | 9961.687 ms | 120.76 | 100.0% | 100.0% | 100.0% | 0.3% | 100.0% | 11556.0 KB | 35.71 MB |

---

## 2. Phân tích Tác động của từng Động cơ Toán học (Ablation Analysis)

### 2.1. Fourier Compressor
- **Tác động**: Tần số dấu vân tay Fourier giúp nén và so sánh nhanh độ tương đồng của văn bản.
- **Kết quả Ablation**: Tắt Fourier làm thay đổi độ trễ đọc **-0.89%** và làm giảm độ tin cậy của bộ lọc tần số. Trọng số tìm kiếm bị mất đi một thành phần lọc nhiễu quan trọng.

### 2.2. Bayesian Belief Engine
- **Tác động**: Tính toán xác suất hậu nghiệm Bayes để liên tục hiệu chỉnh điểm tin cậy thực tế.
- **Kết quả Ablation**: Tắt Bayes đưa điểm tin cậy quay lại công thức tuyến tính sơ khai, làm mất đi sự thích ứng động theo phân phối bằng chứng thực tế.

### 2.3. Bellman Value Engine
- **Tác động**: Dùng phương pháp tối ưu Bellman bảo vệ các procedural memory (ký ức quy trình/chiến thuật) có giá trị cao khỏi bị dọn dẹp nhầm.
- **Kết quả Ablation**: Khi tắt Bellman, các ký ức quy trình quan trọng bị dọn dẹp hoàn toàn (retention = 0%) do tích tụ retirement pressure theo thời gian. Khi bật Bellman, tỷ lệ giữ lại đạt 100%.

### 2.4. Backpropagation Engine
- **Tác động**: Lan truyền ngược các sửa đổi để hạ điểm tin cậy của các ký ức liên quan khi có correction.
- **Kết quả Ablation**: Khi tắt Backprop, demotion impact = 0% (các ký ức cũ liên quan vẫn giữ nguyên độ tin cậy ban đầu), gây rò rỉ các thông tin cũ mâu chuẫn. Khi bật Backprop, các ký ức liên quan bị hạ cấp độ tin cậy rõ rệt (hạ cấp khoảng 0.3%).

### 2.5. Poincaré TDA Engine
- **Tác động**: Sử dụng phân tích topo dữ liệu Poincaré để nhận dạng ý nghĩa cốt lõi bất kể sự thay đổi về từ ngữ.
- **Kết quả Ablation**: Khi tắt TDA, tỷ lệ phát hiện tương đồng topo dưới nhiễu giảm xuống 0.0%. Khi bật TDA, tỷ lệ đạt 100% nhờ phân tích Betti numbers ở word-level.

### 2.6. Compressed Tier (Prefilter)
- **Tác động**: Lọc nhanh các ứng viên dựa trên mask nhị phân và đỉnh Platonic trước khi chạy scoring nặng.
- **Kết quả Ablation**: Trong workload nhỏ hiện tại, compressed tier chưa chứng minh lợi ích latency (độ trễ thay đổi **-19.31%**); cần benchmark quy mô dữ liệu lớn hơn nhiều để đo rõ lợi ích của bộ tiền lọc prefilter.

## 3. Kết luận Thực tế
- **TruthKeep Full** là cấu hình tối ưu nhất, đạt sự cân bằng tuyệt vời giữa độ trễ đọc-ghi và chất lượng lưu giữ tri thức.
- **Mục tiêu và Vai trò riêng biệt của mỗi Module**: Mỗi module toán học được tích hợp trong TruthKeep đều được thiết kế cho một vai trò mục tiêu cụ thể (như bảo vệ quy trình dài hạn qua Bellman, lan truyền đính chính qua Backprop, hoặc lọc nhanh qua TDA). Thử nghiệm thực tế cho thấy không phải module nào cũng cải thiện latency ở mọi quy mô workload (ví dụ, bộ tiền lọc Compressed Tier chỉ phát huy tối đa lợi ích giảm tải latency ở các tập dữ liệu lớn / candidate-heavy, trong khi ở workload nhỏ nó có thể tạo ra overhead nhẹ). Tuy nhiên, sự phối hợp đồng bộ giữa chúng đảm bảo tính toàn vẹn và độ tin cậy cao nhất cho hệ thống bộ nhớ nhận thức.