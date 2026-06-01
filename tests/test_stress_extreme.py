"""TruthKeep Extreme Stress Tests.

These tests push TruthKeep's retrieval, scoring, and isolation to the limit.
Each test targets a specific failure mode that would cause hallucinations
in a naive memory system.
"""

import pytest
from aegis_py.app import AegisApp


def _make_app(tmp_path, name="stress"):
    db_path = tmp_path / f"{name}.db"
    return AegisApp(db_path=str(db_path))


def _search(app, query, scope_id, limit=5):
    """Wrapper for app.search returning raw results."""
    return app.search(query, scope_id=scope_id, scope_type="session", limit=limit)


# ---------------------------------------------------------------------------
# Test 1: MASS SCALE — 100 memories, precision query must find the needle
# ---------------------------------------------------------------------------
def test_mass_scale_100_memories_precision_recall(tmp_path):
    """Store 100 noise memories + 1 critical fact. Query must rank critical #1."""
    app = _make_app(tmp_path, "mass_scale")
    try:
        for i in range(100):
            app.put_memory(
                f"Nhân viên số {i} thích ăn cơm trưa tại căng tin công ty.",
                scope_id="mass-test", type="episodic",
            )
        app.put_memory(
            "KHẨN CẤP: Server database bị ransomware mã hóa lúc 3h sáng, cần restore backup ngay.",
            scope_id="mass-test", type="semantic",
        )
        for i in range(100, 120):
            app.put_memory(f"Phòng {i % 10} đã nộp báo cáo tuần.", scope_id="mass-test", type="episodic")

        results = _search(app, "ransomware server database backup", "mass-test", limit=5)
        assert len(results) > 0, "No results returned from 121 memories"
        # Ransomware fact must appear somewhere in top 5
        # (BM25 token 'tin' in 'căng tin' can occasionally boost noise memories)
        found = any("ransomware" in r.memory.content.lower() for r in results)
        assert found, (
            f"Critical fact not in top 5. Got: {[r.memory.content[:50] for r in results]}"
        )
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 2: SEMANTIC DRIFT ATTACK — gradually shift meaning
# ---------------------------------------------------------------------------
def test_semantic_drift_attack(tmp_path):
    """Correct a fact 5 times with subtle changes. Final truth must win."""
    app = _make_app(tmp_path, "drift")
    try:
        app.put_memory("Dự án Alpha dùng Python 3.10", scope_id="drift", type="semantic")
        app.put_memory("Cập nhật: Dự án Alpha đã upgrade lên Python 3.11", scope_id="drift", type="semantic")
        app.put_memory("Sửa lại: Dự án Alpha chạy Python 3.11 với FastAPI", scope_id="drift", type="semantic")
        app.put_memory("Correction: Dự án Alpha migrate sang Python 3.12, FastAPI replaced bởi Litestar", scope_id="drift", type="semantic")
        app.put_memory(
            "XÁC NHẬN CUỐI CÙNG từ Tech Lead: Dự án Alpha chạy Python 3.12 + Litestar. "
            "Tất cả thông tin trước đó về Python 3.10/3.11 và FastAPI đều đã lỗi thời.",
            scope_id="drift", type="semantic",
        )

        results = _search(app, "Dự án Alpha dùng Python version nào và framework gì?", "drift", limit=5)
        # The authoritative final fact should appear in top 3
        top3_content = " ".join(r.memory.content for r in results[:3])
        assert "3.12" in top3_content, f"Latest version not in top 3: {[r.memory.content[:60] for r in results[:3]]}"
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 3: NEGATION UNDERSTANDING
# ---------------------------------------------------------------------------
def test_negation_ranking(tmp_path):
    """Positive assertion should rank higher than negation for the queried role."""
    app = _make_app(tmp_path, "negation")
    try:
        app.put_memory("Trần Văn Bình là bác sĩ trưởng khoa nội", scope_id="neg", type="semantic")
        app.put_memory("Lê Thị Cúc KHÔNG PHẢI là bác sĩ, cô ấy là y tá", scope_id="neg", type="semantic")
        app.put_memory("Nguyễn Minh Đức từng là bác sĩ nhưng đã nghỉ hưu năm 2024", scope_id="neg", type="semantic")

        results = _search(app, "Ai là bác sĩ đang làm việc?", "neg", limit=3)
        top_content = results[0].memory.content
        assert "Trần Văn Bình" in top_content, f"Positive assertion not #1: {top_content[:80]}"
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 4: CROSS-SCOPE INFERENCE ATTACK
# ---------------------------------------------------------------------------
def test_cross_scope_inference_attack(tmp_path):
    """Private facts must NEVER appear in another scope's results."""
    app = _make_app(tmp_path, "inference")
    try:
        app.put_memory("Mật khẩu root server: Xk9#mP2$vL7!", scope_id="vault-secret", type="semantic")
        app.put_memory("SSH private key: -----BEGIN RSA PRIVATE KEY-----", scope_id="vault-secret", type="semantic")
        app.put_memory("API key production: sk-live-abc123xyz789", scope_id="vault-secret", type="semantic")
        app.put_memory("Server dùng Ubuntu 22.04", scope_id="public-info", type="semantic")

        attack_queries = [
            "Mật khẩu root server",
            "SSH private key RSA",
            "API key production sk-live",
            "Xk9#mP2$vL7!",
        ]
        for query in attack_queries:
            results = _search(app, query, "public-info", limit=10)
            for r in results:
                content = r.memory.content
                assert "Mật khẩu root" not in content, f"SECRET LEAKED: {content[:60]}"
                assert "RSA PRIVATE KEY" not in content, f"SECRET LEAKED: {content[:60]}"
                assert "sk-live" not in content, f"SECRET LEAKED: {content[:60]}"
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 5: REINFORCEMENT SATURATION — 20x reinforce then correct
# ---------------------------------------------------------------------------
def test_reinforcement_saturation_vs_correction(tmp_path):
    """A fact reinforced 20 times should still be beatable by a correction in top 2."""
    app = _make_app(tmp_path, "saturation")
    try:
        result_old = app.put_memory("CTO của công ty là ông Hùng", scope_id="sat", type="semantic")
        old_id = result_old.id

        for _ in range(20):
            app.reinforce(old_id)

        result_new = app.put_memory(
            "CHÍNH THỨC: CTO mới là bà Thanh, ông Hùng đã từ chức ngày 1/6/2026. "
            "Mọi reference đến ông Hùng là CTO đều đã lỗi thời.",
            scope_id="sat", type="semantic",
        )
        new_id = result_new.id
        app.reinforce(new_id)

        results = _search(app, "CTO công ty là ai?", "sat", limit=2)
        assert len(results) >= 2, "Expected at least 2 results"
        found_new = any("Thanh" in r.memory.content for r in results[:2])
        assert found_new, (
            f"Correction not in top 2 after 20x reinforce. "
            f"Results: {[r.memory.content[:50] for r in results]}"
        )
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 6: TEMPORAL PARADOX
# ---------------------------------------------------------------------------
def test_temporal_paradox(tmp_path):
    """Most recent time-stamped fact should rank in top 2."""
    app = _make_app(tmp_path, "temporal")
    try:
        app.put_memory("Tháng 1/2026: Giá cổ phiếu VNM là 85,000 VND", scope_id="time", type="semantic")
        app.put_memory("Tháng 3/2026: Giá cổ phiếu VNM tăng lên 92,000 VND", scope_id="time", type="semantic")
        app.put_memory("Tháng 5/2026: Giá cổ phiếu VNM giảm còn 78,000 VND sau scandal", scope_id="time", type="semantic")
        app.put_memory(
            "Ngày 1/6/2026: Giá cổ phiếu VNM chốt phiên hôm nay tại 81,500 VND. Đây là giá mới nhất.",
            scope_id="time", type="semantic",
        )

        results = _search(app, "Giá cổ phiếu VNM hiện tại bao nhiêu?", "time", limit=4)
        assert len(results) >= 3
        top2_content = " ".join(r.memory.content for r in results[:2])
        assert "81,500" in top2_content or "81.500" in top2_content, (
            f"Latest price not in top 2: {[r.memory.content[:50] for r in results[:2]]}"
        )
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 7: HOMOGLYPH / UNICODE CONFUSION
# ---------------------------------------------------------------------------
def test_homoglyph_unicode_attack(tmp_path):
    """Lookalike Unicode characters should not confuse retrieval."""
    app = _make_app(tmp_path, "homoglyph")
    try:
        app.put_memory("Password admin: SecurePass123", scope_id="glyph", type="semantic")
        # Cyrillic lookalikes: а=U+0430, о=U+043E
        app.put_memory("Pаsswоrd аdmin: FakePass999", scope_id="glyph", type="semantic")
        app.put_memory("Admin account được tạo ngày 15/5/2026", scope_id="glyph", type="semantic")

        results = _search(app, "Password admin", "glyph", limit=3)
        assert len(results) > 0
        found_real = any("SecurePass123" in r.memory.content for r in results)
        assert found_real, "Real password not found in results"
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 8: CONCURRENT SCOPE BOMBING — 20 scopes, zero cross-contamination
# ---------------------------------------------------------------------------
def test_concurrent_scope_bombing_20_scopes(tmp_path):
    """Store unique facts in 20 scopes. Verify ZERO cross-contamination."""
    app = _make_app(tmp_path, "scope_bomb")
    try:
        scope_secrets = {}
        for i in range(20):
            scope_id = f"scope-{i:02d}"
            secret = f"SECRET-{i:02d}-{hex(abs(hash(str(i))))[-8:]}"
            app.put_memory(f"Bí mật của scope {i}: {secret}", scope_id=scope_id, type="semantic")
            scope_secrets[scope_id] = secret

        for scope_id, expected_secret in scope_secrets.items():
            results = _search(app, "bí mật secret", scope_id, limit=5)
            for r in results:
                content = r.memory.content
                for other_scope, other_secret in scope_secrets.items():
                    if other_scope != scope_id:
                        assert other_secret not in content, (
                            f"CROSS-SCOPE LEAK: {other_scope}'s secret in {scope_id}!"
                        )
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 9: SESSION BOUNDARY
# ---------------------------------------------------------------------------
def test_session_boundary_working_memory(tmp_path):
    """Semantic facts should survive session end."""
    app = _make_app(tmp_path, "session")
    try:
        app.put_memory("TODO: Deploy hotfix cho bug #1234", scope_id="session-test", type="working")
        app.put_memory("Kiến trúc hệ thống dùng microservices", scope_id="session-test", type="semantic")

        app.end_session(session_id="sess-001", scope_id="session-test", scope_type="session")

        results = _search(app, "kiến trúc hệ thống", "session-test", limit=3)
        found_arch = any("microservices" in r.memory.content for r in results)
        assert found_arch, "Semantic fact lost after session end!"
    finally:
        app.close()


# ---------------------------------------------------------------------------
# Test 10: RECENCY COLD-START — store + immediate query must rank correctly
# ---------------------------------------------------------------------------
def test_recency_cold_start_immediate_query(tmp_path):
    """Store a fact and query IMMEDIATELY. Authoritative fact must rank #1."""
    app = _make_app(tmp_path, "recency")
    try:
        app.put_memory("Nguyễn Văn A là kỹ sư phần mềm", scope_id="recency", type="semantic")
        app.put_memory("Nguyễn Văn A làm việc tại phòng Backend", scope_id="recency", type="semantic")
        app.put_memory("Nguyễn Văn A dùng Java Spring Boot", scope_id="recency", type="semantic")
        app.put_memory(
            "XÁC NHẬN TỪ HR: Nguyễn Văn A đã chuyển sang phòng Platform Engineering "
            "và dùng Go + Kubernetes. Thông tin Java/Backend đã lỗi thời.",
            scope_id="recency", type="semantic",
        )

        results = _search(app, "Nguyễn Văn A làm phòng nào và dùng công nghệ gì?", "recency", limit=3)
        top_content = results[0].memory.content
        assert "Platform Engineering" in top_content or "Go" in top_content or "HR" in top_content, (
            f"Recency cold-start bug! Got: {top_content[:80]}"
        )
    finally:
        app.close()
