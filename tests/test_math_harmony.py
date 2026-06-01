from __future__ import annotations

import math
import pytest
from aegis_py.storage.modern_math import (
    ForceDirectedPoincareEngine,
    MarkovChainCognitiveEngine,
    DirichletHarmonicEngine,
    TopologicalHoleDetector,
    CategoryTheoryFunctorEngine
)



def test_force_directed_poincare_layout():
    # 1. Tạo 3 node trong đĩa Poincaré
    # Node A và Node B có mối quan hệ supports (hút nhau)
    # Node A và Node C có mối quan hệ contradicts (đẩy nhau mạnh)
    nodes = {
        "A": [0.1, 0.0],
        "B": [0.2, 0.0],
        "C": [0.12, 0.0]
    }
    
    links = [
        {"source": "A", "target": "B", "link_type": "supports", "weight": 0.9},
        {"source": "A", "target": "C", "link_type": "contradicts", "weight": 1.0}
    ]
    
    # Đo khoảng cách ban đầu
    dist_ab_init = ForceDirectedPoincareEngine.poincare_distance(nodes["A"], nodes["B"])
    dist_ac_init = ForceDirectedPoincareEngine.poincare_distance(nodes["A"], nodes["C"])
    
    # Chạy tối ưu lực định hướng Poincaré
    optimized = ForceDirectedPoincareEngine.optimize_layout(
        nodes=nodes,
        links=links,
        iterations=30,
        learning_rate=0.08,
        repulsion_constant=0.05,
        attraction_constant=0.1
    )
    
    dist_ab_opt = ForceDirectedPoincareEngine.poincare_distance(optimized["A"], optimized["B"])
    dist_ac_opt = ForceDirectedPoincareEngine.poincare_distance(optimized["A"], optimized["C"])
    
    # Lực đẩy Coulomb giữa A và C phải làm chúng cách xa nhau hơn ban đầu
    assert dist_ac_opt > dist_ac_init
    
    # Kiểm tra toàn bộ tọa độ nằm trong đĩa Poincaré (L2 norm < 0.98)
    for k, coords in optimized.items():
        norm = math.sqrt(sum(x * x for x in coords))
        assert norm <= 0.98
        assert norm >= 0.05


def test_markov_chain_cognitive_diffusion():
    # Đồ thị 3 nút có ma trận kề (đầy đủ quan hệ)
    # A -> B (weight 0.8), A -> C (weight 0.2)
    # B -> A (weight 0.5), B -> C (weight 0.5)
    # C -> A (weight 1.0)
    adj_matrix = [
        [0.0, 0.8, 0.2],
        [0.5, 0.0, 0.5],
        [1.0, 0.0, 0.0]
    ]
    
    # 1. Tính toán phân phối dừng
    pi = MarkovChainCognitiveEngine.compute_stationary_distribution(adj_matrix, max_iterations=100)
    assert len(pi) == 3
    assert sum(pi) == pytest.approx(1.0, abs=1e-5)
    # Nút A nhận nhiều luồng nhất (C đổ 100% vào A, B đổ 50% vào A) nên pi[0] phải lớn nhất
    assert pi[0] > pi[1]
    assert pi[0] > pi[2]
    
    # 2. Lan truyền đính chính thông tin vô hạn tầng qua chuỗi Markov
    accumulated = MarkovChainCognitiveEngine.propagate_correction_markov(
        start_node_index=0,
        adj_matrix=adj_matrix,
        initial_delta=1.0,
        steps=5,
        decay_factor=0.75
    )
    assert len(accumulated) == 3
    # Nút gốc bắt đầu có tác động lớn nhất
    assert accumulated[0] > 1.0
    # Các nút phụ thuộc B và C cũng nhận được mức lan truyền giảm chấn tự nhiên khác không
    assert accumulated[1] > 0.0
    assert accumulated[2] > 0.0


def test_dirichlet_harmonic_belief_inference():
    # Đồ thị chuỗi tuyến tính 3 nút: A - B - C
    # A kết nối với B, B kết nối với C
    # Ma trận kề đối xứng
    adj_matrix = [
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
        [0.0, 1.0, 0.0]
    ]
    
    # Cố định điều kiện biên:
    # Nút A (Neo sự thật cốt lõi) = 1.0 (Tuyệt đối Đúng)
    # Nút C (Rìa mâu thuẫn) = 0.0 (Tuyệt đối Sai)
    # Nút B ở giữa chưa được dán nhãn (unlabeled)
    labeled_indices = {
        0: 1.0,
        2: 0.0
    }
    
    scores = DirichletHarmonicEngine.solve_harmonic_scores(
        adjacency_matrix=adj_matrix,
        labeled_indices=labeled_indices,
        max_iterations=100
    )
    
    assert len(scores) == 3
    # Biên được giữ cố định
    assert scores[0] == 1.0
    assert scores[2] == 0.0
    # Nút B ở giữa chịu tác động điều hòa của A và C: f(B) = (f(A) * w_AB + f(C) * w_BC) / (w_AB + w_BC)
    # Vì w_AB = w_BC = 1.0, f(B) phải hội tụ về đúng 0.5 (trung bình điều hòa)!
    assert scores[1] == pytest.approx(0.5, abs=1e-3)


def test_topological_hole_detection():
    # Đồ thị 4 nút khép kín vòng tròn không có đường chéo
    logic_graph = {
        "ESP32": ["Bluetooth", "UART_Flash"],
        "Bluetooth": ["ESP32", "RobotApp"],
        "RobotApp": ["Bluetooth", "UART_Flash"],
        "UART_Flash": ["ESP32", "RobotApp"]
    }
    
    holes = TopologicalHoleDetector.detect_logic_voids(logic_graph)
    assert len(holes) == 2  # 2 hướng xoay của cùng 1 chu trình đơn
    assert "ESP32" in holes[0]
    assert "RobotApp" in holes[0]


def test_category_functor_analogy():
    # Phạm trù C: Hệ Mặt Trời
    solar_system = {
        "Sun": [("Planet", "supports")],
        "Planet": [("Sun", "depends_on")]
    }
    
    # Phạm trù D: Mô hình Nguyên tử Rutherford-Bohr
    atomic_model = {
        "Nucleus": [("Electron", "supports")],
        "Electron": [("Nucleus", "depends_on")]
    }
    
    functor_mapping = CategoryTheoryFunctorEngine.find_functorial_analogy(solar_system, atomic_model)
    assert functor_mapping is not None
    assert functor_mapping["Sun"] == "Nucleus"
    assert functor_mapping["Planet"] == "Electron"

