"""Public package surface for TruthKeep Memory."""

from aegis_py.version import get_runtime_version
from .facade import TruthKeep

__version__ = get_runtime_version()

__all__ = ["TruthKeep", "__version__"]
