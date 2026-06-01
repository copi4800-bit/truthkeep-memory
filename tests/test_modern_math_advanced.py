import math
import pytest
from aegis_py.storage.modern_math import (
    SpectralGraphEngine,
    HyperbolicGraphEngine,
    BeltramiDiffusionEngine,
)


def test_spectral_graph_engine_laplacian():
    # 1. Tạo đồ thị đường thẳng đơn giản: 0 --(1.0)-- 1 --(1.0)-- 2
    adjacency = {
        "0": {"1": 1.0},
        "1": {"0": 1.0, "2": 1.0},
        "2": {"1": 1.0},
    }

    nodes, l_sym, degrees = SpectralGraphEngine.compute_symmetric_laplacian(adjacency)

    assert nodes == ["0", "1", "2"]
    assert degrees == [1.0, 2.0, 1.0]

    # Kiểm tra các phần tử ma trận L_sym
    # L_sym[0][0] = 1, L_sym[1][1] = 1, L_sym[2][2] = 1
    # L_sym[0][1] = -1 / sqrt(1*2) = -0.7071
    # L_sym[1][2] = -1 / sqrt(2*1) = -0.7071
    assert math.isclose(l_sym[0][0], 1.0)
    assert math.isclose(l_sym[1][1], 1.0)
    assert math.isclose(l_sym[2][2], 1.0)
    assert math.isclose(l_sym[0][1], -1.0 / math.sqrt(2.0), rel_tol=1e-5)
    assert math.isclose(l_sym[1][0], -1.0 / math.sqrt(2.0), rel_tol=1e-5)


def test_spectral_graph_engine_power_iteration():
    # Đồ thị vòng tròn 4 đỉnh C_4: 0-1-2-3-0
    adjacency = {
        "0": {"1": 1.0, "3": 1.0},
        "1": {"0": 1.0, "2": 1.0},
        "2": {"1": 1.0, "3": 1.0},
        "3": {"0": 1.0, "2": 1.0},
    }

    nodes, l_sym, degrees = SpectralGraphEngine.compute_symmetric_laplacian(adjacency)
    lambda_2, v_2 = SpectralGraphEngine.power_iteration_with_deflation(l_sym, degrees)

    # Đồ thị C_4 có các trị riêng Laplacian chuẩn hóa là: 0, 1, 1, 2
    # Trị riêng nhỏ thứ hai lambda_2 (Fiedler value) của C_4 chuẩn hóa đối xứng là 1.0
    assert math.isclose(lambda_2, 1.0, abs_tol=1e-3)
    
    # Fiedler vector v_2 phải trực giao với v_1
    v_1 = [math.sqrt(d) for d in degrees]
    v_1 = SpectralGraphEngine.l2_normalize(v_1)
    dot = SpectralGraphEngine.dot_product(v_2, v_1)
    assert math.isclose(dot, 0.0, abs_tol=1e-5)


def test_hyperbolic_distance():
    # Điểm ở tâm 0
    u = [0.0, 0.0]
    v = [0.5, 0.0]

    # Khoảng cách hyperbolic từ 0 đến v=(r, 0) là 2 * arctanh(r)
    # Với r = 0.5: 2 * arctanh(0.5) = 2 * 0.549306 = 1.098612
    d_h = HyperbolicGraphEngine.poincare_distance(u, v)
    assert math.isclose(d_h, math.log(3.0), rel_tol=1e-5)


def test_geodesic_midpoint():
    # Hai điểm u và v trên đĩa Poincaré
    u = [0.2, -0.3]
    v = [-0.4, 0.5]

    mid = HyperbolicGraphEngine.geodesic_midpoint(u, v)

    # Điểm trung điểm m phải thỏa mãn d_H(u, m) == d_H(v, m) == 0.5 * d_H(u, v)
    d_uv = HyperbolicGraphEngine.poincare_distance(u, v)
    d_um = HyperbolicGraphEngine.poincare_distance(u, mid)
    d_vm = HyperbolicGraphEngine.poincare_distance(v, mid)

    assert math.isclose(d_um, d_vm, rel_tol=1e-3)
    assert math.isclose(d_um + d_vm, d_uv, rel_tol=1e-3)


def test_sinkhorn_optimal_transport():
    # Hai phân phối xác suất đơn giản trên 2 phần tử
    mu = [0.4, 0.6]
    mv = [0.5, 0.5]
    
    # Ma trận chi phí
    cost = [
        [0.1, 0.8],
        [0.9, 0.2]
    ]

    w_1 = HyperbolicGraphEngine.sinkhorn_optimal_transport(mu, mv, cost, reg=0.1)
    assert w_1 >= 0.0
    # Wasserstein thực tế không có entropy regularization khoảng 0.4*0.1 + 0.1*0.8 + 0.5*0.2 = 0.22
    # Với reg=0.1, nó sẽ xấp xỉ giá trị này
    assert 0.15 <= w_1 <= 0.35


def test_ollivier_ricci_curvature_and_surgery():
    # Tạo đồ thị 2 đỉnh u -- v liên kết với nhau
    adjacency = {
        "u": {"v": 1.0},
        "v": {"u": 1.0}
    }
    poincare_coords = {
        "u": [0.1, 0.1],
        "v": [-0.1, -0.1]
    }

    kappa = HyperbolicGraphEngine.ollivier_ricci_curvature(
        "u", "v", [], [], poincare_coords, adjacency
    )
    
    # Với đồ thị 2 đỉnh cô lập, Ollivier-Ricci curvature kappa(u,v) = 0
    # vì m_u chỉ đặt khối lượng tại u, m_v chỉ đặt khối lượng tại v, W_1 = d_H(u,v) => kappa = 1 - W_1/d_H = 0
    assert math.isclose(kappa, 0.0, abs_tol=1e-2)

    # Test phẫu thuật đồ thị
    # Nếu ta cho độ cong rất âm giả lập hoặc tọa độ khiến độ cong âm
    # (Để chắc chắn ta kiểm tra việc chèn Virtual Node)
    new_adj, new_coords, surgery = HyperbolicGraphEngine.graph_surgery(
        adjacency, poincare_coords, threshold=1.1
    )
    
    assert len(surgery) == 1
    event = surgery[0]
    assert event["source"] == "u"
    assert event["target"] == "v"
    virtual_node = event["virtual_node"]
    assert virtual_node in new_adj
    assert "u" in new_adj[virtual_node]
    assert "v" in new_adj[virtual_node]
    assert virtual_node in new_coords


def test_beltrami_diffusion():
    # Đặc trưng của 2 đỉnh
    features = {
        "0": [1.0, 0.0],
        "1": [0.0, 1.0]
    }
    adjacency = {
        "0": {"1": 1.0},
        "1": {"0": 1.0}
    }

    # Tính toán hệ số Perona-Malik
    g = BeltramiDiffusionEngine.perona_malik_coefficient(features["0"], features["1"], contrast_parameter=1.0)
    # ||[1,0] - [0,1]||^2 = (1-0)^2 + (0-1)^2 = 2.0
    # g = exp(-2.0 / 1.0) = exp(-2) = 0.135335
    assert math.isclose(g, math.exp(-2.0), rel_tol=1e-5)

    # Chạy 1 bước diffusion Beltrami
    new_features = BeltramiDiffusionEngine.beltrami_diffusion_step(
        features, adjacency, dt=0.5, contrast_parameter=1.0
    )

    # Kiểm tra chuẩn L2 của các đặc trưng sau khi khuếch tán luôn bằng 1.0
    mag_0 = math.sqrt(sum(x*x for x in new_features["0"]))
    mag_1 = math.sqrt(sum(x*x for x in new_features["1"]))
    assert math.isclose(mag_0, 1.0, rel_tol=1e-5)
    assert math.isclose(mag_1, 1.0, rel_tol=1e-5)


def test_chebyshev_fhe_evaluation():
    """Test xấp xỉ đa thức Chebyshev trực giao tính hàm Perona-Malik đồng cấu mù trên Ring-LWE."""
    from aegis_py.security.fhe import RingLWEFHEEngine, ChebyshevFHEEngine
    
    # 1. Khởi tạo Ring-LWE với modulus lớn
    fhe_engine = RingLWEFHEEngine(scaling_factor=1000.0, q=8380417)
    sk = fhe_engine.generate_secret_key()
    
    # Khoảng cách Euclid bình phương thực tế z = 0.5. Hệ số K = 1.0
    z = [0.5] + [0.0] * 255
    
    # 2. Client mã hóa z
    c0, c1 = fhe_engine.encrypt_vector(z, sk)
    # Nâng tỉ lệ lên scale_sq để giả lập đúng kết quả nhân chập đồng cấu thực tế
    c0_scaled = [(x * int(fhe_engine.scale)) % fhe_engine.q for x in c0]
    c1_scaled = [(x * int(fhe_engine.scale)) % fhe_engine.q for x in c1]
    enc_z = (c0_scaled, c1_scaled, [0] * 256)  # Ciphertext bậc 2 mô phỏng kết quả nhân chập
    
    # 3. Tính toán các hệ số Chebyshev m = 1 (tuyến tính hóa trực giao triệt tiêu nhiễu Ring-LWE)
    cheb = ChebyshevFHEEngine(fhe_engine)
    coeffs = cheb.compute_chebyshev_coefficients(k=1.0, r_bound=4.0, m_order=1)
    
    # 4. Máy chủ thực hiện homomorphic Chebyshev evaluation hoàn toàn mù
    enc_res = cheb.homomorphic_chebyshev_evaluation(enc_z, coeffs, r_bound=4.0)
    
    # 5. Client giải mã và khôi phục giá trị y đồng cấu, sau đó tự tính giá trị khuếch tán g(z) trên bản rõ
    y_decrypted = fhe_engine.decrypt_score(enc_res, sk, dimension=256)
    
    # Client tự tính giá trị g(z) từ y trên bản rõ bằng công thức xấp xỉ Chebyshev m=1
    g_decrypted = coeffs[0] / 2.0 + coeffs[1] * y_decrypted
    
    # Giá trị Perona-Malik gốc: exp(-0.5 / 1.0) = exp(-0.5) = 0.60653
    g_expected = math.exp(-0.5)
    
    # Sai số xấp xỉ Chebyshev trực giao kết hợp nhiễu Ring-LWE giải mã cực nhỏ (< 0.05)
    assert abs(g_decrypted - g_expected) < 0.05


def test_euler_lagrange_variational_k_adaptation():
    """Test co giãn tự động tham số K mượt mà qua phương trình Euler-Lagrange damped oscillator."""
    from aegis_py.storage.modern_math import EulerLagrangeVariationalEngine
    
    # 1. Đồ thị 4 đỉnh có bậc
    degrees = [3.0, 1.0, 1.0, 1.0]  # Đồ thị hình sao 4 đỉnh
    
    entropy = EulerLagrangeVariationalEngine.compute_shannon_entropy(degrees)
    # H = - (3/6*ln(3/6) + 3 * (1/6*ln(1/6))) = - (0.5 * -0.693 + 0.5 * -1.791) = 0.346 + 0.895 = 1.242
    assert 1.0 <= entropy <= 1.5
    
    # 2. Giả lập co giãn K mượt mà qua Euler-Lagrange tắt dần
    k_val = 0.8
    velocity = 0.0
    dt = 0.1
    
    # Giả lập Entropy thấp -> K_opt ổn định cao
    for _ in range(10):
        k_val, velocity = EulerLagrangeVariationalEngine.damped_oscillator_step(
            k_val, velocity, entropy=0.2, dt=dt, k_spring=0.5, gamma=0.8
        )
    # K phải mượt mà dao động tắt dần tiến về K_opt = 0.8 * exp(-0.2/2) = 0.72
    assert 0.65 <= k_val <= 0.80
    
    # Giả lập Entropy tăng vọt (nhiễu cực lớn) -> Euler-Lagrange kéo K co lại để bảo tồn ký ức
    k_val = 0.8
    velocity = 0.0
    for _ in range(50):
        k_val, velocity = EulerLagrangeVariationalEngine.damped_oscillator_step(
            k_val, velocity, entropy=3.0, dt=dt, k_spring=0.5, gamma=0.8
        )
    # K_opt mới = 0.8 * exp(-3.0/2) = 0.178 -> K phải giảm sâu mượt mà để siết ranh giới
    assert k_val < 0.4
    assert k_val >= 0.1  # Giới hạn an toàn vật lý của K

