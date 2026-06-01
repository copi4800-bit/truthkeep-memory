"""aegis_py.security.renyi_dp — Rényi Differential Privacy Module.

Implements Rényi Differential Privacy (RDP) budget tracking (Ilya Mironov, Google, 2017),
offering a tighter and more mathematically rigorous privacy analysis for sequential 
memory consolidation/fine-tuning operations compared to classical DP composition.

Classes:
- RenyiPrivacyBudgetTracker: Tracks Rényi privacy expenditure and converts to standard (Epsilon, Delta)-DP.
"""

import math
from typing import List, Tuple, Dict

# Standard default Rényi alpha values to search for the optimal conversion bounds
RDP_DEFAULT_ALPHAS = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 32.0, 64.0]
RDP_DEFAULT_DELTA = 1e-5

__all__ = [
    'RenyiPrivacyBudgetTracker',
]


class RenyiPrivacyBudgetTracker:
    """Rényi Differential Privacy (RDP) Budget Tracker.

    Logs privacy loss per memory access/synthesis step and calculates the 
    overall cumulated privacy budget spent in terms of traditional (Epsilon, Delta)-DP.
    """

    def __init__(self, target_delta: float = RDP_DEFAULT_DELTA):
        """Initialize the budget tracker.

        Args:
            target_delta: The allowed failure probability (default: 1e-5).
        """
        self.delta = target_delta
        # Stores list of logged access steps: each as a dict of {alpha: epsilon_alpha}
        self.rdp_steps: List[Dict[float, float]] = []

    def log_gaussian_access(self, sensitivity: float, noise_std: float) -> None:
        """Log a memory access protected by Gaussian noise and calculate its RDP profile.

        Under Gaussian mechanism, the RDP spent at order alpha is:
        RDP(alpha) = alpha * sensitivity^2 / (2 * noise_std^2)

        Args:
            sensitivity: Maximum L2 change in output caused by 1 record (e.g. salience diff).
            noise_std: Standard deviation of the injected Gaussian noise.
        """
        if noise_std <= 0:
            raise ValueError("Noise standard deviation must be positive")
            
        step_profile = {}
        for alpha in RDP_DEFAULT_ALPHAS:
            # RDP formula for Gaussian Mechanism
            rdp_eps = (alpha * (sensitivity ** 2)) / (2 * (noise_std ** 2))
            step_profile[alpha] = rdp_eps
            
        self.rdp_steps.append(step_profile)

    def log_laplace_access(self, sensitivity: float, scale: float) -> None:
        """Log a memory access protected by Laplace noise.

        Computes RDP bound for the Laplace mechanism.

        Args:
            sensitivity: Sensitivity of the query function.
            scale: Scale parameter of the Laplace distribution.
        """
        if scale <= 0:
            raise ValueError("Laplace scale must be positive")
            
        eps = sensitivity / scale
        step_profile = {}
        for alpha in RDP_DEFAULT_ALPHAS:
            # Analytical RDP bound for Laplace Mechanism
            # RDP(alpha) = 1/(alpha-1) * ln( alpha/(2alpha-1) * e^((alpha-1)eps) + (alpha-1)/(2alpha-1) * e^(-alpha*eps) )
            try:
                term1 = (alpha / (2 * alpha - 1)) * math.exp((alpha - 1) * eps)
                term2 = ((alpha - 1) / (2 * alpha - 1)) * math.exp(-alpha * eps)
                rdp_eps = (1.0 / (alpha - 1)) * math.log(term1 + term2)
            except (OverflowError, ValueError):
                # Fallback bound if exponent overflows
                rdp_eps = alpha * eps
            step_profile[alpha] = rdp_eps
            
        self.rdp_steps.append(step_profile)

    def get_total_spent(self) -> Tuple[float, float]:
        """Convert accumulated RDP steps into standard (Epsilon, Delta)-DP.

        Applies the RDP composition theorem: RDP_total(alpha) = sum(RDP_i(alpha))
        Then searches for the optimal alpha minimizing Epsilon using the relation:
        Epsilon = RDP_total(alpha) + ln(1 / Delta) / (alpha - 1)

        Returns:
            Tuple of (Epsilon, Delta) representing the total privacy budget spent.
        """
        if not self.rdp_steps:
            return 0.0, self.delta
            
        # 1. Sum RDP epsilons for each alpha (RDP linear composition)
        total_rdp: Dict[float, float] = {alpha: 0.0 for alpha in RDP_DEFAULT_ALPHAS}
        for step in self.rdp_steps:
            for alpha in RDP_DEFAULT_ALPHAS:
                total_rdp[alpha] += step.get(alpha, 0.0)
                
        # 2. Convert RDP to standard Epsilon for each alpha, find the minimum
        best_epsilon = float('inf')
        for alpha in RDP_DEFAULT_ALPHAS:
            rdp_at_alpha = total_rdp[alpha]
            # Standard conversion formula
            epsilon = rdp_at_alpha + (math.log(1.0 / self.delta) / (alpha - 1))
            if epsilon < best_epsilon:
                best_epsilon = epsilon
                
        return round(best_epsilon, 6), self.delta

    def is_budget_exceeded(self, limit_epsilon: float) -> bool:
        """Check if the total accumulated privacy budget has exceeded the limit."""
        eps, _ = self.get_total_spent()
        return eps > limit_epsilon

    def clear(self) -> None:
        """Reset the budget tracker history."""
        self.rdp_steps.clear()
