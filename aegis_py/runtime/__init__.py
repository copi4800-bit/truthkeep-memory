"""Runtime profile controls for TruthKeep.

This package intentionally does not change TruthKeep's correctness DNA.
It only gates heavy optional engines so MCP/local usage stays fast.
"""

from .profile import (
    PROFILES,
    RuntimeFeatureFlags,
    clear_persisted_profile,
    describe_current_profile,
    get_current_profile,
    get_profile,
    heavy_hot_path_enabled,
    list_profiles,
    persist_profile,
    resolve_profile_name,
)

__all__ = [
    "PROFILES",
    "RuntimeFeatureFlags",
    "clear_persisted_profile",
    "describe_current_profile",
    "get_current_profile",
    "get_profile",
    "heavy_hot_path_enabled",
    "list_profiles",
    "persist_profile",
    "resolve_profile_name",
]
