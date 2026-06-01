from __future__ import annotations

import pytest
from datetime import datetime, timezone

from aegis_py.storage.models import Memory
from aegis_py.graph.relation_types import RelationType
from aegis_py.graph.traversal import expand_graph, TraversalMode
from aegis_py.graph.scoring import compute_graph_score
from aegis_py.graph.explain import explain_graph_path, explain_why_not
from aegis_py.invariants.graph import validate_graph_invariants, GraphInvariantViolationException
from aegis_py.memory.ingest import IngestEngine


def create_test_memory(id_val: str, content: str, subject: str, scope_type: str = "agent", scope_id: str = "xiaozhi", status: str = "active", confidence: float = 0.9) -> Memory:
    return Memory(
        id=id_val,
        content=content,
        subject=subject,
        scope_type=scope_type,
        scope_id=scope_id,
        status=status,
        confidence=confidence,
        type="semantic",
        source_kind="manual",
        source_ref="test",
        access_count=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        last_accessed_at=datetime.now(timezone.utc),
    )


def test_relation_taxonomy_and_graph_repository(runtime_harness):
    storage = runtime_harness.storage
    
    # Tạo các node cùng scope
    m1 = create_test_memory("mem1", "Ký ức gốc về ESP32", "esp32_core")
    m2 = create_test_memory("mem2", "Ký ức đính chính về ESP32 S3", "esp32_core")
    runtime_harness.put(m1)
    runtime_harness.put(m2)
    
    # 1. Thử tạo liên kết không hợp lệ
    with pytest.raises(ValueError, match="Invalid relation type"):
        storage.graph.upsert_memory_link(
            source_id="mem1",
            target_id="mem2",
            link_type="quantum_teleportation"  # Loại quan hệ không có trong taxonomy
        )
        
    # 2. Thử tạo liên kết chéo scope
    m_cross = create_test_memory("mem_cross", "Ký ức ở scope khác", "esp32_core", scope_id="other_agent")
    runtime_harness.put(m_cross)
    
    with pytest.raises(ValueError, match="Cross-scope memory links are not allowed"):
        storage.graph.upsert_memory_link(
            source_id="mem1",
            target_id="mem_cross",
            link_type=RelationType.SUPPORTS.value
        )
        
    # 3. Tạo liên kết hợp lệ
    link = storage.graph.upsert_memory_link(
        source_id="mem1",
        target_id="mem2",
        link_type=RelationType.SUPERSEDED_BY.value,
        weight=0.8
    )
    
    assert link["link_type"] == RelationType.SUPERSEDED_BY.value
    assert link["weight"] == 0.8


def test_direction_aware_traversal_and_leak_prevention(runtime_harness):
    storage = runtime_harness.storage
    
    # Tạo các node thuộc 2 scope khác nhau
    m1 = create_test_memory("mem1", "ESP32 có 2 cores", "esp32_cores", scope_id="xiaozhi")
    m2 = create_test_memory("mem2", "Hỗ trợ nạp ROM qua UART", "rom_flash", scope_id="xiaozhi")
    runtime_harness.put(m1)
    runtime_harness.put(m2)
    
    # Cạnh hợp lệ cùng scope
    storage.graph.upsert_memory_link(
        source_id="mem1",
        target_id="mem2",
        link_type=RelationType.SUPPORTS.value,
        weight=0.9
    )
    
    # Lấy lân cận
    links = expand_graph(
        storage,
        seed_ids=["mem1"],
        mode=TraversalMode.CURRENT_TRUTH,
        scope_type="agent",
        scope_id="xiaozhi"
    )
    
    assert len(links) == 1
    assert links[0]["neighbor_id"] == "mem2"
    assert links[0]["link_type"] == "supports"
    
    # Lọc scope kiểm chứng Cross-Scope Leak
    # Nếu truy vấn với scope_id="other_agent", không được lấy ra bất kỳ cạnh nào
    links_leak = expand_graph(
        storage,
        seed_ids=["mem1"],
        mode=TraversalMode.CURRENT_TRUTH,
        scope_type="agent",
        scope_id="other_agent"
    )
    assert len(links_leak) == 0


def test_graph_aware_scoring_and_path_explanation(runtime_harness):
    storage = runtime_harness.storage
    
    # Tạo các node
    m1 = create_test_memory("mem1", "ESP32 S3 chip", "esp32_s3")
    m2 = create_test_memory("mem2", "Bản ghi chứng cứ hỗ trợ ESP32 S3", "esp32_s3")
    runtime_harness.put(m1)
    runtime_harness.put(m2)
    
    storage.graph.upsert_memory_link(
        source_id="mem2",
        target_id="mem1",
        link_type=RelationType.EVIDENCE_FOR.value,
        weight=0.8
    )
    
    # 1. Kiểm thử compute_graph_score
    score = compute_graph_score(storage, "mem1", "agent", "xiaozhi")
    # mem1 là target của EVIDENCE_FOR từ mem2 => cộng bonus: 0.8 * 0.25 = 0.20
    assert score == pytest.approx(0.20)
    
    # 2. Kiểm thử explain_graph_path
    explanation = explain_graph_path(storage, "mem2", "mem1", "agent", "xiaozhi")
    assert explanation["found"] is True
    assert "là bằng chứng cho" in explanation["explanation"]
    
    # 3. Kiểm thử explain_why_not
    # Sửa mem2 thành superseded
    storage.execute("UPDATE memories SET status = 'superseded' WHERE id = 'mem2'")
    storage.graph.upsert_memory_link(
        source_id="mem2",
        target_id="mem1",
        link_type=RelationType.SUPERSEDED_BY.value,
        weight=0.95
    )
    
    why_not = explain_why_not(storage, "mem2", "agent", "xiaozhi")
    assert why_not["status"] == "superseded"
    assert "bị thay thế hoàn toàn bởi ký ức mới hơn [mem1]" in why_not["explanation"]


def test_graph_invariants_strict_and_graceful(runtime_harness):
    storage = runtime_harness.storage
    
    # 1. No supersedes cycle (Strict Mode)
    m1 = create_test_memory("mem1", "ESP32", "esp32")
    m2 = create_test_memory("mem2", "ESP32 S2", "esp32")
    m3 = create_test_memory("mem3", "ESP32 S3", "esp32")
    runtime_harness.put(m1)
    runtime_harness.put(m2)
    runtime_harness.put(m3)
    
    storage.graph.upsert_memory_link(source_id="mem1", target_id="mem2", link_type=RelationType.SUPERSEDES.value)
    storage.graph.upsert_memory_link(source_id="mem2", target_id="mem3", link_type=RelationType.SUPERSEDES.value)
    storage.graph.upsert_memory_link(source_id="mem3", target_id="mem1", link_type=RelationType.SUPERSEDES.value) # Tạo chu trình
    
    with pytest.raises(GraphInvariantViolationException, match="Supersedes Cycle Detected"):
        validate_graph_invariants(storage, "agent", "xiaozhi", strict=True)
        
    # 2. Contradiction unresolved (Graceful Mode)
    # Xóa chu trình trước
    storage.execute("DELETE FROM memory_links")
    storage.graph.upsert_memory_link(source_id="mem1", target_id="mem2", link_type=RelationType.CONTRADICTS.value, weight=0.75)
    
    # Lúc này 2 node vẫn đang status = 'active', kiểm tra graceful
    report = validate_graph_invariants(storage, "agent", "xiaozhi", strict=False)
    assert report.contradiction_resolved is False
    assert "Graceful Action" in report.violations[-1]
    
    # Sau khi chạy graceful mode, status của cả hai phải chuyển về 'reconcile_required'
    m1_updated = storage.get_memory("mem1")
    m2_updated = storage.get_memory("mem2")
    assert m1_updated.status == "reconcile_required"
    assert m2_updated.status == "reconcile_required"
    
    # Đồng thời sinh ra bản ghi xung đột trong bảng conflicts
    conflict = storage.fetch_one("SELECT * FROM conflicts WHERE memory_a_id = 'mem1' AND memory_b_id = 'mem2'")
    assert conflict is not None
    assert conflict["score"] == 0.75


def test_correction_backpropagation_and_audit(runtime_harness):
    storage = runtime_harness.storage
    pipeline = runtime_harness.pipeline
    
    # Kích hoạt backprop
    from aegis_py.config import features
    features.ENABLE_BACKPROP = True
    
    # Tạo IngestEngine
    ingest_engine = IngestEngine(storage, search_pipeline=pipeline)
    
    # Tạo 1 chain dependencies: mem1 (mới, correct) -> mem2 (phụ thuộc 1 hop) -> mem3 (phụ thuộc 2 hops)
    m1 = create_test_memory("mem1", "ESP32 có bluetooth 5.0", "esp32_bt", status="active", confidence=1.0)
    m2 = create_test_memory("mem2", "Các thư viện BT hoạt động", "bt_lib", status="active", confidence=0.9)
    m3 = create_test_memory("mem3", "App điều khiển robot qua BT", "robot_app", status="active", confidence=0.8)
    
    runtime_harness.put(m1)
    runtime_harness.put(m2)
    runtime_harness.put(m3)
    
    # Tạo liên kết DEPENDS_ON ngược
    # mem3 depends_on mem2 (weight 0.8)
    # mem2 depends_on mem1 (weight 0.9)
    storage.graph.upsert_memory_link(source_id="mem3", target_id="mem2", link_type=RelationType.DEPENDS_ON.value, weight=0.8)
    storage.graph.upsert_memory_link(source_id="mem2", target_id="mem1", link_type=RelationType.DEPENDS_ON.value, weight=0.9)
    
    # Thực hiện ingest một bản ghi mới thay thế cho mem1
    # Điều này sẽ kích hoạt correction và lan truyền giảm điểm cho mem2 và mem3!
    new_mem = create_test_memory("mem1_new", "Đính chính: ESP32 chỉ hỗ trợ bluetooth 4.2 BLE", "esp32_bt", confidence=1.0)
    new_mem.metadata["is_correction"] = True
    new_mem.metadata["corrected_from"] = ["mem1"]
    
    # Đồng bộ hóa FTS5 cho các node hiện tại để search tìm thấy Fact Slot
    runtime_harness.sync_fts()
    
    ingest_engine.ingest(
        content=new_mem.content,
        scope_type="agent",
        scope_id="xiaozhi",
        subject="esp32_bt",
        metadata=new_mem.metadata
    )
    
    # Check mem1 đã bị invalidated (superseded)
    m1_old = storage.get_memory("mem1")
    assert m1_old.status == "superseded"
    
    # Check xem mem2 (depth 1) và mem3 (depth 2) bị hạ confidence theo công thức:
    # delta = correction_delta * (weight ** depth) * 0.7
    # mem2 (depth 1, weight 0.9): delta_raw = 1.0 * (0.9 ** 1) * 0.7 = 0.63 => bị kẹp bởi GRADIENT_CLAMP (0.50)
    #                             => delta_real = -0.50 => new_confidence = 0.9 - 0.5 = 0.40
    # mem3 (depth 2, weight 0.8): delta = 1.0 * (0.8 ** 2) * 0.7 = 0.448 (không bị kẹp)
    #                             => new_confidence = 0.8 - 0.448 = 0.352
    m2_updated = storage.get_memory("mem2")
    m3_updated = storage.get_memory("mem3")
    
    assert m2_updated.confidence == pytest.approx(0.40, abs=0.01)
    assert m3_updated.confidence == pytest.approx(0.352, abs=0.01)
    
    # Kiểm tra xem có 2 bản ghi audit log được tạo trong bảng graph_adjustment_audit
    audits = storage.fetch_all("SELECT * FROM graph_adjustment_audit WHERE source_memory_id = 'mem1' ORDER BY depth ASC")
    assert len(audits) == 2
    
    # Audit 1 (mem2)
    assert audits[0]["target_memory_id"] == "mem2"
    assert audits[0]["relation_type"] == "depends_on"
    assert audits[0]["depth"] == 1
    assert audits[0]["link_weight"] == 0.9
    assert audits[0]["delta"] == pytest.approx(-0.50)
    
    # Audit 2 (mem3)
    assert audits[1]["target_memory_id"] == "mem3"
    assert audits[1]["relation_type"] == "depends_on"
    assert audits[1]["depth"] == 2
    assert audits[1]["link_weight"] == 0.8
    assert audits[1]["delta"] == pytest.approx(-0.448)
