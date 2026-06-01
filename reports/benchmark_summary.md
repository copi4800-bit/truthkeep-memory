# Tóm tắt Báo cáo Hiệu năng: TruthKeep Benchmark Summary

> **Phiên bản động cơ**: v10.6-Professional  
> **Nền tảng kiểm thử**: Windows 11 (AMD64) / Python 3.12  
> **Thư mục raw data**: [reports/raw/](raw/)

---

## 🚀 Tổng quan Hiệu năng Động cơ

Hệ thống **TruthKeep Memory** đã trải qua các cuộc kiểm thử hiệu năng và chất lượng nhận thức cực kỳ khắc nghiệt. Dưới đây là bức tranh toàn cảnh kết hợp từ các báo cáo đo đạc thực tế:

### 1. Báo cáo Tải & Khả năng Mở rộng (Scale Matrix)
*Xem chi tiết tại: [scale_report.md](scale_report.md)*

*   **Measured 10k memories**: p95 Read = **42.47 ms**, DB size = **149.61 MB**.
*   **Stress-Test 77k memories**: p95 Read = **260.40 ms**, DB size = **288.72 MB**.
*   **Extrapolated 1M memories**: p95 Read = **590.20 ms**, DB size = **3.7 GB** (Dự tính dung lượng siêu tối ưu cho Raspberry Pi/Embedded Sidecar).

### 2. Báo cáo Loại trừ Động cơ Toán học (Ablation Matrix)
*Xem chi tiết tại: [ablation_math_report.md](ablation_math_report.md)*

*   **Bellman Value Engine**: Giữ an toàn **100%** tri thức quy trình trọn đời (tắt Bellman -> tỷ lệ sống sót rơi về **0.0%**).
*   **Backpropagation Engine**: Hạ cấp thành công **0.90%** độ tin cậy của các ký ức liên quan khi đính chính xảy ra (tắt Backprop -> demotion impact rơi về **0.0%**, rò rỉ tri thức mâu thuẫn).
*   **Poincaré TDA Engine**: Đạt độ chính xác nhận diện topo ngữ nghĩa **100%** dưới nhiễu cực lớn (tắt TDA -> khả năng so khớp topo rơi về **0.0%**).

---

## 🎓 Kết luận Khoa học

Mọi lõi toán học tích hợp trong TruthKeep đều thực thi một vai trò thực tế rõ rệt, không có sự dư thừa. Động cơ đạt sự cân bằng hoàn mỹ giữa **độ trễ tối ưu của local-first** và **độ tin cậy nhận thức ở cấp độ nghiên cứu ứng dụng**.
