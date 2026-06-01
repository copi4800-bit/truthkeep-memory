# ⏳ Chính Sách Lưu Trữ Và Vòng Đời Dữ Liệu: TruthKeep Data Retention

Tài liệu này đặc tả vòng đời của dữ liệu ký ức, các trạng thái tri thức và các quy trình dọn dẹp, lưu trữ hoặc hủy bỏ dữ liệu một cách an toàn và nhất quán bên trong **TruthKeep Memory**.

---

## 1. Vòng Đời Ký Ức & Các Trạng Thái Tri Thức (Memory Lifecycle)

Một bản ghi ký ức (Memory Node) trong TruthKeep không phải là một dòng dữ liệu tĩnh. Nó là một thực thể tri thức động, có thể tiến hóa và thay đổi trạng thái theo thời gian để phản ánh đúng thực tế khách quan:

```text
       ┌──────────────┐
       │   [Active]   │ ◄──────────────────────────────┐
       └──────┬───────┘                                │
              │                                        │
              │ Bị đính chính / Thay thế                │ Khôi phục (Restore)
              ▼                                        │
       ┌──────────────┐                                │
       │ [Superseded] │ ───────────────────────────────┘
       └──────┬───────┘
              │
              │ Hết hạn / Dọn dẹp (Hygiene)
              ▼
       ┌──────────────┐
       │  [Archived]  │
       └──────┬───────┘
              │
              │ Yêu cầu xóa vĩnh viễn (Purge)
              ▼
             [X] (Bị hủy vĩnh viễn và ghi đè an toàn)
```

### 1.1. Các Trạng Thái Chi Tiết

*   **Active (Đang hoạt động)**: Ký ức đại diện cho sự thật hiện tại (`current_truth`). Có điểm tin cậy cao, tham gia trực tiếp vào quá trình recall ngữ cảnh cho các AI Agent.
*   **Superseded (Bị thay thế/Đính chính)**: Ký ức chứa thông tin cũ đã bị đính chính bởi một ký ức mới hơn (quan hệ `A --SUPERSEDED_BY--> B`). Ký ức này không còn được recall mặc định cho AI, nhưng vẫn được lưu trữ để làm bằng chứng giải thích lịch sử tiến hóa tri thức (`why-not`).
*   **Archived (Đã lưu trữ)**: Dữ liệu ký ức cũ, ít khi được truy cập hoặc đã bị hạ điểm tin cậy xuống dưới mức tối thiểu. Chúng được đóng gói lại để giảm dung lượng tìm kiếm nhưng vẫn có thể được khôi phục khi cần thiết.
*   **Reconcile Required (Cần hòa giải)**: Trạng thái tạm thời khi phát hiện mâu thuẫn trực tiếp giữa hai ký ức (`A contradicts B`) mà hệ thống chưa thể tự động phân xử dựa trên độ tin cậy. Trạng thái này yêu cầu sự can thiệp của người dùng hoặc các tác vụ phân xử nền.

---

## 2. Cơ Chế Dọn Dẹp Và Nén Tri Thức (Hygiene & Consolidation)

Hệ thống tích hợp các Beast nền (nền tảng tự động chạy ngầm hoặc qua CLI) để tối ưu hóa không gian lưu trữ và duy trì tính nhất quán:

### 2.1. ConsolidatorBeast (Nén tri thức)
*   **Tần suất**: Chạy định kỳ hoặc khi số lượng nút ký ức trong một scope vượt ngưỡng quy định.
*   **Nhiệm vụ**:
    *   Phát hiện các chuỗi thay thế dài (`A -> B -> C -> D`) và nén chúng lại trực tiếp để tối ưu hóa đồ thị.
    *   Phát hiện các ký ức trùng lặp hoặc tương đồng cực cao để hợp nhất (Weave) cấu trúc ngữ nghĩa.

### 2.2. HygieneBeast (Vệ sinh bộ nhớ)
*   **Tần suất**: Định kỳ hàng tuần hoặc theo chỉ thị thủ công.
*   **Nhiệm vụ**:
    *   Quét và loại bỏ các liên kết đồ thị mồ côi (orphaned links).
    *   Hạ điểm tin cậy tự nhiên của các ký ức không bao giờ được truy cập trong một khoảng thời gian dài (Phép phân rã tri thức tự nhiên - Decay).
    *   Chuyển các ký ức có confidence thấp dưới ngưỡng sàn (`0.1`) sang trạng thái `Archived`.

---

## 3. Quy Trình Xóa Bỏ An Toàn (Secure Data Purging)

Khi người dùng thực hiện lệnh xóa vĩnh viễn (`purge` hoặc `delete` với flag `--permanent`):

1.  **Thu hồi Đồ thị (Graph Retraction)**: Hệ thống tự động quét và xóa toàn bộ các cạnh liên kết đồ thị (Edges) kết nối với nút ký ức bị xóa trong bảng `memory_links` để tránh liên kết mồ côi.
2.  **Xóa sạch Chỉ mục FTS5**: Gỡ bỏ hoàn toàn mọi chỉ mục tìm kiếm toàn văn của nút đó trong SQLite FTS5 index.
3.  **Xóa vật lý & Ghi đè (Secure Purging)**:
    *   Trong cấu hình Standard, bản ghi bị xóa qua câu lệnh SQL `DELETE`.
    *   Trong cấu hình `strict` hoặc `hardened`, dữ liệu thô trên đĩa sẽ được ghi đè bằng các byte ngẫu nhiên (Zeroing/Shredding) trước khi giải phóng không gian cơ sở dữ liệu (qua câu lệnh `VACUUM` của SQLite) để đảm bảo không một phần mềm khôi phục dữ liệu đĩa nào có thể lấy lại được nội dung cũ.
