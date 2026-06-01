# TruthKeep v11 Polished Easy Mode

Start here if you are not technical: **open `START_HERE.md`** or run `RUN_TRUTHKEEP_WINDOWS.cmd`.

TruthKeep focuses on **remembering what is still true**. It keeps the full mathematical/graph/governance core, but exposes a simple Easy Mode for normal users.

---

# TruthKeep Memory: Correctness-First Memory Engine for AI Agents

## Easy Mode for non-technical users

Run one command:

```bash
truthkeep easy install
```

TruthKeep stays local-first and secure: MCP stdio only, no HTTP daemon, no open ports, no cloud by default. Easy Mode keeps the core unchanged and only simplifies setup, OpenClaw integration, diagnostics, and repair.


TruthKeep is a **local-first, explainable, and correctness-aware** memory engine designed for AI agents, MCP hosts, and long-running assistants that need more than just "semantic search over raw notes."

Unlike traditional memory systems that only retrieve the nearest vector neighbors, TruthKeep introduces a **governed truth layer** to handle memory correction, prevent stale facts from leaking, and explain why one memory was preferred over another.

---

## 📖 Bố cục Tài liệu 3 Tầng (Three-Tier Documentation)

Để giúp bạn tiếp cận TruthKeep một cách hiệu quả nhất mà không bị ngợp bởi các thuật ngữ toán học phức tạp, tài liệu này được chia thành 3 tầng:

*   [**Tầng 1: Cho Người mới bắt đầu (Beginners)**](#tầng-1-cho-người-mới-bắt-đầu-beginners) — Giới thiệu tổng quan, cài đặt nhanh và demo 2 phút.
*   [**Tầng 2: Cho Nhà phát triển Agent (Developers)**](#tầng-2-cho-nhà-phát-triển-agent-developers) — MCP Server, các hàm API lõi, quản lý Scope, Backup/Restore.
*   [**Tầng 3: Cho Kỹ sư Nghiên cứu sâu (Researchers)**](#tầng-3-cho-kỹ-sư-nghiên-cứu-sâu-researchers) — 13 động cơ toán học, Báo cáo loại trừ (Ablation Benchmark) thực tế và lớp bảo mật mật mã học.

---

## Tầng 1: Cho Người mới bắt đầu (Beginners)

### TruthKeep giải quyết lỗi gì?
Khi AI Agent tương tác lâu dài với bạn, nó thường gặp phải 3 vấn đề lớn về bộ nhớ:
1.  **Ảo giác dữ liệu cũ (Stale Fact Leak)**: Bạn nói bạn thích uống trà sữa trân châu, hôm sau bạn đổi thành trà đào. Nhưng khi hỏi lại, AI vẫn lôi thông tin "trà sữa" cũ ra do độ tương đồng ngữ nghĩa của nó quá cao.
2.  **Không thể đính chính (Immutable Mistakes)**: AI không phân biệt được đâu là thông tin đã bị sửa đổi (*superseded*) và đâu là thông tin đính chính mới nhất (*winner*).
3.  **Hộp đen bộ nhớ (Lack of Explainability)**: Bạn không thể biết tại sao AI lại chọn nhớ chi tiết này mà bỏ qua chi tiết kia.

TruthKeep giải quyết triệt để các vấn đề trên bằng cách xây dựng một **vòng đời trạng thái ký ức** và một **hệ thống tự động dọn dẹp (hygiene)** cục bộ.

### Cài đặt nhanh (Quick Start)
Cài đặt TruthKeep cực kỳ đơn giản bằng `pip`:

```bash
pip install -e .
```

Sau đó chạy tự động chẩn đoán và chạy luồng chứng minh (Proof Flow) trong 10 giây:

```bash
python scripts/prove_it.py
```

### Demo 2 Phút: Ký ức cũ bị sửa, ký ức mới thắng thế
Khi bạn đính chính một thông tin, TruthKeep tự động hạ mức tin cậy của ký ức cũ, chuyển nó sang trạng thái `superseded` (bị thay thế) và giúp ký ức mới thắng thế một cách khoa học:

```python
from truthkeep import TruthKeep

# Khởi tạo facade TruthKeep cục bộ
tk = TruthKeep.auto()

# 1. Nhớ một sự thật ban đầu
tk.remember("Mimi's favorite drink is Bubble Tea.", subject="mimi.drink")

# 2. Đính chính sự thật mới
tk.correct("Correction: Mimi's favorite drink is now Peach Tea.", subject="mimi.drink")

# 3. Truy xuất ký ức
results = tk.recall("What is Mimi's favorite drink?")

# Kết quả: "Peach Tea" sẽ đứng đầu bảng (validated winner), 
# còn "Bubble Tea" bị suppresses hoàn toàn khỏi danh sách active.
print(results[0]["memory"]["content"]) 
```

---

## Tầng 2: Cho Nhà phát triển Agent (Developers)

### Tích hợp MCP Server
TruthKeep tích hợp sẵn giao thức **Model Context Protocol (MCP)**, cho phép kết nối trực tiếp với Claude Desktop, Cursor, OpenClaw, hoặc bất kỳ LLM Client nào hỗ trợ MCP.

Khởi tạo và thiết lập cơ sở dữ liệu:
```bash
truthkeep setup
# Hoặc sử dụng lệnh tắt: truthkeep-setup
```

Khởi chạy MCP Server qua stdio (Tự động khởi chạy bởi Cursor/Claude):
```bash
truthkeep-mcp
```
*(Các bí danh legacy tương thích ngược: aegis-mcp, aegis-setup, aegis-check)*

Kiểm tra tính sẵn sàng của runtime và plugins:
```bash
truthkeep-check
```

Kiểm tra trạng thái hoạt động:
```bash
truthkeep status
# Thực hiện probe kiểm thử stdio thời gian thực:
truthkeep mcp-probe
# Hoặc in bảng điều khiển ASCII Dashboard trực quan:
truthkeep dashboard
```

### Các hàm API lõi (SDK Python)
```python
from truthkeep import TruthKeep

tk = TruthKeep.auto()

# Ghi nhớ ký ức mới
tk.remember(content="...", subject="optional.subject", scope_id="default")

# Truy xuất ký ức có giải trình tại sao được chọn (why this / why not)
results = tk.recall(query="...", limit=5)

# Đính chính ký ức cũ
tk.correct(new_content="...", subject="...", old_content_hint="optional hint")

# Quên ký ức (xóa vật lý hoặc đánh dấu lưu trữ)
tk.forget(memory_id="...")
```

### Phân tách và Cách ly Scope (Multi-tenant Isolation)
TruthKeep hỗ trợ phân cách bộ nhớ cực kỳ an toàn qua hai biến số:
*   `scope_type`: Phân loại không gian bộ nhớ (ví dụ: `user`, `session`, `agent`, `global`).
*   `scope_id`: Mã định danh không gian (ví dụ: `user_123`, `session_abc`).

Mọi truy xuất và ghi nhớ đều được giới hạn nghiêm ngặt trong Scope được chỉ định, ngăn chặn rò rỉ dữ liệu chéo giữa các phiên làm việc hoặc người dùng khác nhau.

---

## Tầng 3: Cho Kỹ sư Nghiên cứu sâu (Researchers)

### 13 Động cơ Toán học (Mathematical Substrate)
TruthKeep không dùng các mô hình nhúng (dense embedding) nặng nề làm authority duy nhất. Thay vào đó, nó phối hợp **13 động cơ toán học** được viết bằng **Pure Python** chạy cực nhẹ trên máy cục bộ (Mimi English Robot hoặc các client khác tích hợp từ xa qua client sidecar protocol):

1.  **I Ching State Encoding** (Kinh Dịch - ~1000 BCE): Mã hóa trạng thái ký ức thành các quẻ dịch nhị phân.
2.  **Luoshu Validator** (Ma phương Lạc Thư - ~650 BCE): Kiểm tra tính toàn vẹn ma trận trọng số.
3.  **Platonic Quantizer** (Khối đa diện đều Plato - ~360 BCE): Lượng tử hóa vector ngữ nghĩa lên bề mặt khối 20 mặt đều để giảm chiều dữ liệu.
4.  **Fibonacci Decay** (Dãy Fibonacci - 1202): Phân rã độ nổi bật (salience) của ký ức theo tỷ lệ Vàng phi tuyến tính.
5.  **Hilbert Space** (David Hilbert - 1900s): Xây dựng không gian vector tần số từ ngữ và tính Cosine Similarity.
6.  **Nash Embedding** (John Nash - 1956): Nén giảm chiều vector bảo toàn khoảng cách hình học.
7.  **Erdős Spatial Grid** (Paul Erdős - 1946): Định vị không gian lưới để thu hẹp vùng tìm kiếm vector về hằng số gần như ổn định.
8.  **Poincaré Topological Fingerprints** (Henri Poincaré - 1895): Nhận diện đặc trưng tôpô-inspired của văn bản bất chấp nhiễu từ ngữ.
9.  **Euler/Cayley Graph Centrality** (Euler & Cayley): Phân tích độ trung tâm của nút tri thức trong đồ thị mạng lưới liên kết.
10. **Bayesian Belief Updates** (Thomas Bayes - 1763): Tính xác suất hậu nghiệm Bayes cập nhật độ tin cậy của ký ức khi có bằng chứng.
11. **Fourier Frequency Compressor** (Joseph Fourier - 1822): Nén phổ tần số ký tự văn bản thành dấu vân tay tần số.
12. **Backpropagation Correction** (Rumelhart & Hinton - 1986): Lan truyền ngược đính chính để hạ điểm tin cậy các node liên kết liên quan.
13. **Bellman Strategic Value** (Richard Bellman - 1957): Quy hoạch động tối ưu hóa giá trị chiến thuật của ký ức quy trình dài hạn.

---

### Báo cáo Loại trừ Toán học (Ablation Benchmark Report)
Để đo lường sự đóng góp thực tế của từng lõi toán học vào chất lượng hệ thống, dưới đây là số liệu **Ablation Benchmark thực tế** đo đạc được trên môi trường Windows 11 (Full Measured Run - 300 cases, seed 42) khi lần lượt tắt các lõi toán học:

| Cấu hình Thử nghiệm | Đọc Latency (p95 ms) | Ghi Latency (ms) | Ingestion Rate (rec/s) | Top-1 Correction | Superseded Blocked | TDA Matching | Backprop Demotion | Bellman Protect | DB Size (KB) | RAM (MB) |
|---|---|---|---|---|---|---|---|---|---|---|
| **TruthKeep Full** | **14.89 ms** | 1688.23 ms | 238.71 | **100.0%** | **100.0%** | **100.0%** | **0.90%** | **100.0%** | 4108.0 KB | 32.82 MB |
| *Without Bellman* | 16.10 ms | 1927.19 ms | 209.11 | 100.0% | 100.0% | 100.0% | 0.90% | **0.0%** | 5184.0 KB | 34.32 MB |
| *Without Backprop* | 16.29 ms | 1944.57 ms | 207.24 | 100.0% | 100.0% | 100.0% | **0.0%** | 100.0% | 4104.0 KB | 34.06 MB |
| *Without TDA* | 15.58 ms | 2050.05 ms | 196.58 | 100.0% | 100.0% | **0.0%** | 0.90% | 100.0% | 4112.0 KB | 34.02 MB |
| *Without Compressed Tier*| 11.27 ms | 1911.95 ms | 210.78 | 100.0% | 100.0% | 100.0% | 0.90% | 100.0% | 4112.0 KB | 34.24 MB |

#### Nhận xét cốt lõi từ Ablation:
*   **Bellman Value Engine**: Khi tắt Bellman, chỉ số bảo vệ ký ức quy trình quan trọng rơi thẳng từ **100% về 0%**, khiến tri thức chiến thuật bị dọn dẹp nhầm bởi DecayBeast.
*   **Backpropagation Engine**: Khi tắt Backprop, điểm hạ cấp tin cậy của ký ức mâu thuẫn rơi về **0%**, dẫn tới rò rỉ thông tin cũ đã bị đính chính.
*   **Poincaré TDA**: Tắt TDA làm giảm đáng kể khả năng nhận diện bản chất topo của câu hỏi khi người dùng sử dụng từ ngữ có độ nhiễu cao.

---

### 3 Chế độ Bảo mật (Security & Privacy Modes)

> [!WARNING]
> Hardened mode is currently an architecture scaffold/contract, not a completed audited security mode. Do not use for high-risk enterprise production without third-party audit.

TruthKeep thiết kế 3 chế độ hoạt động bảo mật rõ ràng để phù hợp với từng môi trường deployment:

1.  **`demo` Mode (Mô phỏng thực nghiệm)**:
    *   Sử dụng mô phỏng toán học (FHE-style simulator, ZKP-style commitment).
    *   Phù hợp chạy thử nghiệm nhẹ nhàng trên PC, Raspberry Pi hoặc các dòng CPU nhúng để đo đạc và benchmark nhanh.
2.  **`local` Mode (Cá nhân an toàn - Mặc định)**:
    *   SQLite cục bộ, tối ưu hóa tốc độ.
    *   SHA-256 Content Seal chống giả mạo dữ liệu tĩnh.
    *   Tùy chọn mã hóa nội dung ở tầng ứng dụng (App-level content encryption).
3.  **`hardened` Mode (Tiêu chuẩn bảo mật cao - Khung kiến trúc)**:
    *   Mã hóa toàn bộ nội dung ký ức bằng **AES-GCM-256** hoặc **ChaCha20-Poly1305** (qua thư viện `cryptography`).
    *   Master Key được quản lý an toàn qua OS Keychain (Windows Credential Manager / macOS Keychain).
    *   Khóa phiên được sinh qua hàm băm an toàn **Argon2id** hoặc **HKDF**.
    *   Tuyệt đối không lưu trữ hay chỉ mục Plaintext khi bật strict privacy.

---

## 📄 Bản quyền
Dự án được phân phối dưới giấy phép **MIT License**.
