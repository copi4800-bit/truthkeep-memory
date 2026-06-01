"""TruthKeep Runtime Profiles / Performance Modes.

The profile layer is a dispatcher for optional heavy engines.  It never turns off
TruthKeep's core DNA: graph governance, correction, superseded suppression,
why-not provenance, and invariant enforcement.

Priority order for choosing a profile:
1. TK_RUNTIME_PROFILE environment variable.
2. Persisted user profile in ``~/.truthkeep/runtime_profile.json``.
3. ``local`` default.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

RuntimeProfileName = Literal["demo", "local", "hardened", "enterprise"]


@dataclass(frozen=True)
class RuntimeFeatureFlags:
    profile_name: RuntimeProfileName
    description: str
    # Optional/cold-path engines.  These can change by profile.
    enable_fhe_simulator: bool
    enable_pqc_simulator: bool
    enable_rsa_toy: bool
    enable_tda_signature: bool
    enable_strict_privacy: bool
    enable_fast_crypto_backend: str  # "none", "auto", "required"
    enable_scoped_db_sharding: bool
    enable_profile_benchmarking: bool
    # TruthKeep DNA. These are intentionally always True.
    enable_graph_governance: bool = True
    enable_memory_correction: bool = True
    enable_superseded_suppression: bool = True
    enable_why_not: bool = True
    enable_invariants: bool = True
    # Hot-path guidance for code paths and docs.
    hot_path_policy: str = "core_only"
    cold_path_policy: str = "manual_or_background"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROFILES: dict[str, RuntimeFeatureFlags] = {
    "demo": RuntimeFeatureFlags(
        profile_name="demo",
        description="Fast demo/test mode. Toy math may run, heavy simulators stay out of hot path.",
        enable_fhe_simulator=False,
        enable_pqc_simulator=False,
        enable_rsa_toy=True,
        enable_tda_signature=False,
        enable_strict_privacy=False,
        enable_fast_crypto_backend="none",
        enable_scoped_db_sharding=False,
        enable_profile_benchmarking=True,
        hot_path_policy="fast_demo",
    ),
    "local": RuntimeFeatureFlags(
        profile_name="local",
        description="Default local MCP mode. Correctness-first memory with fast hot path.",
        enable_fhe_simulator=False,
        enable_pqc_simulator=False,
        enable_rsa_toy=False,
        enable_tda_signature=False,
        enable_strict_privacy=False,
        enable_fast_crypto_backend="auto",
        enable_scoped_db_sharding=False,
        enable_profile_benchmarking=True,
        hot_path_policy="mcp_fast_core",
    ),
    "hardened": RuntimeFeatureFlags(
        profile_name="hardened",
        description="Strict local privacy/security candidate. Heavy engines may run in protected/cold paths.",
        enable_fhe_simulator=True,
        enable_pqc_simulator=True,
        enable_rsa_toy=False,
        enable_tda_signature=True,
        enable_strict_privacy=True,
        enable_fast_crypto_backend="auto",
        enable_scoped_db_sharding=False,
        enable_profile_benchmarking=True,
        hot_path_policy="privacy_first",
        cold_path_policy="allowed_when_requested",
    ),
    "enterprise": RuntimeFeatureFlags(
        profile_name="enterprise",
        description="Throughput profile for many agents/scopes. Heavy simulators are bypassed in hot path.",
        enable_fhe_simulator=False,
        enable_pqc_simulator=False,
        enable_rsa_toy=False,
        enable_tda_signature=False,
        enable_strict_privacy=False,
        enable_fast_crypto_backend="auto",
        enable_scoped_db_sharding=True,
        enable_profile_benchmarking=True,
        hot_path_policy="throughput_first",
    ),
}


def truthkeep_config_root() -> Path:
    return Path(os.environ.get("TRUTHKEEP_CONFIG_DIR", str(Path.home() / ".truthkeep"))).expanduser()


def profile_config_path() -> Path:
    return truthkeep_config_root() / "runtime_profile.json"


def list_profiles() -> list[str]:
    return list(PROFILES.keys())


def resolve_profile_name(name: str | None) -> RuntimeProfileName:
    candidate = (name or "local").strip().lower().replace("_", "-")
    aliases = {
        "default": "local",
        "easy": "local",
        "fast": "local",
        "secure": "hardened",
        "strict": "hardened",
        "production": "enterprise",
        "throughput": "enterprise",
    }
    candidate = aliases.get(candidate, candidate)
    if candidate not in PROFILES:
        raise ValueError(f"Unknown TruthKeep runtime profile: {name!r}. Supported: {', '.join(PROFILES)}")
    return candidate  # type: ignore[return-value]


def get_profile(name: str) -> RuntimeFeatureFlags:
    return PROFILES[resolve_profile_name(name)]


def _read_persisted_profile() -> str | None:
    path = profile_config_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("profile")
    except Exception:
        return None


def get_current_profile() -> RuntimeFeatureFlags:
    env_value = os.environ.get("TK_RUNTIME_PROFILE")
    if env_value:
        return get_profile(env_value)
    persisted = _read_persisted_profile()
    if persisted:
        return get_profile(persisted)
    return PROFILES["local"]


def persist_profile(profile_name: str) -> dict[str, Any]:
    resolved = resolve_profile_name(profile_name)
    path = profile_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "profile": resolved,
        "note": "Set by `truthkeep profile set`. TK_RUNTIME_PROFILE environment variable overrides this file.",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(path), "profile": resolved, "flags": PROFILES[resolved].to_dict()}


def clear_persisted_profile() -> dict[str, Any]:
    path = profile_config_path()
    if path.exists():
        path.unlink()
        return {"ok": True, "cleared": True, "path": str(path), "profile": get_current_profile().profile_name}
    return {"ok": True, "cleared": False, "path": str(path), "profile": get_current_profile().profile_name}


def describe_current_profile() -> dict[str, Any]:
    flags = get_current_profile()
    return {
        "active_profile": flags.profile_name,
        "source": "env" if os.environ.get("TK_RUNTIME_PROFILE") else "persisted_or_default",
        "config_path": str(profile_config_path()),
        "flags": flags.to_dict(),
        "dna_enforced": {
            "graph_governance": flags.enable_graph_governance,
            "memory_correction": flags.enable_memory_correction,
            "superseded_suppression": flags.enable_superseded_suppression,
            "why_not": flags.enable_why_not,
            "invariants": flags.enable_invariants,
        },
    }


def heavy_hot_path_enabled() -> bool:
    """Return True only when the operator explicitly allows heavy simulators in MCP hot paths.

    Hardened/research profiles may *allow* heavy engines, but normal MCP calls
    should not pay that cost unless this explicit escape hatch is enabled.
    """
    return os.environ.get("TK_ALLOW_HEAVY_HOT_PATH", "").strip().lower() in {"1", "true", "yes", "on"}
