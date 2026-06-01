# 🤖 Tích hợp Mimi English Robot với TruthKeep Memory (An toàn tuyệt đối)

Tài liệu này hướng dẫn chi tiết cách kết nối **Mimi English Robot (ESP32/Firmware)** với hệ thống bộ nhớ nhận thức **TruthKeep Memory** thông qua mô hình **Secure Companion Gateway**.

Để bảo vệ an toàn thông tin tối đa, TruthKeep strictly áp dụng nguyên lý **Zero Open Ports** (Không mở cổng mạng, không có HTTP server chạy nền). Do đó, Mimi English Robot sẽ không gọi trực tiếp HTTP REST API tới TruthKeep, mà sẽ giao tiếp thông qua một ứng dụng Gateway trung gian chạy cục bộ trên PC của bạn.

---

## 📐 Kiến trúc Tích hợp (Architecture)

Mimi English Robot (chạy ESP32) giao tiếp với PC qua cổng Serial (hoặc mạng cục bộ được mã hóa). Một script Gateway chạy trên PC sẽ nhận diện các gói tin và giao tiếp trực tiếp với tiến trình `truthkeep-mcp` qua luồng stdio an toàn.

```text
[Mimi English Robot (ESP32)]
           │
           │ (Serial Protocol / USB / Bluetooth - JSON Payload)
           ▼
[Local Companion Gateway (PC / Python Companion)]
           │
           │ (Stdio Subprocess Interface / stdin-stdout)
           ▼
[TruthKeep Cognitive Memory Engine] (SQLite, TDA, Bayes, Bellman)
```

---

## 🛠️ Quy trình Kết nối qua Companion Gateway (Khuyên dùng)

### Bước 1: Khởi động Gateway cục bộ trên PC
Chúng ta sẽ viết một đoạn script Python Gateway ngắn chạy trên PC. Script này mở cổng Serial kết nối với Robot, nhận dữ liệu giọng nói/văn bản đã xử lý, sau đó gọi trực tiếp API Python của `truthkeep` (hoặc spawn tiến trình `truthkeep-mcp` qua stdio) để lưu trữ và truy vấn bộ nhớ.

Dưới đây là mã nguồn Python Gateway mẫu chạy trên PC:

```python
import sys
import json
import subprocess
from aegis_py.app import AegisApp

# 1. Khởi tạo kết nối trực tiếp CSDL an toàn không qua cổng mạng
app = AegisApp("memory_aegis.db")

def handle_robot_store(content, subject, scope_id="mimi_english_bot"):
    """Lưu trữ tri thức mới nhận được từ robot."""
    mem = app.put_memory(
        content,
        type="semantic",
        scope_type="agent",
        scope_id=scope_id,
        subject=subject,
        source_kind="voice_interaction"
    )
    if mem:
        print(f"[Gateway] Ghi nhớ thành công: {mem.id}")
        return {"status": "success", "memory_id": mem.id}
    return {"status": "rejected"}

def handle_robot_recall(query, scope_id="mimi_english_bot"):
    """Truy vấn tri thức phù hợp để robot phản hồi thông minh."""
    results = app.search_payload(
        query,
        scope_type="agent",
        scope_id=scope_id,
        limit=3,
        semantic=True
    )
    return {"status": "success", "results": results}

# Giải phóng kết nối sạch sẽ khi tắt Gateway
# app.close()
```

### Bước 2: Lập trình ESP32 truyền nhận dữ liệu
Mimi Robot (ESP32) chỉ cần gửi các gói tin JSON chứa nội dung giao tiếp qua cổng USB Serial.

Ví dụ gói tin nạp ký ức gửi từ ESP32:
```json
{
  "action": "store",
  "content": "User prefers slow and clear English conversation.",
  "subject": "conversation_pace"
}
```

Ví dụ gói tin truy vấn gửi từ ESP32:
```json
{
  "action": "recall",
  "query": "How should I talk to the user?"
}
```

Companion Gateway trên PC sẽ đọc luồng Serial, gọi hàm `handle_robot_recall` tương ứng, và gửi kết quả JSON trả ngược lại cho ESP32 hiển thị hoặc phát âm thanh.

---

## 🔍 Chế độ Giám sát Logs cục bộ
Bạn có thể mở một terminal riêng trên PC và theo dõi toàn bộ nhật ký giao tiếp, đính chính tri thức hoặc dọn dẹp bộ nhớ của Mimi Robot thời gian thực:
```bash
truthkeep logs --tail 50 -f
```

Sự kết hợp này vừa đảm bảo Mimi Robot hoạt động cực kỳ thông minh nhờ lõi nhận thức của TruthKeep, vừa đảm bảo **100% không mở cổng mạng**, ngăn ngừa hoàn toàn nguy cơ rò rỉ dữ liệu hoặc xâm nhập local.
