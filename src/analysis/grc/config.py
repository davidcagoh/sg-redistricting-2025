"""Configuration for the variable-size GRC/SMC ensemble (paper 2).

All config objects are frozen dataclasses. The seat-count vector is
stored as a tuple of (seat_count, num_districts) pairs so that the
district-type composition is fully captured.

2025 actual structure: 15 × SMC(1), 8 × GRC(4), 10 × GRC(5) = 33 districts, 97 seats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class DistrictType:
    """One entry in the seat-count vector."""

    seat_count: int
    num_districts: int

    def __post_init__(self) -> None:
        if self.seat_count < 1:
            raise ValueError(f"seat_count must be >= 1, got {self.seat_count}")
        if self.num_districts < 0:
            raise ValueError(f"num_districts must be >= 0, got {self.num_districts}")


@dataclass(frozen=True)
class GRCConfig:
    """Hyperparameters for a single variable-size GRC/SMC ensemble run.

    district_types encodes the seat-count vector as (seat_count, num_districts) pairs.
    The ordering determines which district IDs get which seat counts:
    districts are numbered 0 … k-1 in the order the types appear.
    """

    district_types: tuple[DistrictType, ...] = (
        # 2025 actual: 15 SMC + 8 four-seat GRC + 10 five-seat GRC
        DistrictType(seat_count=1, num_districts=15),
        DistrictType(seat_count=4, num_districts=8),
        DistrictType(seat_count=5, num_districts=10),
    )
    pop_tolerance: float = 0.10
    seed_pop_tolerance: float = 0.20  # relaxed tolerance used only for seeding
    n_steps: int = 10_000
    burn_in: int = 1_000
    seed: int = 42
    recom_epsilon: float = 0.05
    recom_node_repeats: int = 2
    max_attempts_per_step: int = 100
    run_id: str = ""

    @property
    def k_districts(self) -> int:
        return sum(dt.num_districts for dt in self.district_types)

    @property
    def total_seats(self) -> int:
        return sum(dt.seat_count * dt.num_districts for dt in self.district_types)

    def seat_count_vector(self) -> list[int]:
        """Return a flat list of seat counts, one per district, in district-ID order."""
        result: list[int] = []
        for dt in self.district_types:
            result.extend([dt.seat_count] * dt.num_districts)
        return result

    def seat_counts_by_id(self) -> dict[int, int]:
        """Return mapping district_id → seat_count."""
        vec = self.seat_count_vector()
        return {i: s for i, s in enumerate(vec)}

    @classmethod
    def from_seat_vector(
        cls,
        seat_counts: Sequence[int],
        **kwargs,
    ) -> "GRCConfig":
        """Build a GRCConfig from a flat seat-count sequence.

        Example: from_seat_vector([1]*15 + [4]*8 + [5]*10)
        """
        from collections import Counter

        counts = Counter(seat_counts)
        types = tuple(
            DistrictType(seat_count=s, num_districts=n)
            for s, n in sorted(counts.items())
        )
        return cls(district_types=types, **kwargs)


# ---------------------------------------------------------------------------
# Convenience: 2025 actual plan structure
# ---------------------------------------------------------------------------

SG2025_DISTRICT_TYPES = (
    DistrictType(seat_count=1, num_districts=15),
    DistrictType(seat_count=4, num_districts=8),
    DistrictType(seat_count=5, num_districts=10),
)
