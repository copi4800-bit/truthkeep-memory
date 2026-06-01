from __future__ import annotations

import math
import pytest
from aegis_py.security.privacy_guard import (
    MetricDPGaussianNoise,
    PaillierPartiallyHomomorphicEngine,
    ShannonEntropyPoisonDetector
)


def test_metric_dp_gaussian_noise():
    vector_raw = [0.8, 0.5, 0.3]
    mag_init = math.sqrt(sum(x * x for x in vector_raw))
    vector = [x / mag_init for x in vector_raw]
    assert math.sqrt(sum(x * x for x in vector)) == pytest.approx(1.0, abs=1e-5)
    
    # 2. Áp dụng bảo mật vi sai Gaussian (CMAG 2025)
    noised = MetricDPGaussianNoise.apply_metric_dp(
        vector=vector,
        epsilon=1.5,
        delta=1e-4,
        sensitivity=2.0
    )
    
    assert len(noised) == 3
    # Mặc dù bị bơm nhiễu, vector kết quả phải được re-normalize về mặt cầu L2 chính xác
    mag_noised = math.sqrt(sum(x * x for x in noised))
    assert mag_noised == pytest.approx(1.0, abs=1e-5)


def test_paillier_partially_homomorphic_cryptosystem():
    # 1. Sinh cặp khóa Paillier
    pub_key, priv_key = PaillierPartiallyHomomorphicEngine.generate_keys()
    
    # 2. Mã hóa & Giải mã số dương
    val_pos = 42
    enc_pos = PaillierPartiallyHomomorphicEngine.encrypt(val_pos, pub_key)
    dec_pos = PaillierPartiallyHomomorphicEngine.decrypt(enc_pos, priv_key)
    assert dec_pos == val_pos
    
    # 3. Mã hóa & Giải mã số âm
    val_neg = -15
    enc_neg = PaillierPartiallyHomomorphicEngine.encrypt(val_neg, pub_key)
    dec_neg = PaillierPartiallyHomomorphicEngine.decrypt(enc_neg, priv_key)
    assert dec_neg == val_neg

    # 4. Tích vô hướng đồng cấu hoàn toàn mù trên server (Homomorphic Dot Product)
    # Vector C (Client mã hóa): [10, -5]
    # Vector Q (Server nhân trực tiếp với Plaintext): [2, 3]
    # Phép toán mong đợi: 10 * 2 + (-5) * 3 = 20 - 15 = 5
    vec_c = [10, -5]
    vec_q = [2, 3]
    
    enc_vec = [PaillierPartiallyHomomorphicEngine.encrypt(x, pub_key) for x in vec_c]
    
    # Server thực hiện tích vô hướng đồng cấu mù không cần biết khóa riêng
    enc_dot_result = PaillierPartiallyHomomorphicEngine.homomorphic_dot_product(enc_vec, vec_q, pub_key)
    
    # Client giải mã kết quả
    dec_dot_result = PaillierPartiallyHomomorphicEngine.decrypt(enc_dot_result, priv_key)
    
    assert dec_dot_result == 5


def test_shannon_entropy_data_poisoning_defense():
    # 1. Văn bản bình thường có độ phân tán thông tin cao (High Entropy)
    safe_text = "The quick brown fox jumps over the lazy dog."
    entropy_safe = ShannonEntropyPoisonDetector.compute_shannon_entropy(safe_text)
    
    # 2. Văn bản bị tiêm nhiễm lặp từ độc hại hoặc Prompt Injection (Low Entropy)
    poison_text = "ATTACK ATTACK ATTACK ATTACK ATTACK ATTACK ATTACK ATTACK ATTACK ATTACK"
    entropy_poison = ShannonEntropyPoisonDetector.compute_shannon_entropy(poison_text)
    
    # Entropy văn bản bị lặp từ phải nhỏ hơn hẳn văn bản tự nhiên
    assert entropy_poison < entropy_safe
    
    # 3. Đánh giá nguy cơ
    risk_safe = ShannonEntropyPoisonDetector.assess_poison_risk(safe_text)
    risk_poison = ShannonEntropyPoisonDetector.assess_poison_risk(poison_text)
    
    assert risk_safe["status"] == "safe"
    assert risk_poison["status"] == "poison_detected"
    assert risk_poison["risk_score"] >= 0.7


def test_strict_privacy_mode_at_rest(tmp_path):
    import os
    import sqlite3
    import importlib
    from aegis_py.app import AegisApp
    from aegis_py.security import config
    
    # 1. Bật Strict Mode
    os.environ["TK_PRIVACY_MODE"] = "strict"
    os.environ["TK_MASTER_KEY"] = "my-enterprise-master-key-2026"
    importlib.reload(config)
    
    assert config.STRICT_PRIVACY_ACTIVE is True
    
    db_file = str(tmp_path / "test_strict.db")
    app = AegisApp(db_file)
    
    secret_content = "Dự án Mimi ESP32-S3 sử dụng password tối mật là Mim123!"
    
    # 2. Ghi ký ức ở strict mode
    mem_id = app.put_memory(
        content=secret_content,
        type="semantic",
        scope_type="project",
        scope_id="mimi",
        subject="credentials"
    )
    assert mem_id is not None
    
    # 3. Truy cập trực tiếp SQLite vật lý để kiểm tra xem plaintext có bị lọt xuống đĩa không
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT content, encrypted_content, metadata_json FROM memories WHERE id = ?", (mem_id.id,)).fetchone()
    conn.close()
    
    assert row is not None
    # Plaintext content tuyệt đối không được lọt xuống đĩa!
    assert secret_content not in row["content"]
    assert "password tối mật" not in row["content"]
    
    # Cột content phải chứa bản mã base64 của AES-256-GCM
    assert len(row["content"]) > len(secret_content)
    
    # 4. Đọc qua App API — xác nhận giải mã trong suốt hoàn hảo
    retrieved = app.storage.get_memory(mem_id.id)
    assert retrieved is not None
    assert retrieved.content == secret_content
    
    # 5. Tắt strict mode trong môi trường, kiểm chứng tương thích ngược vẫn giải mã thành công
    os.environ["TK_PRIVACY_MODE"] = ""
    importlib.reload(config)
    assert config.STRICT_PRIVACY_ACTIVE is False
    
    # Khởi tạo instance mới không có strict mode
    app_standard = AegisApp(db_file)
    retrieved_std = app_standard.storage.get_memory(mem_id.id)
    assert retrieved_std is not None
    assert retrieved_std.content == secret_content


def test_fts5_index_is_encrypted_at_rest(tmp_path):
    import os
    import sqlite3
    import importlib
    from aegis_py.app import AegisApp
    from aegis_py.security import config
    
    os.environ["TK_PRIVACY_MODE"] = "strict"
    os.environ["TK_MASTER_KEY"] = "my-enterprise-master-key-2026"
    importlib.reload(config)
    
    db_file = str(tmp_path / "test_fts_strict.db")
    app = AegisApp(db_file)
    
    secret_content = "Thông tin tài khoản ngân hàng tối mật là 123456789"
    mem_id = app.put_memory(
        content=secret_content,
        type="semantic",
        scope_type="project",
        scope_id="finance",
        subject="bank"
    )
    
    # Truy cập bảng FTS5 index xem plaintext FTS5 index có bị lộ không
    conn = sqlite3.connect(db_file)
    row = conn.execute("SELECT content FROM memories_fts WHERE rowid = (SELECT rowid FROM memories WHERE id = ?)", (mem_id.id,)).fetchone()
    conn.close()
    
    assert row is not None
    # Plaintext tuyệt đối không được nằm trong FTS5 index!
    assert "tài khoản ngân hàng" not in row[0]
    assert "123456789" not in row[0]
    
    # FTS5 index chỉ chứa bản mã base64 nhầy nhụa
    assert len(row[0]) > len(secret_content)
    
    # Dọn dẹp env
    os.environ["TK_PRIVACY_MODE"] = ""
    importlib.reload(config)
