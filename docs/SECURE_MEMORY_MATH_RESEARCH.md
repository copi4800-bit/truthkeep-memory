# 🔬 Nghiên Cứu Chuyên Sâu: Nền Tảng Toán Học Bảo Vệ Cấu Trúc Memory AI trong TruthKeep v11

Tài liệu này trình bày các định nghĩa, định lý, mệnh đề toán học và các công trình nghiên cứu chính thống được áp dụng trực tiếp để bảo vệ cấu trúc đồ thị ký ức của **TruthKeep Memory v11**. Chúng tôi cam kết sử dụng các mô hình toán học đã được chứng minh thực nghiệm, loại bỏ hoàn toàn các giả thuyết mơ hồ hay thuật ngữ phóng đại khoa học viễn tưởng.

---

## 1. Bảo Mật Vi Sai Trong Vector DB (Differential Privacy for Embeddings)

Khi AI lưu trữ ký ức dưới dạng các vector nhúng (embeddings) trong SQLite hoặc Vector DB, một kẻ tấn công có thể thực hiện **Membership Inference Attacks (MIA)** — liên tục truy vấn để suy đoán xem một thông tin nhạy cảm cụ thể có tồn tại trong bộ nhớ hay không. Thậm chí, chúng có thể cố gắng đảo ngược (Reverse Engineering) vector nhúng để tái dựng lại văn bản gốc.

### 1.1. Định nghĩa Toán học Gốc (Cynthia Dwork, 2006)
Một thuật toán ngẫu nhiên $\mathcal{M}: \mathcal{D} \to \mathcal{S}$ đạt $(\varepsilon, \delta)$-Differential Privacy nếu với mọi cặp cơ sở dữ liệu lân cận $D, D' \in \mathcal{D}$ (chỉ khác nhau đúng một bản ghi dữ liệu) và mọi tập kết quả $S \subseteq \text{Range}(\mathcal{M})$:

$$P[\mathcal{M}(D) \in S] \leq e^{\varepsilon} \cdot P[\mathcal{M}(D') \in S] + \delta$$

*Trong đó:*
*   $\varepsilon > 0$ là tham số bảo mật (privacy budget), đại diện cho mức độ rò rỉ thông tin tối đa.
*   $\delta \ge 0$ là xác suất thuật toán vi phạm điều kiện $\varepsilon$-DP nghiêm ngặt (thường $\delta \ll 1/|D|$).

### 1.2. Mệnh đề Sequential Composition (Tính cộng gộp tuyến tính)
Nếu hệ thống thực hiện $k$ truy vấn độc lập trên bộ nhớ, mỗi truy vấn $i$ đạt tiêu chuẩn $(\varepsilon_i, \delta_i)$-DP, thì tổng độ rò rỉ bảo mật toàn hệ thống tuân theo:

$$\varepsilon_{\text{total}} = \sum_{i=1}^{k} \varepsilon_i, \quad \delta_{\text{total}} = \sum_{i=1}^{k} \delta_i$$

### 1.3. Cơ chế Metric Differential Privacy cho Sentence Embeddings (CMAG, 2025)
Công trình nghiên cứu *"Covering Metric Analytic Gaussian (CMAG) for Sentence Embeddings"* (2025) chứng minh rằng việc bơm nhiễu Gaussian vào vector nhúng trong không gian metric (ví dụ Poincaré Disk hoặc Euclid) đạt chuẩn bảo mật vi sai mà vẫn duy trì tính tương đồng ngữ nghĩa.

#### Thuật toán Box-Muller sinh nhiễu Gaussian chuẩn
Để tự viết mã nguồn zero-dependency, ta sinh biến ngẫu nhiên Gaussian chuẩn $Z \sim \mathcal{N}(0, 1)$ từ hai biến ngẫu nhiên phân phối đều $U_1, U_2 \sim \mathcal{U}(0, 1)$ bằng công thức:

$$Z_0 = \sqrt{-2 \ln U_1} \cos(2\pi U_2)$$

#### Công thức tính độ lệch chuẩn nhiễu tối thiểu ($\sigma$)
Để đạt tiêu chuẩn $(\varepsilon, \delta)$-DP trên một không gian vector có độ nhạy cảm (sensitivity) $\Delta$, độ lệch chuẩn Gaussian $\sigma$ bắt buộc phải thỏa mãn:

$$\sigma = \frac{\Delta \sqrt{2 \ln(1.25/\delta)}}{\varepsilon}$$

#### Bảo toàn hình học vector (L2 Re-normalization)
Khi thêm nhiễu Gaussian vào từng chiều của vector $v = (v_1, \dots, v_d)$:

$$v'_i = v_i + \mathcal{N}(0, \sigma^2)$$

Để bảo toàn cấu trúc Cosine Similarity và Poincaré Distance, vector bị nhiễu bắt buộc phải được chuẩn hóa L2 về mặt cầu đơn vị:

$$\hat{v} = \frac{v'}{\|v'\|_2}$$

---

## 2. Tính Toán Trên Dữ Liệu Bộ Nhớ Mã Hóa (Paillier Homomorphic Encryption)

Để cho phép máy chủ bên thứ ba (hoặc môi trường không đáng tin cậy) thực hiện tìm kiếm độ tương đồng vector (Vector Similarity Search) mà hoàn toàn không biết nội dung ký ức bên trong (Zero-Knowledge), TruthKeep v11 áp dụng hệ mật mã mã hóa đồng cấu một phần Paillier.

### 2.1. Định lý Mật mã học Paillier (Pascal Paillier, 1999)
Hệ mật mã Paillier dựa trên bài toán **Decisional Composite Residuosity Assumption (DCRA)** (Bài toán thặng dư hợp số quyết định modulo $n^2$).

#### Quy trình Sinh khóa (Key Generation)
1. Chọn hai số nguyên tố lớn $p$ và $q$. Tính $n = pq$ và $\lambda = \text{lcm}(p-1, q-1) = (p-1)(q-1)$ (do $p, q$ là số nguyên tố).
2. Public Key: $(n, g)$ với $g = n + 1$.
3. Private Key: $(\lambda, \mu)$ với $\mu = \lambda^{-1} \pmod n$ (tính bằng Extended Euclidean Algorithm).

#### Quy trình Mã hóa (Encryption)
Bản rõ $m < n$ được mã hóa thành bản mã $c$:

$$c = g^m \cdot r^n \pmod{n^2} = (1 + m \cdot n) \cdot r^n \pmod{n^2}$$

*Trong đó $r$ là số nguyên ngẫu nhiên thỏa mãn $\gcd(r, n) = 1$.*

#### Quy trình Giải mã (Decryption)
Bản rõ $m$ được khôi phục từ bản mã $c$ bằng công thức:

$$m = L(c^\lambda \pmod{n^2}) \cdot \mu \pmod n$$

*Trong đó toán tử $L(u) = \frac{u - 1}{n}$.*

### 2.2. Mệnh đề Đồng cấu Phép nhân Bản mã (Additive Homomorphism)
Bản nhân của hai bản mã tương đương với bản mã của tổng hai thông điệp ban đầu:

$$D(E(m_1, r_1) \cdot E(m_2, r_2) \pmod{n^2}) = m_1 + m_2 \pmod n$$

#### Phép nhân Bản mã với Hằng số (Scalar Multiplication)
Lũy thừa một bản mã với một số nguyên rõ $k$ tương đương với bản mã của tích hai số đó:

$$D(E(m)^k \pmod{n^2}) = k \cdot m \pmod n$$

### 2.3. Ứng dụng: Tích Vô Hướng Mù (Secure Dot Product)
Cho vector bộ nhớ đã mã hóa $E(A) = (E(a_1), \dots, E(a_d))$ và vector truy vấn rõ $B = (b_1, \dots, b_d)$. Máy chủ tính toán bản mã của tích vô hướng:

$$E(\langle A, B \rangle) = \prod_{i=1}^{d} E(a_i)^{b_i} \pmod{n^2}$$

Khi giải mã $E(\langle A, B \rangle)$ tại Client, ta thu được đúng giá trị thực $\sum a_i b_i$ mà máy chủ không hề biết giá trị của vector $A$ hay $B$.

#### Biểu diễn số thực âm/dương trong Modulo Arithmetic
Do vector nhúng chứa các số thực trong khoảng $[-1.0, 1.0]$, ta nhân với hằng số tỉ lệ $S = 1000$ để chuyển thành số nguyên. Số âm $x < 0$ được ánh xạ sang số nguyên dương qua modulo arithmetic:

$$x_{\text{mapped}} = x \pmod n = n + x$$

Khi giải mã, nếu giá trị giải mã $m > n/2$, ta khôi phục lại số âm bằng công thức $x = m - n$.
Để thực hiện phép lũy thừa số mũ âm $b_i < 0$, ta tính nghịch đảo nhân modulo của bản mã $E(a_i)^{-1} \pmod{n^2}$ bằng thuật toán Euclid mở rộng:

$$E(a_i)^{b_i} = \left(E(a_i)^{-1}\right)^{-b_i} \pmod{n^2}$$

---

## 3. Phát Hiện Nhiễm Độc Bộ Nhớ & Prompt Injection (Shannon Entropy Defense)

Kẻ tấn công có thể cố gắng tiêm nhiễm dữ liệu nhạy cảm hoặc các câu lệnh lặp đi lặp lại để ghi đè hệ thống AI (Jailbreak/Data Poisoning). Hành vi này làm thay đổi cấu trúc phân phối xác suất thống kê tự nhiên của văn bản đầu vào.

### 3.1. Định nghĩa Toán học Entropy Thông tin (Claude Shannon, 1948)
Entropy của một biến ngẫu nhiên $X$ nhận các giá trị trong tập $\{x_1, \dots, x_k\}$ với phân phối xác suất $P(x_i)$ là:

$$H(X) = -\sum_{i=1}^{k} P(x_i) \log_2 P(x_i)$$

*Trong đó $H(X)$ đại diện cho lượng thông tin trung bình chứa trong mỗi ký tự/token (bits per character/token).*

### 3.2. Mệnh đề Kiểm định Bất thường (Anomaly Detection Bound)
*   **Hành vi tự nhiên**: Trong một luồng ngôn ngữ tự nhiên, phân phối các ký tự/token phân tán đều và đa dạng, dẫn tới mức Entropy cao và ổn định ($H(X) \ge 3.8$).
*   **Hành vi tấn công (Prompt Injection/Buffer Overflow)**: Kẻ tấn công bơm chuỗi lặp (ví dụ: `A` lặp lại 1000 lần) để tràn bộ đệm hoặc phá vỡ cấu trúc. Khi đó, xác suất của token tấn công $P(x_{\text{attack}}) \to 1$.
*   **Hệ quả**: Do $\lim_{P \to 1} P \log_2 P = 0$ và $\lim_{P \to 0} P \log_2 P = 0$, tổng giá trị Entropy $H(X)$ sụt giảm đột ngột theo một hàm dốc toán học cụ thể hướng về $0$.

Hệ thống bảo vệ của TruthKeep đặt ngưỡng chặn an toàn:
*   $H(X) < 3.2$: Xác định ngay lập tức trạng thái nhiễm độc `poison_detected` và tự động cách ly vector trước khi nạp vào DB.
*   $3.2 \le H(X) < 3.7$: Trạng thái cảnh báo `warning` để giám sát chặt chẽ.

---

## 🔬 Minh Chứng Thực Nghiệm: Sự Khớp Nối Hoàn Hảo Chi Tiết Giữa Toán Học & Mã Nguồn

Toàn bộ các công thức toán học trên được hiện thực hóa thủ công 100% trong [privacy_guard.py](file:///g:/fimwarre%20xiaozhi/truthkeep-memory/aegis_py/security/privacy_guard.py):

*   **Box-Muller & Metric DP**: Được cài đặt tại `MetricDPGaussianNoise.apply_metric_dp` (dòng 231-260). Sử dụng log tự nhiên `math.log` và căn bậc hai để tạo đúng lượng nhiễu Gaussian theo ngân sách $\varepsilon, \delta$, re-normalize L2 bảo toàn mặt cầu đơn vị.
*   **Đồng cấu Paillier**: Được cài đặt tại `PaillierPartiallyHomomorphicEngine` (dòng 267-390). Tự viết các hàm Extended GCD `_ext_gcd` và nghịch đảo modulo `_mod_inverse` để tính toán mù dot product trên số âm/dương hoàn toàn chính xác.
*   **Shannon Entropy**: Được cài đặt tại `ShannonEntropyPoisonDetector` (dòng 395-459). Tính toán chính xác phân phối tần suất và log cơ số 2 `math.log2` để đo lường Entropy bits-per-char của đầu vào.
