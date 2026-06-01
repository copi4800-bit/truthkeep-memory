from __future__ import annotations

import json
import os
from pathlib import Path

from aegis_py.runtime.profile import PROFILES, describe_current_profile, get_current_profile, persist_profile, clear_persisted_profile
from aegis_py.security.config import SecurityConfig


def test_runtime_profiles_keep_truthkeep_dna_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUTHKEEP_CONFIG_DIR", str(tmp_path))
    for name, flags in PROFILES.items():
        monkeypatch.setenv("TK_RUNTIME_PROFILE", name)
        active = get_current_profile()
        assert active.profile_name == name
        assert active.enable_graph_governance is True
        assert active.enable_memory_correction is True
        assert active.enable_superseded_suppression is True
        assert active.enable_why_not is True
        assert active.enable_invariants is True


def test_profile_persistence_and_clear(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUTHKEEP_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("TK_RUNTIME_PROFILE", raising=False)
    result = persist_profile("enterprise")
    assert result["ok"] is True
    assert get_current_profile().profile_name == "enterprise"
    payload = describe_current_profile()
    assert payload["active_profile"] == "enterprise"
    clear_persisted_profile()
    assert get_current_profile().profile_name == "local"


def test_security_config_follows_runtime_profile(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUTHKEEP_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("TK_RUNTIME_PROFILE", "hardened")
    assert SecurityConfig.fhe_simulator_enabled() is True
    assert SecurityConfig.tda_signature_enabled() is True
    assert SecurityConfig.strict_privacy_enabled() is True
    monkeypatch.setenv("TK_RUNTIME_PROFILE", "local")
    assert SecurityConfig.fhe_simulator_enabled() is False
    assert SecurityConfig.tda_signature_enabled() is False
