import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis_py.storage.modern_math import PoincareTDAEngine

text_a = "Mimi is a small blue robotic companion created in Tokyo."
text_b = "Tokyo in created companion robotic blue small a is Mimi"

sig_a = PoincareTDAEngine.compute_persistence_signature(text_a)
sig_b = PoincareTDAEngine.compute_persistence_signature(text_b)
similarity = PoincareTDAEngine.topological_similarity(sig_a, sig_b)

print(f"Sig A: {sig_a}")
print(f"Sig B: {sig_b}")
print(f"Similarity: {similarity}")
