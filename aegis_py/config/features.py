"""aegis_py.config.features — Feature Flags for TruthKeep Mathematical Engines.

Allows dynamic enabling/disabling of individual mathematical core engines
to evaluate their specific impact on overall memory quality and latency
during ablation benchmarking.
"""

import os

# Cờ điều khiển các lõi toán học (có thể override bằng biến môi trường)
ENABLE_FOURIER = os.getenv("TK_ENABLE_FOURIER", "True").lower() == "true"
ENABLE_BAYES = os.getenv("TK_ENABLE_BAYES", "True").lower() == "true"
ENABLE_BELLMAN = os.getenv("TK_ENABLE_BELLMAN", "True").lower() == "true"
ENABLE_BACKPROP = os.getenv("TK_ENABLE_BACKPROP", "True").lower() == "true"
ENABLE_TDA = os.getenv("TK_ENABLE_TDA", "True").lower() == "true"
ENABLE_COMPRESSED_TIER = os.getenv("TK_ENABLE_COMPRESSED_TIER", "True").lower() == "true"

def get_feature_status() -> dict[str, bool]:
    """Returns the current activation status of all mathematical engines."""
    return {
        "fourier": ENABLE_FOURIER,
        "bayes": ENABLE_BAYES,
        "bellman": ENABLE_BELLMAN,
        "backprop": ENABLE_BACKPROP,
        "tda": ENABLE_TDA,
        "compressed_tier": ENABLE_COMPRESSED_TIER,
    }
