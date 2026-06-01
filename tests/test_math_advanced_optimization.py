from __future__ import annotations

import math
import pytest
from aegis_py.security.fhe import (
    power_iteration,
    extract_top_k_eigen,
    anisotropy_whitening_projection
)
from aegis_py.storage.modern_math import (
    MiniCSRMatrix,
    HyperbolicGraphEngine
)


def test_power_iteration_and_deflation():
    # 1. Tạo ma trận hiệp phương sai sigma giả lập 3 chiều
    # Trị riêng lớn nhất sẽ lệch hẳn về hướng [1, 1, 1]
    sigma = [
        [2.0, 1.0, 1.0],
        [1.0, 2.0, 1.0],
        [1.0, 1.0, 2.0]
    ]
    
    # 2. Tìm dominant eigenpair
    val, vec = power_iteration(sigma, num_simulations=30)
    
    # Ma trận này có trị riêng lớn nhất là 4.0 với vector riêng tương ứng là [1/sqrt(3), 1/sqrt(3), 1/sqrt(3)]
    assert val == pytest.approx(4.0, abs=1e-3)
    assert abs(vec[0]) == pytest.approx(1.0 / math.sqrt(3.0), abs=1e-3)
    assert abs(vec[1]) == pytest.approx(1.0 / math.sqrt(3.0), abs=1e-3)
    assert abs(vec[2]) == pytest.approx(1.0 / math.sqrt(3.0), abs=1e-3)
    
    # 3. Trích xuất top k trị riêng (k=2) qua Deflation
    eigenpairs = extract_top_k_eigen(sigma, k=2)
    assert len(eigenpairs) == 2
    assert eigenpairs[0][0] == pytest.approx(4.0, abs=1e-3)
    # Trị riêng thứ hai của ma trận này là 1.0
    assert eigenpairs[1][0] == pytest.approx(1.0, abs=1e-3)


def test_anisotropy_whitening_projection():
    # Giả lập 5 vector embedding bị gom vào một hình nón hẹp (Anisotropy)
    embeddings = [
        [0.85, 0.86, 0.84],
        [0.86, 0.88, 0.85],
        [0.84, 0.85, 0.83],
        [0.87, 0.89, 0.86],
        [0.85, 0.87, 0.84]
    ]
    
    # Chạy làm trắng bẻ thẳng hình nón ngữ nghĩa (k=1)
    projected = anisotropy_whitening_projection(embeddings, k=1)
    
    # Tính ma trận hiệp phương sai mới để xem năng lượng của dominant eigenvector đã bị trừ khử chưa
    n = len(projected)
    d = len(projected[0])
    mu = [sum(row[j] for row in projected) / n for j in range(d)]
    
    sigma_new = [[0.0] * d for _ in range(d)]
    for row in projected:
        diff = [row[j] - mu[j] for j in range(d)]
        for i in range(d):
            for j in range(d):
                sigma_new[i][j] += diff[i] * diff[j]
    sigma_new = [[val / n for val in row] for row in sigma_new]
    
    # Trị riêng lớn nhất của ma trận hiệp phương sai mới phải xấp xỉ 0 (vì đã bị subspace projection loại bỏ trục anisotropy)
    val_new, _ = power_iteration(sigma_new)
    assert val_new < 1e-4


def test_mini_csr_and_sparse_sinkhorn():
    # 1. Tạo ma trận chi phí cost_matrix 4x4
    cost_matrix = [
        [0.1, 0.8, 0.9, 1.2],
        [0.8, 0.1, 0.7, 0.9],
        [0.9, 0.7, 0.2, 0.8],
        [1.2, 0.9, 0.8, 0.1]
    ]
    
    mu = [0.25, 0.25, 0.25, 0.25]
    mv = [0.25, 0.25, 0.25, 0.25]
    
    # 2. Xây dựng MiniCSRMatrix từ cost_matrix
    reg = 0.2
    csr = MiniCSRMatrix.from_dense_cost(cost_matrix, reg=reg, threshold=1e-3)
    
    assert csr.shape == (4, 4)
    # Dòng đầu tiên K_00 = exp(-0.1/0.2) = 0.606, K_03 = exp(-1.2/0.2) = 0.002
    # Vì threshold là 1e-3, tất cả 4 phần tử đều được giữ hoặc ít nhất phần tử 1.2 bị loại bỏ
    assert len(csr.values) > 0
    
    # 3. Tính toán Wasserstein distance thưa và dày để so sánh
    w1_dense = HyperbolicGraphEngine.sinkhorn_optimal_transport(mu, mv, cost_matrix, reg=reg, max_iterations=20)
    w1_sparse = HyperbolicGraphEngine.sinkhorn_optimal_transport_sparse(mu, mv, cost_matrix, reg=reg, max_iterations=20, threshold=1e-4)
    
    # Kết quả thưa phải tiệm cận hoàn hảo với kết quả dày (chênh lệch cực nhỏ < 0.005)
    assert w1_sparse == pytest.approx(w1_dense, abs=0.005)
